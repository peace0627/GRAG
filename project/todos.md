# 高階 Agentic RAG 系統 - 待辦事項清單

## Phase 1: 專案初始化與基礎架構 ✅ 完成
- [x] 建立專案目錄結構 (`/project/`, `/ingestion/`, `/graph_nodes/`, `/schema/`, `/tests/tdd/`, `/tests/bdd/`)
- [x] 建立 `plan.md` 和 `todos.md` 在 project/
- [x] 配置 `requirements.txt` (FastAPI, LlamaIndex, LangGraph, LangChain, pydantic, ollama, pytest, behave)
- [x] 更新關鍵套件版本 (llama-index: 0.9.0→0.14.10, fastapi: 0.104.0→0.127.1)
- [x] 確認 LangChain/LangGraph 版本相容性 (已成功升級到 1.x 版本)
- [x] 優化依賴管理 (移除不必要的 langchain-community)
- [x] 建立 `.env` 檔案管理參數設定
- [x] 建立 `.gitignore` 檔案
- [x] 配置 CI/CD (GitHub Actions: black, flake8, pytest)
- [x] 環境檢查: 驗證 Ollama 已安裝並加載 Gemma 3 Vision 權重
- [x] 實作多主機 Ollama 客戶端 (支援負載均衡、故障轉移)

## Phase 2: BDD 行為定義 🚀 進行中

## Phase 2: BDD 行為定義 🚀 進行中
- [x] Feature 1: 原生按需視覺解析
  - [x] Scenario: 純文本查詢 (不涉及圖表時僅傳送 Markdown)
  - [x] Scenario: 跨模態證據查核 (涉及圖表時檢查快取狀態)
  - [x] Vision Router 核心邏輯實作與測試
- [ ] Feature 2: 醫材本體映射與實體對齊
  - [ ] 使用 Gemma 3 進行三元組提取
  - [ ] 實作別名機制與實體對齊邏輯

## Phase 3: TDD 迭代開發
- [ ] RED: 撰寫失敗測試
  - [ ] MinerU_Parser: 驗證圖片標記為 pending 狀態與 Asset_ID
  - [ ] Vision_Router: 根據意圖與快取狀態決定是否加入 Image_Base64
  - [ ] LlamaIndex: 正確關聯 Markdown 塊與視覺事實節點
- [ ] GREEN: 功能實作
  - [ ] 實現 Gemma 3 單一 API 接口 (純文字/多模態切換)
- [ ] REFACTOR: 優化
  - [ ] 實作 Lazy Loading 邏輯
  - [ ] K-V Cache 優化 (清除不再需要的圖片 Tensor)

## Phase 4: 整合與驗證
- [ ] 視覺快取一致性驗證
  - [ ] 模擬查詢醫療專利圖 (第一次觸發視覺推理)
  - [ ] 第二次查詢相同圖片 (僅觸發文本推理)
- [ ] Schema 演進與聚類
  - [ ] 模擬提取新關係 (Breakthrough_Device_Designation)
  - [ ] 驗證候選池邏輯
- [ ] 高可信度回溯
  - [ ] 確保答案標註證據來源 (文本段落 vs. Gemma 3 視覺解析)

## Phase 5: 生產部署
- [ ] 參考 `database_schema.md` 設計 Neo4j 架構
- [ ] FastAPI 應用部署配置
- [ ] 最終整合測試與效能驗證

## 品質保證任務
- [ ] 設置 pytest 測試框架
- [ ] 配置 behave BDD 測試
- [ ] 實作代碼品質檢查 (black + flake8)
- [ ] 建立效能監控機制

## 風險緩解任務
- [ ] 建立 Ollama 健康檢查機制
- [ ] 實作資源使用監控 (Token 消耗、記憶體)
- [ ] 設計錯誤處理與重試邏輯
- [ ] 建立備份與恢復機制
