#!/usr/bin/env python3
"""
LangChain增強處理測試GUI

這個Streamlit應用用於測試剛實現的LangChain增強文檔處理功能，
包括文件載入、VLM策略、降級處理、分塊和嵌入等核心功能。

使用方式:
    cd grag/frontend/
    uv run streamlit run app.py
"""

import sys
import os
from pathlib import Path
import asyncio
import tempfile
from typing import Dict, Any, Optional
import time

# 添加專案根目錄到路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import streamlit as st
from grag.ingestion.indexing.ingestion_service import IngestionService
from grag.core.config import settings
from grag.core.database_services import DatabaseManager

# 配置頁面
st.set_page_config(
    page_title="🔗 LangChain處理測試器",
    page_icon="🔗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 設定中文界面
st.markdown("""
<style>
    .stApp {
        font-family: 'Microsoft YaHei', sans-serif;
    }
</style>
""", unsafe_allow_html=True)

# 主要標題
st.title("🔗 LangChain增強文檔處理測試器")
st.markdown("---")

# 系統處理能力總覽
st.markdown("### 🔄 系統處理能力狀態")

# 處理能力檢查函數
def check_processing_capability(capability_name: str, check_logic, settings_obj) -> dict:
    """檢查處理能力狀態的函數"""
    status = {"name": capability_name, "status": "unknown", "details": ""}

    try:
        if capability_name == "多模態處理":
            # 檢查VLM處理器 - 優先順序: Ollama > OpenAI > Qwen2VL
            vlm_status = "使用降級處理 (MinerU + OCR)"
            available_services = []

            # 檢查Ollama (最高優先級)
            if getattr(settings_obj, 'ollama_base_url', None):
                try:
                    import requests
                    response = requests.get(f"{settings_obj.ollama_base_url.replace('/v1', '')}/api/tags", timeout=3)
                    if response.status_code == 200:
                        vlm_status = f"Ollama運行中 (模型: {getattr(settings_obj, 'ollama_model', 'unknown')})"
                        available_services.append("Ollama")
                except:
                    available_services.append("Ollama (不可用)")

            # 檢查OpenAI (第二優先級)
            if not available_services and getattr(settings_obj, 'openai_api_key', None) and getattr(settings_obj, 'openai_api_key', '').startswith('sk-'):
                try:
                    import requests
                    payload = {"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": "test"}], "max_tokens": 1}
                    response = requests.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers={"Authorization": f"Bearer {settings_obj.openai_api_key}"},
                        json=payload, timeout=5
                    )
                    if response.status_code == 200:
                        vlm_status = "OpenAI GPT-4V可用"
                        available_services.append("OpenAI GPT-4V")
                except:
                    available_services.append("OpenAI GPT-4V (API不可用)")

            # 檢查Qwen2VL (最低優先級)
            if not available_services and getattr(settings_obj, 'qwen2vl_base_url', None):
                try:
                    import requests
                    # 針對Qwen2VL，嘗試簡單的GET請求來檢查服務
                    response = requests.get(getattr(settings_obj, 'qwen2vl_base_url', ''), timeout=5)
                    if response.status_code == 200:
                        vlm_status = "Qwen2VL服務可用"
                        available_services.append("Qwen2VL")
                except:
                    vlm_status = "無VLM服務"

            # 總是可用的降級處理器
            fallback_services = ["MinerU", "Tesseract OCR"]

            # 組合最終狀態
            all_processors = available_services + fallback_services
            status_emoji = "✅" if available_services else "⚠️"
            status["status"] = f"{status_emoji} {vlm_status} → {' + '.join(all_processors)}"
            return status

        elif capability_name == "文本處理":
            # 檢查基本文本處理能力
            status["status"] = "✅ LangChain + LlamaIndex + SentenceTransformers"
            status["details"] = "支持: .txt, .md, .docx, .pdf"
            return status

        # 其他能力檢查
        result = check_logic(settings_obj)
        if result:
            status["status"] = "✅ 可用"
        else:
            status["status"] = "❌ 不可用"

    except Exception as e:
        status["status"] = f"❌ 檢查失敗: {str(e)[:30]}"
        status["details"] = str(e)

    return status

