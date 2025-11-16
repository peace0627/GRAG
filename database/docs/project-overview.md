# GraphRAG + LLM + VLM 驅動的高階 Agentic RAG 專案

## 🧭 專案目標
建立一個整合 **知識圖譜**、**VLM 模型用於多模態辨識原始檔成為markdown（例如 Qwen2VL）** 與 **高階 Agentic RAG** 系統（LLM問答或者生成markdown文件），使 Agent 能夠自主規劃、多步推理、跨模態（文本與視覺）查詢並回答基於動態知識圖譜的複雜問題。

系統必須支援：
- 知識區隔離（Knowledge Area Isolation）
- VLM、embedding model跟LLM是可以不同模型並支援各家模型
- 混合檢索（Hybrid Retrieval）：關係推理 + 語義搜索 + 視覺內容描述
- 多模態理解（markdown、pdf、文件、圖像、掃描件）
- 時序/動態資料（temporal / evolving knowledge）
- 語義推理與自我反思（Fact-check / Reflection）
- 明確責任分層（Graphiti 負責資料關係、Agent 負責語言/視覺/邏輯）

系統核心元件：
langchain 1.0
langraph 1.0
LlamaIndex
FastAPI/GraphQL
Streamlit

---

## ⚙️ 系統架構概覽
```pgsql
                   ┌──────────────────────────────────┐
                   │           Documents              │
                   │   (PDF / Image / Report / OCR)   │
                   └──────────────────────────────────┘
                                   │
              ┌────────────────────┴────────────────────┐
              │                                         │
              ▼                                         ▼
  (A1) VLM Parsing                            (A2) Text Chunking
    Qwen2VL / OCR / Chart Parser                   LlamaIndex
              │                                         │
              ▼                                         ▼
      ┌──────────────────┐                    ┌──────────────────┐
      │   vlm_regions    │                    │  text_chunks     │
      │ (bbox, caption)  │                    │ (chunks, meta)   │
      └──────────────────┘                    └──────────────────┘
              │                                         │
              ▼                                         ▼
        (A3) Embedding (Unified Multimodal Embeddings: text + vision)
              │                                         │
              ▼                                         ▼
        ┌──────────────────────────────────────────────────────┐
        │                 Supabase pgvector (vectors)          │
        │ text / visual / OCR embeddings + metadata            │
        └──────────────────────────────────────────────────────┘
              │                                         │
              ▼                                         ▼
 (A4) Create VisualFact nodes                    (A5) Create Entity/Event nodes
              │                                         │
              └───────────────► Neo4j Knowledge Graph ◄─┘
                                 (GraphRAG DB)
```


```mathematica
                        ┌───────────────────────────┐
                        │        User Query         │
                        └───────────────────────────┘
                                      │
                                      ▼
                          (B1) LangGraph Planner
                           - 判斷 query 類型
                           - 決定使用哪些工具
                           - 決定是否要查視覺 + 查圖譜
                                      │
                                      ▼
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │                     (B2) Multi-Agent Retrieval Stage                        │
 │─────────────────────────────────────────────────────────────────────────────│
 │ Retrieval Agent:                                                            │
 │     → Query Supabase vectors (semantic dense)                               │
 │     → Query Neo4j (entity / event / visualfact graph walk)                  │
 │                                                                              │
 │ Reasoning Agent:                                                             │
 │     → Neo4j relation reasoning                                               │
 │     → path finding / knowledge subgraph extraction                           │
 │                                                                              │
 │ Tool Agent:                                                                  │
 │     → 調用 OCR / Chunker / LlamaIndex                                        │
 │                                                                              │
 │ Reflector Agent:                                                             │
 │     → 檢查 context 是否足夠                                                  │
 │     → 決定是否重查 / 補查                                                    │
 └─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
                          (B3) Merge Context
                       (vectors + graph subgraph)
                                      │
                                      ▼
                        (B4) LangChain Agent（可選）
              - 如需對最終答案進行：推理、格式化、任務分解、規劃
                                      │
                                      ▼
                            (B5) LLM Final Answer
                       - 深度推論 / Markdown 生成
                                      │
                                      ▼
                     (B6) Backend API (FastAPI / GraphQL)
                                      │
                                      ▼
              (B7) Frontend: Streamlit / Visualization Panel
             - Graph viewer
             - Chunk viewer
             - VLM region viewer
             - RAG trace 展示

```

