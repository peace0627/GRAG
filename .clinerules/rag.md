## 1. 系統架構與資源管理

本架構核心在於 **「按需啟動 (On-demand)」** 與 **「一次性分析 (One-time Inference)」**，將昂貴的 VLM 運算降至最低。

### A. 技術棧整合

- **解析引擎：** **MinerU** (負責 PDF 轉 Markdown 及「預抽離」圖片/表格)。
    
- **索引專家：** **LlamaIndex** (管理文檔層級、表格結構及「視覺事實快取」)。
    
- **邏輯大腦：** **LangGraph** (控制 Agent 狀態機、判斷視覺需求、調度 VLM)。
    
- **底層接口：** **LangChain** (對接 Ollama API、Neo4j Cypher 操作)。
    
- **地端模型：** **Gemma-2-9B** (主推理)、**DeepSeek-VL** (視覺探針)。
    

---

## 2. 核心機制：視覺資源優化策略 (On-Demand VLM)

為了解決 VLM 顯存佔用過高與重複計算問題，系統實施以下配套：

### A. 預抽離與預建檔 (Ingestion Stage)

1. **MinerU 解析：** 系統初步解析時，VLM **不啟動**。
    
2. **Asset Registry 建立：** MinerU 將圖表抽離為實體檔案（如 `fig_001.png`），並在 LlamaIndex 索引中建立關聯節點，標記 `is_analyzed: False`。
    
3. **零成本索引：** 只對圖片周邊的文字描述進行向量化。
    

### B. 觸發與快取 (Retrieval Stage)

1. **意圖偵測 (LangGraph)：** 當用戶查詢需要視覺證據（如「分析這張專利結構圖」）。
    
2. **快取檢查：** LangGraph 檢查 LlamaIndex 中的 `VisualFactCache`。
    
    - **Case 1 (Hit):** 若該圖片已有分析記錄，直接讀取文字描述，**不啟動 VLM**。
        
    - **Case 2 (Miss):** 若未分析過，則動態加載 VLM，執行解析後將結果回寫至 Neo4j/Vector DB，並標記 `is_analyzed: True`。
        
3. **顯存卸載：** 分析任務結束，立即釋放 VLM 顯存，歸還給 Gemma-2-9B。
    

---

## 3. 醫材財報專用 Schema 與 動態演進

### A. 實體對齊 (Entity Resolution)

- 利用 LlamaIndex 的向量搜尋進行初步比對，再由 LangGraph 調用 Gemma-2 進行邏輯確認。
    
- **別名機制：** 統一映射醫材術語（如將 "MDT" 與 "Medtronic" 綁定至單一 ID），確保財報數據不分裂。
    

### B. Schema 自我進化

- 當 Gemma 提取出 Schema 未定義的關係（如「專利訴訟」），LangGraph 會將其存入「候選池」。
    
- 系統定期聚類，若頻率過高則自動建議新增類別。
    

---

## 4. LangChain 與 LangGraph 的分工詳解

|**任務維度**|**LangChain (工具箱)**|**LangGraph (大腦)**|**LlamaIndex (數據夾)**|
|---|---|---|---|
|**視覺觸發**|提供 DeepSeek-VL API 接口。|**判定 Query 是否需看圖**。|**儲存與回傳圖片快取狀態**。|
|**多步推理**|封裝 Cypher 查詢工具。|**控制循環 (Loop)** 直到證據充足。|提供層級上下文 (Context)。|
|**數據入庫**|無。|無。|**表格解析與層級塊切分**。|

---

## 5. 詳細執行流程 (Workflow)

1. **Ingestion:** MinerU 產出 Markdown + 圖片檔。LlamaIndex 建立索引，圖片節點為 `pending` 狀態。
    
2. **User Query:** 用戶提問。
    
3. **Planner (LangGraph):** 決定工具路徑。
    
    - _Step A:_ 查詢圖譜與文本向量。
        
    - _Step B (Conditional):_ 若資料庫中 `visual_description` 為空，且問題需看圖，則跳轉至 **VLM 節點**。
        
4. **VLM Execution:** 讀取圖片 -> 生成描述 -> **回寫快取 (Update Index)** -> 釋放 VLM。
    
5. **Final Synthesis:** 整合文字、表格與視覺事實，生成答案。
    

---

## 6. 嚴謹配套措施 (Implementation Guarantees)

- **單次分析原則：** 每個 Asset_ID 在系統生命週期內僅執行一次 VLM 推論，極大化節省 GPU 成本。
    
- **可追溯性 (Traceability)：** 所有回答必須附帶 `Asset_ID`、`Page_Number` 與 `Source_File`。
    
- **數據安全：** 全流程地端運行，保證醫材研發機密不外洩。
    
- **評估機制：** 整合 RAGAS 定期檢查「視覺事實」對回答準確性的貢獻度。
    

---

## 🎯 結論：這是一套「聰明且節省」的系統

透過這套計畫，您的系統將像一位專業分析師：**平時讀文字，遇到圖表時翻開來看一次並寫下筆記，之後再有人問，就直接翻筆記，不再重複耗費體力。**