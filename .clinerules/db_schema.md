# Database Schema (GraphRAG + Vectors) - 以應用程序為 UUID 協調中心

此架構適應多模態處理流程，**應用程式**負責生成和協調 UUID。Neo4j 和 pgvector 皆為下游服務，共享這些 UUID 以確保同步刪除。

## 1. Neo4j Graph Schema (GraphRAG DB)

Neo4j 作為知識圖譜和結構化資料的主存儲。

### Node Types (所有 ID 均為 UUID)

#### Document

- **document_id**: **UUID** (來自應用程序/上傳服務)
- title: string
- source_path: string
- hash: string
- created_at: datetime
- updated_at: datetime

#### Chunk (Text)

- **chunk_id**: **UUID** (來自 A2 Text Chunking)
- **vector_id**: **UUID** (來自 A3 Embedding，**用於 pgvector 匹配**)
- text: string
- order: int
- page: int
- document_id: string

#### Entity

- **entity_id**: **UUID** (來自 A5 Creation Service)
- name: string
- type: string
- description: string
- aliases: [string]

#### Event

- **event_id**: **UUID** (來自 A5 Creation Service)
- type: string
- timestamp: string
- description: string

#### VisualFact (VLM Regions)

- **fact_id**: **UUID** (來自 A1 VLM Parsing)
- **vector_id**: **UUID** (來自 A3 Embedding，**用於 pgvector 匹配**)
- region_id: string (VLM 專用區域 ID，非 UUID)
- modality: string
- description: string
- bbox: [x, y, w, h]
- page: int

### Relationships (保持不變)

- (Document)-[:HAS_CHUNK]->(Chunk)
- (Entity)-[:MENTIONED_IN]->(Chunk)
- (Event)-[:MENTIONED_IN]->(Chunk)
- (VisualFact)-[:MENTIONED_IN]->(Chunk)
- (Entity)-[:RELATED_TO]->(Entity)
- (Entity)-[:PARTICIPATES_IN]->(Event)
- (Event)-[:CAUSES]->(Event)
- (Entity)-[:DESCRIBED_BY_IMAGE]->(VisualFact)

---

## 2. pgvector Schema (Supabase pgvector)

pgvector 作為向量索引服務。

### vectors

- **vector_id**: **UUID** (主鍵，與 Neo4j 的 `Chunk/VisualFact.vector_id` 匹配)
- embedding: float[]
- **document_id**: **UUID** (💡 用於 Document 級聯刪除)
- **chunk_id**: **UUID** (或 null) (來自 Chunk)
- **fact_id**: **UUID** (或 null) (來自 VisualFact)
- type: "chunk" \| "vlm_region"
- page: int
- order: int

### 💡 數據同步總結：

| 操作                | 執行順序                                                              | 刪除依據 (UUID)                                              |
| :---------------- | :---------------------------------------------------------------- | :------------------------------------------------------- |
| **Document 刪除**   | 1. Neo4j DELETE 2. pgvector DELETE                                | `document_id` (用於兩邊的級聯刪除)                                |
| **Chunk/Fact 刪除** | 1. 應用程式查詢 Neo4j 獲取 `vector_id` 2. Neo4j DELETE 3. pgvector DELETE | Neo4j 使用 `chunk_id/fact_id`， pgvector 使用 **`vector_id`** |