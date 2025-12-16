# Neo4j Relationship Types 遷移指南

## 概述

本指南說明如何從舊的通用relationship types遷移到新的domain-specific relationship types，以提升知識圖譜的查詢精準度和推理能力。

## 背景

### 原有問題
- 過於通用的relationship types（如`RELATED_TO`, `MENTIONED_IN`）
- 缺乏領域特定的語義理解
- LLM推理能力受限於模糊的關係定義

### 新設計特點
- 針對4種知識領域定制relationship types
- LLM驅動的自動分類系統
- 保持向後相容性
- 支援更精準的圖譜查詢

## 遷移策略

### 階段1: 並行運行 (推薦)
```python
# 舊系統繼續使用原有relationships
# 新系統使用domain-specific relationships
# 雙軌運行期間進行A/B測試
```

### 階段2: 漸進遷移
```python
# 按領域逐步遷移
# 從低風險領域開始（如內部報告）
# 驗證查詢性能和準確性
```

### 階段3: 完全替換
```python
# 所有新資料使用新relationships
# 舊資料保持相容性
# 提供查詢轉換層
```

## 領域對應表

### 1. 財報領域 (Financial Reports)

| 舊關係 | 新關係 | 適用場景 |
|--------|--------|----------|
| `RELATED_TO` | `HAS_FINANCIAL_METRIC` | 公司有財務指標 |
| `RELATED_TO` | `SHOWS_TREND` | 指標顯示趨勢 |
| `RELATED_TO` | `COMPETES_WITH` | 公司競爭關係 |
| `PARTICIPATES_IN` | `ANNOUNCES_EARNINGS` | 公布財報 |
| `MENTIONED_IN` | `DISCUSSES_STRATEGY` | 討論策略 |

**遷移示例**:
```cypher
// 舊查詢
MATCH (c1:Company)-[:RELATED_TO]-(c2:Company)
RETURN c1, c2

// 新查詢
MATCH (c1:Company)-[:COMPETES_WITH]-(c2:Company)
RETURN c1, c2
```

### 2. 醫療器材領域 (Medical Devices)

| 舊關係 | 新關係 | 適用場景 |
|--------|--------|----------|
| `RELATED_TO` | `COMPLIES_WITH` | 符合法規 |
| `RELATED_TO` | `APPROVED_BY` | 核准通過 |
| `RELATED_TO` | `HAS_SIDE_EFFECT` | 副作用 |
| `PARTICIPATES_IN` | `UNDERGOES_TRIAL` | 臨床試驗 |
| `MENTIONED_IN` | `MEETS_STANDARD` | 符合標準 |

### 3. 潛在客戶領域 (Prospects)

| 舊關係 | 新關係 | 適用場景 |
|--------|--------|----------|
| `RELATED_TO` | `HAS_REQUIREMENT` | 客戶需求 |
| `RELATED_TO` | `PREFERS_COMPETITOR` | 偏好競爭者 |
| `RELATED_TO` | `HAS_BUDGET_FOR` | 預算配置 |
| `MENTIONED_IN` | `ATTENDED_WEBINAR` | 參加活動 |
| `MENTIONED_IN` | `REQUESTED_DEMO` | 要求演示 |

### 4. 內部報告領域 (Internal Reports)

| 舊關係 | 新關係 | 適用場景 |
|--------|--------|----------|
| `RELATED_TO` | `DISCOVERS_FINDING` | 發現結果 |
| `RELATED_TO` | `MEETS_THRESHOLD` | 符合門檻 |
| `RELATED_TO` | `RECOMMENDS_ACTION` | 建議行動 |
| `PARTICIPATES_IN` | `VALIDATES_HYPOTHESIS` | 驗證假設 |
| `MENTIONED_IN` | `LEADS_TO_IMPROVEMENT` | 導致改善 |

## 實作步驟

### 步驟1: 安裝新模組
```bash
# 新模組已包含在專案中
# 確保以下檔案存在：
# - grag/core/schemas/domain_relationships.py
# - grag/core/relationship_classifier.py
```

### 步驟2: 更新資料庫schema
```python
from grag.core.schemas.domain_relationships import relationship_registry

# 檢查新relationships是否可用
financial_rels = relationship_registry.get_relationships_for_domain("financial")
print(f"Financial relationships: {len(financial_rels)}")
```

### 步驟3: 測試LLM分類器
```python
from grag.core.relationship_classifier import classify_relationship
from grag.core.schemas.domain_relationships import DomainType

# 測試分類
result = await classify_relationship(
    domain=DomainType.FINANCIAL,
    source_node={"type": "Company", "name": "ABC Corp"},
    target_node={"type": "FinancialMetric", "name": "Revenue"},
    context="ABC Corp reported $100M revenue in Q4"
)

print(f"分類結果: {result.relationship_type} (信心: {result.confidence})")
```

