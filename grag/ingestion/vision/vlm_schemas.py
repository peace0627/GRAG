"""Pydantic models for Vision Language Model output"""

from typing import List, Optional
from pydantic import BaseModel, Field


class VLMRegion(BaseModel):
    """Individual visual region from VLM analysis"""
    region_id: str = Field(..., description="Unique region identifier")
    modality: str = Field(..., description="Content modality (text, table, chart, image)")
    description: str = Field(..., description="Visual description of the region")
    bbox: List[float] = Field(..., description="Bounding box [x, y, width, height]")
    confidence: float = Field(default=1.0, description="Detection confidence score")
    page: int = Field(default=1, description="Page number")


class TableData(BaseModel):
    """Structured table data extraction"""
    table_id: str = Field(..., description="Unique table identifier")
    csv_content: str = Field(..., description="Table content as CSV string")
    bbox: List[float] = Field(..., description="Table bounding box")
    page: int = Field(default=1, description="Page number")


class ChartData(BaseModel):
    """Chart data extraction"""
    chart_id: str = Field(..., description="Unique chart identifier")
    chart_type: str = Field(..., description="Type of chart (line, bar, pie, etc.)")
    description: str = Field(..., description="Chart description")
    data_points: Optional[List[List[float]]] = Field(None, description="Extracted data points")
    bbox: List[float] = Field(..., description="Chart bounding box")
    page: int = Field(default=1, description="Page number")


class VLMOutput(BaseModel):
    """Complete VLM processing output for a document"""
    file_id: str = Field(..., description="Source file identifier")
    area_id: Optional[str] = Field(None, description="Knowledge area identifier")
    ocr_text: str = Field("", description="Full OCR extracted text")
    regions: List[VLMRegion] = Field(default_factory=list, description="Visual regions")
    tables: List[TableData] = Field(default_factory=list, description="Extracted tables")
    charts: List[ChartData] = Field(default_factory=list, description="Extracted charts")
    visual_facts: List[dict] = Field(default_factory=list, description="High-level facts and descriptions")
    processing_time: float = Field(default=0.0, description="Processing time in seconds")
    metadata: dict = Field(default_factory=dict, description="Additional processing metadata")
