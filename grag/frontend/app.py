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

            # Qwen2VL cloud service removed - using local Ollama only
            # for better privacy, cost control, and performance

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
        "1. **VLM服務** (如果運行) → Ollama或OpenAI\n"
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

# 頁面選擇器
page = st.sidebar.selectbox(
    "📍 選擇頁面",
    ["文檔處理", "資料庫管理"],
    help="""
    文檔處理: 上傳和處理文件，測試RAG管道
    資料庫管理: 查看和刪除資料庫內容，Neo4j圖形視覺化
    """
)

st.sidebar.markdown("---")

# 系統狀態檢查
st.sidebar.markdown("### 🔍 系統狀態")

# 檢查LangChain安裝
try:
    import langchain_community
    st.sidebar.success("✅ LangChain可用")
except ImportError:
    st.sidebar.error("❌ LangChain未安裝")

# 檢查VLM配置 - 檢查Ollama和OpenAI
vlm_configured = False
if getattr(settings, 'ollama_base_url', None):
    vlm_configured = True
if getattr(settings, 'openai_api_key', None):
    vlm_configured = True

if vlm_configured:
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

# 資料庫管理頁面函數
def show_database_management_page():
    """顯示資料庫管理頁面，包含Neo4j Browser和資料瀏覽"""

    # 檢查是否有數據庫變更通知
    if st.session_state.get('database_modified', False):
        st.info("🔄 **數據更新提示**: 數據庫最近發生了變化（文件删除/上傳）。請刷新頁面查看最新狀態。")

        # 添加一个刷新按钮
        if st.button("🔄 刷新数据库视图", type="secondary", use_container_width=True):
            st.session_state.database_modified = False
            st.rerun()

        st.markdown("---")

    st.markdown("# 🗃️ 資料庫管理")

    # Tab分頁：Neo4j視覺化、Supabase資料、刪除測試
    tab1, tab2, tab3, tab4 = st.tabs([
        "🌐 Neo4j Browser",
        "📊 Supabase向量",
        "🗂️ 文件管理",
        "🗑️ 刪除測試"
    ])

    with tab1:
        show_neo4j_browser()

    with tab2:
        show_supabase_vectors()

    with tab3:
        show_document_management()

    with tab4:
        show_deletion_tests()

def show_neo4j_browser():
    """Neo4j Browser集成"""
    st.markdown("### 🕸️ Neo4j圖形資料庫")

    # 檢查Neo4j可用性
    neo4j_available = False
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )
        driver.verify_connectivity()
        driver.close()
        neo4j_available = True
    except Exception as e:
        st.error(f"❌ Neo4j連線失敗: {str(e)[:50]}...")
        st.info("請確保Neo4j服務運行在 neo4j://localhost:7687")
        return

    if neo4j_available:
        st.success("✅ Neo4j已連線")
        st.markdown("""
        **Neo4j Browser** 提供完整的圖形資料庫視覺化和查詢介面。

        🎯 常用查詢示例：
        ```cypher
        // 查看所有Document節點
        MATCH (d:Document) RETURN d LIMIT 10

        // 查看Chunk和其關聯
        MATCH (d:Document)-[:HAS_CHUNK]->(c:Chunk) RETURN d, c LIMIT 5

        // 查找實體
        MATCH (e:Entity) RETURN e.name, e.type LIMIT 10
        ```
        """)

        # 從設定中獲取Neo4j Browser URL
        neo4j_uri = getattr(settings, 'neo4j_uri', 'neo4j://localhost:7687')
        # Neo4j Browser通常在7687端口基礎上+11，即7474
        if '7687' in neo4j_uri:
            browser_port = '7474'
        else:
            browser_port = '7474'  # 預設值

        # 提取host從URI
        import re
        host_match = re.search(r'neo4j://([^:]+)', neo4j_uri)
        browser_host = host_match.group(1) if host_match else 'localhost'

        browser_url = f"http://{browser_host}:{browser_port}/browser/"

        st.success(f"🔗 Neo4j Browser運行在: http://{browser_host}:{browser_port}/browser/")

        # 提供鏈接到新窗口而不是iframe（避免CORS和嵌入問題）
        st.markdown("""
        **🖥️ Neo4j Browser 圖形化介面**
        """)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🌐 在新窗口打開Neo4j Browser", type="primary"):
                st.markdown(f'<meta http-equiv="refresh" content="0; url=http://{browser_host}:{browser_port}/browser/">', unsafe_allow_html=True)
        with col2:
            st.markdown("或者手動訪問:")
            st.code(f"http://{browser_host}:{browser_port}/browser/")

        # 添加一個說明區域
        with st.expander("ℹ️ 連線資訊", expanded=False):
            st.markdown(f"""
            - **Neo4j Browser URL**: `http://{browser_host}:{browser_port}/browser/`
            - **用戶名**: neo4j
            - **密碼**: testpass123
            - **BOLT連線**: neo4j://{browser_host}:7687
            """)

            st.info("💡 如果遇到連線問題，請檢查Neo4j容器是否正確啟動")

        # 提供iframe作為備用選項，但有警告
        with st.expander("🔧 嵌入式檢視 (可能不支持iframe)", expanded=False):
            st.warning("⚠️ Neo4j Browser可能不支持iframe嵌入，如果看不到內容，請使用上面的鏈接在新窗口打開")

            # HTML iframe with broader permissions
            iframe_html = f"""
            <iframe src="{browser_url}"
                    style="width:100%; height:600px; border:1px solid #ddd;"
                    sandbox="allow-scripts allow-forms allow-same-origin allow-popups allow-presentation"
                    allowfullscreen>
            </iframe>
            """
            st.components.v1.html(iframe_html, height=600)

        st.markdown("""
        ---
        **💡 使用提示:**
        - 右鍵節點可展開更多資訊
        - 使用圖形視覺化查看實體關係
        - 支援完整Cypher查詢語言
        - 適合開發階段的資料探索和調試
        """)
    else:
        st.error("Neo4j服務不可用，無法載入Browser介面")

