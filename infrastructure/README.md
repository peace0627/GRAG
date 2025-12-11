# 🗃️ GraphRAG 基礎設施配置

本目錄包含GraphRAG系統的完整基礎設施配置，包括資料庫、部署腳本和架構文檔。

**🎉 最新狀態**: 系統已實現完整的生產級資料庫架構，所有服務測試通過。

## 結構說明

```
database/
├── neo4j/           # Neo4j圖形資料庫
│   ├── docker/      # Docker配置和啟動腳本
│   └── README.md    # Neo4j專用說明
├── supabase/        # Supabase向量資料庫
│   ├── supabase-setup.sql      # 完整建表和權限腳本
│   ├── supabase-rls-fix.sql    # RLS權限修復腳本
│   └── README.md    # Supabase專用說明
├── docs/            # 資料庫架構文檔
│   ├── db_schema.md        # 資料庫架構說明
│   └── project-overview.md # 專案總體架構
└── migrations/      # 資料庫遷移腳本 (未來的擴充)
```

## 主要資料庫

### 🗂️ Neo4j (知識圖譜)
- **用途**: 存儲實體關係和知識圖譜
- **位置**: `database/neo4j/`
- **啟動**: `docker/neo4j-grag/start-db.sh`

### 🔍 Supabase pgvector (向量搜索)
- **用途**: 儲存向量嵌入和相似性搜尋
- **位置**: `database/supabase/`
- **表名**: `vectors`

## 架構總覽

### 資料流
1. 文檔 → LangChain載入 → 處理器 → 嵌入
2. → Neo4j (圖形存儲)
3. → Supabase (向量存儲)

### 關鍵概念
- **Document**: 文檔節點 (Neo4j)
- **Chunk**: 文檔分塊 (Neo4j)
- **Entity**: 辨識出的實體 (Neo4j)
- **Vector**: 384維嵌入向量 (Supabase)

## 設定與使用

### 環境變數 (在專案根目錄的`.env`)
```bash
# Neo4j設定
NEO4J_URI=neo4j://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=testpass123

# Supabase設定
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
```

### 啟動資料庫

#### Neo4j
```bash
cd database/neo4j/docker
./start-neo4j-manual.sh  # 或使用docker-compose.yaml
```

#### Supabase
1. 打開 [Supabase Dashboard](https://supabase.com/dashboard)
2. 執行 `database/supabase/supabase-setup.sql`
3. 設定RLS權限

### 驗證連線

#### Neo4j檢查
```python
from neo4j import GraphDatabase
driver = GraphDatabase.driver("neo4j://localhost:7687", auth=("neo4j", "testpass123"))
driver.verify_connectivity()
```

#### Supabase檢查
```python
from supabase import create_client
client = create_client(url, key)
response = client.table('vectors').select('*').limit(1).execute()
```

## 資料庫維護

### 定期清理
- Neo4j數據瀏覽器: http://localhost:7474
- Supabase儀表板: https://supabase.com/dashboard

### 故障排除
1. Neo4j啟動問題 → 檢查Docker狀態
2. Supabase連線問題 → 驗證環境變數
3. 權限錯誤 → 執行RLS權限腳本

## 架構細節

詳見 `database/docs/db_schema.md`
