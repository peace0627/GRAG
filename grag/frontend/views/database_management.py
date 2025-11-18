"""
Database Management Page View
資料庫管理頁面，整合 Neo4j 和 Supabase 的查看和管理功能
"""
import streamlit as st
import asyncio
from typing import Dict, Any, List
from pathlib import Path
import time
import uuid
from grag.core.database_services import DatabaseManager
from grag.core.config import settings

def render_database_management_page(config: Dict[str, Any]):
    """
    渲染資料庫管理頁面

    Args:
        config: 應用配置字典
    """
    # 檢查是否有數據庫變更通知
    if st.session_state.get('database_modified', False):
        st.info("🔄 **數據更新提示**: 數據庫最近發生了變化（文件删除/上傳）。請刷新頁面查看最新狀態。")

        if st.button("🔄 刷新数据库视图", type="secondary", use_container_width=True):
            st.session_state.database_modified = False
            st.rerun()

        st.markdown("---")

    # Tab 分頁：Neo4j 視覺化、Supabase 資料、文件管理、删除測試
    tab1, tab2, tab3, tab4 = st.tabs([
        "🌐 Neo4j 圖形資料庫",
        "📊 Supabase 向量資料庫",
        "�️ 文件管理",
        "🗑️ 删除測試"
    ])

    with tab1:
        _render_neo4j_section()

    with tab2:
        _render_supabase_section()

    with tab3:
        _render_file_management_section()

    with tab4:
        _render_deletion_section()

def _render_neo4j_section():
    """渲染 Neo4j 部分"""
    st.markdown("### 🕸️ Neo4j 圖形資料庫")

    try:
        # 檢查 Neo4j 連線
        from neo4j import GraphDatabase
        from grag.core.config import settings

        driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )
        driver.verify_connectivity()
        driver.close()

        st.success("✅ Neo4j 已連線")

        # 基本統計
        with st.expander("📊 圖形統計", expanded=True):
            _show_neo4j_stats()

        # 操作指引
        st.markdown("""
        **💡 使用提示:**
        - Neo4j Browser 提供完整的圖形資料庫視覺化和查詢介面
        - 右鍵節點可展開更多資訊
        - 支援完整 Cypher 查詢語言
        - 適合開發階段的資料探索和調試
        """)

    except Exception as e:
        st.error(f"❌ Neo4j 連線失敗: {str(e)[:50]}...")
        st.info("請確保 Neo4j 服務運行在正確的端點")

def _render_supabase_section():
    """渲染 Supabase 部分"""
    st.markdown("### 🗃️ Supabase 向量資料庫")

    try:
        from supabase import create_client
        from grag.core.config import settings

        client = create_client(settings.supabase_url, settings.supabase_key)

        # 獲取基本統計
        response = client.table('vectors').select('*', count='exact').execute()
        total_vectors = response.count if hasattr(response, 'count') else len(response.data or [])

        st.metric("總向量數", total_vectors)

        # 向量類型統計
        if response.data and len(response.data) > 0:
            vector_types = {}
            for item in response.data:
                vec_type = item.get('type', 'unknown')
                vector_types[vec_type] = vector_types.get(vec_type, 0) + 1

            st.markdown("**向量類型分布:**")
            for vec_type, count in vector_types.items():
                st.write(f"- **{vec_type}**: {count} 個")

        # 最近的向量
        st.markdown("#### 🕒 最近向量記錄")
        if response.data and len(response.data) > 0:
            # 顯示最近 10 個
            recent_vectors = sorted(response.data, key=lambda x: x.get('created_at', ''), reverse=True)[:10]

            import pandas as pd
            df = pd.DataFrame([{
                'ID': v['vector_id'][:8] + '...',
                '類型': v.get('type', 'N/A'),
                '頁面': v.get('page', 'N/A'),
                '創建時間': v.get('created_at', 'N/A')[:19] if v.get('created_at') else 'N/A'
            } for v in recent_vectors])

            st.dataframe(df, use_container_width=True)

        st.success("✅ Supabase 連線正常")

    except Exception as e:
        st.error(f"❌ Supabase 連線失敗: {str(e)[:50]}...")
        st.info("請檢查 Supabase 配置")

