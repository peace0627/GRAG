"""
Frontend Page Views
各個頁面的視圖邏輯，組合組件和服務
"""

from .document_processing import render_document_processing_page
from .database_management import render_database_management_page

__all__ = [
    'render_document_processing_page',
    'render_database_management_page'
]
