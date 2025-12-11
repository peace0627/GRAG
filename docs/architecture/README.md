# 🏗️ GraphRAG 架構說明

## 整體架構概述

GraphRAG是一個**企業級的多模態Agentic RAG系統**，整合了知識圖譜、向量搜索和視覺語言模型，實現智能的文件處理和檢索增強生成。

**🎉 最新狀態**: 已實現完整的生產級系統架構，包含7個專業Agent和REST API，所有核心功能測試通過。

## 核心設計原則

### 🧱 分層架構
```
┌─────────────────┐
│   API Layer     │  FastAPI - RESTful 接口
├─────────────────┤
│ Service Layer   │  業務邏輯封裝
├─────────────────┤
│  Domain Layer   │  核心業務實體
├─────────────────┤
│   Data Layer    │  Neo4j + Supabase
└─────────────────┘
```

### 🔄 數據流設計

#### 文件處理流程
```
Raw Document → [Parser] → Multi-modal Content → [Chunking] → Text Chunks
                                ↓
                          [VLM Processing] → Visual Facts
                                ↓
                    [Embedding] → Vector Embeddings
                                ↓
              Store: Neo4j (Graph) + Supabase (Vectors)
```

#### 檢索流程
```
User Query → [Intent Analysis] → Search Strategy
                      ↓
       ┌──────────────┴──────────────┐
       │                           │
[Vector Search]             [Graph Traversal]
   Supabase                     Neo4j
       │                           │
       └──────────────┬────────────┘
                      ↓
                [Result Fusion] → Final Answer
```

## 核心組件詳解

### 📥 Ingestion Pipeline (數據引入)

#### 文件解析器 (Document Parsers)
- **PDF處理器**: 支持MinerU + OCR降級策略
- **文字處理器**: 直接解析文本文件
- **圖像處理器**: VLM視覺理解
- **混合處理器**: 根據文件類型智能選擇

#### 分塊策略 (Chunking Strategies)
- **語義分塊**: LangChain文本分隔器
- **視覺分塊**: VLM區域分割
- **混合分塊**: 結合文本和視覺信息

#### 嵌入服務 (Embedding Service)
- **多模態嵌入**: 統一的文字和視覺向量表示
- **提供者抽象**: 支持不同嵌入模型
- **批量處理**: 高效的大規模向量生成

### 🗃️ 數據存儲架構

#### Neo4j 知識圖譜
```cypher
// 節點類型
(:Document {document_id, title, source_path, hash, created_at})
(:Chunk {chunk_id, vector_id, text, order, page})
(:VisualFact {fact_id, vector_id, region_id, modality, description, bbox})
(:Entity {entity_id, name, type, description})
(:Event {event_id, type, timestamp, description})

// 關聯類型
(:Document)-[:HAS_CHUNK]->(:Chunk)
(:Chunk)-[:MENTIONED_IN]->(:Entity)
(:Entity)-[:RELATED_TO]->(:Entity)
(:VisualFact)-[:VISUALLY_DESCRIBED]->(:Entity)
```

#### Supabase Vector Store
```sql
-- 向量表結構
vectors (
    vector_id UUID PRIMARY KEY,
    embedding vector(384), -- 或其他維度
    document_id UUID REFERENCES documents,
    chunk_id UUID,
    fact_id UUID,
    type ENUM('chunk', 'vlm_region'),
    page INTEGER,
    order INTEGER,
    content TEXT,
    metadata JSONB
);

-- 性能優化
CREATE INDEX ON vectors USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

### 🤖 Agentic RAG 層

#### 需要實現的核心組件

##### 1. 查詢規劃器 (Query Planner)
```python
class QueryPlanner:
    def analyze_query(self, query: str) -> QueryPlan:
        """分析用戶查詢，返回執行計劃"""
        # 識別查詢類型
        # 確定需要使用的檢索策略
        # 規劃多步推理流程

    def create_execution_plan(self, query_plan: QueryPlan) -> ExecutionPlan:
        """創建可執行的詳細計劃"""
```

##### 2. 多源檢索器 (Multi-Source Retriever)
```python
class MultiSourceRetriever:
    def retrieve(self, query: str, strategies: List[str]) -> RetrievalResult:
        """根據不同策略執行檢索"""
        # 併發執行多個檢索任務
        # 融合結果
        # 重排序和過濾

    def fuse_results(self, results: Dict[str, Any]) -> UnifiedResult:
        """結果融合和去重"""
