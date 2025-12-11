# GraphRAG + LLM + VLM 專案任務清單 (Todos)

## 專案概述
基於 plan.md 和 progress.md 的任務分解，聚焦當前階段7 (Backend API整合) 的實施。

## 階段7: Backend API整合 ✅ 已完成 (100%)
- [x] 實現 FastAPI 應用框架 (`grag/api/app.py`)
- [x] 創建 RAG 查詢端點 (`POST /query`) - 整合 AgenticRAGAgent
- [x] 添加系統狀態監控端點 (`GET /system/status`)
- [x] 實現證據溯源 API (`GET /evidence/{query_id}`) - 待實現
- [x] 配置 CORS 和錯誤處理中間件
- [x] 添加 API 文檔 (Swagger/OpenAPI)
- [ ] 實現異步查詢處理 (background tasks) - 可選增強
- [x] 創建API Schema (`grag/api/schemas.py`)
- [x] 實現簡化RAG查詢端點 (`POST /query/simple`)
- [x] 實現懶加載Agent實例管理
- [x] 配置完整的錯誤處理和響應格式化

## 🎉 階段7里程碑：Agentic RAG API整合完成
**實現功能**:
- ✅ **完整RAG查詢**: POST /query - AgenticRAGAgent完整Pipeline
- ✅ **簡化查詢**: POST /query/simple - SimpleRAGAgent備選方案
- ✅ **系統監控**: GET /system/status - Agent和服務狀態檢查
- ✅ **API Schema**: 完整的Pydantic請求/響應模型
- ✅ **錯誤處理**: 結構化錯誤響應和Agent初始化保護
- ✅ **異步支持**: 全異步API設計，支持高並發

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
