# GraphRAG + LLM + VLM 專案歷史記錄 (History)

## 專案變更歷史

### 2025-12-02: 初始化專案管理和LLM限制確認
**執行內容**:
- 確認專案計劃 (plan.md) 和目前進度 (progress.md)
- 創建任務清單 (todos.md) 基於目前階段7進行中的Backend API整合
- 確認 `grag/core/llm_factory.py` 只使用OpenAI，不支援Ollama等其他提供商
- 更新工廠註釋，明確標記只支援OpenAI
- 創建歷史記錄文件 (history.md)

**變更檔案**:
- `config/todos.md` (新建)
- `config/history.md` (新建)
- `grag/core/llm_factory.py` (註釋更新)

**最小變動原則**: 只修改必要註釋，未改變功能邏輯

### 2025-12-02: 重構LLM工廠支援多提供商
**執行內容**:
- 根據用戶需求重構 `grag/core/llm_factory.py`，支援多種LLM提供商
- 新增支援: OpenAI, Ollama, vLLM, LM Studio, 自定義OpenAI兼容API
- 更新配置系統，添加 `llm_base_url` 和擴展提供商選項
- 修改返回類型為 `BaseChatModel` 以支援不同LLM類型
- 更新 `.env.example` 添加完整的LLM配置選項
- 保持向後兼容，支援現有代碼無縫遷移

**變更檔案**:
- `grag/core/llm_factory.py` (完全重構)
- `grag/core/config.py` (添加 llm_base_url 配置)
- `.env.example` (添加 LLM 配置範例)
- `config/history.md` (更新記錄)

**技術改進**:
- 統一的 `_create_llm` 方法動態選擇提供商
- OpenAI兼容API支援 (Ollama, vLLM, LM Studio等)
- 更好的錯誤處理和fallback機制
- 類型安全: BaseChatModel 抽象介面

### 2025-12-11: 實現Agentic RAG API整合
**執行內容**:
- 實現完整的Backend API整合，連接Agentic RAG Core與前端
- 創建 `grag/api/schemas.py` 定義完整的API請求/響應模型
- 實現RAG查詢端點 (`POST /query`) 整合AgenticRAGAgent
- 添加系統狀態監控 (`GET /system/status`) 包含Agent狀態
- 實現簡化RAG查詢 (`POST /query/simple`) 作為備選方案
- 配置懶加載Agent實例管理和錯誤處理

**變更檔案**:
- `grag/api/schemas.py` (新建 - 完整API Schema定義)
- `grag/api/app.py` (擴展 - 添加RAG查詢功能)
- `config/todos.md` (更新 - 標記API任務完成)
- `config/history.md` (更新記錄)

**技術實現**:
- **API Schema**: Pydantic模型定義所有請求/響應格式
- **Agent整合**: 懶加載AgenticRAGAgent實例，支援異步查詢
- **錯誤處理**: 結構化錯誤響應和Agent初始化失敗處理
- **類型安全**: 完整的請求驗證和響應序列化
- **向後兼容**: 保持現有文件管理API不變

**API端點總覽**:
- `POST /query` - 完整Agentic RAG查詢 (planning + retrieval + reasoning)
- `POST /query/simple` - 簡化RAG查詢 (SimpleRAGAgent)
- `GET /system/status` - 系統狀態檢查 (含Agent狀態)
- `GET /health` - 基礎健康檢查
- 文件管理端點保持不變

---

*歷史記錄版本: 1.2*
*最後更新日期: 2025-12-11*
