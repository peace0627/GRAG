# 🔗 LangChain增強處理測試GUI

這個Streamlit應用專門用於測試我們剛實現的LangChain增強文檔處理功能，包括文件載入、VLM策略、降級處理、分塊和嵌入等核心處理管道。

## 🚀 快速開始

### 環境要求

確保已安裝所需依賴：
```bash
# 從專案根目錄
uv add streamlit langchain-community
```

### 啟動應用

```bash
# 方式一：從專案根目錄
cd /Users/rex/grag
uv run streamlit run grag/frontend/app.py

# 方式二：從frontend目錄
cd grag/frontend
uv run streamlit run app.py

# 方式三：直接用Python
python -m streamlit run grag/frontend/app.py
```

應用將在 `http://localhost:8501` 啟動。

## 🎯 測試功能總覽

### 📤 文件上傳
- **支援格式**: `.pdf`, `.docx`, `.txt`, `.md`
- **檔案大小限制**: 50MB (可配置)
- **即時預覽**: 顯示文件資訊和處理策略提示

### ⚙️ 處理策略配置

#### 三種VLM處理模式：

1. **自動判斷** (推薦)
   - `.pdf`, `.docx` → 使用VLM處理 (視覺分析)
   - `.txt`, `.md` → 直接處理 (LangChain載入)
   - 其他格式 → VLM優先處理

2. **強制開啟**
   - 對所有文檔嘗試VLM處理
   - 失敗時自動降級到結構化文字分析
   - 適合測試降級機制

3. **強制關閉**
   - 跳過VLM，直接使用LangChain載入
   - 使用結構化文字分析
   - 最快速的處理方式

### 📊 處理結果展示

#### 即時統計指標：
- **處理時間**: 從開始到完成的總耗時
- **分塊數量**: 文檔被分割成的chunks數目
- **嵌入向量**: 生成的向量嵌入數量

#### 策略分析：
- **處理狀態**: VLM成功、失敗、降級或直接處理
- **品質等級**: 高/中/低品質評估
- **內容統計**: 文件長度、區域數量等

#### 詳細統計：
- 可展開查看完整處理統計數據
- 包含分塊大小分佈、模型使用情況等

## 🔍 系統狀態檢查

### 側邊欄狀態指示器：

#### ✅ LangChain可用
LangChain Community package已安裝

#### ✅ VLM服務已配置
至少配置了OpenAI或Qwen2VL其中一個API

#### ✅ 嵌入服務可用
Embedding provider正確初始化

#### ⚠️ 配置警告
會顯示缺少配置的服務和建議

## 🧪 測試場景建議

### 1. **基本功能測試**
```
文件: README.md
策略: 自動判斷 (應該直接處理)
期望: ✅成功，處理快，品質中等
```

### 2. **降級機制測試**
```
文件: JPG圖片文件
策略: 強制開啟 (會觸發降級)
期望: ⚠️降級到文字分析，處理慢，但成功
```

### 3. **效能比較測試**
```
文件: 相同內容的三個不同格式
策略: 自動判斷
比較: .txt vs .pdf vs .docx 的處理時間和品質
```

### 4. **錯誤處理測試**
```
文件: 不支援的文件格式
策略: 自動判斷
期望: 顯示清晰錯誤信息和解決建議
```

## 🏗️ 架構說明

### 處理流程：

```
文件上傳 → LangChain載入 → 策略判斷 → [VLM處理 ↗ 降級邏輯]
                                      ↓
分塊處理 ← 結構化文字分析 ← 直接處理 ↗
                                      ↓
嵌入生成 → 統計輸出 → GUI展示
```

### 組件關聯：

- **`ingest_document_enhanced()`**: 核心處理方法 (無資料庫)
- **`LangChainDocumentLoader`**: 多格式載入器
- **`DocumentProcessingStrategy`**: 策略判斷邏輯
- **`StructuredTextFallback`**: VLM失效時的降級處理

## 📝 開發說明

### 擴展新功能：

1. **添加新文件格式**:
   ```python
   # 在LangChainDocumentLoader.loaders中添加
   '.new_ext': NewLoaderClass
   ```

2. **添加新處理策略**:
   ```python
   # 在DocumentProcessingStrategy中擴展邏輯
   def should_use_vlm_first(self, file_path, use_vlm_override):
       # 新邏輯
   ```

3. **添加新統計指標**:
   ```python
   # 在結果處理中添加新欄位
   new_metric = calculate_something()
   st.metric("新指標", new_metric)
   ```

### 配置設定：

應用使用專案的`.env`配置：
- `LANGCHAIN_*`: LangChain相關設定
- `EMBEDDING_*`: 嵌入模型設定
- `MAX_FILE_SIZE_MB`: 文件大小限制

## 🎉 成功指標

當GUI能夠：

1. ✅ **載入多種文件格式** 而不崩潰
2. ✅ **正確應用VLM策略** 根據文件類型
3. ✅ **在VLM失敗時降級** 到文字分析
4. ✅ **生成準確統計** 和處理結果
5. ✅ **提供清楚的反饋** 給用戶

這表示我們的第一階段測試已經成功完成了LangChain增強的處理管道驗證！

---

**下一步**: 等處理管道測試完成後，可以添加第二階段的資料庫整合測試，包含Neo4j圖形資料和pgvector向量索引的端到端測試。