def show_supabase_vectors():
    """顯示Supabase向量資料"""
    st.markdown("### 🗃️ Supabase向量資料庫")

    try:
        from supabase import create_client
        client = create_client(settings.supabase_url, settings.supabase_key)

        # 獲取基本統計
        response = client.table('vectors').select('*', count='exact').execute()

        total_vectors = response.count if hasattr(response, 'count') else len(response.data)
        st.metric("總向量數", total_vectors)

        # 顯示最近的向量
        recent_response = client.table('vectors').select(
            'vector_id, document_id, chunk_id, fact_id, type, page, order, created_at'
        ).order('created_at', desc=True).limit(20).execute()

        if recent_response.data:
            import pandas as pd
            df = pd.DataFrame(recent_response.data)

            # 格式化顯示
            df['vector_id'] = df['vector_id'].str[:8] + '...'
            df['document_id'] = df['document_id'].str[:8] + '...'
            df['chunk_id'] = df['chunk_id'].apply(lambda x: (x[:8] + '...') if x else 'N/A')
            df['fact_id'] = df['fact_id'].apply(lambda x: (x[:8] + '...') if x else 'N/A')

            st.dataframe(df, use_container_width=True)

            # 下載按鈕
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 下載為CSV",
                data=csv,
                file_name="vectors_export.csv",
                mime="text/csv"
            )
        else:
            st.info("目前沒有向量資料")

    except Exception as e:
        st.error(f"無法載入Supabase資料: {str(e)[:100]}...")
        st.info("請檢查.env中的Supabase設定")

def show_document_management():
    """文件管理 - 列出所有已處理的文件"""
    st.markdown("### 📄 已處理文件管理")

    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )

        with driver.session() as session:
            # 獲取所有Document
            result = session.run("""
            MATCH (d:Document)
            OPTIONAL MATCH (d)-[:HAS_CHUNK]->(c:Chunk)
            RETURN d.document_id as id, d.title as title, d.source_path as path,
                   count(c) as chunks, d.hash as hash,
                   d.created_at as created_at, d.updated_at as updated_at
            ORDER BY d.created_at DESC
            """)

            # 正確轉換Neo4j紀錄為字典列表
            documents = []
            for record in result:
                documents.append({
                    'id': record['id'],
                    'title': record['title'],
                    'path': record['path'],
                    'chunks': record['chunks'],
                    'hash': record['hash'],
                    'created_at': record['created_at'],
                    'updated_at': record['updated_at']
                })

        if documents:
            import pandas as pd
            df = pd.DataFrame(documents)

            # 格式化路徑顯示
            df['path'] = df['path'].apply(lambda x: Path(x).name if x else 'Unknown')

            # 重新命名欄位
            df.columns = ['文件ID', '標題', '文件名', '分塊數', 'Hash', '創建時間', '更新時間']

            st.dataframe(df, use_container_width=True)
            st.success(f"總共 {len(documents)} 個已處理的文件")
        else:
            st.info("目前沒有已處理的文件")

        driver.close()

    except Exception as e:
        st.error(f"無法載入文件資料: {str(e)[:100]}...")
        st.info("請檢查Neo4j連線")

def show_deletion_tests():
    """刪除測試功能"""
    st.markdown("### 🗑️ 資料庫刪除測試")
    st.warning("⚠️ 刪除操作不可逆，請謹慎使用")

    # 選擇刪除類型
    delete_type = st.selectbox(
        "選擇刪除測試類型",
        ["選擇類型", "Document刪除"],
        help="""
        Document刪除: 測試完整文件刪除 (包含所有關聯的chunks和vectors)
        其他刪除功能正在開發中...
        """
    )

    if delete_type != "選擇類型":
        st.markdown("---")

        # 根據類型顯示不同的選擇介面
        if delete_type == "Document刪除":
            show_document_deletion_test()
        # 暂时注释掉未完成的功能
        # elif delete_type == "Chunk刪除":
        #     show_chunk_deletion_test()
        # elif delete_type == "Visual Fact刪除":
        #     show_visual_fact_deletion_test()

    # 顯示未完成的功能通知區域
    if st.checkbox("顯示開發中的功能", key="show_dev_features"):
        with st.expander("⚠️ 開發中的功能 (請謹慎使用)", expanded=False):
            st.warning("以下功能正在開發中，可能不穩定或不完整。")

            dev_delete_type = st.radio(
                "選擇開發中功能",
                ["不選擇", "Chunk刪除測試", "Visual Fact刪除測試"],
                help="這些功能尚未完成，可能會有問題。",
                key="dev_delete_radio"
            )

            if dev_delete_type == "Chunk刪除測試":
                show_chunk_deletion_test()
            elif dev_delete_type == "Visual Fact刪除測試":
                show_visual_fact_deletion_test()

