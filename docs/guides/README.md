# GraphRAG 使用指南

## 快速入門

### 🚀 五分鐘上手

1. **安裝依賴**
   ```bash
   uv sync
   ```

2. **設定環境變數**
   ```bash
   cp .env.example .env
   # 編輯 .env 文件，填入 Neo4j 和 Supabase 配置
   ```

3. **啟動服務**
   ```bash
   # 啟動資料庫
   uv run infrastructure/neo4j/start-neo4j-manual.sh

   # 初始化Supabase (在Supabase控制台執行)
   cat infrastructure/supabase/supabase-setup.sql

   # 啟動API服務
   uv run grag-api
   ```

4. **測試功能**
   ```bash
   # 檢查系統狀態
   uv run grag health

   # 上傳文檔
   uv run grag upload sample.pdf

   # 查看API文檔
   # 訪問: http://localhost:8000/docs
   ```

### 📋 系統準備檢查清单

- [ ] Python 3.10+ 已安裝
- [ ] Neo4j 資料庫已啟動
- [ ] Supabase 專案已建立
- [ ] 環境變數已正確設定
- [ ] 網路連線正常

## 核心功能指南

### 📤 文件上傳和管理

#### 支持的文件類型

| 類型 | 說明 | 處理方式 |
|-----|------|----------|
| `.pdf` | PDF文檔 | VLM解析 + OCR降級 |
| `.docx` | Word文檔 | 結構化文字處理 |
| `.md` | Markdown | 語義分塊 |
| `.txt` | 純文字 | 段落分割 |

#### 上傳策略

系統支援多種處理策略：

- **自動判斷**: 根據文件類型智能選擇最適合的處理方式
- **強制VLM優先**: 對所有文件使用視覺語言模型處理
- **文字優先**: 跳過圖像處理，專注於文字內容

#### 文件大小限制

- 單個文件: ≤ 50MB
- 批量上傳: 每次最多 10 個文件
- 建議文件大小: < 20MB (處理更快速)

### 🔍 資料庫操作

#### Neo4j 圖形查詢

```cypher
// 查看所有文檔
MATCH (d:Document)
RETURN d.title, d.created_at
ORDER BY d.created_at DESC

// 查詢實體及其關聯
MATCH (e:Entity)-[:MENTIONED_IN]->(c:Chunk)<-[:HAS_CHUNK]-(d:Document)
WHERE d.document_id = "your-doc-id"
RETURN e.name, e.type, c.text
LIMIT 20

// 搜尋包含關鍵詞的內容
MATCH (c:Chunk)-[:HAS_CHUNK]->(d:Document)
WHERE c.text CONTAINS "關鍵詞"
RETURN d.title, c.text, c.page
```

#### Supabase 向量檢索

```sql
-- 查找相似內容 (需要具體的向量)
SELECT content, page, order_num
FROM vectors
WHERE document_id = 'your-doc-id'
ORDER BY embedding <=> '[query-vector]'
LIMIT 10;
```

### ⚡ 命令行工具

#### 健康檢查
```bash
uv run grag health
```
輸出示例：
```
=== 系統健康檢查 ===
時間戳: 2025-11-18T21:20:45.123456
整體健康度: excellent

服務狀態:
  Neo4j:    ✅
  Supabase: ✅
  LangChain:✅
  VLM:      ✅
  嵌入服務:  ✅
```

#### 文件上傳
```bash
# 基本上傳
uv run grag upload document.pdf

# 強制VLM處理
uv run grag upload document.pdf --force-vlm

# 查看幫助
uv run grag upload --help
```

#### 文件删除
```bash
# 删除單個文件
uv run grag delete 550e8400-e29b-41d4-a716-446655440000

# 查看統計
uv run grag stats
```

### 🌐 API 使用指南

#### 基本概念

API 採用 RESTful 設計，所有端點都返回統一的 JSON 格式響應。

#### 驗證和安全

目前版本的 API 不需要驗證，但生產環境推薦：
- API Key 驗證
- Rate Limiting
- HTTPS 加密

#### 錯誤處理

所有錯誤響應都包含統一格式：
```json
{
  "detail": "Error message with description"
}
```

#### 使用示例

##### cURL 請求
```bash
# 健康檢查
curl http://localhost:8000/health

# 上傳文件
curl -X POST "http://localhost:8000/upload/single" \
     -F "file=@document.pdf"

# 删除文件
curl -X DELETE "http://localhost:8000/documents/uuid-here"

# 查看API文檔
curl http://localhost:8000/docs
```

##### Python 客戶端
```python
import requests
import json

class GraphRAGClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url

    def health_check(self):
        response = requests.get(f"{self.base_url}/health")
        return response.json()

    def upload_file(self, file_path):
        with open(file_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(f"{self.base_url}/upload/single", files=files)
            return response.json()

    def delete_document(self, doc_id):
        response = requests.delete(f"{self.base_url}/documents/{doc_id}")
        return response.json()

# 使用示例
client = GraphRAGClient()
print("Health:", client.health_check())

# result = client.upload_file("document.pdf")
# print("Upload result:", result)
```