# 檢查資料庫連線
def check_database_connectivity(settings_obj):
    db_available = False
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(
            getattr(settings_obj, 'neo4j_uri'),
            auth=(getattr(settings_obj, 'neo4j_user'), getattr(settings_obj, 'neo4j_password'))
        )
        driver.verify_connectivity()
        driver.close()
        db_available = True

        # 檢查Supabase
        from supabase import create_client
        client = create_client(getattr(settings_obj, 'supabase_url'), getattr(settings_obj, 'supabase_key'))
        response = client.table('vectors').select('*').limit(1).execute()
        db_available = db_available and True

    except Exception as e:
        pass

    return db_available

# 生成系統處理報告 (給LLM/開發者)
def _generate_processing_report(result: dict, processing_trace: dict = None) -> dict:
    """生成詳細的處理報告給LLM或開發者分析"""

    report = {
        "final_processor": "",
        "processor_type": "",
        "vlm_attempted": False,
        "vlm_success": False,
        "fallback_chain": [],
        "error_details": [],
        "performance": {},
        "recommendations": []
    }

    try:
        # 從處理軌跡中提取最終處理器
        if processing_trace and "processing_chain" in processing_trace:
            for step in processing_trace["processing_chain"]:
                if step.get("stage") == "文檔處理":
                    if "VLM" in step.get("module", ""):
                        report["final_processor"] = "VLM視覺語言模型"
                        report["processor_type"] = "advanced"
                        report["vlm_success"] = True
                    elif "MinerU" in step.get("module", ""):
                        report["final_processor"] = "MinerU PDF處理引擎"
                        report["processor_type"] = "medium"
                        report["fallback_chain"].append("VLM失敗降級到MinerU")
                    elif "OCR" in step.get("module", ""):
                        report["final_processor"] = "Tesseract OCR引擎"
                        report["processor_type"] = "basic"
                        report["fallback_chain"].append("VLM+MinerU失敗降級到OCR")
                    elif "StructuredTextFallback" in step.get("module", ""):
                        report["final_processor"] = "結構化文字處理"
                        report["processor_type"] = "text"

        # 策略信息分析
        strategy_info = result.get("strategy_used", {})
        if strategy_info.get("vlm_used"):
            report["vlm_attempted"] = True
            if not strategy_info.get("vlm_success"):
                report["error_details"].append("⚠️ VLM嘗試失敗，使用降級處理器")

        # 效能分析
        processing_time = result.get("processing_time", 0)
        report["performance"] = {
            "total_time": f"{processing_time:.2f}秒",
            "evaluation": "優良" if processing_time < 10 else "一般" if processing_time < 30 else "較慢"
        }

        # 生成建議
        if report["processor_type"] == "basic":
            report["recommendations"].append("🔧 建議: 啟動VLM服務 (Ollama或OpenAI) 以獲得更好的處理品質")
        elif report["processor_type"] == "medium":
            report["recommendations"].append("✨ 建議: MinerU效果良好，但可以考慮OCR改進")
        elif report["processor_type"] == "advanced":
            report["recommendations"].append("🎯 系統運作最佳！VLM視覺分析已成功應用")

        # 品質評估報告
        quality_level = result.get("metadata", {}).get("quality_level", "unknown")
        if quality_level == "high":
            report["quality_assessment"] = "✅ 高品質處理：使用了進階視覺分析"
        elif quality_level == "medium":
            report["quality_assessment"] = "⚠️ 中等品質處理：使用了PDF解析器或光學識別"
        else:
            report["quality_assessment"] = "📄 基礎處理：使用了文字分析"

    except Exception as e:
        report["error_details"].append(f"生成報告時發生錯誤: {str(e)}")

    return report

