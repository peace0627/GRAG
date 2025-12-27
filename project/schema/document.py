"""
文檔相關的 Pydantic Schema 定義
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    """文檔類型枚舉"""
    PDF = "pdf"
    IMAGE = "image"
    TEXT = "text"


class VisualAssetStatus(str, Enum):
    """視覺資源狀態"""
    PENDING = "pending"      # 等待解析
    COMPLETED = "completed"  # 已解析完畢
    FAILED = "failed"        # 解析失敗


class DocumentMetadata(BaseModel):
    """文檔元數據"""
    document_id: str = Field(..., description="文檔唯一識別碼")
    filename: str = Field(..., description="原始檔案名稱")
    document_type: DocumentType = Field(..., description="文檔類型")
    file_size: int = Field(..., description="檔案大小（字節）")
    page_count: Optional[int] = Field(None, description="頁數")
    created_at: datetime = Field(default_factory=datetime.now, description="創建時間")
    processed_at: Optional[datetime] = Field(None, description="處理完成時間")
    source_url: Optional[str] = Field(None, description="來源 URL")

    model_config = {
        "use_enum_values": True
    }


class VisualAsset(BaseModel):
    """視覺資源（圖片/圖表）"""
    asset_id: str = Field(..., description="視覺資源唯一識別碼")
    document_id: str = Field(..., description="所屬文檔 ID")
    page_number: int = Field(..., description="頁碼")
    position: Dict[str, Any] = Field(..., description="在頁面中的位置信息")
    image_path: str = Field(..., description="圖片檔案路徑")
    image_base64: Optional[str] = Field(None, description="Base64 編碼的圖片數據")
    status: VisualAssetStatus = Field(default=VisualAssetStatus.PENDING, description="解析狀態")
    description: Optional[str] = Field(None, description="圖片描述")
    extracted_text: Optional[str] = Field(None, description="OCR 提取的文字")
    visual_facts: List[str] = Field(default_factory=list, description="視覺事實清單")
    created_at: datetime = Field(default_factory=datetime.now, description="創建時間")
    processed_at: Optional[datetime] = Field(None, description="處理完成時間")

    model_config = {
        "use_enum_values": True
    }


class DocumentChunk(BaseModel):
    """文檔分塊"""
    chunk_id: str = Field(..., description="分塊唯一識別碼")
    document_id: str = Field(..., description="所屬文檔 ID")
    content: str = Field(..., description="分塊內容")
    page_number: int = Field(..., description="頁碼")
    position: Dict[str, Any] = Field(..., description="位置信息")
    token_count: int = Field(..., description="Token 數量")
    visual_assets: List[str] = Field(default_factory=list, description="關聯的視覺資源 ID 清單")
    entities: List[str] = Field(default_factory=list, description="提取的實體清單")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="額外元數據")
    created_at: datetime = Field(default_factory=datetime.now, description="創建時間")

    model_config = {
        "use_enum_values": True
    }
