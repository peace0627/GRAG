"""
實體和關係相關的 Pydantic Schema 定義
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class EntityType(str, Enum):
    """實體類型枚舉"""
    MEDICAL_DEVICE = "medical_device"          # 醫材設備
    PHARMACEUTICAL = "pharmaceutical"          # 藥品
    COMPANY = "company"                        # 公司
    PERSON = "person"                          # 個人
    LOCATION = "location"                      # 地點
    DATE = "date"                             # 日期
    CURRENCY = "currency"                     # 貨幣
    PERCENTAGE = "percentage"                 # 百分比
    REGULATORY_BODY = "regulatory_body"       # 監管機構
    CLINICAL_TRIAL = "clinical_trial"         # 臨床試驗


class RelationType(str, Enum):
    """關係類型枚舉"""
    OWNS = "owns"                             # 擁有
    DEVELOPS = "develops"                      # 開發
    REGULATES = "regulates"                    # 監管
    APPROVES = "approves"                      # 批准
    ACQUIRES = "acquires"                      # 收購
    PARTNERS_WITH = "partners_with"            # 合作
    COMPETES_WITH = "competes_with"            # 競爭
    LOCATED_IN = "located_in"                  # 位於
    EMPLOYED_BY = "employed_by"                # 受僱於
    INVESTS_IN = "invests_in"                  # 投資
    BREAKTHROUGH_DESIGNATION = "breakthrough_designation"  # 突破性指定


class MedicalEntity(BaseModel):
    """醫材領域實體"""
    entity_id: str = Field(..., description="實體唯一識別碼")
    name: str = Field(..., description="實體名稱")
    type: EntityType = Field(..., description="實體類型")
    aliases: List[str] = Field(default_factory=list, description="別名清單")
    description: Optional[str] = Field(None, description="實體描述")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="提取信心分數")
    source_documents: List[str] = Field(default_factory=list, description="來源文檔 ID 清單")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="額外元數據")
    created_at: datetime = Field(default_factory=datetime.now, description="實體創建時間")
    updated_at: datetime = Field(default_factory=datetime.now, description="實體更新時間")

    model_config = {
        "use_enum_values": True
    }


class EntityRelation(BaseModel):
    """實體關係"""
    relation_id: str = Field(..., description="關係唯一識別碼")
    subject_id: str = Field(..., description="主體實體 ID")
    object_id: str = Field(..., description="客體實體 ID")
    relation_type: RelationType = Field(..., description="關係類型")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="關係信心分數")
    evidence_text: str = Field(..., description="證據文字")
    source_document: str = Field(..., description="來源文檔 ID")
    source_page: Optional[int] = Field(None, description="來源頁碼")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="額外元數據")
    created_at: datetime = Field(default_factory=datetime.now, description="關係創建時間")

    model_config = {
        "use_enum_values": True
    }


class EntityResolution(BaseModel):
    """實體對齊/解析"""
    resolution_id: str = Field(..., description="對齊唯一識別碼")
    canonical_entity_id: str = Field(..., description="標準實體 ID")
    resolved_entities: List[str] = Field(..., description="被對齊的實體 ID 清單")
    method: str = Field(..., description="對齊方法（semantic_similarity, rule_based, manual）")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="對齊信心分數")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="額外元數據")
    created_at: datetime = Field(default_factory=datetime.now, description="對齊創建時間")

    model_config = {
        "use_enum_values": True
    }