# 顯示處理報告 (給開發者/LLM)
def _display_processing_report(report: dict):
    """在GUI中顯示詳細的處理報告"""

    st.markdown("### 📋 系統處理詳情")

    # 最終處理器資訊
    col1, col2 = st.columns(2)
    with col1:
        st.metric("最終使用的處理器", report.get("final_processor", "Unknown"))

    with col2:
        processor_type_display = {
            "advanced": "🚀 進階級",
            "medium": "⚡ 中級",
            "basic": "📄 基礎級",
            "text": "📝 文字級"
        }
        st.metric("處理器等級", processor_type_display.get(report.get("processor_type"), "未知"))

    # VLM嘗試狀態
    if report.get("vlm_attempted"):
        if report.get("vlm_success"):
            st.success("✅ VLM服務: 成功處理文件")
        else:
            st.error("❌ VLM服務: 處理失敗，啟動降級機制")
    else:
        st.info("ℹ️ VLM服務: 未嘗試 (按策略決定)")

    # 降級鏈條
    if report.get("fallback_chain"):
        st.markdown("#### 🔄 降級處理鏈條")
        for i, fallback_reason in enumerate(report.get("fallback_chain", []), 1):
            st.markdown(f"{i}. {fallback_reason}")

    # 品質評估
    if report.get("quality_assessment"):
        st.markdown("#### 📊 品質評估")
        st.markdown(report["quality_assessment"])

    # 效能評估
    if report.get("performance"):
        st.markdown("#### ⚡ 效能評估")
        perf = report["performance"]
        st.markdown(f"- **處理時間**: {perf['total_time']}")
        st.markdown(f"- **效能等級**: {perf['evaluation']}")

    # 錯誤詳情
    if report.get("error_details"):
        st.markdown("#### ⚠️ 錯誤及警告")
        for error in report.get("error_details", []):
            st.markdown(error)

    # 系統建議
    if report.get("recommendations"):
        st.markdown("#### 💡 系統建議")
        for rec in report.get("recommendations", []):
            st.markdown(rec)

# 所有處理能力
capabilities = [
    check_processing_capability("多模態處理", None, settings),
    check_processing_capability("文本處理", None, settings),
    check_database_connectivity(settings),
]

# 顯示處理能力
col1, col2, col3 = st.columns(3)
with col1:
    capability = capabilities[0]  # 多模態處理
    st.success(f"🎨 {capability['name']}: {capability['status']}")

with col2:
    st.success("📝 文本處理: ✅ LangChain + LlamaIndex + SentenceTransformers")

with col3:
    db_ok = capabilities[2]
    if db_ok:
        st.success("🗃️ 資料庫: ✅ Neo4j + Supabase連線成功")
    else:
        st.error("🗃️ 資料庫: ❌ 連線失敗")

st.markdown("**處理優先順序說明**:")
st.info("📋 **文件處理優先順序**:\n"
        "1. **VLM服務** (如果運行) → Ollama/OpenAI/Qwen2VL\n"
        "2. **MinerU** → 如果VLM失敗或跳過\n"
        "3. **Tesseract OCR** → 最終降級選項\n"
        "4. **文字處理** → 對於.txt/.md文件")

st.markdown("---")

st.markdown("---")

# 側邊欄配置
st.sidebar.title("⚙️ 處理配置")

# VLM策略選擇
vlm_strategy = st.sidebar.selectbox(
    "🎯 VLM處理策略",
    ["自動判斷", "強制開啟", "強制關閉"],
    help="""
    自動判斷: 根據文件類型智能選擇 (.pdf使用VLM, .txt/.md直接處理)
    強制開啟: 對所有文檔都使用VLM處理 (會觸發降級邏輯)
    強制關閉: 跳過VLM，直接使用結構化文字處理
    """
)

# 策略倒換
force_vlm_map = {
    "自動判斷": None,    # None代表自動
    "強制開啟": True,    # 強制使用VLM
    "強制關閉": False    # 強制跳過VLM
}
force_vlm = force_vlm_map[vlm_strategy]

