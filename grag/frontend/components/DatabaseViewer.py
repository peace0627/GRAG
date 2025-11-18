"""
Database Viewer Component
資料庫查看組件，提供 Neo4j 和 Supabase 的簡單查看介面
"""
import streamlit as st
from typing import Dict, Any, Optional

class DatabaseViewer:
    """資料庫查看組件"""

    def __init__(self):
        pass

    def show_neo4j_summary(self):
        """顯示 Neo4j 摘要統計"""
        try:
            from neo4j import GraphDatabase
            from grag.core.config import settings

            driver = GraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password)
            )

            with driver.session() as session:
                # 基本統計
                doc_result = session.run("MATCH (d:Document) RETURN count(d) as count")
                doc_count = doc_result.single()["count"]

                chunk_result = session.run("MATCH (c:Chunk) RETURN count(c) as count")
                chunk_count = chunk_result.single()["count"]

                entity_result = session.run("MATCH (e:Entity) RETURN count(e) as count")
                entity_count = entity_result.single()["count"]

                vfact_result = session.run("MATCH (v:VisualFact) RETURN count(v) as count")
                vfact_count = vfact_result.single()["count"]

            driver.close()

            # 顯示統計
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("📄 Documents", doc_count)
            with col2:
                st.metric("📝 Chunks", chunk_count)
            with col3:
                st.metric("🏷️ Entities", entity_count)
            with col4:
                st.metric("👁️ VisualFacts", vfact_count)

            return True

        except Exception as e:
            st.error(f"Neo4j 統計載入失敗: {str(e)[:50]}...")
            return False

    def show_supabase_summary(self):
        """顯示 Supabase 摘要統計"""
        try:
            from supabase import create_client
            from grag.core.config import settings

            client = create_client(settings.supabase_url, settings.supabase_key)
            response = client.table('vectors').select('*', count='exact').execute()
            vectors_count = response.count if hasattr(response, 'count') else 0

            # 向量類型統計
            vector_types = {}
            if response.data:
                for item in response.data:
                    vec_type = item.get('type', 'unknown')
                    vector_types[vec_type] = vector_types.get(vec_type, 0) + 1

            # 顯示統計
            col1, col2 = st.columns(2)
            with col1:
                st.metric("🗃️ Vectors", vectors_count)
            with col2:
                types_count = len(vector_types)
                st.metric("🔢 Vector Types", types_count)

            if vector_types:
                st.caption("向量類型分布:")
                for vec_type, count in vector_types.items():
                    st.caption(f"• {vec_type}: {count}")

            return True

        except Exception as e:
            st.error(f"Supabase 統計載入失敗: {str(e)[:50]}...")
            return False

    def show_recent_documents(self, limit: int = 5):
        """顯示最近的文件"""
        try:
            from neo4j import GraphDatabase
            from grag.core.config import settings

            driver = GraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password)
            )

            with driver.session() as session:
                result = session.run("""
                MATCH (d:Document)
                RETURN d.document_id as id, d.title as title,
                       d.created_at as created_at
                ORDER BY d.created_at DESC
                LIMIT $limit
                """, limit=limit)

                documents = []
                for record in result:
                    documents.append({
                        'id': record['id'][:16] + '...',
                        'title': record['title'][:30] + '...' if len(record['title']) > 30 else record['title'],
                        'created_at': record['created_at'].strftime("%Y-%m-%d %H:%M") if record['created_at'] else 'Unknown'
                    })

            driver.close()

            if documents:
                import pandas as pd
                df = pd.DataFrame(documents)
                st.dataframe(df, use_container_width=True)
            else:
                st.info("目前沒有已處理的文件")

        except Exception as e:
            st.error(f"文檔載入失敗: {str(e)[:50]}...")

    def show_recent_vectors(self, limit: int = 10):
        """顯示最近的向量"""
        try:
            from supabase import create_client
            from grag.core.config import settings

            client = create_client(settings.supabase_url, settings.supabase_key)
            response = client.table('vectors').select(
                'vector_id, type, page, created_at'
            ).order('created_at', desc=True).limit(limit).execute()

            if response.data:
                vectors = []
                for item in response.data:
                    vectors.append({
                        'id': item['vector_id'][:8] + '...',
                        'type': item.get('type', 'unknown'),
                        'page': item.get('page', 'N/A'),
                        'created_at': item.get('created_at', 'N/A')[:19] if item.get('created_at') else 'N/A'
                    })

                import pandas as pd
                df = pd.DataFrame(vectors)
                st.dataframe(df, use_container_width=True)
            else:
                st.info("目前沒有向量數據")

        except Exception as e:
            st.error(f"向量載入失敗: {str(e)[:50]}...")

    def get_database_health(self) -> Dict[str, bool]:
        """檢查資料庫健康狀態"""
        health = {}

        # 檢查 Neo4j
        try:
            from neo4j import GraphDatabase
            from grag.core.config import settings

            driver = GraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password)
            )
            driver.verify_connectivity()
            driver.close()
            health['neo4j'] = True
        except:
            health['neo4j'] = False

        # 檢查 Supabase
        try:
            from supabase import create_client
            from grag.core.config import settings

            client = create_client(settings.supabase_url, settings.supabase_key)
            storage = client.storage
            health['supabase'] = True
        except:
            health['supabase'] = False

        return health
