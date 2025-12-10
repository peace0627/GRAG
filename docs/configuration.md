# 🔧 配置系統架構說明 (包含LLM配置)

## 📋 配置層次結構

```
環境變數 (.env) ← 最高優先級 (運行時覆蓋)
    ↓
設定類 (config.py) ← 中間層 (帶預設值)
    ↓
常數 (constants.py) ← 基礎層 (應用邏輯常數)
```

## 🤖 LLM 配置系統

### 架構設計

專案實現了**集中式LLM配置管理系統**，支持多種LLM提供商和動態配置：

```
環境變數 (.env)
    ↓
Settings (config.py)
    ↓
LLMFactory (llm_factory.py)
    ↓
各Agent實例
```

## 🎯 各層級說明

### 1. 環境變數 (.env) - 最高優先級

#### 用途
- **環境特定配置**: 開發/測試/生產環境差異
- **敏感資訊**: API 金鑰、資料庫密碼
- **動態調整**: 運行時覆蓋而不修改代碼
- **安全性**: 不應提交到版本控制

#### 範例 `.env` 文件
```bash
# 資料庫配置
NEO4J_URI=neo4j://production-server:7687
NEO4J_USER=myuser
NEO4J_PASSWORD=mysecret

# API 金鑰
OPENAI_API_KEY=sk-your-openai-key-here
SUPABASE_KEY=your-supabase-anon-key

# LLM 配置
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
LLM_TEMPERATURE=0.1
PLANNER_LLM_MODEL=gpt-4o-mini
ANSWERER_LLM_MODEL=gpt-4

# 應用配置
DEBUG=false
LOG_LEVEL=WARNING
KNOWLEDGE_AREA_ID=production_area

# 處理參數 (可覆蓋預設值)
CHUNK_SIZE=1500
MIN_ENTITY_CONFIDENCE=0.7
```

#### 讀取方式
- 系統環境變數
- `.env` 文件 (由 python-dotenv 載入)
- Docker/Kubernetes 環境變數

### 2. 設定類 (config.py) - 中間層

#### 用途
- **類型安全**: 使用 Pydantic 進行類型驗證
- **預設值管理**: 提供合理的預設配置
- **環境變數整合**: 自動從環境變數讀取
- **驗證與轉換**: 資料類型轉換和驗證

#### 實現方式

```python
# grag/core/config.py
from pydantic_settings import BaseSettings
from .constants import DEFAULT_CHUNK_SIZE, VECTOR_DIMENSIONS

class Settings(BaseSettings):
    # 資料庫配置 (可被 .env 覆蓋)
    neo4j_uri: str = "neo4j://localhost:7687"
    neo4j_user: str = "neo4j"

    # 處理參數 (使用常數作為預設值)
    chunk_size: int = DEFAULT_CHUNK_SIZE
    embedding_dimension: int = VECTOR_DIMENSIONS["sentence_transformers"]

    class Config:
        env_file = ".env"
        case_sensitive = False
```

#### 特點
- ✅ **自動環境變數映射**: `neo4j_uri` → `NEO4J_URI`
- ✅ **預設值支援**: 環境變數不存在時使用預設值
- ✅ **類型驗證**: 確保配置值的正確類型
- ✅ **快取實例**: 使用 `@lru_cache` 避免重複初始化

#### LLM 配置實現

```python
class Settings(BaseSettings):
    # === AI Model Configuration ===
    # LLM Configuration (Centralized)
    llm_provider: str = "openai"  # openai, ollama, vllm, lmstudio, custom, etc.
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.1
    llm_max_tokens: int = 2000
    openai_api_key: str = ""  # Will be read from OPENAI_API_KEY env var

    # Agent-specific LLM configurations
    planner_llm_model: str = "gpt-4o-mini"  # Query planning - needs precision
    reasoner_llm_model: str = "gpt-4o-mini"  # Reasoning tasks - needs analysis
    answerer_llm_model: str = "gpt-4"       # Final answer generation - needs quality
    query_parser_llm_model: str = "gpt-4o"  # Structured query parsing - needs understanding

    # Agent-specific temperature settings
    query_parser_temperature: float = 0.1   # Low temperature for consistent parsing
    answerer_temperature: float = 0.3       # Slightly higher for natural responses

    # Ollama (local VLM service)
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_api_key: str = "ollama"
    ollama_model: str = "qwen3-vl:235b-cloud"

### 3. 常數 (constants.py) - 基礎層

#### 用途
- **應用邏輯常數**: 不應變化的固定值
- **枚舉與選項**: 支援的格式、品質等級
- **預設參數**: 處理演算法的基礎參數
- **錯誤訊息**: 統一的錯誤訊息定義

#### 範例內容

```python
# grag/core/constants.py