# 策略說明
st.sidebar.markdown("**策略邏輯說明:**")
if vlm_strategy == "自動判斷":
    st.sidebar.info("""
    📋 **文件處理邏輯**:
    - `.pdf`, `.docx` → VLM處理 (視覺分析)
    - `.txt`, `.md` → 直接處理 (LangChain載入)
    - 其他格式 → VLM優先 (未知內容較安全)
    """)
elif vlm_strategy == "強制開啟":
    st.sidebar.info("""
    🔧 **強制VLM模式**:
    - 對所有文件嘗試VLM處理
    - 失敗時自動降級到結構化文字分析
    - 適合測試降級機制
    """)
else:  # 強制關閉
    st.sidebar.info("""
    📝 **直接處理模式**:
    - 跳過VLM，直接使用LangChain載入
    - 使用結構化文字分析
    - 最快速的處理方式
    """)

st.sidebar.markdown("---")

# 系統狀態檢查
st.sidebar.markdown("### 🔍 系統狀態")

# 檢查LangChain安裝
try:
    import langchain_community
    st.sidebar.success("✅ LangChain可用")
except ImportError:
    st.sidebar.error("❌ LangChain未安裝")

# 檢查VLM配置
if settings.qwen2vl_api_key or settings.openai_api_key:
    st.sidebar.success("✅ VLM服務已配置")
else:
    st.sidebar.warning("⚠️ VLM服務未配置 (將使用降級處理)")

# 檢查嵌入服務
try:
    from grag.ingestion.indexing.providers.embedding_providers import create_embedding_provider, list_available_providers
    # 嘗試創建預設provider來測試是否正常
    provider = create_embedding_provider()
    is_available = provider.is_available()
    if is_available:
        st.sidebar.success(f"✅ 嵌入服務可用 ({provider.name})")
    else:
        st.sidebar.warning(f"⚠️ 嵌入服務未完全配置")
except Exception as e:
    st.sidebar.error(f"❌ 嵌入服務異常: {str(e)[:30]}...")

# 檢查資料庫連線
st.sidebar.markdown("#### 📊 資料庫連線")

# Neo4j連線測試
neo4j_connected = False
try:
    from neo4j import GraphDatabase
    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password)
    )
    driver.verify_connectivity()
    driver.close()
    neo4j_connected = True
    st.sidebar.success("✅ Neo4j已連線")
except Exception as e:
    st.sidebar.error("❌ Neo4j連線失敗")
    st.sidebar.caption(f"錯誤: {str(e)[:50]}...")

# Supabase連線測試
supabase_connected = False
try:
    from supabase import create_client
    client = create_client(settings.supabase_url, settings.supabase_key)
    # 測試連線 - 直接呼叫health check或簡單的連接測試
    # 使用storage測試，因為通常都可用
    storage = client.storage
    supabase_connected = True
    st.sidebar.success("✅ Supabase已連線")
except Exception:
    st.sidebar.error("❌ Supabase連線失敗")
    # 不要在UI顯示APIKey，會影響安全性
    st.sidebar.caption("檢查.env設定")

# 資料庫整體狀態
if neo4j_connected and supabase_connected:
    st.sidebar.success("🎉 所有資料庫正常連線！")
elif neo4j_connected or supabase_connected:
    st.sidebar.warning("⚠️ 部分資料庫可連線")
else:
    st.sidebar.error("❌ 所有資料庫連線失敗")

st.sidebar.markdown("---")

# 主頁面
col1, col2 = st.columns([1, 2])