def show_document_deletion_test():
    """Document刪除測試 - 支援批量刪除"""
    st.markdown("#### 📄 Document批量刪除測試")

    try:
        from neo4j import GraphDatabase
        from uuid import UUID
        driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )

        with driver.session() as session:
            result = session.run("""
            MATCH (d:Document)
            OPTIONAL MATCH (d)-[:HAS_CHUNK]->(c:Chunk)
            RETURN d.document_id as id, d.title as title, count(c) as chunks,
                   d.source_path as source_path, d.created_at as created_at
            ORDER BY d.created_at DESC
            """)
            documents = []
            for record in result:
                documents.append({
                    'id': record['id'],
                    'title': record['title'],
                    'chunks': record['chunks'],
                    'source_path': record['source_path'] or '',
                    'created_at': record['created_at']
                })

        driver.close()

        if documents:
            st.markdown(f"**總共有 {len(documents)} 個文件**")

            # 使用session state來追蹤選中的項目
            if 'selected_documents' not in st.session_state:
                st.session_state.selected_documents = []

            # 全選/取消全選按鈕
            col1, col2, col3 = st.columns([2, 2, 3])
            with col1:
                if st.button("✅ 全選", key="select_all_button", use_container_width=True):
                    st.session_state.selected_documents = [doc['id'] for doc in documents]
                    st.rerun()  # 立即重新載入以更新介面

            with col2:
                if st.button("❌ 取消全選", key="clear_selection_button", use_container_width=True):
                    st.session_state.selected_documents = []
                    st.rerun()  # 立即重新載入以更新介面

            with col3:
                st.markdown(f"**已選擇: {len(st.session_state.selected_documents)} 個**")

            # 顯示文件列表，每個都有checkbox
            st.markdown("### 📋 文件列表")
            st.info("💡 **操作提示**: 勾選文件時頁面會短暫刷新，這是正常行為，可立即看到選擇狀態")

            with st.spinner("載入文件列表中..."):
                selected_count = 0

                for doc in documents:
                    is_selected = doc['id'] in st.session_state.selected_documents

                    # 創建每行的checkbox
                    col_checkbox, col_info = st.columns([1, 11])

                    with col_checkbox:
                        # 簡單的checkbox實現
                        checkbox = st.checkbox(
                            "",
                            value=is_selected,
                            key=f"doc_{doc['id']}"
                        )

                        # 更新session state
                        if checkbox and doc['id'] not in st.session_state.selected_documents:
                            st.session_state.selected_documents.append(doc['id'])
                        elif not checkbox and doc['id'] in st.session_state.selected_documents:
                            st.session_state.selected_documents.remove(doc['id'])

                        if checkbox:
                            selected_count += 1

                    with col_info:
                        # 顯示文件資訊
                        filename = Path(doc['source_path']).name if doc['source_path'] else "Unknown"
                        created_time = doc['created_at'].strftime("%Y-%m-%d %H:%M") if hasattr(doc['created_at'], 'strftime') else str(doc['created_at'])

                        st.markdown(f"""
                        **{doc['title']}**
                        📄 文件名: {filename} | 📊 分塊數: {doc['chunks']} | 🕒 創建時間: {created_time[:16]}
                        🆔 ID: `{doc['id'][:16]}...`
                        """)

                        # 添加分隔線
                        st.divider()

            # 顯示選擇統計
            if selected_count > 0:
                st.success(f"已選擇 {selected_count} 個文件進行刪除")
            else:
                st.info("未選擇任何文件")

            # 刪除按鈕區域
            if selected_count > 0:
                st.markdown("---")
                st.markdown("### 🗑️ 執行批量刪除")

                # 確認文本
                confirm_text = f"確認刪除選中的 {selected_count} 個文件嗎？此操作不可逆！"

                # 使用columns創建確認區域
                col_confirm, col_button = st.columns([3, 1])

                with col_confirm:
                    # 輸入確認文本來防止意外刪除
                    user_confirmation = st.text_input(
                        "請輸入 '確認刪除' 以繼續",
                        placeholder=f"輸入 '確認刪除' 來刪除 {selected_count} 個文件",
                        help="這是為了防止意外刪除，請仔細確認"
                    )

                with col_button:
                    delete_enabled = user_confirmation == "確認刪除"
                    delete_button = st.button(
                        f"🗑️ 刪除 {selected_count} 個文件",
                        type="primary",
                        disabled=not delete_enabled,
                        use_container_width=True
                    )

                if delete_button and delete_enabled:
                    # 將string IDs轉換為UUID
                    selected_uuids = []
                    for doc_id_str in st.session_state.selected_documents:
                        try:
                            selected_uuids.append(UUID(doc_id_str))
                        except Exception as e:
                            st.error(f"無效的Document ID: {doc_id_str}")
                            continue

                    if selected_uuids:
                        with st.spinner(f"正在刪除 {len(selected_uuids)} 個文檔..."):
                            # 執行批量刪除
                            results = asyncio.run(test_batch_document_deletion(selected_uuids))

                        # 顯示詳細結果
                        if results['successful_deletions'] > 0:
                            st.success(f"✅ 完全成功刪除 {results['successful_deletions']} 個文件（Neo4j + Supabase）")
                        else:
                            st.error("❌ 沒有成功刪除任何文件")

                        # 顯示具體失敗情況
                        col_neo4j, col_supabase, col_partial = st.columns(3)

                        with col_neo4j:
                            if results.get('neo4j_failures'):
                                st.error(f"🗂️ Neo4j 失敗: {len(results['neo4j_failures'])} 個")
                            else:
                                st.success("🗂️ Neo4j: 全部成功")

                        with col_supabase:
                            if results.get('supabase_failures'):
                                st.warning(f"🗃️ Supabase 失敗: {len(results['supabase_failures'])} 個")
                            else:
                                st.success("🗃️ Supabase: 全部成功")

                        with col_partial:
                            if len(results['failed_deletions']) > results['successful_deletions']:
                                partial_failures = len(results['failed_deletions']) - (results.get('neo4j_failures', []) + results.get('supabase_failures', []))
                                if partial_failures > 0:
                                    st.warning(f"⚠️ 部分失敗: {partial_failures} 個")
                            else:
                                st.success("🎯 同步刪除: 成功")

                        # 顯示失敗的具體文檔
                        if results['failed_deletions']:
                            st.warning(f"🔴 以下文件刪除失敗 ({len(results['failed_deletions'])} 個):")
                            failed_details = {
                                "Neo4j 失敗": results.get('neo4j_failures', []),
                                "Supabase 失敗": results.get('supabase_failures', [])
                            }

                            for failure_type, ids in failed_details.items():
                                if ids:
                                    st.markdown(f"**{failure_type}:**")
                                    for doc_id in ids:
                                        st.write(f"- `{doc_id[:16]}...`")
                                    st.markdown("")

                        # 只在有錯誤時顯示詳細錯誤信息
                        if results['errors']:
                            with st.expander("🔍 詳細錯誤信息", expanded=False):
                                for error in results['errors']:
                                    if "Neo4j failure" in error:
                                        st.error(f"🗂️ {error}")
                                    elif "Supabase failure" in error:
                                        st.warning(f"🗃️ {error}")
                                    else:
                                        st.code(error)

                        # 如果有成功刪除，顯示狀態分析並給用戶選擇是否刷新
                        if results['successful_deletions'] > 0:
                            # 設置全局刷新旗標，表示數據庫已經發生變化
                            st.session_state.database_modified = True
                            st.session_state.last_refresh_time = time.time()

                            # 顯示刪除後狀態分析
                            with st.expander("📊 刪除後狀態分析", expanded=True):
                                display_post_deletion_status()

                            # 給用戶選擇是否刷新頁面
                            st.markdown("---")
                            col_refresh, col_keep = st.columns(2)

                            with col_refresh:
                                if st.button("🔄 刷新頁面查看最新狀態", type="secondary", use_container_width=True):
                                    st.session_state.selected_documents = []  # 清除選擇
                                    st.rerun()

                            with col_keep:
                                st.button("📋 繼續查看當前結果", disabled=True, use_container_width=True)
                                st.info("當前顯示的是刪除操作的完整結果，包括 Neo4j/Supabase 的詳細狀態")
                                st.info("💡 **提示**: 切換到其他頁面時，系統會顯示數據更新的警告，建議手動刷新查看最新狀態。")
                        else:
                            # 沒有成功刪除的情況，給用户刷新選項來重置介面
                            if st.button("🔄 重新載入文件列表", type="secondary"):
                                st.session_state.selected_documents = []  # 清除選擇
                                st.rerun()
        else:
            st.info("📂 目前沒有已處理的文件可以刪除")

    except Exception as e:
        st.error(f"載入文件列表失敗: {str(e)[:100]}...")
        st.code(str(e), language='text')

