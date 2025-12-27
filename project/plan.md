# 高階 Agentic RAG 系統 - 醫材財報分析專案計劃

## 系統概述
這是一個專為醫材公司財報分析設計的高階 Agentic RAG 系統，利用 Gemma 3 的原生多模態能力實現「按需調用視覺」與「一次性視覺事實化」，在不犧牲精度的前提下極大化減少 Token 消耗與顯存負擔。

### 核心組件
- **MinerU**: PDF 結構化解析與圖片/表格資產提取
- **LlamaIndex**: 層級節點管理、表格索引與原生視覺事實快取
- **LangGraph**: 狀態機控制、智慧路由、多模態推理路徑管理
- **Gemma 3 (via Ollama)**: 單一模型負責文字推理、Schema 提取、原生視覺解析

## 技術棧
- **語言**: Python
- **框架**: FastAPI, LlamaIndex, LangGraph, LangChain
- **模型接口**: Ollama (Gemma 3 Vision) - 支援多主機負載均衡與故障轉移
- **資料庫**: Neo4j (圖譜資料)
- **測試**: pytest, behave (TDD/BDD)
- **環境管理**: uv

## 架構原則
1. **單一模型語義一致性**: 文字與圖片皆由 Gemma 3 處理，消除跨模型語義誤差
2. **按需視覺調用**: 僅在必要時觸發視覺推理，避免重複計算
3. **一次性視覺事實化**: 每個圖片僅分析一次，後續以文字化記錄重用
4. **資源優化**: 關注 Token 消耗與顯存使用，實現 Lazy Loading

## 開發階段

### Phase 1: 專案初始化與基礎架構
- [x] 建立專案目錄結構
- [ ] 配置 Python 環境與依賴管理
- [ ] 建立核心模組架構
- [ ] 配置 CI/CD 流水線
- [ ] 環境檢查與驗證

### Phase 2: BDD 行為定義
- [ ] Feature 1: 原生按需視覺解析
  - Scenario: 純文本查詢
  - Scenario: 跨模態證據查核
- [ ] Feature 2: 醫材本體映射與實體對齊

### Phase 3: TDD 迭代開發
- [ ] RED: 撰寫失敗測試
  - MinerU_Parser 圖片標記測試
  - Vision_Router 意圖與快取狀態測試
  - LlamaIndex 視覺事實節點關聯測試
- [ ] GREEN: 功能實作
  - Gemma 3 單一 API 接口實現
- [ ] REFACTOR: 優化
  - Lazy Loading 邏輯
  - K-V Cache 管理

### Phase 4: 整合與驗證
- [ ] 視覺快取一致性驗證
- [ ] Schema 演進與聚類邏輯
- [ ] 高可信度回溯機制

### Phase 5: 生產部署
- [ ] 資料庫架構設計
- [ ] FastAPI 應用部署
- [ ] 最終整合測試

## 資料流程
1. **Ingestion**: MinerU 解析 PDF → Markdown + 圖片抽離
2. **Indexing**: LlamaIndex 建立層級節點與 Asset Registry
3. **Query Processing**: LangGraph 分析意圖 → 決定是否需要視覺推理
4. **Inference**: Gemma 3 處理文字/圖片 → 生成結構化輸出
5. **Response**: 整合多模態證據 → 提供可追溯答案

## 品質保證
- **測試覆蓋**: TDD/BDD 雙軌測試策略
- **代碼品質**: Black 格式化, Flake8 檢查
- **效能監控**: Token 消耗與記憶體使用追蹤
- **安全合規**: 地端運行，保護醫材敏感資料

## 風險與緩解
- **模型可用性**: 確保 Ollama 穩定運行 Gemma 3
- **資源消耗**: 實現視覺資源的精確控制
- **資料一致性**: 單一模型保證語義一致性
- **可擴展性**: 模組化設計支持 Schema 演進
