"""
GraphRAG (Graph Retrieval-Augmented Generation)
圖形化檢索增強生成的AI系統

主要功能:
- 文件上傳和處理 (PDF, DOCX, TXT, MD)
- 自動分塊和向量化
- 圖形數據庫 (Neo4j) 和向量數據庫 (Supabase) 存儲
- RESTful API接口
- 命令行工具

使用示例:
    # CLI工具
    python -m grag.cli health        # 檢查系統狀態
    python -m grag.cli upload file.pdf  # 上傳處理文件

    # FastAPI服務
    python -m grag.api.app          # 啟動API服務
"""

from .core.config import settings
from .core.health_service import HealthService

__version__ = "1.0.0"
__author__ = "GraphRAG Team"

# 導出主要組件
__all__ = [
    "settings",
    "HealthService"
]
