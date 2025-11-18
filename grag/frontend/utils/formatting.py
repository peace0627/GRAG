"""
Formatting Utilities for Display
資料格式化工具，提升界面展示品質
"""
import streamlit as st
from typing import Dict, List, Any, Optional

def format_processing_stats(metadata: dict) -> dict:
    """格式化處理統計資訊"""
    if not metadata:
        return {}

    formatted = {
        '處理時間': f"{metadata.get('processing_time', 0):.1f}秒",
        '分塊數量': metadata.get('chunks_created', 0),
        '向量數量': metadata.get('embeddings_created', 0)
    }

    # 添加嵌入信息
    if metadata.get('embeddings_created', 0) > 0:
        embedding_info = metadata.get('embedding_provider', 'unknown').upper()
        dimension = metadata.get('embedding_dimension', 0)
        formatted['嵌入資訊'] = f"{embedding_info} ({dimension}維)"

    # 添加向量類型統計
    vector_stats = metadata.get('vector_type_stats', {})
    if vector_stats:
        vector_breakdown = []
        for vec_type, count in vector_stats.items():
            if count > 0:
                vector_breakdown.append(f"{vec_type}: {count}")
        if vector_breakdown:
            formatted['向量分布'] = " | ".join(vector_breakdown)

    return formatted

def format_vector_stats(stats: dict) -> dict:
    """格式化向量統計顯示"""
    formatted = {}

    if 'total_vectors' in stats:
        formatted['總向量數'] = stats['total_vectors']

    if 'vector_types' in stats:
        type_info = []
        for vec_type, count in stats['vector_types'].items():
            type_info.append(f"{vec_type}: {count}")
        formatted['向量類型分布'] = " | ".join(type_info)

    if 'avg_dimensions' in stats:
        formatted['平均維度'] = stats['avg_dimensions']

    return formatted

def format_database_stats(stats: dict) -> dict:
    """格式化數據庫統計顯示"""
    formatted = {}

    # Neo4j 統計
    neo4j_stats = stats.get('neo4j', {})
    if neo4j_stats:
        formatted['Document 節點'] = neo4j_stats.get('documents', 0)
        formatted['Chunk 節點'] = neo4j_stats.get('chunks', 0)
        formatted['Entity 節點'] = neo4j_stats.get('entities', 0)
        formatted['VisualFact 節點'] = neo4j_stats.get('visualfacts', 0)
        formatted['總節點數'] = neo4j_stats.get('total_nodes', 0)

    # Supabase 統計
    supabase_stats = stats.get('supabase', {})
    if supabase_stats:
        formatted['向量記錄數'] = supabase_stats.get('vectors', 0)

    return formatted

def display_metrics_grid(metrics: dict, columns: int = 3):
    """以網格形式顯示多個指標"""
    if not metrics:
        return

    items = list(metrics.items())
    rows = (len(items) + columns - 1) // columns

    for i in range(rows):
        cols = st.columns(columns)
        for j in range(columns):
            idx = i * columns + j
            if idx < len(items):
                key, value = items[idx]
                with cols[j]:
                    st.metric(key, value)

def format_error_message(error: Any, max_length: int = 100) -> str:
    """格式化錯誤信息顯示"""
    if isinstance(error, Exception):
        error_msg = str(error)
    elif isinstance(error, dict) and 'error' in error:
        error_msg = error['error']
    else:
        error_msg = str(error)

    if len(error_msg) > max_length:
        error_msg = error_msg[:max_length - 3] + "..."

    return error_msg

def format_batch_results(results: List[dict]) -> dict:
    """格式化批量處理結果"""
    total_files = len(results)
    successful = sum(1 for r in results if r.get('success', False))
    failed = total_files - successful

    formatted = {
        '總文件數': total_files,
        '成功處理': successful,
        '處理失敗': failed,
        '成功率': ".1f"
    }

    if successful > 0:
        avg_processing_time = sum(r.get('processing_time', 0) for r in results if r.get('success')) / successful
        formatted['平均處理時間'] = ".1f"
        formatted['總向量生成'] = sum(r.get('metadata', {}).get('embeddings_created', 0) for r in results if r.get('success'))

    return formatted

def create_status_badge(status: bool, text: str) -> str:
    """創建狀態徽章"""
    if status:
        return f"🟢 {text}"
    else:
        return f"🔴 {text}"

def format_file_list(files: List[dict], max_display: int = 5) -> str:
    """格式化文件列表顯示"""
    if not files:
        return "無文件"

    display_files = files[:max_display]
    file_names = [f['name'][:20] + "..." if len(f['name']) > 20 else f['name'] for f in display_files]

    if len(files) > max_display:
        file_names.append(f"... 等 {len(files) - max_display} 個文件")

    return ", ".join(file_names)