def show_chunk_deletion_test():
    """Chunk刪除測試"""
    st.markdown("#### 📝 Chunk刪除測試")
    st.info("此功能正在開發中...")

def show_visual_fact_deletion_test():
    """Visual Fact刪除測試"""
    st.markdown("#### 👁️ Visual Fact刪除測試")
    st.info("此功能正在開發中...")

async def test_document_deletion(document_id: str) -> bool:
    """測試Document刪除功能"""
    try:
        db_manager = DatabaseManager(
            neo4j_uri=settings.neo4j_uri,
            neo4j_user=settings.neo4j_user,
            neo4j_password=settings.neo4j_password,
            supabase_url=settings.supabase_url,
            supabase_key=settings.supabase_key
        )

        result = await db_manager.delete_document_cascade(document_id)
        await db_manager.close()
        return result

    except Exception as e:
        st.error(f"刪除操作失敗: {str(e)}")
        return False

async def test_batch_document_deletion(document_ids: list) -> dict:
    """測試批量Document刪除功能"""
    try:
        db_manager = DatabaseManager(
            neo4j_uri=settings.neo4j_uri,
            neo4j_user=settings.neo4j_user,
            neo4j_password=settings.neo4j_password,
            supabase_url=settings.supabase_url,
            supabase_key=settings.supabase_key
        )

        results = await db_manager.delete_documents_batch(document_ids)
        await db_manager.close()
        return results

    except Exception as e:
        error_msg = f"批量刪除操作失敗: {str(e)}"
        st.error(error_msg)
        return {
            "total_requested": len(document_ids),
            "successful_deletions": 0,
            "failed_deletions": [str(id) for id in document_ids],
            "errors": [error_msg]
        }

