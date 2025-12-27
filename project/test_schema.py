#!/usr/bin/env python3
"""
測試 Pydantic Schema 的簡單腳本
"""

from schema import (
    DocumentMetadata, DocumentType, VisualAsset, VisualAssetStatus,
    QueryRequest, QueryIntent, QueryResponse, Evidence, EvidenceType,
    VisionRequest, VisionTaskType, VisionResponse, VisualFact,
    MedicalEntity, EntityType, EntityRelation, RelationType
)

def test_document_schemas():
    """測試文檔相關 schema"""
    print("🧪 測試文檔 Schema...")

    # 測試 DocumentMetadata
    metadata = DocumentMetadata(
        document_id="doc_001",
        filename="medical_report.pdf",
        document_type=DocumentType.PDF,
        file_size=1024000,
        page_count=10
    )
    print(f"✅ DocumentMetadata: {metadata.document_id}")

    # 測試 VisualAsset
    asset = VisualAsset(
        asset_id="asset_001",
        document_id="doc_001",
        page_number=5,
        position={"x": 100, "y": 200, "width": 300, "height": 150},
        image_path="/path/to/image.jpg",
        status=VisualAssetStatus.PENDING
    )
    print(f"✅ VisualAsset: {asset.asset_id}, status: {asset.status}")

def test_query_schemas():
    """測試查詢相關 schema"""
    print("🧪 測試查詢 Schema...")

    # 測試 QueryRequest
    request = QueryRequest(
        query_id="query_001",
        question="美敦力公司的研發支出如何？",
        intent=QueryIntent.TEXT_ONLY
    )
    print(f"✅ QueryRequest: {request.question}")

    # 測試 Evidence
    evidence = Evidence(
        evidence_id="evidence_001",
        type=EvidenceType.TEXT_CHUNK,
        content="根據財報顯示，2023年研發支出為25億美元",
        source_document="doc_001",
        source_page=15,
        confidence_score=0.95
    )
    print(f"✅ Evidence: {evidence.content[:30]}...")

def test_vision_schemas():
    """測試視覺相關 schema"""
    print("🧪 測試視覺 Schema...")

    # 測試 VisionRequest
    vision_request = VisionRequest(
        request_id="vision_001",
        asset_id="asset_001",
        task_type=VisionTaskType.CHART_ANALYSIS,
        image_base64="base64_encoded_image_data_here"
    )
    print(f"✅ VisionRequest: {vision_request.task_type}")

    # 測試 VisualFact
    fact = VisualFact(
        fact_id="fact_001",
        asset_id="asset_001",
        content="圖表顯示2023年銷售額成長15%",
        fact_type="numerical_value",
        confidence_score=0.88
    )
    print(f"✅ VisualFact: {fact.content}")

def test_entity_schemas():
    """測試實體相關 schema"""
    print("🧪 測試實體 Schema...")

    # 測試 MedicalEntity
    entity = MedicalEntity(
        entity_id="entity_001",
        name="Medtronic",
        type=EntityType.COMPANY,
        aliases=["美敦力", "Medtronic Inc."],
        confidence_score=0.98
    )
    print(f"✅ MedicalEntity: {entity.name}, aliases: {entity.aliases}")

    # 測試 EntityRelation
    relation = EntityRelation(
        relation_id="relation_001",
        subject_id="entity_001",
        object_id="entity_002",
        relation_type=RelationType.DEVELOPS,
        confidence_score=0.85,
        evidence_text="Medtronic開發了新型心臟起搏器",
        source_document="doc_001"
    )
    print(f"✅ EntityRelation: {relation.subject_id} {relation.relation_type} {relation.object_id}")

if __name__ == "__main__":
    print("🚀 開始 Schema 測試\n")

    try:
        test_document_schemas()
        print()
        test_query_schemas()
        print()
        test_vision_schemas()
        print()
        test_entity_schemas()
        print()
        print("🎉 所有 Schema 測試通過！")
    except Exception as e:
        print(f"❌ Schema 測試失敗: {str(e)}")
        raise
