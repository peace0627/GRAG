"""
UI Constants and Configuration
集中管理界面相關的常量和配置
"""

# UI 基本配置
UI_CONFIG = {
    'page_settings': {
        'page_title': "🔗 LangChain處理測試器",
        'page_icon': "🔗",
        'layout': "wide",
        'initial_sidebar_state': "expanded"
    },
    'capabilities_order': ['multimodal', 'text', 'database'],
    'processing_options': {
        'vlm_strategies': ['自動判斷', '強制開啟', '強制關閉'],
        'upload_modes': ['單個文件', '批量上傳']
    },
    'page_options': ['文檔處理', '資料庫管理'],
    'max_files': 10,
    'supported_formats': ['pdf', 'docx', 'txt', 'md']
}

# 圖標和樣式
ICONS = {
    'multimodal': '🎨',
    'text': '📝',
    'database': '🗃️',
    'processing': '⚙️',
    'upload': '📤',
    'download': '📥',
    'success': '✅',
    'error': '❌',
    'warning': '⚠️',
    'info': 'ℹ️'
}

# 狀態映射
STATUS_MAPPING = {
    True: ('✅', 'lime'),
    False: ('❌', 'red'),
    None: ('⏳', 'orange')
}

# 常用文本
MESSAGES = {
    'processing': {
        'uploading': '正在上傳文件...',
        'processing': '正在處理文件...',
        'analyzing': '正在分析結果...',
        'complete': '處理完成！',
        'error': '處理過程中發生錯誤'
    },
    'validation': {
        'file_too_large': '文件大小超過限制',
        'unsupported_format': '不支持的文件格式',
        'duplicate_file': '發現重複文件',
        'max_files_reached': '已達到最大文件數量限制'
    },
    'ui': {
        'no_files_selected': '請選擇要處理的文件',
        'confirm_deletion': '確定要刪除這些文件嗎？',
        'deletion_warning': '此操作不可逆，請謹慎操作'
    }
}

# 導出常用常量
MAX_FILES = UI_CONFIG['max_files']
SUPPORTED_FORMATS = UI_CONFIG['supported_formats']
