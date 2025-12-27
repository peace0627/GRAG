## 1. 系統架構與資源管理

本架構核心在於利用 **Gemma 3 的原生多模態能力**，實施 **「按需調用視覺 (Vision On-demand)」** 與 **「一次性視覺事實化 (One-time Visual Factoring)」**，在不犧牲精度的前提下極大化減少 Token 消耗與顯存負擔。

### A. 技術棧整合

- **解析引擎：** **MinerU** (負責 PDF 轉 Markdown 及「預抽離」圖片/表格資產)。
    
- **索引專家：** **LlamaIndex** (管理文檔層級、表格結構及「**原生視覺事實快取**」)。
    
- **邏輯大腦：** **LangGraph** (控制 Agent 狀態機、判斷視覺需求、管理多模態推理路徑)。
    
- **底層接口：** **LangChain** (對接 Ollama API 標準介面、Neo4j Cypher 操作)。
    
- **地端模型：** **Gemma 3 (Vision 版)** (單一模型處理：主推理、Schema 提取、視覺解析)。
    

---

## 2. 核心機制：Gemma 3 原生視覺資源優化策略

為了發揮 Gemma 3 原生視覺優勢同時避免重複計算，系統實施以下配套：

### A. 預抽離與預建檔 (Ingestion Stage)

1. **MinerU 解析：** 系統初步解析時，僅傳輸文本給 Gemma 3，**視覺能力處於休眠狀態**。
    
2. **Asset Registry 建立：** MinerU 將圖表抽離並賦予 `Asset_ID`，LlamaIndex 建立關聯節點，並標記 `visual_fact_status: "pending"`。
    
3. **零成本索引：** 只對圖片周邊的文字描述進行向量化，不預先執行視覺推論。
    

### B. 觸發與快取 (Retrieval Stage)

1. **意圖偵測 (LangGraph)：** 當用戶查詢涉及「技術結構圖」、「數據趨勢」或「產品比例」時。
    
2. **視覺快取檢查：** LangGraph 檢查 LlamaIndex 中的 `VisualFactCache`。
    
    - **Case 1 (Cache Hit):** 該圖片已有文字化的分析記錄，Gemma 3 直接讀取該記錄（純文本模式），**不傳送圖片張量 (Image Tensor)**。
        
    - **Case 2 (Cache Miss):** 若未分析過，Ollama API 調用 Gemma 3 的視覺能力，傳入圖片解析後，將結果回寫至圖譜/向量庫，並更新狀態為 `"completed"`。
        
3. **Token 優化：** 只要分析過一次，該圖片在系統中即「文字化」，後續對話不再消耗視覺 Token。
    

---

## 3. 醫材財報專用 Schema 與 動態演進

### A. 原生實體對齊 (Native Entity Resolution)

- 利用 **Gemma 3** 的原生推理能力。在提取「美敦力 (Medtronic)」等實體時，利用同一個模型的語義空間直接比對 LlamaIndex 中的既存節點。
    
- **別名機制：** 透過 Gemma 3 判定語義等價性，將多樣稱呼統一映射至唯一 ID，確保醫材財務數據的完整性。
    

### B. Schema 自我進化

- 當 Gemma 3 提取出 Schema 未定義的關係（如「併購意向」、「臨床違規」），LangGraph 會將其存入「候選池」。
    
- 系統定期聚類，若某類新關係頻繁出現，則自動建議更新 Pydantic Schema。
    

---

## 4. LangChain、LangGraph 與 LlamaIndex 的分工詳解

|**任務維度**|**LangChain (工具箱)**|**LangGraph (大腦)**|**LlamaIndex (數據夾)**|
|---|---|---|---|
|**視覺觸發**|對接 Ollama Gemma 3 Vision API。|**判定是否需傳送 Image Tensor**。|**儲存與回傳圖片視覺描述快取**。|
|**多模態推理**|封裝多模態 Message 格式。|**控制推理循環**，整合文字與圖表證據。|提供層級上下文與表格結構。|
|**數據入庫**|管理 Neo4j 寫入。|驅動實體對齊邏輯。|**表格解析與層級節點管理**。|

---

## 5. 詳細執行流程 (Workflow)

1. **Ingestion:** MinerU 產出 Markdown + 圖片。LlamaIndex 建立帶有 `Asset_ID` 的索引。
    
2. **User Query:** 用戶提問（如：「比對 Hugo 手術系統與對手的臨床成功率趨勢」）。
    
3. **Planner (LangGraph):** - _Step A:_ 查詢圖譜與文本。若發現「臨床趨勢」數據僅存在於圖片中。
    
    - _Step B (Conditional):_ 檢查快取。若無描述，則加載圖片傳送給 **Ollama-Gemma 3**。
        
4. **Gemma 3 Vision Execution:** 讀取圖片 -> 生成結構化描述 -> **更新 LlamaIndex 視覺快取**。
    
5. **Final Synthesis:** Gemma 3 整合剛生成的視覺事實與既存文本數據，生成具備證據鏈的答案。
    

---

## 6. 嚴謹配套措施 (Implementation Guarantees)

- **單次視覺推論原則：** 每個 Asset 僅在「初次需求」時由 Gemma 3 進行視覺掃描，極大化減少運算資源浪費。
    
- **單一模型語義一致性：** 由於文字與圖片皆由 **Gemma 3** 處理，消除了跨模型（文字模型 vs. 視覺模型）之間的語義對齊誤差。
    
- **可追溯性 (Traceability)：** 回答強制附帶 `Asset_ID`、頁碼、文件來源，並標註該段落是否來自 Gemma 3 的視覺解析。
    
- **數據安全：** 全流程在 **Ollama** 地端運行，保證醫材研發機密與財務敏感資料不外洩。