# 處理參數
DEFAULT_CHUNK_SIZE = 1000
OVERLAP_SIZE = 200
DEFAULT_ENTITY_CONFIDENCE = 0.5

# 支援格式
SUPPORTED_EXTENSIONS = {
    "pdf": "pdf",
    "word": "docx",
    "images": ["png", "jpg", "jpeg"]
}

# 品質等級
QUALITY_LEVELS = ["high", "medium", "low", "unknown"]

# 向量維度映射
VECTOR_DIMENSIONS = {
    "sentence_transformers": 384,
    "openai": 1536,
    "cohere": 1024
}
```

#### 特點
- ✅ **版本控制**: 隨代碼一起管理
- ✅ **文檔化**: 清楚說明每個常數用途
- ✅ **可引用**: 其他模組可直接 import 使用
- ✅ **測試友好**: 常數便於單元測試

## 🔄 配置解析流程

### 完整解析順序

1. **環境變數檢查**
   ```bash
   # 檢查系統環境變數
   echo $NEO4J_URI

   # 檢查 .env 文件
   cat .env | grep NEO4J_URI
   ```

2. **Pydantic Settings 處理**
   ```python
   # 自動轉換環境變數名稱
   neo4j_uri → NEO4J_URI (大寫)
   chunk_size → CHUNK_SIZE

   # 使用預設值 (如果環境變數不存在)
   neo4j_uri = os.getenv('NEO4J_URI', 'neo4j://localhost:7687')
   ```

3. **常數整合**
   ```python
   # config.py 使用 constants.py 的值
   from .constants import DEFAULT_CHUNK_SIZE
   chunk_size: int = DEFAULT_CHUNK_SIZE
   ```

### 實際使用範例

```python
from grag.core.config import settings

# 這些值可能來自：
# 1. 環境變數 NEO4J_URI
# 2. .env 文件中的 neo4j_uri
# 3. 預設值 "neo4j://localhost:7687"
print(f"Neo4j URI: {settings.neo4j_uri}")

# 這些值來自 constants.py：
# DEFAULT_CHUNK_SIZE = 1000
print(f"Chunk size: {settings.chunk_size}")

# 如果環境變數存在，會覆蓋常數的預設值
# CHUNK_SIZE=1500 → settings.chunk_size = 1500
```

## 🛠️ 配置管理最佳實踐

### 環境變數命名慣例
```bash
# 資料庫相關
NEO4J_URI=...
SUPABASE_URL=...

# AI 模型相關
OPENAI_API_KEY=...
OLLAMA_BASE_URL=...

# 應用配置
DEBUG=true
LOG_LEVEL=INFO
```

### 常數定義原則
```python
# ✅ 好的常數定義
DEFAULT_TIMEOUT = 120  # 秒
MAX_RETRIES = 3
SUPPORTED_FORMATS = ["pdf", "docx", "txt"]

# ❌ 避免的做法
timeout = 120  # 沒有說明單位
formats = ["pdf", "docx"]  # 沒有 DEFAULT_ 前綴
```

### 設定類組織
```python
class Settings(BaseSettings):
    # 按功能分組並加上註釋
    # === Database Configuration ===
    neo4j_uri: str = "..."

    # === AI Model Configuration ===
    llm_model: str = "..."

    # === Processing Configuration ===
    chunk_size: int = DEFAULT_CHUNK_SIZE