def _render_statistics_section():
    """渲染統計部分"""
    st.markdown("### 📈 資料庫統計總覽")

    try:
        # Neo4j 統計
        st.markdown("#### 🕸️ Neo4j 統計")

        _show_neo4j_stats()

        st.markdown("---")

        # Supabase 統計
        st.markdown("#### 🗃️ Supabase 統計")

        from supabase import create_client
        from grag.core.config import settings

        client = create_client(settings.supabase_url, settings.supabase_key)
        response = client.table('vectors').select('*', count='exact').execute()
        vectors_count = response.count if hasattr(response, 'count') else 0

        col1, col2 = st.columns(2)
        with col1:
            st.metric("向量記錄總數", vectors_count)
        with col2:
            avg_vectors = vectors_count / max(1, _get_document_count_neo4j())
            st.metric("平均向量/文檔", ".1f")

    except Exception as e:
        st.error(f"❌ 統計資訊載入失敗: {str(e)[:50]}...")

def _show_neo4j_stats():
    """顯示 Neo4j 統計信息"""
    try:
        from neo4j import GraphDatabase
        from grag.core.config import settings

        driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )

        with driver.session() as session:
            # Document 節點數量
            doc_result = session.run("MATCH (d:Document) RETURN count(d) as count")
            doc_count = doc_result.single()["count"]

            # Chunk 節點數量
            chunk_result = session.run("MATCH (c:Chunk) RETURN count(c) as count")
            chunk_count = chunk_result.single()["count"]

            # Entity 節點數量
            entity_result = session.run("MATCH (e:Entity) RETURN count(e) as count")
            entity_count = entity_result.single()["count"]

            # VisualFact 節點數量
            vfact_result = session.run("MATCH (v:VisualFact) RETURN count(v) as count")
            vfact_count = vfact_result.single()["count"]

            # 所有節點數量
            all_result = session.run("MATCH (n) RETURN count(n) as count")
            total_nodes = all_result.single()["count"]

            # 關係數量
            rel_result = session.run("MATCH ()-[r]-() RETURN count(DISTINCT r) as count")
            total_relationships = rel_result.single()["count"]

        driver.close()

        # 顯示統計
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📄 Document", doc_count)
            st.metric("📝 Chunk", chunk_count)
        with col2:
            st.metric("🏷️ Entity", entity_count)
            st.metric("👁️ VisualFact", vfact_count)
        with col3:
            st.metric("🔗 總節點", total_nodes)
            st.metric("⚡ 關係", total_relationships)

    except Exception as e:
        st.error(f"Neo4j 統計載入失敗: {str(e)[:50]}...")

def _get_document_count_neo4j() -> int:
    """獲取 Neo4j 中的文檔數量"""
    try:
        from neo4j import GraphDatabase
        from grag.core.config import settings

        driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )

        with driver.session() as session:
            result = session.run("MATCH (d:Document) RETURN count(d) as count")
            count = result.single()["count"]

        driver.close()
        return count
    except:
        return 0

def _render_file_management_section():
    """渲染文件管理部分 - 列出所有已處理的文件"""
    st.markdown("### 📄 已處理文件管理")

    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )

        with driver.session() as session:
            result = session.run("""
            MATCH (d:Document)
            OPTIONAL MATCH (d)-[:HAS_CHUNK]->(c:Chunk)
            RETURN d.document_id as id, d.title as title, count(c) as chunks,
                   d.source_path as path, d.created_at as created_at,
                   d.hash as hash
            ORDER BY d.created_at DESC
            """)

            documents = []
            for record in result:
                documents.append({
                    'id': record['id'],
                    'title': record['title'],
                    'chunks': record['chunks'],
                    'path': record['path'] or '',
                    'created_at': record['created_at']
                })

        driver.close()

        if documents:
            import pandas as pd
            df = pd.DataFrame(documents)
            df['path'] = df['path'].apply(lambda x: Path(x).name if x else 'Unknown')
            df.columns = ['文件ID', '標題', '文件名', '分塊數', '創建時間']
            st.dataframe(df, use_container_width=True)
            st.success(f"總共 {len(documents)} 個已處理的文件")
        else:
            st.info("目前沒有已處理的文件")

    except Exception as e:
        st.error(f"無法載入文件資料: {str(e)[:100]}...")
        st.info("請檢查Neo4j連線")

