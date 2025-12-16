"""
Domain-Specific Relationship Types for Neo4j GraphRAG

This module defines specialized relationship types for different knowledge domains:
1. Financial Reports (上市公司財報)
2. Medical Devices (醫療器材文件)
3. Prospects/Clients (潛在客戶資訊)
4. Internal Reports (公司內部報告)

Each domain has tailored relationship types that enable more precise reasoning
and querying capabilities.
"""

from enum import Enum
from typing import Dict, List, Any
from pydantic import BaseModel


class DomainType(str, Enum):
    """Knowledge domain types"""
    FINANCIAL = "financial"
    MEDICAL_DEVICE = "medical_device"
    PROSPECT = "prospect"
    INTERNAL_REPORT = "internal_report"
    GENERAL = "general"


class RelationshipCategory(str, Enum):
    """Relationship categories for better organization"""
    MENTIONING = "mentioning"          # How entities are mentioned in content
    SEMANTIC = "semantic"             # Semantic relationships between entities
    TEMPORAL = "temporal"             # Time-based relationships
    SPATIAL = "spatial"               # Location/space-based relationships
    CAUSAL = "causal"                 # Cause-effect relationships
    HIERARCHICAL = "hierarchical"     # Parent-child, part-whole relationships
    QUALITATIVE = "qualitative"       # Quality, performance relationships


# Financial Domain Relationships
FINANCIAL_RELATIONSHIPS = {
    # Financial Metrics
    "HAS_FINANCIAL_METRIC": {
        "description": "Company has a financial metric (revenue, profit, etc.)",
        "from_types": ["Company", "Organization"],
        "to_types": ["FinancialMetric", "KPI"],
        "category": RelationshipCategory.SEMANTIC,
        "properties": ["value", "period", "currency"]
    },
    "SHOWS_TREND": {
        "description": "Financial metric shows a trend",
        "from_types": ["FinancialMetric", "KPI"],
        "to_types": ["Trend"],
        "category": RelationshipCategory.SEMANTIC,
        "properties": ["direction", "magnitude", "timeframe"]
    },
    "COMPARED_TO": {
        "description": "Compare financial metrics between periods/entities",
        "from_types": ["FinancialMetric", "KPI"],
        "to_types": ["FinancialMetric", "KPI"],
        "category": RelationshipCategory.SEMANTIC,
        "properties": ["difference", "percentage_change"]
    },
    "PROJECTS_VALUE": {
        "description": "Financial projection or forecast",
        "from_types": ["FinancialMetric", "Company"],
        "to_types": ["Value", "Prediction"],
        "category": RelationshipCategory.SEMANTIC,
        "properties": ["confidence", "timeframe"]
    },

    # Financial Events & Communications
    "ANNOUNCES_EARNINGS": {
        "description": "Company announces earnings report",
        "from_types": ["Company", "Organization"],
        "to_types": ["Report", "Document"],
        "category": RelationshipCategory.SEMANTIC,
        "properties": ["quarter", "year", "surprise_factor"]
    },
    "HOSTS_CONFERENCE": {
        "description": "Company hosts earnings conference call",
        "from_types": ["Company", "Organization"],
        "to_types": ["Event", "ConferenceCall"],
        "category": RelationshipCategory.SEMANTIC,
        "properties": ["date", "participants"]
    },
    "DISCUSSES_STRATEGY": {
        "description": "Executive discusses business strategy",
        "from_types": ["Person", "Executive"],
        "to_types": ["Strategy", "Plan"],
        "category": RelationshipCategory.SEMANTIC,
        "properties": ["confidence_level", "timeframe"]
    },
    "REPORTS_RISK": {
        "description": "Report identifies or discusses risk",
        "from_types": ["Report", "Document"],
        "to_types": ["Risk", "Threat"],
        "category": RelationshipCategory.SEMANTIC,
        "properties": ["severity", "probability", "impact"]
    },

    # Market Relationships
    "COMPETES_WITH": {
        "description": "Companies compete in the same market",
        "from_types": ["Company", "Organization"],
        "to_types": ["Company", "Organization"],
        "category": RelationshipCategory.SEMANTIC,
        "properties": ["market_segment", "competitive_intensity"]
    },
    "OPERATES_IN": {
        "description": "Company operates in market/geography",
        "from_types": ["Company", "Organization"],
        "to_types": ["Market", "Geography", "Industry"],
        "category": RelationshipCategory.HIERARCHICAL,
        "properties": ["market_share", "revenue_contribution"]
    },
    "INFLUENCED_BY": {
        "description": "Financial performance influenced by external factors",
        "from_types": ["FinancialMetric", "Company"],
        "to_types": ["Event", "EconomicIndicator", "Regulation"],
        "category": RelationshipCategory.CAUSAL,
        "properties": ["impact_strength", "direction"]
    }
}