### 步驟4: 更新知識提取流程
```python
# 修改 grag/ingestion/indexing/llm_knowledge_extractor.py

from grag.core.relationship_classifier import relationship_classifier
from grag.core.schemas.domain_relationships import DomainType

class EnhancedKnowledgeExtractor:
    async def extract_relationships_with_domain_awareness(self, chunks, domain):
        # 使用domain-specific分類
        for chunk in chunks:
            entities = self.extract_entities(chunk)
            relationships = []

            for i, entity1 in enumerate(entities):
                for j, entity2 in enumerate(entities):
                    if i != j:
                        classification = await relationship_classifier.classify_relationship(
                            domain=domain,
                            source_node=entity1,
                            target_node=entity2,
                            context_text=chunk.text
                        )

                        relationships.append({
                            "from_entity": entity1,
                            "to_entity": entity2,
                            "relationship_type": classification.relationship_type,
                            "confidence": classification.confidence,
                            "properties": classification.properties
                        })

            return relationships
```

### 步驟5: 更新查詢邏輯
```python
# 修改 grag/agents/reasoning_agent.py

class EnhancedReasoningAgent:
    def _find_relationships_between_entities(self, session, entity1, entity2, domain):
        # 使用domain-specific relationships進行查詢
        domain_rels = relationship_registry.get_available_relationships(
            domain, entity1.get("type"), entity2.get("type")
        )

        # 建構動態Cypher查詢
        rel_patterns = " | ".join([f"[:{rel}]" for rel in domain_rels])

        cypher_query = f"""
        MATCH (e1 {{entity_id: $id1}})-{rel_patterns}->(e2 {{entity_id: $id2}})
        RETURN type(r) as relationship_type, r
        """

        # 執行查詢...
```

## 效能考量

### 查詢優化
```cypher
// 創建domain-specific索引
CREATE INDEX domain_relationship_idx FOR ()-[r]-()
WHERE r.domain IN ['financial', 'medical_device', 'prospect', 'internal_report']
```

### 快取策略
```python
# 快取常用relationship分類結果
relationship_cache = {}

async def cached_classify_relationship(domain, source, target, context):
    cache_key = f"{domain}_{source['name']}_{target['name']}_{hash(context)}"

    if cache_key in relationship_cache:
        return relationship_cache[cache_key]

    result = await classify_relationship(domain, source, target, context)
    relationship_cache[cache_key] = result

    return result
```

## 測試與驗證

### 單元測試
```python
def test_relationship_classification():
    classifier = RelationshipClassifier()

    # 測試財報領域
    result = await classifier.classify_relationship(
        domain=DomainType.FINANCIAL,
        source_node={"type": "Company", "name": "Apple"},
        target_node={"type": "FinancialMetric", "name": "Revenue"},
        context="Apple reported record revenue growth"
    )

    assert result.relationship_type == "HAS_FINANCIAL_METRIC"
    assert result.confidence > 0.7
```

### 集成測試
```python
def test_full_pipeline():
    # 測試從文件處理到relationship建立的完整流程
    document = process_financial_report("apple_10k.pdf")

    # 提取實體和關係
    entities, relationships = await extract_knowledge_with_domain_awareness(
        document, DomainType.FINANCIAL
    )

    # 驗證使用新relationship types
    financial_rels = [r for r in relationships if r["type"].startswith("HAS_FINANCIAL_METRIC")]
    assert len(financial_rels) > 0
```

## 回滾計劃

### 如果需要回滾
```python
# 1. 停止使用新relationship分類器
# 2. 回歸到通用relationships
# 3. 保留新relationships作為可選功能
# 4. 資料保持完整（新舊relationships並存）
```

## 支援資源

### 文件
- `grag/core/schemas/domain_relationships.py` - 完整relationship定義
- `grag/core/relationship_classifier.py` - LLM分類器實作
- `docs/architecture/relationship_design.md` - 設計原則

### 範例
```python
# 簡單使用範例
from grag.core.relationship_classifier import classify_relationship, DomainType

# 分類財報關係
result = await classify_relationship(
    DomainType.FINANCIAL,
    {"type": "Company", "name": "Tesla"},
    {"type": "Event", "description": "Earnings Call"},
    "Tesla held its Q4 earnings conference call"
)

print(f"建議關係: {result.relationship_type}")
```

---

## 總結

新的domain-specific relationship設計提供了：

1. **更高的語義精準度**: 每個領域都有最適合的關係類型
2. **更好的LLM推理**: 模型能理解專業領域的關係
3. **更強的查詢能力**: 支援複雜的領域特定查詢
4. **向後相容性**: 舊系統繼續正常運作
5. **可擴展性**: 容易添加新領域和新關係類型

遷移過程是漸進式的，允許團隊在生產環境中安全地採用新系統。