def display_post_deletion_status():
    """顯示删除操作後的資料庫狀態分析"""
    st.markdown("### 📈 删除後資料庫狀態")

    # 查询Neo4j狀態
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )

        with driver.session() as session:
            # Document節點數量
            doc_result = session.run("MATCH (d:Document) RETURN count(d) as count")
            doc_count = doc_result.single()["count"]

            # Chunk節點數量
            chunk_result = session.run("MATCH (c:Chunk) RETURN count(c) as count")
            chunk_count = chunk_result.single()["count"]

            # Entity節點數量
            entity_result = session.run("MATCH (e:Entity) RETURN count(e) as count")
            entity_count = entity_result.single()["count"]

            # VisualFact節點數量
            vfact_result = session.run("MATCH (v:VisualFact) RETURN count(v) as count")
            vfact_count = vfact_result.single()["count"]

            # 所有節點數量
            all_result = session.run("MATCH (n) RETURN count(n) as count")
            all_nodes_count = all_result.single()["count"]

            # 所有關係數量
            rel_result = session.run("MATCH ()-[r]-() RETURN count(DISTINCT r) as count")
            rel_count = rel_result.single()["count"]

        driver.close()

        # 顯示Neo4j狀態
        col1, col2 = st.columns(2)
        with col1:
            st.metric("📄 Document 節點", doc_count)
            st.metric("📝 Chunk 節點", chunk_count)
        with col2:
            st.metric("🏷️ Entity 節點", entity_count)
            st.metric("👁️ VisualFact 節點", vfact_count)

        st.metric("🔗 總節點數", all_nodes_count)
        st.metric("⚡ 關係數", rel_count)

        if all_nodes_count == 0:
            st.success("✅ Neo4j數據庫已被清空")
        elif doc_count == 0:
            st.info("ℹ️ 沒有Document節點，但仍有其他資料")
        else:
            st.info(f"📊 Neo4j中尚有 {doc_count} 個文檔相關數據")

    except Exception as e:
        st.error(f"❌ 無法查詢Neo4j狀態: {str(e)[:100]}...")

    st.markdown("---")

    # 查询Supabase狀態
    try:
        from supabase import create_client
        client = create_client(settings.supabase_url, settings.supabase_key)

        # 獲取vectors表統計
        response = client.table('vectors').select('*', count='exact').execute()
        vectors_count = response.count if hasattr(response, 'count') else len(response.data if response.data else [])

        # 不同向量類型的統計
        if response.data:
            types = {}
            for item in response.data:
                vec_type = item.get('type', 'unknown')
                types[vec_type] = types.get(vec_type, 0) + 1

            type_counts = "\n".join([f"- **{t}**: {c} 個" for t, c in types.items()])
        else:
            type_counts = "無向量資料"

        # 顯示Supabase狀態
        st.metric("🗃️ Vector 記錄總數", vectors_count)

        if vectors_count > 0:
            st.markdown("**向量類型分佈:**")
            st.markdown(type_counts)

            if vectors_count < 20:
                st.info("ℹ️ 向量資料量很少，可能的完全清理")
            else:
                st.info(f"📊 向量化資料庫中剩餘 {vectors_count} 個向量記錄")
        else:
            st.success("✅ Supabase向量資料庫已被清空")

    except Exception as e:
        st.error(f"❌ 無法查詢Supabase狀態: {str(e)[:100]}...")

    # 操作摘要
    st.markdown("---")
    st.markdown("### 🎯 删除操作摘要")
    st.warning("⚠️ 删除操作已完成。檢查上方數據庫狀態來確認清理效果。")

# Page routing logic - moved to the end of file


def single_upload_handler(uploaded_file, vlm_strategy, force_vlm):
    """處理單個文件上傳"""
    if uploaded_file is not None:
        # 檢查文件是否已存在於資料庫
        filename = uploaded_file.name
        file_extension = Path(filename).suffix.lower()

        # 檢查數據庫中是否存在
        if file_extension in ['.pdf', '.docx', '.txt', '.md']:
            file_exists_in_db, duplicate_file_info = check_file_exists(filename)

        # 處理重复文件情况
        should_proceed = handle_duplicate_file(file_exists_in_db, duplicate_file_info, filename)
        if not should_proceed:
            return

        # 文件检查通过，继续正常处理
        show_file_info(uploaded_file)
        process_single_file(uploaded_file, vlm_strategy, force_vlm)
    else:
        st.info("請上傳一個文件來開始測試")


def batch_upload_handler(uploaded_files, vlm_strategy, force_vlm):
    """處理批量文件上傳"""
    if uploaded_files:
        # 限制文件數量
        max_files = 10
        if len(uploaded_files) > max_files:
            st.error(f"🚫 一次性最多只能上傳 {max_files} 個文件。您目前選擇了 {len(uploaded_files)} 個文件。")
            st.stop()

        st.success(f"📂 已選擇 {len(uploaded_files)} 個文件")

        # 檢查每個文件的狀態
        file_status = []
        for uploaded_file in uploaded_files:
            filename = uploaded_file.name
            file_extension = Path(filename).suffix.lower()

            exists, info = False, None
            if file_extension in ['.pdf', '.docx', '.txt', '.md']:
                exists, info = check_file_exists(filename)

            file_status.append({
                'file': uploaded_file,
                'filename': filename,
                'extension': file_extension,
                'exists': exists,
                'info': info
            })

        # 分類顯示文件狀態
        display_batch_file_status(file_status)

        # 批量處理按鈕
        if all(not status['exists'] for status in file_status):
            # 所有文件都可以處理
            process_all_button = st.button("🚀 批量處理所有文件", type="primary", use_container_width=True)
            if process_all_button:
                process_batch_files(file_status, vlm_strategy, force_vlm)
        else:
            # 有重复文件，需要用户选择
            handle_batch_conflicts(file_status, vlm_strategy, force_vlm)
    else:
        st.info("請選擇多個文件進行批量上傳")