```

## 🤖 Agent 專用 LLM 配置

### 各 Agent 的最佳配置

#### **1. Query Planner (查詢規劃)**
```python
# 推薦配置
PLANNER_LLM_MODEL=gpt-4o-mini
LLM_TEMPERATURE=0.1  # 需要一致性

# 用途: 分析查詢意圖、分類查詢類型、生成執行計劃
# 考量: 低temperature確保計劃的確定性
```

#### **2. Query Parser (查詢解析)**
```python
# 推薦配置
QUERY_PARSER_LLM_MODEL=gpt-4o
QUERY_PARSER_TEMPERATURE=0.1  # 需要精確解析

# 用途: 將自然語言轉為結構化JSON
# 考量: 需要理解複雜語意，建議使用較強模型
```

#### **3. Reasoning Agent (推理分析)**
```python
# 推薦配置
REASONER_LLM_MODEL=gpt-4o-mini
LLM_TEMPERATURE=0.1  # 需要邏輯一致性

# 用途: 知識圖譜推理、關係分析
# 考量: 平衡性能與準確性
```

#### **4. Answerer (答案生成)**
```python
# 推薦配置
ANSWERER_LLM_MODEL=gpt-4
ANSWERER_TEMPERATURE=0.3  # 允許一定創造性

# 用途: 基於證據生成最終答案
# 考量: 需要高品質回應，稍微提高temperature以增加自然度
```

### 配置選擇指南

| 場景 | 推薦模型 | Temperature | 考量點 |
|-----|---------|-------------|--------|
| **開發測試** | gpt-3.5-turbo | 0.1 | 成本效益 |
| **生產環境** | gpt-4o-mini | 0.1 | 性能平衡 |
| **複雜解析** | gpt-4o | 0.1 | 高準確性 |
| **答案生成** | gpt-4 | 0.3 | 高品質 |

## 🧪 LLM 配置測試

### 測試 LLM 連線

#### **連線測試**
```python
# scripts/test_llm_connectivity.py
from grag.core.llm_factory import LLMFactory

async def test_connectivity():
    result = LLMFactory.validate_llm_connectivity()
    print(f"Status: {result['status']}")
    print(f"Available models: {result['models_available']}")

    if result['status'] != 'operational':
        print("Errors:", result['errors'])
```

#### **運行測試**
```bash
# 測試LLM配置
uv run python scripts/test_llm_connectivity.py
```

### 效能測試

#### **Token 使用量監控**
```python
# 監控LLM調用
with get_openai_callback() as cb:
    result = await agent.query("Test query")
    print(f"Tokens used: {cb.total_tokens}")
    print(f"Cost: ${cb.total_cost}")
```

## 🔍 除錯與驗證

### 檢查當前配置
```python
from grag.core.config import settings

# 查看所有設定值
print(settings.dict())

# 檢查特定值來源
import os
print(f"NEO4J_URI from env: {os.getenv('NEO4J_URI')}")
print(f"Settings value: {settings.neo4j_uri}")
```

### 驗證配置載入
```bash
# 測試環境變數覆蓋
export CHUNK_SIZE=2000
python -c "from grag.core.config import settings; print(settings.chunk_size)"

# 檢查 .env 文件
python -c "import os; print('DEBUG:', os.getenv('DEBUG', 'not set'))"
```

## 📝 總結

這個三層配置系統提供了：

1. **靈活性**: 環境變數允許運行時調整
2. **安全性**: 敏感資訊不進入版本控制
3. **可維護性**: 常數集中管理，預設值統一
4. **類型安全**: Pydantic 提供驗證和轉換
5. **開發友好**: 清楚的優先級和覆蓋機制
6. **LLM 支持**: 集中式LLM配置管理，支持多Agent專用模型

### 特別針對 LLM 配置：

- **多模型支持**: 支持 OpenAI、Ollama 等多種提供商
- **Agent 優化**: 各 Agent 使用最適合的模型和參數
- **成本控制**: 根據任務複雜度選擇合適模型
- **性能監控**: Token 使用量和成本追蹤
- **測試驗證**: 完整的連線和配置測試工具

---

*配置系統設計遵循 12-Factor App 原則，支援雲原生部署和容器化環境*
