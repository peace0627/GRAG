"""
視覺路由器 - 決定是否需要視覺推理的核心組件

負責分析查詢意圖，檢查視覺資源快取狀態，
決定是否需要調用 Gemma 3 的視覺能力。
"""

import re
from typing import Dict, List, Optional, Set
from dataclasses import dataclass

from schema import (
    QueryIntent,
    QueryRequest,
    VisualAsset,
    VisualAssetStatus,
    VisionRequest,
    VisionTaskType
)


@dataclass
class VisionRoutingDecision:
    """視覺路由決策結果"""
    needs_vision: bool
    required_assets: List[str]
    reasoning: str
    confidence_score: float


class VisionRouter:
    """
    視覺路由器 - 實現按需視覺調用邏輯

    核心機制：
    1. 意圖分析：檢測查詢是否需要視覺信息
    2. 快取檢查：確認視覺資源是否已分析
    3. 路由決策：決定是否調用視覺推理
    """

    def __init__(self):
        # 視覺相關關鍵詞模式
        self.vision_keywords = {
            'chart': ['圖表', '圖示', 'chart', 'graph', 'diagram', 'plot'],
            'trend': ['趨勢', '變化', '成長', 'trend', 'growth', 'change'],
            'comparison': ['比較', '對比', 'compare', 'versus', 'vs'],
            'percentage': ['百分比', '比例', 'percentage', 'ratio', 'share'],
            'financial': ['財務', '營收', '利潤', '收入', 'profit', 'revenue'],
            'visual': ['顯示', '展示', '呈現', 'show', 'display', 'present'],
            'data': ['數據', '資料', '統計', 'data', 'statistics']
        }

        # 不需要視覺的純文字查詢模式
        self.text_only_patterns = [
            r'^(什麼是|介紹|定義|解釋|describe|explain)',
            r'.*(公司|企業|組織|人|個人|地點|時間|日期).*(是誰|在哪|什麼時候)',
            r'.*(總結|摘要|總結|summary|overview)',
            r'.*(法律|法規|政策|regulation|policy)',
            r'.*(歷史|發展|沿革|history|evolution)'
        ]

    def analyze_intent(self, question: str) -> QueryIntent:
        """
        分析查詢意圖，決定是否需要視覺解析

        Args:
            question: 用戶問題

        Returns:
            QueryIntent: 識別出的查詢意圖
        """
        question_lower = question.lower()

        # 檢查是否為純文字查詢
        for pattern in self.text_only_patterns:
            if re.search(pattern, question, re.IGNORECASE):
                return QueryIntent.TEXT_ONLY

        # 檢查是否包含視覺相關關鍵詞
        visual_score = 0
        for category, keywords in self.vision_keywords.items():
            for keyword in keywords:
                if keyword.lower() in question_lower:
                    visual_score += 1
                    break

        # 基於關鍵詞數量決定意圖
        if visual_score >= 2:
            return QueryIntent.VISUAL_REQUIRED
        elif visual_score == 1:
            # 單一關鍵詞可能是模糊的，需要進一步分析上下文
            return self._analyze_context(question)
        else:
            return QueryIntent.TEXT_ONLY

    def _analyze_context(self, question: str) -> QueryIntent:
        """
        分析上下文來決定是否需要視覺

        Args:
            question: 用戶問題

        Returns:
            QueryIntent: 分析結果
        """
        # 對於包含比較關鍵詞的查詢，即使較短也需要視覺
        comparison_indicators = ['比較', '對比', '多少', '幾個', '比例', '變化', '成長', '下降']
        for indicator in comparison_indicators:
            if indicator in question:
                return QueryIntent.VISUAL_REQUIRED

        # 檢查問題長度和具體程度
        if len(question) < 20:
            return QueryIntent.TEXT_ONLY

        # 其他上下文分析邏輯
        return QueryIntent.TEXT_ONLY

    def check_visual_cache(self, visual_assets: List[VisualAsset]) -> Dict[str, bool]:
        """
        檢查視覺資源的快取狀態

        Args:
            visual_assets: 視覺資源清單

        Returns:
            Dict[str, bool]: asset_id -> 是否已快取
        """
        cache_status = {}
        for asset in visual_assets:
            # 如果狀態為 COMPLETED 且有視覺事實，則認為已快取
            is_cached = (
                asset.status == VisualAssetStatus.COMPLETED and
                len(asset.visual_facts) > 0
            )
            cache_status[asset.asset_id] = is_cached

        return cache_status

    def route_vision_request(
        self,
        query_request: QueryRequest,
        visual_assets: List[VisualAsset]
    ) -> VisionRoutingDecision:
        """
        主要的路由決策邏輯

        Args:
            query_request: 查詢請求
            visual_assets: 相關的視覺資源

        Returns:
            VisionRoutingDecision: 路由決策結果
        """

        # 1. 分析查詢意圖
        intent = query_request.intent
        if intent is None:
            intent = self.analyze_intent(query_request.question)

        # 2. 如果是純文字查詢，直接返回不需要視覺
        if intent == QueryIntent.TEXT_ONLY:
            return VisionRoutingDecision(
                needs_vision=False,
                required_assets=[],
                reasoning="查詢為純文字問題，不需要視覺解析",
                confidence_score=0.95
            )

        # 3. 如果需要視覺但沒有視覺資源，返回不需要（可能是配置錯誤）
        if not visual_assets:
            return VisionRoutingDecision(
                needs_vision=False,
                required_assets=[],
                reasoning="查詢需要視覺信息但未找到相關視覺資源",
                confidence_score=0.90
            )

        # 4. 檢查視覺資源快取狀態
        cache_status = self.check_visual_cache(visual_assets)

        # 5. 找出未快取的資源
        uncached_assets = [
            asset_id for asset_id, is_cached in cache_status.items()
            if not is_cached
        ]

        # 6. 決定是否需要視覺推理
        needs_vision = len(uncached_assets) > 0

        reasoning = self._generate_reasoning(intent, cache_status, uncached_assets)

        # 7. 計算信心分數
        confidence = self._calculate_confidence(intent, visual_assets, cache_status)

        return VisionRoutingDecision(
            needs_vision=needs_vision,
            required_assets=uncached_assets,
            reasoning=reasoning,
            confidence_score=confidence
        )

    def _generate_reasoning(
        self,
        intent: QueryIntent,
        cache_status: Dict[str, bool],
        uncached_assets: List[str]
    ) -> str:
        """生成決策理由"""
        total_assets = len(cache_status)
        cached_count = sum(1 for status in cache_status.values() if status)
        uncached_count = len(uncached_assets)

        if intent == QueryIntent.VISUAL_REQUIRED:
            if uncached_count > 0:
                return f"查詢需要視覺信息，發現 {uncached_count}/{total_assets} 個視覺資源未快取，需要視覺推理"
            else:
                return f"查詢需要視覺信息，但所有 {total_assets} 個視覺資源均已快取，可直接使用"
        else:
            return f"查詢識別為純文字類型，無需視覺推理"

    def _calculate_confidence(
        self,
        intent: QueryIntent,
        visual_assets: List[VisualAsset],
        cache_status: Dict[str, bool]
    ) -> float:
        """計算決策信心分數"""
        base_confidence = 0.8

        # 意圖清晰度加成
        if intent == QueryIntent.VISUAL_REQUIRED:
            base_confidence += 0.1
        elif intent == QueryIntent.TEXT_ONLY:
            base_confidence += 0.05

        # 資源數量影響
        asset_count = len(visual_assets)
        if asset_count > 0:
            base_confidence += 0.05
        else:
            base_confidence -= 0.1

        return min(base_confidence, 1.0)

    def create_vision_requests(
        self,
        routing_decision: VisionRoutingDecision,
        query_request: QueryRequest,
        visual_assets: List[VisualAsset]
    ) -> List[VisionRequest]:
        """
        基於路由決策創建視覺處理請求

        Args:
            routing_decision: 路由決策結果
            query_request: 原始查詢請求
            visual_assets: 視覺資源清單

        Returns:
            List[VisionRequest]: 視覺處理請求清單
        """
        if not routing_decision.needs_vision:
            return []

        requests = []
        asset_dict = {asset.asset_id: asset for asset in visual_assets}

        for asset_id in routing_decision.required_assets:
            if asset_id in asset_dict:
                asset = asset_dict[asset_id]

                # 根據查詢內容決定任務類型
                task_type = self._determine_task_type(query_request.question, asset)

                request = VisionRequest(
                    request_id=f"vision_{query_request.query_id}_{asset_id}",
                    asset_id=asset_id,
                    task_type=task_type,
                    image_base64=asset.image_base64 or "",
                    context_text=query_request.question,
                    metadata={
                        "query_id": query_request.query_id,
                        "original_question": query_request.question
                    }
                )
                requests.append(request)

        return requests

    def _determine_task_type(self, question: str, asset: VisualAsset) -> VisionTaskType:
        """根據問題和資源類型決定任務類型"""
        question_lower = question.lower()

        # 檢查是否為圖表分析
        chart_keywords = ['圖表', 'chart', 'graph', 'trend', '趨勢', '變化', '成長']
        if any(keyword in question_lower for keyword in chart_keywords):
            return VisionTaskType.CHART_ANALYSIS

        # 檢查是否為醫材設備分析
        medical_keywords = ['設備', '儀器', 'device', 'instrument', '手術']
        if any(keyword in question_lower for keyword in medical_keywords):
            return VisionTaskType.MEDICAL_DEVICE_ANALYSIS

        # 預設為圖片描述
        return VisionTaskType.IMAGE_DESCRIPTION