# Medical Device Domain Relationships
MEDICAL_DEVICE_RELATIONSHIPS = {
    # Regulatory Compliance (compatible with LLM entity types)
    "REGULATES": {
        "description": "Regulatory body regulates manufacturers/organizations",
        "from_types": ["ORGANIZATION", "RegulatoryBody", "FDA", "EMA"],
        "to_types": ["ORGANIZATION", "Company", "Manufacturer"],
        "category": RelationshipCategory.SEMANTIC,
        "properties": ["compliance_level", "certification_date"]
    },
    "COMPLIES_WITH": {
        "description": "Organization/product complies with regulation",
        "from_types": ["ORGANIZATION", "Company", "PRODUCT", "Device", "Product"],
        "to_types": ["ORGANIZATION", "Regulation", "Standard", "Guideline"],
        "category": RelationshipCategory.SEMANTIC,
        "properties": ["compliance_level", "certification_date"]
    },
    "SUBMITTED_TO": {
        "description": "Application submitted to regulatory body",
        "from_types": ["ORGANIZATION", "Company", "Application", "Submission"],
        "to_types": ["ORGANIZATION", "RegulatoryBody", "FDA", "EMA"],
        "category": RelationshipCategory.SEMANTIC,
        "properties": ["submission_date", "status", "tracking_number"]
    },
    "APPROVED_BY": {
        "description": "Product approved by regulatory authority",
        "from_types": ["PRODUCT", "Device", "Product"],
        "to_types": ["ORGANIZATION", "RegulatoryBody", "FDA", "EMA"],
        "category": RelationshipCategory.SEMANTIC,
        "properties": ["approval_date", "approval_number", "conditions"]
    },

    # Clinical & Safety (compatible with LLM entity types)
    "REQUIRES": {
        "description": "Medical devices require clinical trials/approval",
        "from_types": ["PRODUCT", "Device", "Product"],
        "to_types": ["ClinicalTrial", "Study", "Approval"],
        "category": RelationshipCategory.SEMANTIC,
        "properties": ["phase", "status", "completion_date"]
    },
    "UNDERGOES_TRIAL": {
        "description": "Device undergoes clinical trial",
        "from_types": ["PRODUCT", "Device", "Product"],
        "to_types": ["ClinicalTrial", "Study"],
        "category": RelationshipCategory.SEMANTIC,
        "properties": ["phase", "status", "completion_date"]
    },
    "DEMONSTRATES": {
        "description": "Trials demonstrate efficacy/safety",
        "from_types": ["ClinicalTrial", "Study"],
        "to_types": ["Outcome", "Result", "Safety", "Efficacy"],
        "category": RelationshipCategory.QUALITATIVE,
        "properties": ["effect_size", "statistical_significance", "study_quality"]
    },
    "REPORTS_TO": {
        "description": "Manufacturers report adverse events to FDA",
        "from_types": ["ORGANIZATION", "Company", "Manufacturer"],
        "to_types": ["ORGANIZATION", "RegulatoryBody", "FDA"],
        "category": RelationshipCategory.SEMANTIC,
        "properties": ["reporting_frequency", "event_type", "severity"]
    },

    # Manufacturing & Quality (compatible with LLM entity types)
    "MANUFACTURES": {
        "description": "Company manufactures medical devices",
        "from_types": ["ORGANIZATION", "Company", "Manufacturer"],
        "to_types": ["PRODUCT", "Device", "Product"],
        "category": RelationshipCategory.HIERARCHICAL,
        "properties": ["facility_location", "production_volume"]
    },
    "MANUFACTURED_BY": {
        "description": "Device manufactured by company",
        "from_types": ["PRODUCT", "Device", "Product"],
        "to_types": ["ORGANIZATION", "Company", "Manufacturer"],
        "category": RelationshipCategory.HIERARCHICAL,
        "properties": ["facility_location", "production_volume"]
    },
    "MEETS_STANDARD": {
        "description": "Product meets quality standard",
        "from_types": ["PRODUCT", "Device", "Product", "Process"],
        "to_types": ["Standard", "Specification"],
        "category": RelationshipCategory.QUALITATIVE,
        "properties": ["compliance_score", "audit_date"]
    },
    "PREVENTS": {
        "description": "Quality systems prevent defects/issues",
        "from_types": ["Process", "QualitySystem"],
        "to_types": ["Defect", "Issue", "Problem"],
        "category": RelationshipCategory.SEMANTIC,
        "properties": ["severity", "effectiveness", "monitoring_frequency"]
    }
}