def _render_deletion_section():
    """渲染删除測試部分"""
    st.markdown("### 🗑️ 資料庫删除測試")
    st.warning("⚠️ 删除操作不可逆，請謹慎使用")

    # 選擇删除類型
    delete_type = st.selectbox(
        "選擇删除測試類型",
        ["選擇類型", "Document刪除"],
        help="""
        Document刪除: 測試完整文件刪除 (包含所有關聯的chunks和vectors)
        其他删除功能正在開發中...
        """
    )

    if delete_type != "選擇類型":
        st.markdown("---")

        if delete_type == "Document刪除":
            _show_document_deletion_interface()

def _show_document_deletion_interface():
    """Document删除測試 - 支援批量删除"""
    st.markdown("#### 📄 Document批量删除測試")

    try:
        from neo4j import GraphDatabase
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

            # 使用session state來追蹤選中的項目 - 初始化
            if 'selected_documents' not in st.session_state:
                st.session_state.selected_documents = []
            if 'documents_list' not in st.session_state:
                st.session_state.documents_list = [doc['id'] for doc in documents]

            # 全選/取消全選按鈕 - 使用更清晰的邏輯
            col1, col2, col3 = st.columns([2, 2, 3])

            # session state 初始化已在上面做了

            with col1:
                select_all = st.button("✅ 全選全部", key="select_all_button", use_container_width=True)
                if select_all:
                    st.session_state.selected_documents = [doc['id'] for doc in documents]
                    st.success("✅ 已全選所有文件")
                    st.rerun()  # 强制重新渲染以更新checkbox

            with col2:
                clear_all = st.button("❌ 清除全部", key="clear_all_button", use_container_width=True)
                if clear_all:
                    st.session_state.selected_documents = []
                    st.info("ℹ️ 已清除所有選擇")
                    st.rerun()  # 强制重新渲染以更新checkbox

            with col3:
                selected_count = len(st.session_state.selected_documents)
                if selected_count == 0:
                    st.info("**未選擇任何文件**")
                else:
                    st.success(f"**已選擇: {selected_count} 個文件**")

            # 顯示文件列表，每個都有checkbox
            st.markdown("### 📋 文件列表")
            st.info("💡 **操作提示**: 勾選/取消勾選文件會立即更新選擇狀態")

            selected_items = []

            for i, doc in enumerate(documents):
                doc_id = doc['id']

                # 使用容器保持布局整齊
                with st.container():
                    col_checkbox, col_info = st.columns([1, 11])

                    with col_checkbox:
                        # checkbox邏輯 - 不再手動管理session state
                        is_checked = st.checkbox(
                            f"",
                            value=(doc_id in st.session_state.selected_documents),
                            key=f"checkbox_{i}_{doc_id}",  # 使用索引确保唯一性
                            label_visibility="collapsed"
                        )

                        if is_checked:
                            selected_items.append(doc_id)

                    with col_info:
                        # 顯示文件資訊
                        filename = Path(doc['source_path']).name if doc['source_path'] else "Unknown"
                        created_time = doc['created_at'].strftime("%Y-%m-%d %H:%M") if hasattr(doc['created_at'], 'strftime') else str(doc['created_at'])

                        # 使用expander顯示詳細資訊
                        with st.expander(f"📄 {doc['title']} - {filename}", expanded=False):
                            st.markdown(f"""
                            **📋 文件詳細資訊:**
                            - **名稱**: {doc['title']}
                            - **文件名**: {filename}
                            - **分塊數**: {doc['chunks']} 個
                            - **創建時間**: {created_time[:16]}
                            - **文件ID**: `{doc_id[:16]}...`
                            """)

                        # 添加分隔線（輕量級）
                        st.markdown("---")

            # 更新session state - 在所有checkbox渲染後
            st.session_state.selected_documents = selected_items
            final_selected_count = len(selected_items)

            # 顯示最終選擇統計
            if final_selected_count > 0:
                st.success(f"📊 目前已選擇 **{final_selected_count}** 個文件進行删除")

                # 删除按鈕區域
                st.markdown("---")
                st.markdown("### 🗑️ 執行批量删除")

                # 兩個column的佈局
                col_left, col_right = st.columns([2, 1])

                with col_left:
                    # 輸入確認文本來防止意外删除
                    user_confirmation = st.text_input(
                        "🔒 安全確認 - 請輸入 '確認刪除'",
                        placeholder="輸入 '確認刪除' 來啟用刪除按鈕",
                        help=f"這將永久刪除 {final_selected_count} 個文件及其所有相關數據",
                        key="delete_confirmation"
                    )

                    # 調試信息：顯示輸入內容和判斷結果
                    debug_info = f"""
                    輸入內容: '{user_confirmation}'
                    處理後: '{user_confirmation.strip()}'
                    判斷結果: {user_confirmation.strip() == "確認刪除"}
                    """
                    if user_confirmation:  # 只有輸入時才顯示
                        with st.expander("🔍 調試信息 (開發時使用)", expanded=False):
                            st.code(debug_info)

                with col_right:
                    delete_enabled = (user_confirmation.strip() == "確認刪除")
                    delete_button = st.button(
                        f"🗑️ 立即刪除 {final_selected_count} 個文件\n(需正確輸入確認文字)",
                        type="primary",
                        disabled=not delete_enabled,
                        use_container_width=True,
                        key="execute_delete"
                    )

                    # 狀態提示
                    if delete_enabled:
                        st.success("✅ 確認文字正確，已啟用刪除按鈕")
                    elif user_confirmation and user_confirmation.strip():
                        st.warning("⚠️ 請正確輸入 '確認刪除' 來啟用刪除功能")
                    else:
                        st.info("ℹ️ 請輸入確認文字來啟用刪除功能")

                if delete_button and delete_enabled:
                    st.markdown("---")

                    # 顯示即將删除的文件列表確認
                    with st.expander("📋 确认删除清单", expanded=True):
                        st.warning(f"⚠️ 即將删除以下 **{final_selected_count}** 個文件：")
                        for doc_id in selected_items:
                            doc_info = next((d for d in documents if d['id'] == doc_id), None)
                            if doc_info:
                                filename = Path(doc_info['source_path']).name if doc_info['source_path'] else "Unknown"
                                st.write(f"• `{doc_info['title']}` ({filename}) - {doc_info['chunks']} 個分塊")

                    # 最後確認按鈕
                    final_confirm_col1, final_confirm_col2 = st.columns([3, 1])
                    with final_confirm_col1:
                        st.error("🛑 **最後警告**: 此操作無法撤銷！請仔細確認所選文件。")
                    with final_confirm_col2:
                        final_execute = st.button(
                            "💀 最終確認删除",
                            type="primary",
                            use_container_width=True,
                            key="final_execute_delete"
                        )

                    if final_execute:
                        # 執行批量删除
                        with st.spinner(f"正在删除 {final_selected_count} 個文件..."):
                            results = asyncio.run(test_batch_document_deletion(selected_items))

                        # 顯示詳細結果
                        st.markdown("---")
                        st.markdown("### 📊 删除執行結果")

                        if results.get('successful_deletions', 0) > 0:
                            st.success(f"✅ **完全成功删除 {results['successful_deletions']} 個文件**")
                            st.info("🗃️ 同時清除了 Neo4j 圖形數據和 Supabase 向量數據")
                        else:
                            st.error("❌ 沒有成功删除任何文件")

                        # 显示失败情况
                        if results.get('failed_deletions'):
                            st.warning(f"🔴 **删除失敗 ({len(results['failed_deletions'])} 個)**:")
                            for doc_id in results.get('failed_deletions', []):
                                st.write(f"• 文件ID: `{doc_id[:16]}...`")

                        if results.get('errors'):
                            with st.expander("🔍 技術錯誤詳情", expanded=False):
                                for error in results.get('errors', []):
                                    st.code(error)

                        # 如果有成功删除，设置状态并清除选择
                        if results.get('successful_deletions', 0) > 0:
                            st.session_state.database_modified = True
                            st.session_state.selected_documents = []

                            st.balloons()  # 庆祝成功
                            st.markdown("---")
                            if st.button("🔄 刷新頁面查看最新狀態", type="secondary"):
                                st.rerun()
                else:
                    st.info("請輸入確認文字以啟用删除功能")
            else:
                st.info("未選擇任何文件。請勾選上方列表中的文件進行删除。")
        else:
            st.info("📂 目前沒有已處理的文件可以删除")

    except Exception as e:
        st.error(f"載入文件列表失敗: {str(e)[:100]}...")
        st.code(str(e), language='text')

async def test_batch_document_deletion(document_ids: list) -> dict:
    """測試批量Document删除功能"""
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
        error_msg = f"批量删除操作失敗: {str(e)}"
        return {
            "successful_deletions": 0,
            "failed_deletions": document_ids,
            "errors": [error_msg]
        }