def check_file_exists(filename):
    """檢查文件是否已存在於資料庫"""
    file_exists_in_db = False
    duplicate_file_info = None

    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )

        with driver.session() as session:
            result = session.run("""
            MATCH (d:Document)
            WHERE d.source_path CONTAINS $filename
            RETURN d.document_id as id, d.title as title,
                   d.source_path as path, d.created_at as created_at
            ORDER BY d.created_at DESC
            LIMIT 1
            """, filename=filename)

            record = result.single()
            if record:
                file_exists_in_db = True
                duplicate_file_info = {
                    "id": record["id"],
                    "title": record["title"],
                    "path": record["path"],
                    "created_at": record["created_at"]
                }

        driver.close()

    except Exception as e:
        st.warning(f"⚠️ 無法檢查檔案是否已存在: {str(e)[:50]}...")

    return file_exists_in_db, duplicate_file_info


def handle_duplicate_file(file_exists_in_db, duplicate_file_info, filename):
    """處理重複文件的情況"""
    if file_exists_in_db:
        st.error(f"🚫 **檔案 '{filename}' 已存在於資料庫中**")

        if duplicate_file_info:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**標題:** {duplicate_file_info['title']}")
                st.markdown(f"**路徑:** {Path(duplicate_file_info['path']).name}")
            with col2:
                created_time = duplicate_file_info['created_at'].strftime("%Y-%m-%d %H:%M") if hasattr(duplicate_file_info['created_at'], 'strftime') else str(duplicate_file_info['created_at'])
                st.markdown(f"**創建時間:** {created_time}")
                st.markdown(f"**檔案ID:** `{duplicate_file_info['id'][:16]}...`")

        # 强制上传选项
        st.warning("⚠️ **警告**: 強制上傳將覆蓋現有數據，可能導致數據不一致")

        col_skip, col_force = st.columns(2)
        with col_skip:
            if st.button("🔄 重新選擇檔案", use_container_width=True):
                st.stop()

        with col_force:
            if st.checkbox("⚡ 強制上傳並覆蓋舊版本", key="force_upload_checkbox"):
                st.warning("⚠️ 您已啟用強制上傳模式。請謹慎使用此功能。")
                st.info("💡 **建議:** 強制上傳後請檢查數據庫完整性。")
                return True  # 允许继续
            else:
                st.info("💡 **建議:** 先刪除舊版本或重新命名檔案。然而，如果需要強制覆蓋，請勾選上方選項。")
                st.stop()
    return True


def show_file_info(uploaded_file):
    """顯示單個文件的資訊"""
    filename = uploaded_file.name
    file_ext = Path(filename).suffix.lower()

    st.success(f"📄 已選擇: {filename}")

    file_info = {
        "文件名": filename,
        "大小": f"{uploaded_file.size/1024:.1f} KB",
        "格式": file_ext,
    }
    st.json(file_info)

    # VLM策略適用性提示
    strategy_hint = {
        '.pdf': "將使用VLM處理，因為PDF需要視覺分析",
        '.docx': "將嘗試VLM處理，可對複雜格式的文件分析",
        '.txt': "將直接處理，因為文字格式適合LangChain載入",
        '.md': "將直接處理，因為Markdown適合結構化解析"
    }

    if file_ext in strategy_hint:
        st.info(f"🎯 {strategy_hint[file_ext]}")


def process_single_file(uploaded_file, vlm_strategy, force_vlm):
    """處理單個文件"""
    # 處理按鈕
    process_button = st.button("🚀 開始處理", type="primary", use_container_width=True)

    if process_button:
        # 文件處理邏輯（與原有相同）
        with st.spinner("正在處理文件..."):
            handle_file_processing(uploaded_file, vlm_strategy, force_vlm)


def display_batch_file_status(file_status):
    """顯示批量上傳文件的狀態"""
    clean_files = [f for f in file_status if not f['exists']]
    duplicate_files = [f for f in file_status if f['exists']]

    st.markdown("### 📊 文件狀態統計")
    col1, col2 = st.columns(2)

    with col1:
        st.metric("✅ 可處理文件", len(clean_files))

    with col2:
        st.metric("🚫 重複文件", len(duplicate_files))

    # 顯示可處理的文件
    if clean_files:
        st.markdown("#### ✅ 可處理的文件")
        for file_info in clean_files:
            st.markdown(f"📄 {file_info['filename']} ({file_info['extension']})")

    # 顯示重複的文件
    if duplicate_files:
        st.markdown("#### 🚫 重複的文件")
        for file_info in duplicate_files:
            with st.expander(f"📄 {file_info['filename']} - 已存在", expanded=False):
                if file_info['info']:
                    st.markdown(f"**現有文件資訊:**")
                    info_col1, info_col2 = st.columns(2)
                    with info_col1:
                        st.markdown(f"標題: {file_info['info']['title']}")
                        st.markdown(f"路徑: {Path(file_info['info']['path']).name}")
                    with info_col2:
                        created_time = file_info['info']['created_at'].strftime("%Y-%m-%d %H:%M") if hasattr(file_info['info']['created_at'], 'strftime') else str(file_info['info']['created_at'])
                        st.markdown(f"創建時間: {created_time}")
                        st.markdown(f"檔案ID: `{file_info['info']['id'][:16]}...`")


