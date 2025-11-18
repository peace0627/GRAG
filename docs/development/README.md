# GraphRAG 開發指南

## 本地開發環境設置

### 開發工具安裝

#### 使用 uv (推薦)
```bash
# 安裝 uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 進入專案目錄
cd grag

# 安裝依賴
uv sync

# 啟動開發模式
uv run --with pytest --with ruff --with black python -m grag.cli health
```

#### 使用 pip (傳統方式)
```bash
# 安裝依賴
pip install -e .[dev]

# 或者使用 requirements.txt
pip install -r requirements/dev.txt
```

### 開發環境配置

#### 環境變數設置
```bash
# 複製環境模板
cp .env.example .env

# 編輯開發配置
nano .env
```

#### IDE 配置
**VS Code 推薦設定**:
```json
{
  "python.defaultInterpreterPath": "./.venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.formatting.provider": "black",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests"]
}
```

## 開發工作流程

### 🐛 代碼規範

#### 代碼格式化
```bash
# 自動格式化所有代碼
uv run black grag/

# 檢查代碼品質
uv run ruff check grag/

# 自動修復可修復的問題
uv run ruff check --fix grag/
```

#### 類型檢查
```bash
# 類型檢查 (如果有 mypy 配置)
uv run mypy grag/
```

### 🧪 測試策略

#### 測試結構
```
tests/
├── unit/              # 單元測試
│   ├── test_health_service.py
│   ├── test_database_services.py
│   └── test_embedding_providers.py
├── integration/       # 整合測試
│   └── test_ingestion_pipeline.py
└── fixtures/          # 測試數據
    ├── sample_docs/
    └── test_configs.py
```

#### 運行測試
```bash
# 運行所有測試
uv run pytest

# 運行特定測試
uv run pytest tests/test_health_service.py

# 測試覆蓋率
uv run pytest --cov=grag --cov-report=html

# 並行測試
uv run pytest -n auto
```

#### 編寫測試的原則
```python
import pytest
from grag.core.health_service import HealthService

class TestHealthService:
    @pytest.fixture
    def health_service(self):
        return HealthService()

    def test_get_system_status_returns_dict(self, health_service):
        """測試系統狀態返回字典格式"""
        result = health_service.get_system_status()
        assert isinstance(result, dict)
        assert 'overall_health' in result

    def test_overall_health_is_valid(self, health_service):
        """測試整體健康度是有效值"""
        result = health_service.get_system_status()
        valid_health = ['excellent', 'good', 'fair', 'poor', 'unknown']
        assert result['overall_health'] in valid_health
```

### 🔄 持續集成

#### Git Hooks 設置
```bash
# 安裝 pre-commit hooks
pip install pre-commit
pre-commit install

# 手動運行檢查
pre-commit run --all-files
```

#### CI/CD 配置示例 (.github/workflows/ci.yml)
```yaml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - uses: astral-sh/setup-uv@v1
    - name: Install dependencies
      run: uv sync
    - name: Run tests
      run: uv run pytest --cov=grag --cov-report=xml
    - name: Upload coverage
      uses: codecov/codecov-action@v3

  lint:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - uses: astral-sh/setup-uv@v1
    - name: Install dependencies
      run: uv sync
    - name: Check formatting
      run: uv run black --check grag/
    - name: Lint code
      run: uv run ruff check grag/
```

## 代碼組織原則

### 📁 目錄結構最佳實踐

```
grag/
├── core/                  # 核心服務層
│   ├── __init__.py
│   ├── config.py          # 組態管理
│   ├── health_service.py  # 健康檢查
│   ├── cache_manager.py   # 快取管理
│   └── schemas/           # 數據模式
│       ├── __init__.py
│       ├── neo4j_schemas.py
│       └── pgvector_schemas.py
├── api/                   # API層
│   ├── __init__.py
│   └── app.py            # FastAPI應用
├── ingestion/            # 數據處理層
│   ├── __init__.py
│   ├── loaders/          # 文件載入器
│   ├── processors/       # 處理器
│   ├── services/         # 業務服務
│   ├── vision/           # 視覺處理
│   └── indexing/         # 索引處理
├── agents/               # Agent邏輯 (將來實現)
├── retrieval/            # 檢索邏輯 (將來實現)
└── cli.py               # 命令行接口
```

### 🏗️ 架構原則

#### 1. 關注點分離 (Separation of Concerns)
- **API層**: 只負責HTTP請求/響應處理
- **服務層**: 封裝業務邏輯
- **數據層**: 處理數據存儲和檢索

#### 2. 依賴倒轉 (Dependency Inversion)
```python
# 好的例子: 依賴抽象
class DatabaseService(ABC):
    @abstractmethod
    async def save_document(self, doc: Document) -> UUID:
        pass

# 避免: 直接依賴具體實現
def save_to_neo4j(doc: Document):
    # 直接使用Neo4j驅動
    pass
```