## 高級使用場景

### 📊 批量處理工作流

```bash
#!/bin/bash
# 批量處理工作流腳本

DOC_DIR="./documents"
RESULTS_FILE="processing_results.json"

echo "開始批量處理文檔..."

for file in "$DOC_DIR"/*.{pdf,docx,md}; do
    if [ -f "$file" ]; then
        echo "處理: $file"
        result=$(uv run grag upload "$file")

        # 記錄結果
        echo "$result" >> "$RESULTS_FILE"

        # 添加小延遲避免過載
        sleep 2
    fi
done

echo "批量處理完成。結果保存在: $RESULTS_FILE"
```

### 🔄 CI/CD 集成

#### GitHub Actions 示例
```yaml
name: Process Documentation

on:
  push:
    paths:
      - 'docs/**'

jobs:
  process-docs:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - uses: astral-sh/setup-uv@v1

    - name: Setup environment
      run: |
        uv sync
        cp .env.ci .env

    - name: Start databases
      run: |
        uv run infrastructure/neo4j/start-neo4j-manual.sh &
        sleep 30  # 等待 Neo4j 啟動

    - name: Process documents
      run: |
        for doc in docs/**/*.md; do
          uv run grag upload "$doc"
        done

    - name: Health check
      run: uv run grag health
```

### 📈 監控和維護

#### 系統健康監控
```bash
#!/bin/bash
# 健康監控腳本

HEALTH_URL="http://localhost:8000/health"
LOG_FILE="health_monitor.log"

while true; do
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    health=$(curl -s "$HEALTH_URL")

    # 記錄健康狀態
    echo "[$timestamp] $health" >> "$LOG_FILE"

    # 檢查關鍵指標
    if ! echo "$health" | jq -e '.services.neo4j and .services.supabase' > /dev/null; then
        echo "[$timestamp] WARNING: Critical service down!" >&2
        # 發送警報通知
    fi

    sleep 300  # 每5分鐘檢查一次
done
```

#### 數據庫維護
```bash
# Neo4j 數據庫維護
# 連接到 Neo4j Browser: http://localhost:7474

# 查看系統統計
CALL db.resample.index.all();

# 查看索引使用情況
:schema

# 性能監控查詢
MATCH ()-[r]-()
RETURN type(r) as relationship_type, count(r) as count
ORDER BY count DESC;

# 清理孤立節點 (如果有)
MATCH (n)
WHERE NOT (n)--()
DELETE n;
```

### 🔒 生產環境部署

#### Docker 部署
```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# 安裝Python依賴
COPY pyproject.toml .
RUN pip install .

# 複製應用程式
COPY . .

# 設定環境
ENV PYTHONPATH=/app
EXPOSE 8000

# 啟動命令
CMD ["python", "-m", "uvicorn", "grag.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Kubernetes 部署
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: grag-deployment
spec:
  replicas: 3
  selector:
    matchLabels:
      app: grag
  template:
    metadata:
      labels:
        app: grag
    spec:
      containers:
      - name: grag
        image: grag:latest
        ports:
        - containerPort: 8000
        env:
        - name: NEO4J_URI
          valueFrom:
            secretKeyRef:
              name: neo4j-secret
              key: uri
        resources:
          limits:
            cpu: 1000m
            memory: 2Gi
          requests:
            cpu: 500m
            memory: 1Gi
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
```

### 🚀 性能優化建議

#### 索引優化
```cypher
// Neo4j 索引優化
CREATE INDEX document_id_index FOR (d:Document) ON (d.document_id);
CREATE INDEX chunk_text_index FOR (c:Chunk) ON (c.text);
CREATE FULLTEXT INDEX entity_name_index FOR (e:Entity) ON EACH [e.name];
```

#### 文件預處理
- PDF 文件：預先轉換為圖像避免重複 OCR
- 大文件：分割為小塊並行處理
- 快取: 啟用 FastAPI 響應快取

#### 記憶體管理
```python
# 大文件處理時使用串流
from pathlib import Path

def process_large_file(file_path: Path):
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b""):
            process_chunk(chunk)
```

## 故障排除

### 常見問題解決

#### 上傳失敗
- 檢查文件大小是否超限 (< 50MB)
- 驗證文件類型是否受支持
- 確認網路連線正常

#### Neo4j 連接問題
- 檢查 Docker 容器是否運行: `docker ps | grep neo4j`
- 驗證連接字符串: `echo $NEO4J_URI`
- 測試連接: 訪問 http://localhost:7474

#### Supabase 問題
- 確認 API Key 正確
- 檢查專案狀態是否活躍
- 驗證網路連線

#### 效能問題
- 檢查系統資源使用情況
- 優化查詢參數
- 考慮升級硬體配置

### 支持資源

- 📖 [完整API文檔](/docs/api/)
- 🏗️ [架構說明](/docs/architecture/)
- 🔧 [開發指南](/docs/development/)
- 💬 [GitHub Issues](https://github.com/your-repo/issues)
- 📧 聯絡郵箱: support@grag-project.com
