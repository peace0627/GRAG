"""
Generic Helper Functions
通用輔助函數，提升代碼重用性
"""
import time
from typing import Any, Optional
from pathlib import Path

def format_file_size(size_bytes: int) -> str:
    """格式化文件大小顯示"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return ".1f"
        size_bytes /= 1024.0
    return ".1f"

def format_timestamp(timestamp: Any, format_str: str = "%Y-%m-%d %H:%M") -> str:
    """格式化時間戳顯示"""
    if hasattr(timestamp, 'strftime'):
        return timestamp.strftime(format_str)
    elif isinstance(timestamp, (int, float)):
        return time.strftime(format_str, time.localtime(timestamp))
    else:
        return str(timestamp)[:16]

def truncate_text(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """截斷長文本"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix

def validate_file_format(filename: Path, supported_formats: list) -> bool:
    """驗證文件格式"""
    extension = filename.suffix.lower().lstrip('.')
    return extension in supported_formats

def get_file_info(uploaded_file) -> dict:
    """獲取上傳文件的基本信息"""
    filename = uploaded_file.name
    file_path = Path(filename)

    return {
        'name': filename,
        'path': file_path,
        'size': uploaded_file.size,
        'size_formatted': format_file_size(uploaded_file.size),
        'extension': file_path.suffix.lower(),
        'is_supported': validate_file_format(file_path, ['pdf', 'docx', 'txt', 'md'])
    }

def safe_getattr(obj: Any, attr_path: str, default: Any = None) -> Any:
    """安全獲取對象屬性，支持嵌套屬性"""
    try:
        for attr in attr_path.split('.'):
            obj = getattr(obj, attr)
        return obj
    except (AttributeError, TypeError):
        return default

def merge_dicts(*dicts: dict) -> dict:
    """合併多個字典"""
    result = {}
    for d in dicts:
        if d:
            result.update(d)
    return result

def create_progress_callback():
    """創建一個進度回調函數生成器"""
    def progress_callback(current: int, total: int, message: str = ""):
        if total > 0:
            progress = current / total
            st.progress(progress, f"{message} ({current}/{total})")
    return progress_callback