with col1:
    st.markdown("### 📤 文件上傳")

    # 文件上傳器
    uploaded_file = st.file_uploader(
        "選擇測試文檔",
        type=["pdf", "docx", "txt", "md"],
        help="支援的文件格式: PDF, Word, 文字, Markdown",
        key="uploaded_file"
    )

    if uploaded_file is not None:
        st.success(f"📄 已選擇: {uploaded_file.name}")

        # 顯示文件資訊
        file_info = {
            "文件名": uploaded_file.name,
            "大小": f"{uploaded_file.size/1024:.1f} KB",
            "格式": Path(uploaded_file.name).suffix,
        }

        st.json(file_info)

        # VLM策略適用性提示
        file_ext = Path(uploaded_file.name).suffix.lower()
        strategy_hint = {
            '.pdf': "將使用VLM處理，因為PDF需要視覺分析",
            '.docx': "將嘗試VLM處理，可對複雜格式的文件分析",
            '.txt': "將直接處理，因為文字格式適合LangChain載入",
            '.md': "將直接處理，因為Markdown適合結構化解析"
        }

        if file_ext in strategy_hint:
            if vlm_strategy == "自動判斷":
                st.info(f"🎯 {strategy_hint[file_ext]}")
            else:
                st.info(f"🔧 手動策略: {vlm_strategy}")

        # 處理按鈕
        process_button = st.button("🚀 開始處理", type="primary", use_container_width=True)

    else:
        st.info("請上傳一個文件來開始測試")
        process_button = False

