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
    from grag.ingestion.indexing.providers.embedding_providers import EmbeddingProviderManager
    st.sidebar.success("✅ 嵌入服務可用")
except Exception:
    st.sidebar.error("❌ 嵌入服務異常")

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

            # 顯示結果
            with result_area.container():
                if result.get("success"):
                    st.success("✅ 處理成功完成!")

                    # 統計指標
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.metric("處理時間", f"{processing_time:.2f}s")
                    with col_b:
                        st.metric("分塊數", result.get("metadata", {}).get("chunks_created", 0))
                    with col_c:
                        st.metric("嵌入向量", result.get("metadata", {}).get("embeddings_created", 0))

                    # 策略和品質信息
                    strategy_info = result.get("strategy_used", {})
                    metadata = result.get("metadata", {})

                    st.markdown("#### 🎯 處理策略結果")
                    strategy_cols = st.columns(2)

                    with strategy_cols[0]:
                        vlm_used = strategy_info.get("vlm_used", False)
                        vlm_success = strategy_info.get("vlm_success", False)
                        fallback_used = strategy_info.get("fallback_used", False)

                        if fallback_used:
                            st.warning("⚠️ 使用降級處理")
                        elif vlm_used and vlm_success:
                            st.success("✅ VLM處理成功")
                        elif vlm_used and not vlm_success:
                            st.warning("⚠️ VLM嘗試失敗")
                        else:
                            st.info("📝 直接處理")

                    with strategy_cols[1]:
                        quality_level = metadata.get("quality_level", "unknown")
                        # 修復統計計算
                        try:
                            chunk_stats = result.get("statistics", {}).get("chunks", {})
                            if isinstance(chunk_stats, dict) and "total_characters" in chunk_stats:
                                content_len = chunk_stats.get("total_characters", 0)
                            else:
                                content_len = 0
                        except:
                            content_len = 0
                        st.metric("內容長度", f"{content_len}字符")
                        st.metric("品質等級", quality_level.upper())

                    # 詳細統計
                    if "statistics" in result:
                        with st.expander("📊 詳細統計", expanded=False):
                            st.json(result["statistics"])

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
