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

---

*歷史記錄版本: 1.1*
*最後更新日期: 2025-12-02*