```

##### 3. 事實檢查器 (Fact Checker)
```python
class FactChecker:
    def verify_claims(self, answer: str, evidence: List[Evidence]) -> VerificationResult:
        """驗證答案的事實準確性"""
        # 交叉引用多個證據來源
        # 檢測矛盾
        # 提供置信度評分
```

### 🌐 API 架構 (✅ 已實現)

#### RESTful API 設計
```
GET    /health              # 系統健康檢查
GET    /system/status       # 完整系統狀態 (Agent + 服務)
POST   /query               # 🤖 Agentic RAG 智能查詢
POST   /query/simple        # 🔍 簡化RAG查詢
POST   /upload/single       # 單文件上傳
POST   /upload/batch        # 批量文件上傳 (最多10個)
DELETE /documents/{id}      # 單文件删除
DELETE /documents/batch     # 批量删除
GET    /documents           # 文檔列表 (準備中)
POST   /search              # 檢索查詢 (準備中)
GET    /statistics          # 系統統計
```

#### API 特點
- **異步支持**: 所有I/O操作都是異步的
- **錯誤處理**: 統一的錯誤響應格式和Pydantic驗證
- **數據驗證**: 完整的請求/響應模型驗證
- **文檔生成**: 自動FastAPI Swagger/OpenAPI文檔
- **類型安全**: 端到端類型檢查
- **測試通過**: 所有端點功能驗證完成

### 🔧 服務層設計

#### 服務抽象
```python
# 依賴注入模式
class ServiceRegistry:
    def get_database_service(self) -> DatabaseService:
    def get_ingestion_service(self) -> IngestionService:
    def get_embedding_service(self) -> EmbeddingService:
    def get_cache_service(self) -> CacheService:
```

#### 配置管理
```python
class ConfigManager:
    # 環境變數管理
    # 服務發現
    # 動態配置更新
```

## 擴展性和可維護性

### 🏗️ 架構優勢

#### 可擴展性
- **模塊化設計**: 每個組件都是獨立的
- **插件架構**: 新的處理器和檢索器可以輕鬆添加
- **服務抽象**: 底層實現可以替換而不影響上層

#### 可維護性
- **清晰的分層**: API → Service → Domain → Data
- **依賴注入**: 組件間耦合度低
- **測試友好**: 每個模塊都可以單獨測試

#### 高可用性
- **異步處理**: 非阻塞的I/O操作
- **錯誤隔離**: 單個組件的失敗不會影響整個系統
- **資源管理**: 適當的連接池和快取策略

### 🔮 未來擴展計劃

1. **Agentic RAG 核心**: 實現自主查詢規劃和推理
2. **先進檢索算法**: 實現混合檢索和重新排序
3. **前端界面**: React/Vue.js 現代化UI
4. **分布式部署**: Kubernetes 支持
5. **監控和觀測**: Prometheus + Grafana
6. **多租戶支持**: 用戶隔離和權限管理

## 性能優化策略

### 🎯 關鍵性能指標

#### 處理速度目標
- 單個PDF文檔: < 5秒處理完成
- 批量處理: < 1秒/文檔
- API響應: < 100ms (非處理操作)

#### 資源使用優化
- **記憶體管理**: 流式處理大文件
- **連接池**: Neo4j和Supabase連接複用
- **快取策略**: 多層快取覆蓋熱點數據

### 📊 監控指標

#### 業務指標
- 文件處理成功率
- 查詢響應時間
- 用戶滿意度評分

#### 技術指標
- API可用性 (99.9%)
- 數據庫連接池利用率
- 快取命中率

#### 資源指標
- CPU/記憶體使用率
- 存儲空間使用情況
- 網路頻寬使用

## 安全考慮

### 🔒 安全性措施

#### 數據保護
- 敏感數據加密存儲
- 安全的API認證機制
- 輸入驗證和清理

#### 訪問控制
- 角色-based訪問控制 (RBAC)
- API速率限制
- 日誌審計

#### 合規性
- GDPR數據保護
- SOC2安全標準
- 隱私保護措施
