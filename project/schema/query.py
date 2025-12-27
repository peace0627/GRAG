"""
查詢相關的 Pydantic Schema 定義
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field


class QueryIntent(str, Enum):
    """查詢意圖枚舉"""
    TEXT_ONLY = "text_only"              # 純文本查詢
    VISUAL_REQUIRED = "visual_required"  # 需要視覺解析
    ENTITY_EXTRACTION = "entity_extraction"  # 實體提取
    RELATION_ANALYSIS = "relation_analysis"   # 關係分析


class EvidenceType(str, Enum):
    """證據類型"""
    TEXT_CHUNK = "text_chunk"        # 文本分塊
    VISUAL_FACT = "visual_fact"      # 視覺事實
    ENTITY_RELATION = "entity_relation"  # 實體關係


class QueryRequest(BaseModel):
    """查詢請求"""
    query_id: str = Field(..., description="查詢唯一識別碼")
    question: str = Field(..., description="用戶問題")
    context_documents: List[str] = Field(default_factory=list, description="相關文檔 ID 清單")
    intent: Optional[QueryIntent] = Field(None, description="查詢意圖（可由系統自動檢測）")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="額外元數據")
    created_at: datetime = Field(default_factory=datetime.now, description="請求創建時間")

    model_config = {
        "use_enum_values": True
    }


class Evidence(BaseModel):
    """證據來源"""
    evidence_id: str = Field(..., description="證據唯一識別碼")
    type: EvidenceType = Field(..., description="證據類型")
    content: str = Field(..., description="證據內容")
    source_document: str = Field(..., description="來源文檔 ID")
    source_page: Optional[int] = Field(None, description="來源頁碼")
    source_asset: Optional[str] = Field(None, description="來源視覺資源 ID")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="信心分數")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="額外元數據")

    model_config = {
        "use_enum_values": True
    }


class QueryResponse(BaseModel):
    """查詢回應"""
    query_id: str = Field(..., description="對應的查詢 ID")
    answer: str = Field(..., description="回答內容")
    intent: QueryIntent = Field(..., description="識別出的查詢意圖")
    evidence_list: List[Evidence] = Field(default_factory=list, description="證據來源清單")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="整體回答信心分數")
    processing_time: float = Field(..., description="處理時間（秒）")
    token_usage: Optional[Dict[str, int]] = Field(None, description="Token 使用統計")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="額外元數據")
    created_at: datetime = Field(default_factory=datetime.now, description="回應生成時間")

    model_config = {
        "use_enum_values": True
    }
