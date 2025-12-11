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

## 階段8: 前端介面 - React + Next.js 架構 🔄 架構規劃完成
**架構決策**: 放棄Streamlit，改用React + Next.js + TypeScript
**理由**: Streamlit重新執行問題嚴重影響用戶體驗，React生態更適合複雜的GraphRAG介面

- [x] 評估前端技術選項 (完成比較分析)
- [x] 設置React + Next.js專案結構
- [x] 實現API客戶端和類型定義
- [x] 創建基礎UI組件 (shadcn/ui + Tailwind)
- [x] 實現查詢介面 (多語言輸入 + 實時建議)
- [x] 實現文件上傳功能 (拖拽上傳 + 進度指示器)
- [ ] 添加Agent reasoning trace展示 (準備實現)
- [ ] 實現圖譜視覺化 (Cytoscape.js) (準備實現)
- [ ] 實現VLM region高亮和多模態展示 (準備實現)
- [ ] 添加系統監控和實時狀態 (準備實現)

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
- [x] 更新所有專案文檔以反映React + Next.js架構決策
  - [x] config/plan.md - 更新階段8詳細計劃
  - [x] config/progress.md - 修正前端狀態描述
  - [x] config/todos.md - 更新任務清單
  - [x] config/history.md - 記錄架構決策
  - [x] README.md - 更新專案概述
  - [x] docs/architecture/README.md - 更新架構說明
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