```scss
           ┌─────────────── A. Ingestion ───────────────┐
Document → VLM Parsing → vlm_regions → vectors → Neo4j ← Text Chunking
           └────────────────────────────────────────────┘

                              │
                              ▼

          ┌──────────── B. Agentic RAG Runtime ───────────┐
User Query → LangGraph Planner
              → Retrieval Agent (vectors)
              → Reasoning Agent (Neo4j)
              → Reflector Agent
              → Merge Context
              → LangChain Agent（可選）
              → LLM Final Output
          └──────────────────────────────────────────────┘

                              │
                              ▼
                Backend API (FastAPI/GraphQL)
                              │
                              ▼
                   Frontend (Streamlit Dashboard)

---

## 🧱 元件與職責說明（含新增 VLM 層）

### 1️⃣ VLM / Qwen2.5VL 層（**文件視覺處理**）
**功能**：
- 處理原始文件（PDF 掃描、JPG、PNG、截圖、表格、圖表）。
- 執行高品質 OCR、表格識別（表格到 CSV）、圖表解析（ex. 曲線、條狀圖數據點萃取）。
- 產生多尺度文本描述：短摘要 + 詳細視覺事實清單（包括 bounding boxes/region id）。
- 提供結構化 JSON 輸出（`regions[]`, `ocr_text`, `tables[]`, `charts[]`, `visual_facts[]`）。

**輸出格式（範例）**：
```json
{
  "file_id":"...",
  "area_id":"sales_q4",
  "ocr_text":"...",
  "tables":[{"table_id":"t1","csv":"..."}],
  "charts":[{"chart_id":"c1","type":"line","points":[...] }],
  "visual_facts":[{"entity":"Revenue","value":"$1.2M","region":"bbox_3"}]
}
```

**檢查點**：
- 支援 PDF、PNG、JPG；對掃描品質（傾斜、噪點）有容錯策略。
- 生成描述需包含 metadata：`area_id`, `event_time`, `source_file_id`, `region_id`。
- 帶 region reference 的描述能回溯到原始影像位置（便於人機核驗）。

---

### 2️⃣ LlamaIndex 層
**功能**：
- 將原始文本與 VLM 的結構化描述同等處理（chunking + embeddings）。
- 從文本與視覺描述中萃取三元組（triples）並送至 GraphRAG DB。
- 向 Supabase Vector DB 寫入 embeddings，metadata 必含 `area_id` 與 `event_time`。

**檢查點**：
- VLM 輸出必須可溯源：每個 chunk 的 metadata 要能追溯到 `file_id` 與 `region_id`。
- 寫入 GraphRAG DB 與 Supabase 的操作要保證原子性或有補償機制（transaction 或 retry + idempotency token）。

---

### 3️⃣ GraphRAG DB 層（Neo4j 知識圖譜）

**功能**：

- 以 **Neo4j** 作為底層圖形資料庫，儲存實體（nodes）、關聯（edges）、時間資訊與資料來源（provenance）。
    
- graph DB SDK（或 API）負責將 LlamaIndex 萃取出的三元組（triples）寫入 Neo4j。
    
- 提供關聯查詢（relationship reasoning）、時序查詢（temporal filter）與跨資料域的 KnowledgeArea 隔離。
    

**資料結構對應**：
請參考文件 agentic_rag_db_schema.md

**檢查點**：

- Neo4j 驅動（`neo4j>=5.20.0`）需在環境中可連線，連線 URI 透過 `.env` 管理。
- 支援 cascade delete：刪除 KnowledgeArea 時，同步觸發 Neo4j node/edge 清除 + Supabase vector 同步刪除。
- 所有 Graphiti 寫入動作必須可追溯來源（`source_file_id`, `region_id`）。

---

### 4️⃣ LangChain Agent 層（Planner）
**功能**：
- 分解複雜任務（multi-step planning），在 call tools 前輸出執行計畫（Plan）。
- Tool selection：GraphitiQueryTool（關係查詢） vs VectorSearchTool（語義/視覺描述檢索） vs VLM-Refetch Tool（必要時重新請求視覺解析）。
- 自我反思（Reflection / Fact-Check）：生成答案前，比對 Graphiti 與 Vector DB 的證據。

**新增要求**：
- Agent 能辨識『需要視覺證據』的問題（例如："圖表顯示哪個月銷售最低？"），並強制呼叫 VectorSearchTool 去檢索 VLM 的 `visual_facts`。
- Hybrid Fallback：若第一次檢索結果不足，Agent 必須自動再做一次不同策略（更寬鬆的時間窗或使用 Graphiti 邏輯查詢）。

---

### 5️⃣ API Gateway / Backend（FastAPI）
**功能**：
- 單一入口，接收 user query，代理呼叫 Agent、回傳結果。
- 支援 REST / GraphQL，並提供 Audit log（每次 query 之 Plan、tools 呼叫與 evidence）。

**檢查點**：
- Response 必包含 evidence list（來源 node id 或 vector id 與 snippet 或 visual region reference）。

---

### 6️⃣ Streamlit 前端層（User GUI）
**功能**：
- 作為系統的人機介面，負責使用者查詢輸入、結果展示與證據回溯。
- 提供多語介面（中/英），支援上傳檔案（PDF、圖片、報告）。
- 展示 Agent 的 reasoning 流程（plan、tool 呼叫順序、evidence trace）。
- 視覺化顯示 VLM region 引用（例如在原圖上高亮被引用的區域）。
- 提供 Knowledge Area 選擇器與時間範圍篩選（temporal filter UI）。

**檢查點**：
- 使用 Streamlit session state 保存查詢上下文（包括 area_id、語言、上一輪回答）。
- 確保每個回答區塊附 evidence 展示連結（可展開 graph DB node 或 VLM region）。
- 支援 API Gateway 的 async 呼叫與 loading indicator。
- 支援 dark/light mode、可視化圖表（Plotly/Altair）顯示 graph DB 結果。

---

## 🧩 資料流程總表（簡化）

1. File/Image → Qwen2VL (OCR + charts + visual facts) → structured JSON
2. Qwen2VL 輸出 → LlamaIndex 處理（chunk + embeddings）→ graph DB (triples) & Supabase (vectors)
3. User Query → API Gateway → Agent(plan) → Tool(s) → graph DB / Supabase 回傳 evidence
4. Agent Fact-check → 產出帶 evidence 的回答 → API 回給使用者

---

## 🎯 系統核心檢查清單（快速）
- [ ] 所有寫入 graph DB/Supabase 的物件都含 `area_id`。
- [ ] VLM 輸出包含 region id 與 source file id。
- [ ] Agent 在產出最終答案前有 Fact-Check 步驟。
- [ ] 刪除 KnowledgeArea 時 graph DB 與 Supabase 全面同步刪除。
- [ ] 每個回答必附帶至少 1 個可追溯證據（graph DB node 或 VLM region）。

---

## 🔧 技術實作建議與 Sample requirements.txt
**主要 Python 套件（示例）**
```
# === Core Graph & AI Framework ===
llama-index>=0.14.0,<0.15.0
langchain>=1.0.0,<2.0.0

