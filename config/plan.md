# GraphRAG + LLM + VLM 專案實施計劃 (Plan)

## 專案概述
本專案實作一個整合知識圖譜、VLM (Qwen2VL) 和 LLM 的高階 Agentic RAG 系統，支援多模態查詢和 Agent 自助推理。系統採用 LangChain/LangGraph、LlamaIndex、Neo4j、Supabase pgvector、FastAPI 和 Streamlit。

## 實施階段

### 階段 0: 專案初始化 (Project Initialization)
1. 設置版本控制 (.gitignore 已建立)
2. 確認專案結構和配置文件請求
3. 決定目標架構模組

### 階段 1: 環境設置 (Environment Setup)
1. 初始化 Python 项目 (requirements.txt/pyproject.toml)
2. 設置 uv 環境管理
3. 配置 .env 文件模板 (Neo4j, Supabase, API keys)
4. 安裝核心依賴: LangChain, LlamaIndex, FastAPI, Streamlit 等

### 階段 2: 數據庫架構實施 (Database Schema Implementation)
1. Neo4j 知識圖譜設計
   - Node 類型: Document, Chunk, Entity, Event, VisualFact
   - Relationship 定義
2. Supabase pgvector 向量庫設計
   - vectors 表結構
3. 實現同步刪除邏輯 (Cascade Delete)

### 階段 3: VLM/視覺處理層 (VLM/Visual Processing Layer)
1. 實現 VLM 解析器 (Qwen2VL client)
   - 支援 PDF, JPG, PNG
   - OCR 功能集 (pytesseract, pdfplumber)
   - 表格和圖表解析
   - 結構化輸出: regions[], ocr_text, tables[], charts[], visual_facts[]
2. VLM 輸出格式定義 (Pydantic models)
3. 錯誤處理和掃描品質容錯

### 階段 4: LlamaIndex 集成 (LlamaIndex Integration)
1. 文本分塊 (Text Chunking) 服務
2. 統一嵌入 (Unified Embedding) 服務
   - Text embeddings
   - Visual embeddings
3. 三元組提取 (Triple Extraction) from text and visual
4. 區塊/事實匯入 Pipeline 到 Neo4j

### 階段 5: 知識圖譜引擎 (Knowledge Graph Engine)
1. Neo4j 驅動和連接管理 (.env)
2. 實體/事件/視覺事實節點創建服務
3. 關係建立和維護
4. 時序查詢和知識區隔離 (Knowledge Area Isolation)
5. 圖譜走訪和子圖提取

### 階段 6: Agentic RAG 核心 (Agentic RAG Core)
1. LangGraph Planner 開發
   - Query 類型判斷
   - 工具選擇邏輯
   - 多模態需求識別
2. Retrieval Agent
   - Supabase 向量查詢 (semantic search)
   - Neo4j 圖譜走訪 (graph traversal)
3. Reasoning Agent
   - 關係推理 (relation reasoning)
   - 路徑尋找和子圖提取
4. Tool Agent 和 Reflector Agent
   - 工具調用 (OCR, Chunker)
   - 上下文充足性檢查
5. 上下文合併和可選 LangChain Agent
6. LLM 生成最終答案 (Markdown 生成)

### 階段 7: 後端 API (Backend API)
1. FastAPI 應用設置
2. REST/GraphQL API 端點
   - Query 入口
   - 結果返回 (含 evidence list)
3. Audit log 實現 (Plan, tools, evidence)
4. 錯誤處理和回溯邏輯

### 階段 8: 前端介面 (Frontend Interface)
1. Streamlit 應用框架
2. 用戶查詢介面
   - 多語支援 (中/英)
   - 檔案上傳 (PDF, images)
   - Knowledge Area 選擇器
   - 時間範圍篩選 (temporal filter)
3. 結果展示
   - Agent reasoning trace
   - Evidence 展示和 VLM region 高亮
4. 可視化組件
   - 圖譜 viewer (Neo4j subgraph)
   - Chunk viewer
   - VLM region viewer
5. Session state 管理

### 階段 9: 測試與評估 (Testing & Evaluation)
1. 單元測試和集成測試
2. 樣本資料導入測試 (sample PDF)
3. 視覺解析準確率測試 (OCR CER/WER, table parsing F1)
4. 三元組提取一致性測試 (precision/recall)
5. Agent 規劃完整性測試 (multi-step plans)
6. 端到端可追溯性驗證 (evidence tracking)
7. 性能基準測試

### 階段 10: 部署與運維 (Deployment & Operations)
1. Docker 容器化
2. Kubernetes 部署 (使用 kubectl)
3. CI/CD 管道設置 (GitHub Actions 示例)
4. 監控和日誌配置
5. 安全考量 (數據隱私, API 保護)
6. 文件和文檔更新

## 如果專案規模較小，可選捷徑
- 階段 3-4: 從簡單文本處理開始，後依序添加 VLM 功能
- 前端 (階段 8): 先實作基本查詢介面，逐步新增視覺化
- 階段 9: 使用小型標註集迭代模型訓練和 prompt 調整

## 檢查清單 (Checklist)
- [ ] 所有寫入 Neo4j/Supabase 的物件都含 `area_id`
- [ ] VLM 輸出包含 `region_id` 和 `source_file_id`
- [ ] Agent 在產出最終答案前有 Fact-Check 步驟
- [ ] 刪除 Knowledge Area 時 Neo4j 和 Supabase 同步刪除
- [ ] 每個回答必附帶至少 1 個可追溯證據 (graph node 或 VLM region)
- [ ] requirements.txt 無未使用套件
- [ ] 所有配置在 .env 管理
- [ ] 程式結構使用 Pydantic 控制
- [ ] 程式運行在 uv 環境下

## 風險與注意事項
- VLM 模型部署成本 (GPU, on-prem vs cloud)
- 資料隱私處理 (log, cache, sensitive documents)
- 早期階段建議建構標註集來優化 VLM prompt
- 確保各模型 (VLM, embedding, LLM) 可靈活替換

## 交付項目
1. 完整專案代碼基底
2. API 規格 (Swagger/OpenAPI)
3. 資料約定: VLM → LlamaIndex JSON schema
4. CI 測試腳本: sample data ingestion
5. 部署指南
6. 用戶手冊和架構文檔

---

*計劃版本: 1.0*
*更新日期: 2025-11-15*