# Prospect/Client Domain Relationships
PROSPECT_RELATIONSHIPS = {
    # Contact & Relationship Network
    "CONTACTS_PERSON": {
        "description": "Company contacts specific person",
        "from_types": ["Company", "Organization"],
        "to_types": ["Person", "Contact"],
        "category": RelationshipCategory.SEMANTIC,
        "properties": ["contact_method", "frequency", "relationship_strength"]
    },
    "HAS_REQUIREMENT": {
        "description": "Client has specific requirement or need",
        "from_types": ["Client", "Prospect"],
        "to_types": ["Requirement", "Need", "Feature"],
        "category": RelationshipCategory.SEMANTIC,
        "properties": ["priority", "budget_allocated", "timeline"]
    },
    "EXPRESSES_INTEREST": {
        "description": "Prospect expresses interest in product/solution",
        "from_types": ["Prospect", "Client"],
        "to_types": ["Product", "Solution", "Service"],
        "category": RelationshipCategory.SEMANTIC,
        "properties": ["interest_level", "engagement_score", "last_contact"]
    },
    "HAS_BUDGET_FOR": {
        "description": "Company has budget allocated for solution",
        "from_types": ["Company", "Organization"],
        "to_types": ["Product", "Solution"],
        "category": RelationshipCategory.SEMANTIC,
        "properties": ["budget_amount", "currency", "approval_status"]
    },

    # Competitive Analysis
    "PREFERS_COMPETITOR": {
        "description": "Client prefers competitor's solution",
        "from_types": ["Client", "Prospect"],
        "to_types": ["Company", "Product"],
        "category": RelationshipCategory.SEMANTIC,
        "properties": ["preference_reason", "switching_cost", "competitor_strength"]
    },
    "EVALUATING_OPTIONS": {
        "description": "Prospect evaluating multiple options",
        "from_types": ["Prospect", "Client"],
        "to_types": ["Product", "Solution"],
        "category": RelationshipCategory.SEMANTIC,
        "properties": ["evaluation_stage", "decision_criteria", "timeline"]
    },

    # Interaction History
    "ATTENDED_WEBINAR": {
        "description": "Person attended webinar/event",
        "from_types": ["Person", "Contact"],
        "to_types": ["Event", "Webinar"],
        "category": RelationshipCategory.SEMANTIC,
        "properties": ["attendance_duration", "engagement_level"]
    },
    "DOWNLOADED_CONTENT": {
        "description": "Person downloaded marketing content",
        "from_types": ["Person", "Contact"],
        "to_types": ["Document", "Content", "Whitepaper"],
        "category": RelationshipCategory.SEMANTIC,
        "properties": ["download_date", "content_type", "follow_up_sent"]
    },
    "REQUESTED_DEMO": {
        "description": "Company requested product demo",
        "from_types": ["Company", "Organization"],
        "to_types": ["Product", "Solution"],
        "category": RelationshipCategory.SEMANTIC,
        "properties": ["request_date", "demo_scheduled", "demo_completed"]
    },
    "PROVIDED_FEEDBACK": {
        "description": "Client provided feedback on product/solution",
        "from_types": ["Client", "Prospect"],
        "to_types": ["Product", "Service"],
        "category": RelationshipCategory.SEMANTIC,
        "properties": ["feedback_type", "sentiment", "action_required"]
    }
}


