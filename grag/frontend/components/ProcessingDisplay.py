"""
Processing Display Component
處理結果顯示組件，提供統一的處理狀態和結果展示
"""
import streamlit as st
from typing import Dict, List, Any, Optional

class ProcessingDisplay:
    """處理結果顯示組件"""

    def __init__(self):
        pass

    def show_processing_progress(self, current: int, total: int, message: str = ""):
        """顯示處理進度"""
        if total > 0:
            progress = current / total
            st.progress(progress, f"{message} ({current}/{total})")

    def show_file_result(self, result: Dict[str, Any]):
        """顯示單個文件處理結果"""
        if result.get("success"):
            st.success("🎉 處理成功！")

            # 處理統計
            metadata = result.get("metadata", {})
            self._show_processing_stats(metadata)

        else:
            st.error(f"❌ 處理失敗: {result.get('error', '未知錯誤')}")

    def show_batch_results(self, results: List[Dict[str, Any]]):
        """顯示批量處理結果"""
        total_files = len(results)
        successful = sum(1 for r in results if r.get('success', False))
        failed = total_files - successful

        # 總結統計
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📂 總文件數", total_files)
        with col2:
            st.metric("✅ 成功處理", successful)
        with col3:
            st.metric("❌ 處理失敗", failed)

        # 詳細結果
        st.markdown("### 📋 詳細結果")

        successful_results = [r for r in results if r.get('success')]
        failed_results = [r for r in results if not r.get('success')]

        # 成功結果
        if successful_results:
            with st.expander(f"✅ 成功的文件 ({len(successful_results)} 個)", expanded=True):
                for result in successful_results:
                    self._show_individual_success(result)

        # 失敗結果
        if failed_results:
            with st.expander(f"❌ 失敗的文件 ({len(failed_results)} 個)", expanded=False):
                for result in failed_results:
                    self._show_individual_failure(result)

    def _show_individual_success(self, result: Dict[str, Any]):
        """顯示單個成功結果"""
        filename = result.get('filename', 'Unknown')
        metadata = result.get('metadata', {})

        st.markdown(f"**{filename}** ✅")

        # 簡要統計
        chunks = metadata.get('chunks_created', 0)
        embeddings = metadata.get('embeddings_created', 0)

        col1, col2 = st.columns(2)
        with col1:
            st.caption(f"分塊: {chunks}")
        with col2:
            st.caption(f"向量: {embeddings}")

    def _show_individual_failure(self, result: Dict[str, Any]):
        """顯示單個失敗結果"""
        filename = result.get('filename', 'Unknown')
        error = result.get('error', '未知錯誤')

        st.markdown(f"**{filename}** ❌")
        st.caption(f"錯誤: {error}")

    def _show_processing_stats(self, metadata: Dict[str, Any]):
        """顯示處理統計資訊"""
        if not metadata:
            return

        # 基本統計
        processing_time = metadata.get('processing_time', 0)
        chunks_created = metadata.get('chunks_created', 0)
        embeddings_created = metadata.get('embeddings_created', 0)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("⏱️ 處理時間", ".1f")
        with col2:
            st.metric("📊 分塊數", chunks_created)
        with col3:
            st.metric("🧮 向量數", embeddings_created)

        # 嵌入資訊
        if embeddings_created > 0:
            provider_name = metadata.get("embedding_provider", "unknown").upper()
            dimension = metadata.get("embedding_dimension", "N/A")
            st.info(f"🤖 **嵌入資訊**: 使用 {provider_name} 模型，"
                   f"向量維度: {dimension}，生成向量: {embeddings_created} 個")

            # 向量類型統計（如果有的話）
            vector_stats = metadata.get("vector_type_stats", {})
            if vector_stats:
                vector_info = []
                for vec_type, count in vector_stats.items():
                    if count > 0:
                        vector_info.append(f"{vec_type}: {count}")
                if vector_info:
                    st.caption(f"向量類型分布: {' | '.join(vector_info)}")

    def show_real_time_processing(self, filename: str, stage: str, progress: float):
        """顯示實時處理狀態"""
        st.markdown(f"**正在處理**: {filename}")
        st.progress(progress, f"階段: {stage}")

    def show_processing_summary(self, stats: Dict[str, Any]):
        """顯示處理總結"""
        from grag.frontend.utils import display_metrics_grid

        st.markdown("### 📊 處理總結")

        # 轉換為可顯示的格式
        display_stats = {}
        for key, value in stats.items():
            display_stats[key] = str(value) if not isinstance(value, str) else value

        display_metrics_grid(display_stats, columns=2)

    def show_error_details(self, errors: List[str]):
        """顯示錯誤詳細資訊"""
        if not errors:
            return

        st.markdown("### ⚠️ 錯誤詳細資訊")

        with st.expander("點擊查看錯誤詳情", expanded=False):
            for i, error in enumerate(errors, 1):
                st.error(f"{i}. {error}")

    def create_processing_report(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """創建處理報告"""
        total_files = len(results)
        successful = sum(1 for r in results if r.get('success', False))
        failed = total_files - successful

        report = {
            'summary': {
                'total_files': total_files,
                'successful': successful,
                'failed': failed,
                'success_rate': ".1f"
            },
            'performance': self._calculate_performance_stats(results),
            'errors': [r.get('error') for r in results if not r.get('success')]
        }

        return report

    def _calculate_performance_stats(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """計算效能統計"""
        successful_results = [r for r in results if r.get('success')]

        if not successful_results:
            return {}

        avg_processing_time = sum(r.get('metadata', {}).get('processing_time', 0)
                                for r in successful_results) / len(successful_results)

        total_chunks = sum(r.get('metadata', {}).get('chunks_created', 0)
                          for r in successful_results)

        total_embeddings = sum(r.get('metadata', {}).get('embeddings_created', 0)
                             for r in successful_results)

        return {
            'avg_processing_time': ".1f",
            'total_chunks': total_chunks,
            'total_embeddings': total_embeddings,
            'avg_chunks_per_file': total_chunks / len(successful_results),
            'avg_embeddings_per_file': total_embeddings / len(successful_results)
        }