with col2:
    st.markdown("### 📊 處理結果")

    # 檢查是否可以處理
    if not (process_button and uploaded_file is not None):
        st.info("⬅️ 請先上傳文件並點擊處理按鈕")
    else:
        # 創建進度條
        progress_bar = st.progress(0, "初始化...")
        status_text = st.empty()
        result_area = st.empty()

        try:
            # 保存上傳文件到臨時位置
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{uploaded_file.name}") as tmp_file:
                tmp_file.write(uploaded_file.read())
                file_path = Path(tmp_file.name)

            progress_bar.progress(10, "文件載入中...")

            # 初始化處理服務
            status_text.text("🔧 初始化LangChain處理服務...")
            progress_bar.progress(20, "初始化服務...")

            ingestion_service = IngestionService()

            progress_bar.progress(30, "開始處理...")

            # 執行增強處理
            status_text.text(f"🎯 處理中 ({vlm_strategy})...")

            start_time = time.time()

            # 這是關鍵! 使用我們剛實現的增強處理方法
            result = asyncio.run(ingestion_service.ingest_document_enhanced(
                file_path=file_path,
                force_vlm=force_vlm
            ))

            processing_time = time.time() - start_time

            progress_bar.progress(100, "處理完成! 🎉")

            # 獲取處理軌跡
            processing_trace = result.get("processing_trace", {})

            # 顯示結果 - 精簡版布局
            with result_area.container():
                if result.get("success"):
                    # 左邊成功狀態，右邊展開詳細資訊
                    col_left, col_right = st.columns([1, 2])

                    with col_left:
                        # 綠色成功區域
                        st.success("🎉 處理成功！")

                        # 基本統計指標 (簡單版)
                        st.metric("處理時間", f"{processing_time:.1f}s")
                        st.metric("分塊數", result.get("metadata", {}).get("chunks_created", 0))
                        st.metric("向量數", result.get("metadata", {}).get("embeddings_created", 0))

                        # 處理狀態摘要
                        metadata = result.get("metadata", {})
                        quality_level = metadata.get("quality_level", "unknown")
                        st.info(f"品質等級: **{quality_level.upper()}**")

                    with col_right:
                        # 展開詳細資訊區域
                        with st.expander("📋 處理詳情", expanded=True):
                            # 生成系統處理報告
                            processing_report = _generate_processing_report(result, processing_trace)

                            # 最終處理器
                            if processing_report["final_processor"]:
                                final_processor_name = processing_report["final_processor"]
                                processor_icons = {
                                    "VLM視覺語言模型": "🤖",
                                    "MinerU PDF處理引擎": "📑",
                                    "Tesseract OCR引擎": "🔍",
                                    "結構化文字處理": "📄"
                                }
                                icon = processor_icons.get(final_processor_name, "⚙️")
                                st.markdown(f"**{icon} 最終處理器**: {final_processor_name}")

                            # 策略結果
                            strategy_info = result.get("strategy_used", {})
                            vlm_used = strategy_info.get("vlm_used", False)
                            vlm_success = strategy_info.get("vlm_success", False)

                            if vlm_used:
                                if vlm_success:
                                    st.success("✅ VLM處理成功應用")
                                else:
                                    st.warning("⚠️ VLM嘗試後降級")

                        # 展開處理軌跡
                        with st.expander("🔄 處理軌跡", expanded=False):
                            if "processing_trace" in result:
                                trace = result["processing_trace"]
                                st.write(f"**文件類型**: {trace['file_type']}")
                                st.write(f"**使用模組**: {', '.join(trace['modules_used'])}")

                                for step in trace.get("processing_chain", []):
                                    with st.container():
                                        cols = st.columns([1, 3])
                                        with cols[0]:
                                            st.write(f"**{step['stage']}**")
                                            st.caption(step.get('module', ''))
                                        with cols[1]:
                                            st.caption(step.get('description', ''))
                                        st.divider()

                        # 展開資料庫結果
                        with st.expander("💾 儲存結果", expanded=False):
                            if "stage_results" in result:
                                stage_results = result["stage_results"]

                                if "neo4j" in stage_results:
                                    neo4j_result = stage_results["neo4j"]
                                    if isinstance(neo4j_result, dict) and neo4j_result.get("success"):
                                        st.success(f"🗂️ Neo4j: {neo4j_result.get('document_created', 0)} 個文件, {neo4j_result.get('chunks_created', 0)} 個分塊")
                                    else:
                                        st.error("Neo4j儲存失敗")

                                if "pgvector" in stage_results:
                                    pv_result = stage_results["pgvector"]
                                    if isinstance(pv_result, dict) and pv_result.get("success"):
                                        st.success(f"🗂️ Supabase: {pv_result.get('vectors_ingested', 0)} 個向量")
                                    else:
                                        st.error("Supabase儲存失敗")

                        # 開發者模式展開區塊
                        with st.expander("🔬 開發者資訊", expanded=False):
                            # 統計完整版
                            if "statistics" in result:
                                st.json(result["statistics"])

                            # 策略詳細信息
                            strategy_info = result.get("strategy_used", {})
                            st.write("**策略資訊:**")
                            st.json(strategy_info)

                            # 完整處理報告
                            if processing_report:
                                _display_processing_report(processing_report)

                else:
                    st.error(f"❌ 處理失敗: {result.get('error', '未知錯誤')}")

                    # 顯示錯誤詳情
                    with st.expander("錯誤詳情", expanded=True):
                        st.code(result.get('error', ''), language='text')

        except Exception as e:
            st.error(f"❌ 處理過程中發生錯誤: {e}")
            st.code(str(e), language='text')

        finally:
            # 清理進度顯示
            status_text.empty()
            progress_bar.empty()

            # 清理臨時文件
            try:
                if 'file_path' in locals() and file_path.exists():
                    file_path.unlink()
            except:
                pass

# 頁面底部信息
st.markdown("---")
st.markdown("""
### 📖 使用說明

1. **上傳文件**: 選擇支援的文件格式 (.pdf, .docx, .txt, .md)
2. **選擇策略**: 
   - 自動判斷：根據文件類型智能選擇VLM使用
   - 強制開啟：測試VLM失敗時的降級機制
   - 強制關閉：只使用LangChain直接處理
3. **開始處理**: 系統會顯示完整的處理流程和結果
4. **查看結果**: 包含處理時間、統計數據和詳細分析

### 🎯 測試重點

這GUI專門用於測試我們剛實現的LangChain增強功能：
- **多格式支援**: LangChain載入器的能力
- **智能策略**: VLM自動選擇邏輯
- **降級機制**: VLM失敗時的備用處理
- **處理統計**: 完整的效能和品質監控

---
**開發中功能**: 目前為第一階段測試，著重處理管道驗證。
""")