# Internal Report Domain Relationships
INTERNAL_REPORT_RELATIONSHIPS = {
    # Research & Discovery
    "DISCOVERS_FINDING": {
        "description": "Research discovers finding or insight",
        "from_types": ["Research", "Study", "Experiment"],
        "to_types": ["Finding", "Insight", "Discovery"],
        "category": RelationshipCategory.SEMANTIC,
        "properties": ["confidence_level", "novelty_score", "impact"]
    },
    "VALIDATES_HYPOTHESIS": {
        "description": "Experiment validates hypothesis",
        "from_types": ["Experiment", "Study"],
        "to_types": ["Hypothesis", "Theory"],
        "category": RelationshipCategory.QUALITATIVE,
        "properties": ["validation_strength", "p_value", "effect_size"]
    },
    "PRODUCES_DATA": {
        "description": "Study produces data or dataset",
        "from_types": ["Study", "Experiment", "Research"],
        "to_types": ["Dataset", "Data", "Measurement"],
        "category": RelationshipCategory.SEMANTIC,
        "properties": ["data_quality", "sample_size", "collection_method"]
    },
    "CHALLENGES_ASSUMPTION": {
        "description": "Finding challenges existing assumption",
        "from_types": ["Finding", "Result"],
        "to_types": ["Assumption", "Belief", "Theory"],
        "category": RelationshipCategory.SEMANTIC,
        "properties": ["challenge_strength", "evidence_quality"]
    },

    # Quality & Performance
    "MEETS_THRESHOLD": {
        "description": "Product/process meets quality threshold",
        "from_types": ["Product", "Process", "Component"],
        "to_types": ["Threshold", "Standard", "Specification"],
        "category": RelationshipCategory.QUALITATIVE,
        "properties": ["margin", "measurement_date", "certification"]
    },
    "SHOWS_DEGRADATION": {
        "description": "Component shows performance degradation",
        "from_types": ["Component", "Product", "Material"],
        "to_types": ["Degradation", "Issue"],
        "category": RelationshipCategory.QUALITATIVE,
        "properties": ["degradation_rate", "time_to_failure", "severity"]
    },
    "REQUIRES_MAINTENANCE": {
        "description": "Equipment requires maintenance",
        "from_types": ["Equipment", "Asset"],
        "to_types": ["Maintenance", "Service"],
        "category": RelationshipCategory.SEMANTIC,
        "properties": ["urgency", "scheduled_date", "estimated_cost"]
    },
    "ACHIEVES_METRIC": {
        "description": "Process achieves performance metric",
        "from_types": ["Process", "Operation"],
        "to_types": ["Metric", "KPI", "Target"],
        "category": RelationshipCategory.QUALITATIVE,
        "properties": ["achievement_level", "benchmark_comparison"]
    },

    # Recommendations & Actions
    "RECOMMENDS_ACTION": {
        "description": "Report recommends specific action",
        "from_types": ["Report", "Analysis"],
        "to_types": ["Action", "Recommendation", "Change"],
        "category": RelationshipCategory.SEMANTIC,
        "properties": ["priority", "timeline", "resource_required"]
    },
    "REQUIRES_APPROVAL": {
        "description": "Change requires approval",
        "from_types": ["Change", "Action", "Decision"],
        "to_types": ["Person", "Committee", "Manager"],
        "category": RelationshipCategory.SEMANTIC,
        "properties": ["approval_level", "deadline", "escalation_path"]
    },
    "DEPENDS_ON": {
        "description": "Task depends on another task",
        "from_types": ["Task", "Action", "Project"],
        "to_types": ["Task", "Action", "Milestone"],
        "category": RelationshipCategory.SEMANTIC,
        "properties": ["dependency_type", "lag_time", "critical_path"]
    },
    "LEADS_TO_IMPROVEMENT": {
        "description": "Change leads to performance improvement",
        "from_types": ["Change", "Action"],
        "to_types": ["Improvement", "Metric", "Outcome"],
        "category": RelationshipCategory.CAUSAL,
        "properties": ["improvement_magnitude", "time_to_impact"]
    }
}


