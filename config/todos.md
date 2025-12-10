# GraphRAG + LLM + VLM 專案任務清單 (Todos)

## 專案概述
基於 plan.md 和 progress.md 的任務分解，聚焦當前階段7 (Backend API整合) 的實施。

## 階段7: Backend API整合 (進行中)
- [ ] 實現 FastAPI 應用框架 (`grag/api/app.py`)
- [ ] 創建 RAG 查詢端點 (`POST /query`) - 整合 AgenticRAGAgent
- [ ] 添加系統狀態監控端點 (`GET /health`)
- [ ] 實現證據溯源 API (`GET /evidence/{query_id}`)
- [ ] 配置 CORS 和錯誤處理中間件
- [ ] 添加 API 文檔 (Swagger/OpenAPI)
- [ ] 實現異步查詢處理 (background tasks)

## LLM 工廠多提供商支援
- [x] 重構 `grag/core/llm_factory.py` 支援多種LLM提供商
- [x] 新增支援: OpenAI, Ollama, vLLM, LM Studio, 自定義OpenAI兼容API
- [x] 更新配置系統添加 `llm_base_url` 選項
- [x] 修改返回類型為 `BaseChatModel` 支援不同LLM類型
- [x] 更新 `.env.example` 添加完整LLM配置範例

## 專案維護任務
- [ ] 檢查 requirements.txt 無未使用套件
- [ ] 驗證所有配置都在 .env 管理
- [ ] 確保程式結構使用 Pydantic 控制
- [ ] 確認程式運行在 uv 環境下
- [x] 更新 history.md (已創建)

## 測試與驗證
- [ ] 運行現有測試 (`tests/` 目錄)
- [ ] 驗證 LLM 連線 (`python -m grag.cli health`)
- [ ] 測試文件上傳和處理流程
- [ ] 端到端 RAG 查詢測試

## 文件更新
- [ ] 更新 README.md (如果有變更)
- [ ] 更新 API 規格文檔
- [ ] 更新部署指南

---

*任務清單版本: 1.0*
*基於 plan.md 和 progress.md 生成*
*創建日期: 2025-12-02*
