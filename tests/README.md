# GraphRAG 測試文檔

## 測試結構總覽

```
tests/
├── README.md                 # 測試文檔 (本文件)
├── integration_test.py       # 統一集成測試 (主要測試入口)
├── test_langchain_ingestion.py  # LangChain組件測試
├── test_embedding_providers.py  # 嵌入提供商測試
├── test_structured_query_parser.py  # 查詢解析器測試
└── test_unified_knowledge_system.py  # 知識系統測試

根目錄臨時測試文件 (可清理):
├── test_api_upload.py        # API上傳測試 (已整合到integration_test.py)
├── test_pdf_upload.py        # PDF上傳組件測試 (已整合)
├── test_full_ingestion.py    # 完整處理管道測試 (已整合)
├── test_supabase.py          # Supabase測試
├── test_vector_*.py          # 向量搜索測試
├── test_fix_simple.py        # 簡單修復測試
├── test_document.txt         # 測試文檔
└── test_frontend_upload.html # 前端測試HTML
```

## 主要測試分類

### 1. 集成測試 (`integration_test.py`)
**用途**: 系統級功能驗證，確保各組件協同工作
**運行方式**:
```bash
cd /path/to/grag
uv run python tests/integration_test.py
```

**測試內容**:
- ✅ LangChain組件功能測試
- ✅ API文件上傳測試
- ✅ 前端文件驗證邏輯測試
- ✅ 系統健康檢查測試

### 2. 單元測試 (`tests/` 目錄下)
**用途**: 個別組件的功能測試
**運行方式**:
```bash
# 運行所有pytest測試
uv run pytest tests/

# 運行特定測試
uv run pytest tests/test_langchain_ingestion.py -v
```

### 3. 開發測試 (根目錄)
**用途**: 開發期間的臨時測試，修復特定問題
**清理建議**: 問題修復後可移動到 `tests/` 或刪除

## 測試環境要求

### 服務依賴
- ✅ Neo4j (localhost:7687)
- ✅ Supabase (配置在.env)
- ✅ FastAPI服務 (localhost:8000)
- ✅ Next.js前端 (localhost:3000)

### 環境變數
```bash
# 複製並配置環境變數
cp .env.example .env
# 編輯 .env 文件，填入實際的數據庫連接信息
```

## 快速測試檢查

### 1. 啟動服務
```bash
# 後端API服務
uv run grag-api

# 前端服務 (新終端)
cd frontend && npm run dev
```

### 2. 運行集成測試
```bash
uv run python tests/integration_test.py
```

### 3. 測試結果解讀
```
🎯 測試通過率: 4/4 (100.0%)
🎉 所有集成測試通過！系統運行正常。
```

## 故障排除

### 常見問題

#### 1. 循環Import錯誤
```
ImportError: cannot import name '...' from partially initialized module
```
**解決方案**: 檢查 `grag/ingestion/vision/__init__.py` 是否有不必要的導入

#### 2. API連接失敗
```
❌ API連接失敗: [Errno 61] Connection refused
```
**解決方案**: 確保FastAPI服務正在運行 (`uv run grag-api`)

#### 3. 數據庫連接失敗
```
❌ Neo4j/Supabase connection failed
```
**解決方案**: 檢查 `.env` 配置和數據庫服務狀態

#### 4. 模組未找到
```
ModuleNotFoundError: No module named 'pydantic_settings'
```
**解決方案**: 安裝依賴項 (`uv sync`)

## 測試開發指南

### 添加新測試
1. 在 `tests/` 目錄下創建測試文件
2. 使用 `pytest` 框架和 `asyncio` 支持
3. 遵循命名慣例: `test_*.py`
4. 在 `integration_test.py` 中添加集成測試項

### 測試文件命名慣例
- `test_langchain_*.py` - LangChain相關測試
- `test_api_*.py` - API端點測試
- `test_frontend_*.py` - 前端邏輯測試
- `test_database_*.py` - 數據庫操作測試
- `integration_test.py` - 系統集成測試

## CI/CD 集成

將以下命令添加到 CI 管道:
```yaml
- name: Run Integration Tests
  run: |
    uv run python tests/integration_test.py
```

---

*最後更新: 2025-12-12*