# Cross-Domain Relationships (適用於所有領域)
CROSS_DOMAIN_RELATIONSHIPS = {
    # Document & Source Relationships
    "BELONGS_TO_DOMAIN": {
        "description": "Document belongs to knowledge domain",
        "from_types": ["Document", "Report"],
        "to_types": ["Domain"],
        "category": RelationshipCategory.HIERARCHICAL,
        "properties": ["domain_confidence", "classification_method"]
    },
    "CITES_SOURCE": {
        "description": "Document cites external source",
        "from_types": ["Document", "Report"],
        "to_types": ["Source", "Reference"],
        "category": RelationshipCategory.SEMANTIC,
        "properties": ["citation_type", "relevance", "verification_status"]
    },
    "DERIVED_FROM": {
        "description": "Knowledge derived from source data",
        "from_types": ["Knowledge", "Insight", "Finding"],
        "to_types": ["Data", "Document", "Source"],
        "category": RelationshipCategory.SEMANTIC,
        "properties": ["derivation_method", "confidence", "timestamp"]
    },
    "SUPPORTS_CLAIM": {
        "description": "Evidence supports claim or assertion",
        "from_types": ["Evidence", "Fact"],
        "to_types": ["Claim", "Assertion", "Hypothesis"],
        "category": RelationshipCategory.SEMANTIC,
        "properties": ["support_strength", "evidence_quality"]
    },

    # Time & Version Relationships
    "SUPERSEDES": {
        "description": "New version supersedes old version",
        "from_types": ["Document", "Report", "Standard"],
        "to_types": ["Document", "Report", "Standard"],
        "category": RelationshipCategory.TEMPORAL,
        "properties": ["supersession_date", "reason"]
    },
    "VALID_FROM": {
        "description": "Regulation/policy valid from date",
        "from_types": ["Regulation", "Policy", "Standard"],
        "to_types": ["Date", "TimePeriod"],
        "category": RelationshipCategory.TEMPORAL,
        "properties": ["end_date", "conditions"]
    },
    "EXPIRES_AT": {
        "description": "Approval/certificate expires",
        "from_types": ["Approval", "Certificate", "License"],
        "to_types": ["Date", "TimePeriod"],
        "category": RelationshipCategory.TEMPORAL,
        "properties": ["renewal_required", "grace_period"]
    },
    "VERSION_OF": {
        "description": "Document is version of base document",
        "from_types": ["Document", "Report"],
        "to_types": ["Document", "Report"],
        "category": RelationshipCategory.HIERARCHICAL,
        "properties": ["version_number", "change_summary"]
    }
}


