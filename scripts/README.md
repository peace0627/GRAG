# GraphRAG 腳本說明

本目錄包含GraphRAG系統的部署和測試腳本。

## 🚀 部署腳本

### run_server.sh

啟動GraphRAG REST API服務的腳本。

**使用方法**:
```bash
# 基本啟動
./scripts/run_server.sh

# 或直接使用uv
uv run uvicorn grag.api.app:app --host 0.0.0.0 --port 8000 --reload
```

**功能特點**:
- 自動檢測Python環境 (優先使用uv)
- 設置正確的PYTHONPATH
- 顯示服務信息和文檔鏈接
- 支持熱重載開發模式

**啟動後訪問**:
- API服務: http://localhost:8000
- API文檔: http://localhost:8000/docs
- 替代文檔: http://localhost:8000/redoc

## 🧪 測試腳本

### test_agent.py

Agentic RAG系統的互動式測試工具。

**使用方法**:
```bash
# 運行完整測試
uv run python scripts/test_agent.py

# 或直接運行
python scripts/test_agent.py
```

**測試功能**:
- 🤖 **AgenticRAGAgent測試**: 完整的智能查詢Pipeline
- 🔍 **SimpleRAGAgent測試**: 簡化查詢測試
- 📊 **性能評估**: 查詢時間和信心度量
- 🛠️ **組件測試**: 各個Agent模塊單獨測試
- 📝 **日誌記錄**: 詳細的測試結果和錯誤信息

**測試場景**:
1. **基本查詢測試** - 測試不同類型的查詢
2. **多模態查詢** - 圖表分析、視覺問題
3. **推理測試** - 複雜邏輯推理
4. **錯誤處理** - 異常情況處理
5. **性能測試** - 響應時間和資源使用

**測試輸出示例**:
```
🚀 GraphRAG Agent 測試工具
================================

選擇測試類型:
1. AgenticRAGAgent 完整測試
2. SimpleRAGAgent 快速測試
3. 性能基準測試
4. 組件單元測試

輸入選擇 (1-4): 1

執行 AgenticRAGAgent 測試...
查詢: "圖表顯示哪個月銷售最低？"

📊 測試結果:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
查詢ID: visual_123456
查詢類型: visual
最終答案: 根據數據顯示，2月份銷售額最低，為150萬。
信心度: 0.85
證據數量: 3
執行時間: 0.504秒

✅ 測試通過！
```

## 🔧 開發工具

### 自定義腳本創建

如需創建新的測試或部署腳本，請遵循以下模式：

```bash
#!/bin/bash
# GraphRAG 自定義腳本

# 環境檢查
if ! command -v uv &> /dev/null; then
    echo "❌ 需要安裝 uv"
    exit 1
fi

# 主要邏輯
echo "🚀 執行自定義任務..."
uv run python your_script.py
```

### 環境變數

腳本會自動讀取 `.env` 文件中的配置：
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`
- `SUPABASE_URL`, `SUPABASE_KEY`
- `OPENAI_API_KEY`, `LLM_MODEL`
- `DEBUG`, `LOG_LEVEL`

## 📊 監控和日誌

### 服務日誌
```bash
# 查看API服務日誌
docker logs neo4j-grag  # Neo4j日誌
uv run uvicorn grag.api.app:app --log-level debug  # 詳細API日誌
```

### 性能監控
```bash
# 系統狀態檢查
curl http://localhost:8000/system/status

# 健康檢查
curl http://localhost:8000/health
```

## 🐛 故障排除

### 常見問題

#### 腳本執行失敗
```bash
# 檢查權限
chmod +x scripts/run_server.sh

# 檢查Python環境
uv --version
python --version
```

#### 端口衝突
```bash
# 修改端口
uv run uvicorn grag.api.app:app --host 0.0.0.0 --port 8001 --reload
```

#### 依賴問題
```bash
# 重新安裝依賴
uv sync --reinstall
```

## 📝 腳本維護

- **版本控制**: 所有腳本都應加入Git版本控制
- **文檔更新**: 修改腳本時同步更新此README
- **測試驗證**: 重要腳本應有對應的測試
- **錯誤處理**: 包含適當的錯誤處理和用戶友好的錯誤信息

---

*最後更新: 2025-12-11*
