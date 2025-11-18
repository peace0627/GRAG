"""
File Upload Component
文件上傳組件，提供統一的文件選擇介面
"""
import streamlit as st
from typing import List, Any, Optional

class FileUpload:
    """文件上傳組件"""

    def __init__(self):
        self.uploaded_files = []
        self.upload_mode = "single"  # single or batch

    def render_single_upload(self) -> Optional[Any]:
        """渲染單個文件上傳"""
        from grag.frontend.utils import SUPPORTED_FORMATS

        uploaded_file = st.file_uploader(
            "選擇測試文檔",
            type=SUPPORTED_FORMATS,
            help=f"支援的文件格式: {', '.join(SUPPORTED_FORMATS).upper()}",
            key="single_file_uploader"
        )

        return uploaded_file

    def render_batch_upload(self) -> List[Any]:
        """渲染批量文件上傳"""
        from grag.frontend.utils import SUPPORTED_FORMATS, MAX_FILES

        uploaded_files = st.file_uploader(
            "選擇多個測試文檔",
            type=SUPPORTED_FORMATS,
            accept_multiple_files=True,
            help=f"支援的文件格式: {', '.join(SUPPORTED_FORMATS).upper()}，一次最多 {MAX_FILES} 個文件",
            key="batch_file_uploader"
        )

        return uploaded_files or []

    def validate_files(self, files: List[Any]) -> dict:
        """驗證上傳的文件"""
        from grag.frontend.utils import MAX_FILES, get_file_info

        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'file_infos': []
        }

        if not files:
            result['valid'] = False
            result['errors'].append("沒有選擇文件")
            return result

        # 檢查文件數量
        if len(files) > MAX_FILES:
            result['valid'] = False
            result['errors'].append(f"文件數量超過限制，最多 {MAX_FILES} 個")
            return result

        # 驗證每個文件
        for file in files:
            file_info = get_file_info(file)
            result['file_infos'].append(file_info)

            if not file_info['is_supported']:
                result['valid'] = False
                result['errors'].append(f"不支持的文件格式: {file_info['name']}")

            if file.size > 50 * 1024 * 1024:  # 50MB
                result['warnings'].append(f"文件較大: {file_info['name']} ({file_info['size_formatted']})")

        return result

    def render(self, mode: str = "single") -> Any:
        """主要的渲染方法

        Args:
            mode: "single" 或 "batch"

        Returns:
            上傳的文件或文件列表
        """
        self.upload_mode = mode

        if mode == "single":
            return self.render_single_upload()
        else:
            files = self.render_batch_upload()
            if files:
                validation = self.validate_files(files)
                if not validation['valid']:
                    for error in validation['errors']:
                        st.error(error)
                    return []

                if validation['warnings']:
                    for warning in validation['warnings']:
                        st.warning(warning)

                st.success(f"📂 已選擇 {len(files)} 個文件")
                return files

            return []
