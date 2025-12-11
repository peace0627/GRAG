"""
Evidence Fusion Engine

This module implements intelligent fusion of evidence from multiple sources,
providing unified ranking, deduplication, and quality assessment.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict
import math

from ..core.schemas.unified_schemas import UnifiedEvidence, KnowledgeUnit, SourceType, Modality

logger = logging.getLogger(__name__)


class EvidenceFusionEngine:
    """Engine for fusing and ranking evidence from multiple sources"""

    def __init__(self):
        self.fusion_strategies = {
            "weighted_average": self._weighted_average_fusion,
            "bayesian_fusion": self._bayesian_fusion,
            "source_reliability": self._source_reliability_fusion,
            "adaptive_fusion": self._adaptive_fusion
        }

    def fuse_evidence(self, evidence_sets: List[List[UnifiedEvidence]],
                     fusion_strategy: str = "adaptive_fusion",
                     query_context: Optional[Dict[str, Any]] = None) -> List[UnifiedEvidence]:
        """Fuse multiple evidence sets into unified ranked list

        Args:
            evidence_sets: List of evidence lists from different sources
            fusion_strategy: Fusion strategy to use
            query_context: Query context for adaptive fusion

        Returns:
            Fused and ranked list of evidence
        """
        if not evidence_sets:
            return []

        # Flatten all evidence
        all_evidence = []
        for evidence_set in evidence_sets:
            all_evidence.extend(evidence_set)

        if not all_evidence:
            return []

        logger.info(f"Fusing {len(all_evidence)} evidence items using {fusion_strategy}")

        # Apply deduplication first
        deduplicated_evidence = self._deduplicate_evidence(all_evidence)

        # Apply selected fusion strategy
        fusion_func = self.fusion_strategies.get(fusion_strategy, self._adaptive_fusion)
        fused_evidence = fusion_func(deduplicated_evidence, query_context)

        # Apply final ranking
        ranked_evidence = self._apply_final_ranking(fused_evidence, query_context)

        logger.info(f"Fusion complete: {len(ranked_evidence)} unique evidence items")
        return ranked_evidence

    def _deduplicate_evidence(self, evidence_list: List[UnifiedEvidence]) -> List[UnifiedEvidence]:
        """Remove duplicate evidence based on content similarity"""
        if not evidence_list:
            return []

        # Group by content similarity
        content_groups = defaultdict(list)

        for evidence in evidence_list:
            # Create content signature for deduplication
            signature = self._create_content_signature(evidence)
            content_groups[signature].append(evidence)

        # Merge duplicates within each group
        deduplicated = []
        for signature, group in content_groups.items():
            if len(group) == 1:
                deduplicated.append(group[0])
            else:
                # Merge duplicate evidence
                merged = self._merge_duplicate_evidence(group)
                deduplicated.append(merged)

        return deduplicated

    def _create_content_signature(self, evidence: UnifiedEvidence) -> str:
        """Create content signature for deduplication"""
        # Use combination of content hash and key metadata
        content_hash = hash(evidence.content.lower().strip()[:200])  # First 200 chars

        # Add source and modality to signature
        signature_parts = [
            str(content_hash),
            evidence.source_type.value,
            evidence.modality.value
        ]

        # Add document info if available
        if evidence.traceability:
            signature_parts.extend([
                str(evidence.traceability.document_id),
                str(evidence.traceability.page_number or 0)
            ])

        return "|".join(signature_parts)

    def _merge_duplicate_evidence(self, evidence_group: List[UnifiedEvidence]) -> UnifiedEvidence:
        """Merge duplicate evidence items"""
        if len(evidence_group) == 1:
            return evidence_group[0]

        # Use the highest quality evidence as base
        base_evidence = max(evidence_group, key=lambda x: x.get_combined_score())

        # Merge metadata from all sources
        merged_metadata = {}
        source_confidences = {}
        all_related_units = set()

        for evidence in evidence_group:
            # Collect metadata
            merged_metadata.update(evidence.metadata)

            # Track source confidences
            source_confidences[evidence.source_type.value] = evidence.confidence

            # Collect related units
            all_related_units.update(evidence.related_units)

        # Update base evidence
        base_evidence.metadata = merged_metadata
        base_evidence.metadata["source_confidences"] = source_confidences
        base_evidence.metadata["merged_from"] = len(evidence_group)
        base_evidence.related_units = list(all_related_units)

        # Recalculate confidence as average of all sources
        if source_confidences:
            base_evidence.confidence = sum(source_confidences.values()) / len(source_confidences)

        return base_evidence

    def _weighted_average_fusion(self, evidence_list: List[UnifiedEvidence],
                                query_context: Optional[Dict[str, Any]] = None) -> List[UnifiedEvidence]:
        """Simple weighted average fusion"""
        for evidence in evidence_list:
            # Apply source reliability weights
            source_weight = self._get_source_weight(evidence.source_type)
            evidence.relevance_score = evidence.relevance_score * source_weight

        return evidence_list

    def _bayesian_fusion(self, evidence_list: List[UnifiedEvidence],
                        query_context: Optional[Dict[str, Any]] = None) -> List[UnifiedEvidence]:
        """Bayesian fusion considering source reliability and evidence quality"""
        for evidence in evidence_list:
            # Calculate prior probability based on source reliability
            prior = self._get_source_reliability_prior(evidence.source_type)

            # Update with evidence quality
            likelihood = evidence.quality_score

            # Simple Bayesian update (posterior ∝ prior × likelihood)
            posterior = (prior * likelihood) / ((prior * likelihood) + ((1 - prior) * (1 - likelihood)))

            evidence.confidence = posterior

        return evidence_list

    def _source_reliability_fusion(self, evidence_list: List[UnifiedEvidence],
                                  query_context: Optional[Dict[str, Any]] = None) -> List[UnifiedEvidence]:
        """Fusion based on learned source reliability scores"""
        # This would use learned reliability scores from feedback
        # For now, use predefined reliability scores
        reliability_scores = {
            SourceType.NEO4J: 0.85,
            SourceType.SUPABASE: 0.80,
            SourceType.HYBRID: 0.90,
            SourceType.EXTERNAL: 0.70
        }

        for evidence in evidence_list:
            reliability = reliability_scores.get(evidence.source_type, 0.75)
            evidence.confidence = evidence.confidence * reliability

        return evidence_list

    def _adaptive_fusion(self, evidence_list: List[UnifiedEvidence],
                        query_context: Optional[Dict[str, Any]] = None) -> List[UnifiedEvidence]:
        """Adaptive fusion based on query context and evidence characteristics"""
        if not query_context:
            return self._weighted_average_fusion(evidence_list)

        # Analyze query requirements
        query_type = query_context.get("query_type", "factual")
        requires_precision = query_context.get("requires_high_precision", False)

        # Choose fusion strategy based on query type
        if query_type in ["causal", "analytical"]:
            # High precision required - use Bayesian fusion
            return self._bayesian_fusion(evidence_list, query_context)
        elif query_type == "visual":
            # Visual queries - prefer VLM sources
            return self._modality_aware_fusion(evidence_list, query_context)
        elif requires_precision:
            # Precision-critical queries
            return self._source_reliability_fusion(evidence_list, query_context)
        else:
            # Default weighted fusion
            return self._weighted_average_fusion(evidence_list, query_context)

    def _modality_aware_fusion(self, evidence_list: List[UnifiedEvidence],
                             query_context: Optional[Dict[str, Any]] = None) -> List[UnifiedEvidence]:
        """Fusion considering modality preferences"""
        modality_weights = {
            Modality.VISUAL: 1.2,  # Boost visual evidence
            Modality.TEXT: 1.0,
            Modality.RELATIONAL: 0.9,
            Modality.TEMPORAL: 0.8,
            Modality.HYBRID: 1.1
        }

        for evidence in evidence_list:
            modality_weight = modality_weights.get(evidence.modality, 1.0)
            evidence.relevance_score = evidence.relevance_score * modality_weight

        return evidence_list

    def _apply_final_ranking(self, evidence_list: List[UnifiedEvidence],
                           query_context: Optional[Dict[str, Any]] = None) -> List[UnifiedEvidence]:
        """Apply final ranking based on combined scores"""
        # Sort by combined relevance and quality score
        ranked = sorted(evidence_list,
                       key=lambda x: x.get_combined_score(),
                       reverse=True)

        # Apply diversity penalty if too many from same source
        if len(ranked) > 5:
            ranked = self._apply_diversity_penalty(ranked)

        return ranked

    def _apply_diversity_penalty(self, evidence_list: List[UnifiedEvidence]) -> List[UnifiedEvidence]:
        """Apply diversity penalty to avoid source bias"""
        source_counts = defaultdict(int)
        diversity_penalty = 0.05  # 5% penalty per additional item from same source

        adjusted_scores = []
        for evidence in evidence_list:
            source = evidence.source_type.value
            penalty = source_counts[source] * diversity_penalty
            adjusted_score = evidence.get_combined_score() * (1 - penalty)
            adjusted_scores.append((evidence, adjusted_score))
            source_counts[source] += 1

        # Re-sort with diversity adjustment
        adjusted_scores.sort(key=lambda x: x[1], reverse=True)
        return [evidence for evidence, _ in adjusted_scores]

    def _get_source_weight(self, source_type: SourceType) -> float:
        """Get weight for different source types"""
        weights = {
            SourceType.NEO4J: 1.0,      # Graph database - good for relationships
            SourceType.SUPABASE: 0.9,   # Vector database - good for similarity
            SourceType.HYBRID: 1.1,     # Combined sources - highest weight
            SourceType.EXTERNAL: 0.8    # External sources - lower weight
        }
        return weights.get(source_type, 0.8)

    def _get_source_reliability_prior(self, source_type: SourceType) -> float:
        """Get prior reliability probability for source type"""
        priors = {
            SourceType.NEO4J: 0.85,
            SourceType.SUPABASE: 0.80,
            SourceType.HYBRID: 0.90,
            SourceType.EXTERNAL: 0.70
        }
        return priors.get(source_type, 0.75)

    def get_fusion_statistics(self, evidence_sets: List[List[UnifiedEvidence]]) -> Dict[str, Any]:
        """Get statistics about the fusion process"""
        total_evidence = sum(len(ev_set) for ev_set in evidence_sets)

        if total_evidence == 0:
            return {"total_input": 0, "unique_output": 0, "deduplication_ratio": 0}

        # Count by source
        source_counts = defaultdict(int)
        modality_counts = defaultdict(int)
        quality_distribution = {"high": 0, "medium": 0, "low": 0}

        for ev_set in evidence_sets:
            for evidence in ev_set:
                source_counts[evidence.source_type.value] += 1
                modality_counts[evidence.modality.value] += 1

                # Quality distribution
                combined_score = evidence.get_combined_score()
                if combined_score >= 0.8:
                    quality_distribution["high"] += 1
                elif combined_score >= 0.6:
                    quality_distribution["medium"] += 1
                else:
                    quality_distribution["low"] += 1

        return {
            "total_input": total_evidence,
            "source_distribution": dict(source_counts),
            "modality_distribution": dict(modality_counts),
            "quality_distribution": quality_distribution,
            "average_quality": sum(quality_distribution.values()) / total_evidence if total_evidence > 0 else 0
        }

    def _analyze_evidence_contradictions(self, evidence_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze evidence for contradictions and conflicts"""
        analysis = {
            "has_contradictions": False,
            "contradiction_count": 0,
            "conflicting_evidence_pairs": [],
            "severity": "none",  # none, low, medium, high
            "recommendations": []
        }

        if len(evidence_list) < 2:
            return analysis

        # Simple contradiction detection (can be enhanced with LLM)
        content_hashes = {}
        contradictions_found = []

        for i, evidence in enumerate(evidence_list):
            content_hash = hash(evidence["content"].lower().strip()[:100])  # First 100 chars

            if content_hash in content_hashes:
                existing_idx = content_hashes[content_hash]
                # Check if confidence scores differ significantly
                conf_diff = abs(evidence["confidence"] - evidence_list[existing_idx]["confidence"])

                if conf_diff > 0.3:  # Significant confidence difference
                    contradictions_found.append({
                        "evidence_1": existing_idx,
                        "evidence_2": i,
                        "confidence_diff": conf_diff,
                        "content_similarity": "high"
                    })

            content_hashes[content_hash] = i

        if contradictions_found:
            analysis["has_contradictions"] = True
            analysis["contradiction_count"] = len(contradictions_found)
            analysis["conflicting_evidence_pairs"] = contradictions_found

            # Assess severity
            if len(contradictions_found) >= 3:
                analysis["severity"] = "high"
            elif len(contradictions_found) >= 2:
                analysis["severity"] = "medium"
            else:
                analysis["severity"] = "low"

            analysis["recommendations"] = [
                "Consider the source reliability of conflicting evidence",
                "Look for additional corroborating evidence",
                "Note uncertainty in areas with conflicting information"
            ]

        return analysis

    def validate_evidence_quality(self, evidence_list: List[UnifiedEvidence]) -> Dict[str, Any]:
        """Validate and assess evidence quality"""
        validation_results = {
            "total_evidence": len(evidence_list),
            "quality_checks": {
                "has_content": 0,
                "has_traceability": 0,
                "has_confidence": 0,
                "high_confidence": 0
            },
            "issues": []
        }

        for evidence in evidence_list:
            # Check content
            if evidence.content and len(evidence.content.strip()) > 10:
                validation_results["quality_checks"]["has_content"] += 1
            else:
                validation_results["issues"].append(f"Evidence {evidence.evidence_id}: insufficient content")

            # Check traceability
            if evidence.traceability:
                validation_results["quality_checks"]["has_traceability"] += 1

            # Check confidence
            if evidence.confidence > 0:
                validation_results["quality_checks"]["has_confidence"] += 1
                if evidence.confidence >= 0.8:
                    validation_results["quality_checks"]["high_confidence"] += 1

        return validation_results