# === Storage / Database Layer ===
neo4j>=5.20.0                     # Neo4j official Python driver
supabase>=1.0.0,<2.0.0

# === Multimodal / Vision Layer ===
# Qwen2VL has been removed - using Ollama for local VLM instead
pdfplumber>=0.10.0
pytesseract>=0.3.10
transformers>=4.40.0
sentence-transformers>=2.3.0

# === API / Backend ===
fastapi>=0.110.0
uvicorn>=0.23.0
pydantic>=2.0.0,<3.0.0

# === Frontend / Visualization ===
streamlit>=1.30.0
plotly>=6.0.0
altair>=5.0.0

# === Optional ===
openai>=1.0.0                     # 若使用 OpenAI 介面
py2neo>=2021.2.3                  # optional for direct Neo4j ops

```

---

## 🧪 測試、驗證與評估
- **視覺解析準確率**：OCR 字詞準確率（CER/WER）、表格解析 F1。
- **三元組萃取一致性**：人工標註集 vs 自動萃取召回率/精準率。
- **Agent 規劃完整性測試**：模擬複雜 query，檢查 Plan 是否多於一步且對每步有工具選擇理由。
- **端到端可追溯性**：對每個最終答案，驗證至少包含 1 個 Graphiti node 或 VLM region 引用。

---

## ✅ 交付項目
1. 完整 Markdown 專案說明（本文件）。
2. API 規格草案（Swagger / OpenAPI）。
3. Data contract：VLM → LlamaIndex JSON schema。
4. CI / 流程測試腳本：導入 sample PDF，檢查 end-to-end workflow。

---

## 最後提醒
- 若要將 Qwen2VL 或其他 VLM 模型部署於內部（on-prem / private cloud），請特別注意運算成本、GPU 設備、以及資料隱私（敏感文件處理時的 log 與快取政策）。
- 在系統早期，建議先搭建一個小型標註集（含掃描件 + 人工標註的表格/圖表），用來迭代 VLM 的解析 prompt 與後處理規則。

---

*文件版本：2025-11-11*
