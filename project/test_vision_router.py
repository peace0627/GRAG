#!/usr/bin/env python3
"""
測試 Vision Router 的功能
"""

from schema import (
    QueryRequest,
    QueryIntent,
    VisualAsset,
    VisualAssetStatus,
    VisionRequest,
    VisionTaskType
)
from graph_nodes.vision_router import VisionRouter, VisionRoutingDecision


def test_intent_analysis():
    """測試意圖分析功能"""
    print("🧪 測試意圖分析...")

    router = VisionRouter()

    # 測試純文字查詢
    text_queries = [
        "美敦力公司是什麼？",
        "介紹一下心臟起搏器",
        "什麼是醫材法規？",
        "醫療器械的分類有哪些？"
    ]

    for query in text_queries:
        intent = router.analyze_intent(query)
        print(f"  📝 '{query}' -> {intent}")
        assert intent == QueryIntent.TEXT_ONLY, f"預期 TEXT_ONLY，但得到 {intent}"

    # 測試需要視覺的查詢
    visual_queries = [
        "圖表顯示銷售趨勢如何？",
        "營收成長變化圖表",
        "比較不同產品的市場佔有率",
        "財務數據的圖表分析"
    ]

    for query in visual_queries:
        intent = router.analyze_intent(query)
        print(f"  📊 '{query}' -> {intent}")
        assert intent == QueryIntent.VISUAL_REQUIRED, f"預期 VISUAL_REQUIRED，但得到 {intent}"

    print("✅ 意圖分析測試通過")


def test_cache_check():
    """測試快取檢查功能"""
    print("🧪 測試快取檢查...")

    router = VisionRouter()

    # 建立測試視覺資源
    assets = [
        VisualAsset(
            asset_id="asset_001",
            document_id="doc_001",
            page_number=5,
            position={"x": 100, "y": 200},
            image_path="/path/to/chart1.jpg",
            status=VisualAssetStatus.COMPLETED,
            visual_facts=["銷售額2023年成長15%"]
        ),
        VisualAsset(
            asset_id="asset_002",
            document_id="doc_001",
            page_number=10,
            position={"x": 150, "y": 250},
            image_path="/path/to/chart2.jpg",
            status=VisualAssetStatus.PENDING,
            visual_facts=[]
        )
    ]

    cache_status = router.check_visual_cache(assets)
    print(f"  📦 快取狀態: {cache_status}")

    assert cache_status["asset_001"] == True, "已完成的資源應該被標記為已快取"
    assert cache_status["asset_002"] == False, "待處理的資源應該被標記為未快取"

    print("✅ 快取檢查測試通過")


def test_routing_decision():
    """測試路由決策功能"""
    print("🧪 測試路由決策...")

    router = VisionRouter()

    # 測試純文字查詢
    text_request = QueryRequest(
        query_id="query_001",
        question="美敦力公司是什麼？",
        intent=QueryIntent.TEXT_ONLY
    )

    assets = [
        VisualAsset(
            asset_id="asset_001",
            document_id="doc_001",
            page_number=5,
            position={"x": 100, "y": 200},
            image_path="/path/to/image.jpg",
            status=VisualAssetStatus.PENDING
        )
    ]

    decision = router.route_vision_request(text_request, assets)
    print(f"  🚫 純文字查詢決策: needs_vision={decision.needs_vision}, reasoning='{decision.reasoning}'")
    assert not decision.needs_vision, "純文字查詢不應該需要視覺"
    assert decision.confidence_score > 0.9, "信心分數應該很高"

    # 測試需要視覺的查詢
    visual_request = QueryRequest(
        query_id="query_002",
        question="圖表顯示銷售趨勢如何？",
        intent=QueryIntent.VISUAL_REQUIRED
    )

    decision = router.route_vision_request(visual_request, assets)
    print(f"  ✅ 視覺查詢決策: needs_vision={decision.needs_vision}, assets={decision.required_assets}")
    assert decision.needs_vision, "視覺查詢應該需要視覺推理"
    assert "asset_001" in decision.required_assets, "應該包含未快取的資源"

    print("✅ 路由決策測試通過")


def test_vision_request_creation():
    """測試視覺請求創建功能"""
    print("🧪 測試視覺請求創建...")

    router = VisionRouter()

    # 創建路由決策
    decision = VisionRoutingDecision(
        needs_vision=True,
        required_assets=["asset_001", "asset_002"],
        reasoning="需要視覺推理",
        confidence_score=0.85
    )

    # 創建查詢請求
    query_request = QueryRequest(
        query_id="query_003",
        question="比較產品A和產品B的市場佔有率變化",
        intent=QueryIntent.VISUAL_REQUIRED
    )

    # 創建視覺資源
    assets = [
        VisualAsset(
            asset_id="asset_001",
            document_id="doc_001",
            page_number=5,
            position={"x": 100, "y": 200},
            image_path="/path/to/chart1.jpg",
            status=VisualAssetStatus.PENDING,
            image_base64="base64_data_1"
        ),
        VisualAsset(
            asset_id="asset_002",
            document_id="doc_001",
            page_number=10,
            position={"x": 150, "y": 250},
            image_path="/path/to/chart2.jpg",
            status=VisualAssetStatus.PENDING,
            image_base64="base64_data_2"
        )
    ]

    vision_requests = router.create_vision_requests(decision, query_request, assets)
    print(f"  📋 創建了 {len(vision_requests)} 個視覺請求")

    assert len(vision_requests) == 2, "應該創建2個視覺請求"

    for request in vision_requests:
        assert request.request_id.startswith("vision_query_003_"), "請求ID格式不正確"
        assert request.task_type == VisionTaskType.CHART_ANALYSIS, "應該是圖表分析任務"
        assert request.context_text == query_request.question, "應該包含原始問題"
        print(f"    📄 請求: {request.request_id} -> {request.task_type}")

    print("✅ 視覺請求創建測試通過")


if __name__ == "__main__":
    print("🚀 開始 Vision Router 測試\n")

    try:
        test_intent_analysis()
        print()
        test_cache_check()
        print()
        test_routing_decision()
        print()
        test_vision_request_creation()
        print()
        print("🎉 所有 Vision Router 測試通過！")
    except Exception as e:
        print(f"❌ 測試失敗: {str(e)}")
        raise