# Legacy Relationships (for backward compatibility)
LEGACY_RELATIONSHIPS = {
    "HAS_CHUNK": {
        "description": "Document has text chunk",
        "from_types": ["Document"],
        "to_types": ["Chunk"],
        "category": RelationshipCategory.HIERARCHICAL,
        "properties": ["order", "page"]
    },
    "MENTIONED_IN": {
        "description": "Entity/Event/VisualFact mentioned in chunk",
        "from_types": ["Entity", "Event", "VisualFact"],
        "to_types": ["Chunk"],
        "category": RelationshipCategory.MENTIONING,
        "properties": ["mention_type", "confidence"]
    },
    "RELATED_TO": {
        "description": "Generic relationship between entities",
        "from_types": ["Entity"],
        "to_types": ["Entity"],
        "category": RelationshipCategory.SEMANTIC,
        "properties": ["relationship_strength", "context"]
    },
    "PARTICIPATES_IN": {
        "description": "Entity participates in event",
        "from_types": ["Entity"],
        "to_types": ["Event"],
        "category": RelationshipCategory.SEMANTIC,
        "properties": ["role", "contribution"]
    },
    "CAUSES": {
        "description": "Event causes another event",
        "from_types": ["Event"],
        "to_types": ["Event"],
        "category": RelationshipCategory.CAUSAL,
        "properties": ["causality_strength", "evidence"]
    },
    "DESCRIBED_BY_IMAGE": {
        "description": "Entity described by visual content",
        "from_types": ["Entity"],
        "to_types": ["VisualFact"],
        "category": RelationshipCategory.SEMANTIC,
        "properties": ["description_quality", "relevance"]
    }
}


class DomainRelationshipRegistry:
    """Registry for managing domain-specific relationships"""

    def __init__(self):
        self.relationships = {
            DomainType.FINANCIAL: FINANCIAL_RELATIONSHIPS,
            DomainType.MEDICAL_DEVICE: MEDICAL_DEVICE_RELATIONSHIPS,
            DomainType.PROSPECT: PROSPECT_RELATIONSHIPS,
            DomainType.INTERNAL_REPORT: INTERNAL_REPORT_RELATIONSHIPS,
            DomainType.GENERAL: CROSS_DOMAIN_RELATIONSHIPS
        }

        # Add legacy relationships to all domains for backward compatibility
        for domain in self.relationships:
            self.relationships[domain].update(LEGACY_RELATIONSHIPS)

    def get_relationships_for_domain(self, domain: DomainType) -> Dict[str, Dict]:
        """Get all relationships for a specific domain"""
        return self.relationships.get(domain, {})

    def get_relationship_definition(self, domain: DomainType, relationship_type: str) -> Dict:
        """Get definition for specific relationship type in domain"""
        domain_rels = self.get_relationships_for_domain(domain)
        return domain_rels.get(relationship_type, {})

    def get_relationships_by_category(self, domain: DomainType, category: RelationshipCategory) -> Dict[str, Dict]:
        """Get relationships filtered by category"""
        domain_rels = self.get_relationships_for_domain(domain)
        return {
            rel_type: rel_def
            for rel_type, rel_def in domain_rels.items()
            if rel_def.get("category") == category
        }

    def validate_relationship(self, domain: DomainType, relationship_type: str,
                            from_node_type: str, to_node_type: str) -> bool:
        """Validate if relationship is allowed between node types"""
        rel_def = self.get_relationship_definition(domain, relationship_type)

        if not rel_def:
            return False

        from_types = rel_def.get("from_types", [])
        to_types = rel_def.get("to_types", [])

        return (from_node_type in from_types or not from_types) and \
               (to_node_type in to_types or not to_types)

    def get_available_relationships(self, domain: DomainType, from_node_type: str,
                                  to_node_type: str) -> List[str]:
        """Get available relationship types between two node types"""
        domain_rels = self.get_relationships_for_domain(domain)

        available = []
        for rel_type, rel_def in domain_rels.items():
            if self.validate_relationship(domain, rel_type, from_node_type, to_node_type):
                available.append(rel_type)

        return available


# Global registry instance
relationship_registry = DomainRelationshipRegistry()


class RelationshipClassificationRequest(BaseModel):
    """Request model for LLM-based relationship classification"""
    domain: DomainType
    source_node: Dict[str, Any]
    target_node: Dict[str, Any]
    context_text: str
    available_relationships: List[str]


class RelationshipClassificationResponse(BaseModel):
    """Response model for relationship classification"""
    relationship_type: str
    confidence: float
    reasoning: str
    properties: Dict[str, Any] = {}
