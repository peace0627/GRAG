#!/usr/bin/env python3
"""
重構後的 LangChain 處理測試 GUI
模塊化架構，清晰的職責分離
"""

import sys
from pathlib import Path

# 添加專案根目錄到路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import streamlit as st
from grag.frontend.components import ConfigSidebar
from grag.frontend.views import render_document_processing_page, render_database_management_page
from grag.frontend.utils import UI_CONFIG

def main():
    """主應用入口"""
    # 頁面配置
    st.set_page_config(**UI_CONFIG['page_settings'])

    # 自定義樣式
    st.markdown("""
    <style>
        .stApp {
            font-family: 'Microsoft YaHei', 'PingFang SC', 'Hiragino Sans GB', 'SimHei', sans-serif;
        }
    </style>
    """, unsafe_allow_html=True)

    # 主標題
    st.title("🔗 LangChain處理測試器")
    st.markdown("---")

    # 系統能力總覽
    _render_system_capabilities()

    # 載入側邊欄配置
    config_sidebar = ConfigSidebar()
    app_config = config_sidebar.render()

    # 頁面路由
    page = app_config.get('page', '文檔處理')

    # 分頁容器 - 保留側邊欄配置邏輯
    tab1, tab2 = st.tabs(["📄 文檔處理", "🗃️ 資料庫管理"])

    with tab1:
        if page == "文檔處理":
            st.markdown("## 📄 文檔處理")
            render_document_processing_page(app_config)
        else:
            st.info("💡 **提示**: 請在側邊欄選擇「文檔處理」頁面來啟用此標籤")

    with tab2:
        if page == "資料庫管理":
            st.markdown("## 🗃️ 資料庫管理")
            render_database_management_page(app_config)
        else:
            st.info("💡 **提示**: 請在側邊欄選擇「資料庫管理」頁面來啟用此標籤")

    # 頁面底部信息
    _render_footer_info()

def _render_system_capabilities():
    """渲染系統能力總覽"""
    st.markdown("### 🔄 系統處理能力狀態")

    # 從服務中獲取能力狀態
    try:
        from grag.frontend.services import SystemCheckService
        system_check = SystemCheckService()
        status = system_check.get_system_status()

        # 顯示關鍵能力狀態
        col1, col2, col3 = st.columns(3)
        with col1:
            multimodal_status = "✅ VLM 處理" if status.get('vlm_configured') else "⚠️ 基本處理"
            st.success(f"🎨 多模態處理: {multimodal_status}")

        with col2:
            text_status = "✅ 可用" if status.get('langchain') else "❌ 未安裝"
            st.success(f"📝 文本處理: {text_status}")

        with col3:
            db_status = status.get('database', {})
            if db_status.get('neo4j') and db_status.get('supabase'):
                st.success("🗃️ 資料庫: ✅ Neo4j + Supabase")
            elif db_status.get('neo4j') or db_status.get('supabase'):
                st.warning("🗃️ 資料庫: ⚠️ 部分連接")
            else:
                st.error("🗃️ 資料庫: ❌ 連接失敗")

        # 處理策略說明
        st.info("📋 **處理優先順序**: VLM服務 → MinerU → Tesseract OCR → 文字處理")

    except Exception as e:
        st.warning(f"⚠️ 系統狀態檢查失敗: {str(e)[:50]}...")

    st.markdown("---")

def _render_footer_info():
    """渲染頁面底部信息"""
    st.markdown("---")
    st.markdown("""
    ### 📖 系統特色

    #### 🚀 **最新功能**
    - 🤖 **多模態嵌入**: 支援 CLIP 等多模態模型
    - 📂 **批量處理**: 一次處理多個文件
    - 🎯 **智慧路由**: 自動選擇最佳處理策略
    - 📊 **詳細統計**: 完整的處理和嵌入統計

    #### 🎨 **模塊化架構**
    - 🧩 **組件化**: UI組件獨立管理
    - ⚙️ **服務化**: 業務邏輯層分離
    - 🛠️ **工具化**: 通用功能抽象
    - 📱 **視圖化**: 頁面邏輯清晰

    ---
    **🏗️ 架構優化**: 原始 1,766 行代碼已重構為模塊化結構
    """)

if __name__ == "__main__":
    main()
