"""
Configuration Sidebar Component
側邊欄配置組件，統一管理系統配置選項
"""
import streamlit as st
from typing import Dict, Any, Optional
from grag.frontend.services import SystemCheckService, EmbeddingService
from grag.frontend.utils import UI_CONFIG, ICONS

class ConfigSidebar:
    """側邊欄配置組件"""

    def __init__(self):
        self.system_check = SystemCheckService()
        self.embedding_service = EmbeddingService()

    def render(self) -> Dict[str, Any]:
        """
        渲染配置側邊欄並返回配置

        Returns:
            dict: 包含所有配置的字典
        """
        # 側邊欄標題
        st.sidebar.title(f"{ICONS['processing']} 處理配置")

        # 初始化配置
        config = {
            'vlm_strategy': '自動判斷',
            'force_vlm': None,
            'embedding_provider': 'sentence_transformers',
            'page': '文檔處理'
        }

        try:
            # VLM 策略選擇
            config.update(self._render_vlm_strategy_config())

            # 嵌入提供者選擇
            embedding_config = self._render_embedding_config()
            config.update(embedding_config)

            # 頁面選擇
            config['page'] = self._render_page_selection()

            # 系統狀態檢查
            self._render_system_status()

        except Exception as e:
            st.sidebar.error(f"⚠️ 配置載入失敗: {str(e)[:50]}...")
            st.sidebar.info("系統將使用預設配置繼續運行")

        return config

    def _render_vlm_strategy_config(self) -> Dict[str, Any]:
        """渲染 VLM 策略配置"""
        st.sidebar.markdown("### 🎯 VLM 處理策略")

        strategy = st.sidebar.selectbox(
            "選擇策略",
            UI_CONFIG['processing_options']['vlm_strategies'],
            index=0,
            key="vlm_strategy_selectbox",
            help="""
            自動判斷: 根據文件類型智能選擇 (.pdf使用VLM, .txt/.md直接處理)
            強制開啟: 對所有文檔都使用VLM處理 (會觸發降級邏輯)
            強制關閉: 跳過VLM，直接使用結構化文字處理
            """
        )

        # 策略解釋
        self._render_strategy_explanation(strategy)

        # 轉換配置
        force_vlm_map = {
            "自動判斷": None,
            "強制開啟": True,
            "強制關閉": False
        }

        return {
            'vlm_strategy': strategy,
            'force_vlm': force_vlm_map[strategy]
        }

    def _render_strategy_explanation(self, strategy: str):
        """渲染策略解釋"""
        st.sidebar.markdown("**策略邏輯說明:**")

        explanations = {
            "自動判斷": f"""
            📋 **文件處理邏輯**:
            - `.pdf`, `.docx` → VLM處理 (視覺分析)
            - `.txt`, `.md` → 直接處理 (LangChain載入)
            - 其他格式 → VLM優先 (未知內容較安全)
            """,
            "強制開啟": f"""
            🔧 **強制VLM模式**:
            - 對所有文件嘗試VLM處理
            - 失敗時自動降級到結構化文字分析
            - 適合測試降級機制
            """,
            "強制關閉": f"""
            📝 **直接處理模式**:
            - 跳過VLM，直接使用LangChain載入
            - 使用結構化文字分析
            - 最快速的處理方式
            """
        }

        if strategy in explanations:
            st.sidebar.info(explanations[strategy])

        st.sidebar.markdown("---")

    def _render_embedding_config(self) -> Dict[str, Any]:
        """渲染嵌入提供者配置"""
        st.sidebar.markdown("### 🤖 嵌入模型選擇")

        try:
            # 獲取可用提供者
            available_providers = self.embedding_service.get_available_providers()

            if not available_providers:
                st.sidebar.warning("⚠️ 沒有可用的嵌入提供者")
                return {'embedding_provider': None}

            # 提供者選擇
            selected_provider = st.sidebar.selectbox(
                "嵌入模型",
                available_providers,
                index=0,
                key="embedding_provider_selectbox",
                help="""
                選擇用於向量化的嵌入模型:
                - sentence_transformers: 高品質本地模型 (推薦)
                - openai: OpenAI API (需要API key)
                - cohere: Cohere API (企業級)
                - clip: CLIP多模態模型 (支援圖文)
                """
            )

            # 顯示提供者資訊
            self._render_provider_info(selected_provider)

            # 檢查提供者狀態
            status = self.embedding_service.check_provider_status(selected_provider)
            self._render_provider_status(status)

            return {'embedding_provider': selected_provider}

        except Exception as e:
            st.sidebar.error(f"❌ 嵌入服務載入失敗: {str(e)[:50]}...")
            return {'embedding_provider': 'sentence_transformers'}

    def _render_provider_info(self, provider: str):
        """渲染提供者資訊"""
        info = self.embedding_service.get_provider_info(provider)

        if info:
            col1, col2 = st.sidebar.columns(2)
            with col1:
                st.sidebar.caption(f"維度: {info.get('dimension', 'N/A')}")
            with col2:
                st.sidebar.caption(f"費用: {info.get('cost', 'N/A')}")

            description = info.get('description', '')
            if description:
                with st.sidebar.expander("ℹ️ 詳細資訊", expanded=False):
                    st.write(description)

    def _render_provider_status(self, status: Dict[str, Any]):
        """渲染提供者狀態"""
        if status.get('available'):
            st.sidebar.success(f"✅ {status.get('name', 'Unknown')} 可用")
        else:
            st.sidebar.error(f"❌ {status.get('name', 'Unknown')} 不可用")
            if status.get('error'):
                st.sidebar.caption(f"錯誤: {status['error']}")

    def _render_page_selection(self) -> str:
        """渲染頁面選擇"""
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 📍 頁面導航")

        page = st.sidebar.selectbox(
            "選擇頁面",
            UI_CONFIG['page_options'],
            index=0,
            key="page_selector",
            help="""
            文檔處理: 上傳和處理文件，測試RAG管道
            資料庫管理: 查看和刪除資料庫內容，Neo4j圖形視覺化
            """
        )

        return page

    def _render_system_status(self):
        """渲染系統狀態檢查"""
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🔍 系統狀態")

        # 檢查各項服務狀態
        system_status = self.system_check.get_system_status()

        # LangChain
        if system_status.get('langchain'):
            st.sidebar.success("✅ LangChain 可用")
        else:
            st.sidebar.error("❌ LangChain 未安裝")

        # VLM 服務
        vlm_configured = system_status.get('vlm_configured', False)
        if vlm_configured:
            st.sidebar.success("✅ VLM 服務已配置")
        else:
            st.sidebar.warning("⚠️ VLM 服務未配置")

        # 嵌入服務已在上面顯示

        # 資料庫連接
        st.sidebar.markdown("#### 📊 資料庫連線")

        db_status = system_status.get('database', {})
        if db_status.get('neo4j'):
            st.sidebar.success("✅ Neo4j 已連線")
        else:
            st.sidebar.error("❌ Neo4j 連線失敗")

        if db_status.get('supabase'):
            st.sidebar.success("✅ Supabase 已連線")
        else:
            st.sidebar.error("❌ Supabase 連線失敗")

        # 整體狀態
        if db_status.get('neo4j') and db_status.get('supabase'):
            st.sidebar.success("🎉 所有資料庫正常連線！")
        elif db_status.get('neo4j') or db_status.get('supabase'):
            st.sidebar.warning("⚠️ 部分資料庫可連線")
        else:
            st.sidebar.error("❌ 所有資料庫連線失敗")