#### 3. 單一責任原則 (Single Responsibility)
```python
# 好的例子: 每個類只有一個改變的理由
class DocumentParser:
    """只負責解析文檔"""
    def parse(self, file_path: Path) -> ParsedDocument:
        pass

class ChunkGenerator:
    """只負責生成分塊"""
    def generate_chunks(self, doc: ParsedDocument) -> List[Chunk]:
        pass

# 避免: 一個類做太多事情
class DocumentProcessor:
    """這個類做了太多事情"""
    def parse_and_chunk_and_embed(self, file_path):
        # 解析 + 分塊 + 嵌入 = 三個責任
        pass
```

### 🔄 異步編程模式

#### Async/Await 使用原則
```python
# ✅ 正確的使用異步
@app.post("/upload")
async def upload_file(file: UploadFile):
    # 所有I/O操作都是異步的
    result = await ingestion_service.process_file(file)
    return result

# ❌ 避免在異步函數中混用同步操作
async def bad_example():
    # 不要在異步函數中調用同步數據庫操作
    sync_db_operation()  # 會阻塞事件循環
```

#### 異步測試
```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result is not None

# 使用 pytest-asyncio 插件提供更好的支持
```

## 性能優化技巧

### 🎯 FastAPI 性能優化

#### 1. 使用依賴注入
```python
from fastapi import Depends

def get_database_service() -> DatabaseService:
    return DatabaseService()

@app.get("/health")
async def health_check(service: DatabaseService = Depends(get_database_service)):
    return await service.get_status()
```

#### 2. 響應壓縮
```python
from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(GZipMiddleware, minimum_size=1000)
```

#### 3. 快取策略
```python
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend

@app.on_event("startup")
async def startup():
    redis = aioredis.from_url("redis://localhost")
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")
```

### 🌐 Neo4j 優化

#### 連接池配置
```python
from neo4j import AsyncGraphDatabase

# 生產環境配置
driver = AsyncGraphDatabase.driver(
    uri,
    auth=auth,
    max_connection_lifetime=30,  # 30分鐘
    max_connection_pool_size=50, # 最大連接數
    connection_acquisition_timeout=10  # 獲取連接超時
)
```

#### 查詢優化
```cypher
// ✅ 好的查詢: 使用索引
MATCH (d:Document {document_id: $doc_id})
RETURN d

// ✅ 批量操作: 使用參數化查詢
UNWIND $document_ids AS doc_id
MATCH (d:Document {document_id: doc_id})
RETURN d
```

### ⚡ Supabase 優化

#### 向量搜索優化
```sql
-- 創建適當的索引
CREATE INDEX ON vectors USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- 使用適當的搜索參數
SELECT * FROM vectors
ORDER BY embedding <=> '[query_vector]'
LIMIT 20;
```

## 調試技巧

### 🔍 常見調試技巧

#### 1. 日誌配置
```python
import logging

# 配置結構化日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# 在代碼中使用
logger.info("Processing document", extra={"document_id": doc_id})
```

#### 2. 開發環境調試
```python
import os

if os.getenv('DEBUG') == 'true':
    # 開發環境下的調試邏輯
    import pdb; pdb.set_trace()
```

#### 3. FastAPI 調試模式
```bash
# 啟動時包含調試信息
uv run uvicorn grag.api.app:app --reload --log-level debug
```

### 🐛 常見錯誤排查

#### Neo4j 連接問題
```bash
# 檢查 Neo4j 服務狀態
curl http://localhost:7474

# 檢查連接字符串
echo $NEO4J_URI

# 測試連接
python -c "from neo4j import GraphDatabase; driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'password')); driver.verify_connectivity(); driver.close()"
```

#### Supabase 配置問題
```bash
# 檢查環境變數
echo $SUPABASE_URL
echo $SUPABASE_KEY

# 測試連接
python -c "import supabase; client = supabase.create_client('$SUPABASE_URL', '$SUPABASE_KEY'); print('Connected successfully')"
```

## 貢獻指南

### 📝 提交規範

#### Commit 消息格式
```
type(scope): description

[optional body]

[optional footer]
```

#### Type 類型
- `feat`: 新功能
- `fix`: 修復錯誤
- `docs`: 文檔更新
- `style`: 代碼格式
- `refactor`: 重構
- `test`: 測試相關
- `chore`: 構建/工具

#### 示例
```bash
git commit -m "feat(ingestion): add PDF parsing support

Add support for parsing PDF documents with OCR fallback.
Includes multi-language OCR and table extraction.

Closes #123"
```

### 🔄 分支策略

#### Git Flow 工作流程
```bash
# 創建功能分支
git checkout -b feature/pdf-parsing

# 開發完成
git commit -m "feat: implement PDF parsing"

# 推送到遠程
git push origin feature/pdf-parsing

# 創建 PR
# 在 GitHub 上創建 Pull Request
```

### 📋 Pull Request 檢查清单

#### 代碼品質
- [ ] 通過所有測試 (`pytest`)
- [ ] 代碼格式化正確 (`black`)
- [ ] 通過代碼檢查 (`ruff`)
- [ ] 類型註解完整

#### 文檔
- [ ] 更新相關的文檔
- [ ] 添加必要的註釋
- [ ] 更新變更日誌

#### 測試
- [ ] 添加單元測試
- [ ] 測試覆蓋率 ≥ 80%
- [ ] 通過整合測試

#### 兼容性
- [ ] 向後兼容的變更
- [ ] 更新依賴項版本
- [ ] 檢查 breaking changes
