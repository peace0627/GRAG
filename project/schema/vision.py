"""
視覺處理相關的 Pydantic Schema 定義
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class VisionTaskType(str, Enum):
    """視覺任務類型"""
    IMAGE_DESCRIPTION = "image_description"      # 圖片描述
    CHART_ANALYSIS = "chart_analysis"           # 圖表分析
    TEXT_EXTRACTION = "text_extraction"         # 文字提取
    OBJECT_DETECTION = "object_detection"       # 物件偵測
    MEDICAL_DEVICE_ANALYSIS = "medical_device_analysis"  # 醫材設備分析


class VisionRequest(BaseModel):
    """視覺處理請求"""
    request_id: str = Field(..., description="請求唯一識別碼")
    asset_id: str = Field(..., description="視覺資源 ID")
    task_type: VisionTaskType = Field(..., description="任務類型")
    image_base64: str = Field(..., description="Base64 編碼的圖片數據")
    context_text: Optional[str] = Field(None, description="相關的上下文文字")
    prompt_template: Optional[str] = Field(None, description="自定義提示模板")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="額外元數據")
    created_at: datetime = Field(default_factory=datetime.now, description="請求創建時間")

    model_config = {
        "use_enum_values": True
    }


class VisualFact(BaseModel):
    """視覺事實"""
    fact_id: str = Field(..., description="事實唯一識別碼")
    asset_id: str = Field(..., description="來源視覺資源 ID")
    content: str = Field(..., description="事實內容")
    fact_type: str = Field(..., description="事實類型（數值、描述、關係等）")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="信心分數")
    bounding_box: Optional[Dict[str, Any]] = Field(None, description="邊界框坐標")
    related_entities: List[str] = Field(default_factory=list, description="相關實體清單")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="額外元數據")
    created_at: datetime = Field(default_factory=datetime.now, description="事實創建時間")

    model_config = {
        "use_enum_values": True
    }


class VisionResponse(BaseModel):
    """視覺處理回應"""
    request_id: str = Field(..., description="對應的請求 ID")
    asset_id: str = Field(..., description="視覺資源 ID")
    task_type: VisionTaskType = Field(..., description="處理的任務類型")
    description: str = Field(..., description="圖片描述")
    extracted_text: Optional[str] = Field(None, description="提取的文字")
    visual_facts: List[VisualFact] = Field(default_factory=list, description="提取的視覺事實")
    objects_detected: List[Dict[str, Any]] = Field(default_factory=list, description="偵測到的物件")
    processing_time: float = Field(..., description="處理時間（秒）")
    token_usage: Optional[Dict[str, int]] = Field(None, description="Token 使用統計")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="整體信心分數")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="額外元數據")
    created_at: datetime = Field(default_factory=datetime.now, description="回應生成時間")

    model_config = {
        "use_enum_values": True
    }
