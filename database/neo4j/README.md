# Neo4j 圖形資料庫配置

Neo4j 是 GRAG 專案的知識圖譜資料庫，用於儲存實體、關係和事件資訊。

## 🐳 Docker 配置

### 快速啟動
```bash
# 方法1: 使用腳本
./database/neo4j/docker/start-neo4j-manual.sh

# 方法2: 使用 docker-compose
cd database/neo4j/docker
docker-compose up -d neo4j
```

### 停止與清理
```bash
# 停止容器
docker stop neo4j-grag

# 刪除包含資料
docker rm neo4j-grag
docker volume rm neo4j-grag-data
```

## 🌐 訪問介面

- **Neo4j Browser**: http://localhost:7474
- **Bolt協議**: neo4j://localhost:7687
- **預設帳號**: neo4j / testpass123

## 📊 資料結構

### 核心節點類型

#### Document (文檔)
```cypher
CREATE (d:Document {
    document_id: 'uuid-string',
    title: '文件名稱',
    source_path: '/path/to/file.pdf',
    hash: 'file_hash',
    created_at: datetime(),
    updated_at: datetime()
})
```

#### Chunk (文本分塊)
```cypher
CREATE (c:Chunk {
    chunk_id: 'uuid-string',
    vector_id: 'uuid-string',  // 對應 Supabase
    text: '分塊內容',
    order: 1,
    page: 1
})
```

#### Entity (實體)
```cypher
CREATE (e:Entity {
    entity_id: 'uuid-string',
    name: '實體名稱',
    type: 'PERSON|ORG|LOCATION|...',
    description: '實體描述'
})
```

#### VisualFact (視覺事實)
```cypher
CREATE (v:VisualFact {
    fact_id: 'uuid-string',
    vector_id: 'uuid-string',  // 對應 Supabase
    region_id: 'region-001',
    modality: 'text|image|chart',
    description: '視覺元素描述',
    bbox: [x, y, width, height],
    page: 1
})
```

## 🔗 關係類型

### 核心關係
```cypher
// 文檔與分塊
(d:Document)-[:HAS_CHUNK]->(c:Chunk)

// 實體與分塊
(e:Entity)-[:MENTIONED_IN]->(c:Chunk)

// 實體互動
(e1:Entity)-[:RELATED_TO]->(e2:Entity)
(e1:Entity)-[:WORKS_AT]->(e2:Entity)

// 視覺元素
(e:Entity)-[:DESCRIBED_BY_IMAGE]->(v:VisualFact)
(v:VisualFact)-[:LOCATED_IN]->(c:Chunk)
```

## 🛠️ 常用查詢

### 統計資訊
```cypher
// 節點統計
MATCH (n) RETURN labels(n), count(*) ORDER BY count(*) DESC;

// 關係統計
MATCH ()-[r]->() RETURN type(r), count(*) ORDER BY count(*) DESC;
```

### 文檔檢索
```cypher
// 查找文檔及其相關分塊
MATCH (d:Document {document_id: $doc_id})-[:HAS_CHUNK]->(c:Chunk)
RETURN d, c ORDER BY c.order;
```

### 實體搜尋
```cypher
// 查找人名實體及其出現的文檔
MATCH (e:Entity {type: 'PERSON'})-[:MENTIONED_IN]->(c:Chunk)<-[:HAS_CHUNK]-(d:Document)
RETURN e.name, collect(d.title) as documents, count(*) as mentions
ORDER BY count(*) DESC;
```

### 語義檢索
```cypher
// 基於實體的二度聯繫搜尋
MATCH (center:Entity {name: '初始實體'})
-[:RELATED_TO*1..2]-(related:Entity)
RETURN related.name, length(path) as distance
ORDER BY distance;
```

## 🔧 維護操作

### 清除所有資料
```cypher
// 注意：此操作不可逆
MATCH (n) DETACH DELETE n;
```

### 效能優化
```cypher
// 創建索引
CREATE INDEX FOR (n:Document) ON (n.document_id);
CREATE INDEX FOR (n:Entity) ON (n.name);
CREATE INDEX FOR (n:Chunk) ON (n.chunk_id);

// 顯示現有索引
SHOW INDEXES;
```

### 備份與還原
```bash
# 備份
neo4j-admin dump --database=graph.db --to=/path/to/backup.dump

# 還原
neo4j-admin load --from=/path/to/backup.dump --database=graph.db --force
```

## 🔍 除錯技巧

### 連線測試
```python
from neo4j import GraphDatabase

def test_connection():
    try:
        driver = GraphDatabase.driver(
            "neo4j://localhost:7687",
            auth=("neo4j", "testpass123")
        )
        driver.verify_connectivity()
        print("✅ Neo4j 連線成功")
        driver.close()
    except Exception as e:
        print(f"❌ Neo4j 連線失敗: {e}")

test_connection()
```

### 查詢慢的原因分析
```cypher
// 查看查詢效能
EXPLAIN MATCH (e:Entity)-[:MENTIONED_IN]->(c:Chunk)<-[:HAS_CHUNK]-(d:Document)
WHERE e.name CONTAINS "關鍵詞"
RETURN e, d, c;
```

## 📋 配置說明

### docker-compose.yml 參數
```yaml
neo4j:
  image: neo4j:5.20-community
  environment:
    NEO4J_AUTH: neo4j/testpass123
    NEO4J_PLUGINS: '["graph-data-science"]'  # 可選
  ports:
    - "7474:7474"  # Browser
    - "7687:7687"  # Bolt
  volumes:
    - neo4j-grag-data:/data
    - neo4j-grag-logs:/logs
```

## 🚨 注意事項

1. **密碼修改**: 首次登入後應修改預設密碼
2. **記憶體設定**: 根據可用系統記憶體調整 Neo4j 配置
3. **備份策略**: 定期備份重要的圖形資料
4. **索引設計**: 為常見查詢模式設計適當的索引
5. **關聯性清理**: 刪除節點時使用 `DETACH DELETE` 以避免孤立節點

## 🔗 相關檔案

- [主專案檔案](../README.md)
- [資料庫架構說明](./docs/db_schema.md)
- [Supabase配置](../supabase/README.md)
