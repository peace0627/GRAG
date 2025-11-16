# 🐳 GRAG專案 Docker 服務

為GraphRAG + LLM + VLM專案提供完整的Docker容器化環境。

## 📦 包含服務

### Neo4j圖形資料庫 (`neo4j-grag`)
- **Neo4j版本**: 5.0 (最新穩定版)
- **初始帳密**: neo4j / testpass123
- **暴露連接埠**:
  - `7474`: 網頁管理介面 (http://localhost:7474)
  - `7687`: Bolt資料庫連線 (neo4j://localhost:7687)
- **插件**: Graph Data Science (圖形分析)
- **資源配置**:
  - JVM堆內存: 512MB - 1GB
  - 頁面快取: 512MB
- **持久化**: 數據和日誌自動保存到Docker volume

### 支持服務
- Supabase本地開發環境 (已註釋，需要時取消註釋)

## 🚀 快速啟動

### 1. 基本啟動
```bash
cd docker

# 啟動Neo4j容器
docker-compose up -d neo4j

# 或使用簡易腳本
./start-neo4j.sh
```

### 2. 完整環境啟動
```bash
# 啟動所有服務 (如果配置了Supabase)
docker-compose up -d
```

### 3. 檢查狀態
```bash
# 查看運行狀態
docker-compose ps

# 查看日誌
docker-compose logs neo4j

# 檢查Neo4j健康狀態
docker-compose exec neo4j cypher-shell -u neo4j -p testpass123 "MATCH () RETURN count(*) limit 1"
```

## 🔑 連線資訊

Neo4j啟動成功後，使用以下資訊：

```bash
# Python連線設定
URI = "neo4j://localhost:7687"
USER = "neo4j"
PASSWORD = "testpass123"

# 環境變數設定 (.env)
NEO4J_URI=neo4j://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=testpass123
```

## 🛠️ 管理命令

### 停止服務
```bash
# 停止Neo4j
docker-compose stop neo4j

# 停止所有服務
docker-compose down
```

### 數據重置
```bash
# 停止容器並刪除所有數據
docker-compose down -v

# 重新啟動
docker-compose up -d neo4j
```

### Neo4j命令行工具
```bash
# 進入容器
docker-compose exec neo4j bash

# 使用cypher-shell
docker-compose exec neo4j cypher-shell -u neo4j -p testpass123

# 執行特定查詢
docker-compose exec neo4j cypher-shell -u neo4j -p testpass123 \
  "MATCH (n) RETURN count(n) as node_count;"

# 查看Neo4j狀態
docker-compose exec neo4j neo4j status
```

## 📊 Neo4j網頁介面

訪問 http://localhost:7474 查看並管理資料庫：

- **初始登入**: neo4j / testpass123
- **範例查詢**:
  ```cypher
  // 查看所有節點
  MATCH (n) RETURN n LIMIT 10;

  // 查看圖形結構
  CALL db.schema.visualization();

  // 基本統計
  MATCH (n) RETURN labels(n) as label, count(n) as count;
  ```

## 🔍 故障排除

### 端口衝突
```bash
# 檢查端口使用
lsof -i :7474 -i :7687

# 修改端口映射 (在docker-compose.yml中)
ports:
  - "7475:7474"  # 將本地7475映射到容器7474
  - "7688:7687"
```

### 記憶體不足
```bash
# Neo4j需要至少2GB RAM
# 在環境變數中調整：
NEO4J_server_memory_heap_max__size=512M  # 調低到512MB
```

### 持久化問題
```bash
# 如果Neo4j無法啟動，檢查Docker volumes
docker volume ls | grep neo4j
docker volume rm $(docker volume ls -q | grep neo4j)

# 然後重新啟動
docker-compose up -d neo4j
```

## 🧪 測試連接

運行專案中的連線測試：

```bash
cd /path/to/grag/project

# 啟動Python測試
python -c "
from neo4j import GraphDatabase
driver = GraphDatabase.driver('neo4j://localhost:7687', auth=('neo4j', 'testpass123'))

with driver.session() as session:
    result = session.run('RETURN \"Neo4j Docker Connected!\" as message')
    print(result.single()['message'])

driver.close()
"
```

成功輸出訊息表示Neo4j服務正常運行！

---

**下一步**: Neo4j啟動成功後，記得更新專案的 `.env` 文件以包含正確的連線資訊。
