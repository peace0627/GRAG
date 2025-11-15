# GraphRAG + LLM + VLM 專案 (GRAG)

一個整合知識圖譜、視覺語言模型 (VLM/Qwen2VL) 和大型語言模型 (LLM) 的高階 Agentic RAG 系統。

## 專案概覽
本系統支援多模態查詢、自主推理和動態知識圖譜，實現 Agent 自助規劃、跨模態檢索和事實檢查。

## 架構模組
```
grag/
├── core/          # 核心服務 (Neo4j, Supabase, 配置)
├── agents/        # Agentic RAG 邏輯 (Planner, Retrieval, Reasoning)
├── ingestion/     # 數據引入管道 (VLM, Text Chunking, Embedding)
├── retrieval/     # 檢索引擎 (Hybrid search, Graph traversal)
├── api/           # 後端 API (FastAPI)
├── frontend/      # 前端介面 (Streamlit)
tests/             # 測試套件
docs/              # 文件
```

## 初始實施重點 (階段 0 決定)
依照增量開發原則，按以下優先順序實現模組：
1. **core/ 模組**: 數據庫連接、配置管理 (Neo4j, Supabase)
2. **agents/ 模組**: 核心 Agentic RAG 邏輯 (文本優先，後添加 VLM)
3. **ingestion/ 模組**: 文本 chunking 和 embedding
4. **retrieval/ 模組**: 向量和圖譜檢索
5. **api/ 和 frontend/ 模組**: 完整 API 和 UI

前 3-4 個版本聚焦文本 RAG + 知識圖譜，後續版本逐步整合 VLM 多模態支援。

## 安裝
```bash
# 使用 uv (推薦)
uv sync
uv run ...
```

## 環境要求
- Python >= 3.10
- Neo4j >= 5.20.0
- Supabase

---