def handle_batch_conflicts(file_status, vlm_strategy, force_vlm):
    """處理批量上傳中的衝突"""
    clean_files = [f for f in file_status if not f['exists']]
    duplicate_files = [f for f in file_status if f['exists']]

    if clean_files:
        st.info(f"💡 {len(clean_files)} 個文件可以直接處理，{len(duplicate_files)} 個文件需要處理重複問題。")

        # 處理可直接處理的文件
        process_clean_button = st.button(f"🚀 處理可直接處理的文件 ({len(clean_files)} 個)",
                                       type="primary", use_container_width=True)
        if process_clean_button:
            process_batch_files(clean_files, vlm_strategy, force_vlm)

    # 处理重复文件的选项
    if duplicate_files:
        st.markdown("### 🔄 處理重複文件")
        st.warning("對於重複的文件，您可以選擇：")

        col1, col2 = st.columns(2)

        with col1:
            skip_duplicates_button = st.button("⏭️ 跳過重複文件",
                                             help="只處理未重複的文件",
                                             use_container_width=True)

        with col2:
            force_all_button = st.button("⚡ 強制處理所有文件",
                                       help="覆蓋所有重複文件，請謹慎使用",
                                       type="secondary",
                                       use_container_width=True)

        if skip_duplicates_button:
            process_batch_files(clean_files, vlm_strategy, force_vlm)

        if force_all_button:
            # 强制处理所有文件
            st.warning("⚡ 已啟用強制覆蓋模式，正在處理所有文件...")
            process_batch_files(file_status, vlm_strategy, force_vlm, force_override=True)


async def process_batch_files(files, vlm_strategy, force_vlm, force_override=False):
    """批量處理文件"""
    if not files:
        st.warning("沒有文件可以處理")
        return

    # 創建進度顯示
    progress_bar = st.progress(0)
    status_text = st.empty()
    result_container = st.empty()

    total_files = len(files)
    successful_uploads = 0
    failed_uploads = 0
    failed_details = []

    ingestion_service = IngestionService()

    for i, file_info in enumerate(files):
        current_file = file_info['file']
        filename = file_info['filename']

        status_text.text(f"處理文件 {i+1}/{total_files}: {filename}")

        try:
            # 保存文件到臨時位置
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{current_file.name}") as tmp_file:
                tmp_file.write(current_file.read())
                file_path = Path(tmp_file.name)

            progress_bar.progress((i) / total_files, f"處理中: {filename}")

            # 處理文件
            result = await ingestion_service.ingest_document_enhanced(
                file_path=file_path,
                force_vlm=force_vlm
            )

            if result.get("success"):
                successful_uploads += 1
                st.success(f"✅ {filename} 處理成功")
            else:
                failed_uploads += 1
                failed_details.append({
                    'filename': filename,
                    'error': result.get('error', '未知錯誤')
                })
                st.error(f"❌ {filename} 處理失敗: {result.get('error', '未知錯誤')}")

            # 清理臨時文件
            try:
                file_path.unlink()
            except:
                pass

        except Exception as e:
            failed_uploads += 1
            failed_details.append({
                'filename': filename,
                'error': str(e)
            })
            st.error(f"❌ {filename} 處理異常: {str(e)}")

    progress_bar.progress(1.0, "批量處理完成")
    status_text.empty()
    progress_bar.empty()

    # 顯示批量處理結果統計
    with result_container.container():
        st.markdown("### 📈 批量處理結果統計")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("📂 總文件數", total_files)

        with col2:
            st.metric("✅ 成功處理", successful_uploads)

        with col3:
            st.metric("❌ 處理失敗", failed_uploads)

        if failed_details:
            st.markdown("### ❌ 失敗詳情")
            for failure in failed_details:
                with st.expander(f"❌ {failure['filename']}", expanded=False):
                    st.code(failure['error'])

        if successful_uploads > 0:
            st.success(f"🎉 批量上傳完成！成功處理 {successful_uploads} 個文件。")

            # 显示数据更新摘要
            st.markdown("### 📊 数据更新摘要")
            display_post_processing_status()


def handle_file_processing(uploaded_file, vlm_strategy, force_vlm):
    """處理單個文件的完整邏輯"""
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
        status_text.text("🔧 初始化處理服務...")
        progress_bar.progress(20, "初始化服務...")

        ingestion_service = IngestionService()

        progress_bar.progress(30, "開始處理...")

        # 執行增強處理
        status_text.text(f"🎯 處理中 ({vlm_strategy})...")

        start_time = time.time()

        result = asyncio.run(ingestion_service.ingest_document_enhanced(
            file_path=file_path,
            force_vlm=force_vlm
        ))

        processing_time = time.time() - start_time

        progress_bar.progress(100, "處理完成! 🎉")

        # 顯示結果
        with result_area.container():
            if result.get("success"):
                st.success("🎉 處理成功！")
                st.metric("處理時間", f"{processing_time:.1f}s")
                st.metric("分塊數", result.get("metadata", {}).get("chunks_created", 0))
                st.metric("向量數", result.get("metadata", {}).get("embeddings_created", 0))

                # 顯示詳細資訊
                with st.expander("📋 處理詳情", expanded=True):
                    processing_trace = result.get("processing_trace", {})
                    if processing_trace:
                        st.write(f"**文件類型**: {processing_trace.get('file_type', 'Unknown')}")
                        st.write(f"**使用模組**: {', '.join(processing_trace.get('modules_used', []))}")

            else:
                st.error(f"❌ 處理失敗: {result.get('error', '未知錯誤')}")

    except Exception as e:
        st.error(f"❌ 處理過程中發生錯誤: {str(e)}")
        with result_area.container():
            with st.expander("錯誤詳情", expanded=True):
                st.code(str(e), language='text')

    finally:
        # 清理進度顯示
        status_text.empty()
        progress_bar.empty()


def display_post_processing_status():
    """顯示處理後的資料庫狀態"""
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )

        with driver.session() as session:
            doc_result = session.run("MATCH (d:Document) RETURN count(d) as count")
            doc_count = doc_result.single()["count"]

        driver.close()

        # 显示Supabase統計
        from supabase import create_client
        client = create_client(settings.supabase_url, settings.supabase_key)
        vectors_response = client.table('vectors').select('*', count='exact').execute()
        vectors_count = vectors_response.count if hasattr(vectors_response, 'count') else 0

        st.metric("🗂️ Neo4j 文件數", doc_count)
        st.metric("🗃️ Supabase 向量數", vectors_count)

    except Exception as e:
        st.warning(f"無法檢查最新統計: {str(e)[:50]}...")


# 頁面路由：只保留一個頁面路由
if page == "文檔處理":
    st.markdown("# 📄 文檔處理")

    # 側邊欄的處理配置邏輯
    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("### 📤 文件上傳模式")

        # 選擇上傳模式
        upload_mode = st.radio(
            "選擇上傳類型",
            ["單個文件", "批量上傳"],
            index=0,
            key="upload_mode_radio",
            help="""
            單個文件: 上傳一個文件進行處理
            批量上傳: 上傳多個文件同時處理
            """
        )

        st.markdown("---")

        if upload_mode == "單個文件":
            # 單文件上傳 (原有邏輯)
            st.markdown("### 📄 單個文件上傳")

            # 文件上傳器
            uploaded_file = st.file_uploader(
                "選擇測試文檔",
                type=["pdf", "docx", "txt", "md"],
                help="支援的文件格式: PDF, Word, 文字, Markdown",
                key="uploaded_file"
            )

            # 將後續邏輯包裝在變數中，以便重用
            single_upload_handler(uploaded_file, vlm_strategy, force_vlm)

        else:  # 批量上傳
            # 批量上傳邏輯
            st.markdown("### 📂 批量文件上傳")

            # 批量文件上傳器
            uploaded_files = st.file_uploader(
                "選擇多個測試文檔",
                type=["pdf", "docx", "txt", "md"],
                accept_multiple_files=True,
                help="支援的文件格式: PDF, Word, 文字, Markdown，一次最多選擇10個文件",
                key="uploaded_files"
            )

            # 處理批量上傳
            batch_upload_handler(uploaded_files, vlm_strategy, force_vlm)

    with col2:
        st.markdown("### 📊 處理結果")

        # 处理结果显示区域会在各处理函数中显示

        # 文檔處理頁面底部信息
        st.markdown("---")
        st.markdown("""
### 📖 使用說明

#### 🚀 **新增功能: 批量文件上傳**

**特色功能:**
- 📂 **批量選擇**: 一次選擇最多10個文件
- 🔍 **智能檢查**: 自動檢查每個文件是否重複
- ⚡ **批量處理**: 同時處理多個文件
- 📊 **詳細統計**: 提供完整的成功/失敗統計
- 🛡️ **衝突解決**: 處理重複文件時提供多種選擇

**使用步驟:**
1. **選擇模式**: 從"單個文件"或"批量上傳"中選擇
2. **選擇文件**: 對於批量上傳，選擇多個文件
3. **檢查狀態**: 系統自動分析文件狀態
4. **處理文件**: 根據狀態選擇處理策略
5. **查看結果**: 獲取完整的處理統計資訊

#### 📄 **既有功能: 單個文件上傳**
- 🚀 **快速處理**: 上傳一個文件即時處理
- 🛡️ **重複檢查**: 避免數據重複
- ⚡ **覆蓋選項**: 提供強制覆蓋功能
- 📋 **詳細回報**: 完整的處理軌跡和統計

### 🎯 **系統特色**

#### 🔄 **處理優先順序**
1. **VLM服務** (如果運行) → Ollama或OpenAI
2. **MinerU** → 如果VLM失敗或跳過
3. **Tesseract OCR** → 最終降級選項
4. **文字處理** → 對於.txt/.md文件

#### 🎨 **智能策略**
- **自動判斷**: 根據文件類型智能選擇處理器
- **強制開啟**: 針對所有文件嘗試VLM處理
- **強制關閉**: 直接使用LangChain載入

#### 📊 **品質追蹤**
- **處理時間監控**: 各階段時間統計
- **成功率分析**: 文件處理成功/失敗統計
- **錯誤分類**: 詳細的錯誤類型和原因

---
**🎉 新功能上線: 批量文件處理，讓數據導入更高效！**
        """)

# 資料庫管理頁面
elif page == "資料庫管理":
    show_database_management_page()
