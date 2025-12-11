# GraphRAG Tests

專案的測試套件，驗證核心業務邏輯和集成功能。

## 🧪 測試總覽

### 目前的測試

| 測試文件 | 測試對象 | 當前狀態 | 描述 |
|---------|---------|----------|-----|
| `test_embedding_providers.py` | 向量嵌入功能 | ✅ **可用** | 測試嵌入服務的配置、載入和向量生成 |
| `test_langchain_ingestion.py` | 數據導入管道 | ✅ **可用** | 測試LangChain組件和數據處理流程 |
| `test_structured_query_parser.py` | 查詢解析器 | ✅ **可用** | 測試LLM驅動的結構化查詢解析功能 |
| `test_unified_knowledge_system.py` | 統一知識系統 | ✅ **可用** | 測試知識表示、Agent路由和證據融合 |

### 測試類型

#### 1. 單元測試 (Unit Tests)
- 函數級驗證
- 不依賴外部服務
- 快速執行

#### 2. 集成測試 (Integration Tests)
- 測試組件間互動
- 可能需要外部依賴
- 更貼近現實場景

## 🚀 運行測試

### 環境準備

```bash
# 1. 安裝依賴
uv sync

# 2. 設置環境變數 (測試用)
cp .env.example .env.test

# 編輯 .env.test 以包含基本配置
# 至少需要嵌套服務的基本配置

# 3. 如果需要外部服務，啟動它們
# Neo4j (可選)
uv run infrastructure/neo4j/start-neo4j-manual.sh

# Supabase (測試時可使用mock)
```

### 運行單個測試文件

```bash
# 嵌入提供者測試 (需要基本配置)
uv run python tests/test_embedding_providers.py

# LangChain導入測試 (無外部依賴)
uv run python tests/test_langchain_ingestion.py
```

### Agent功能測試 (推薦開始)

```bash
# 1. 運行Agent測試腳本 (互動式)
uv run python scripts/test_agent.py

# 2. 運行單個Agent查詢
uv run python scripts/test_agent.py "請介紹一下這個系統的主要功能"

# 3. 使用pytest運行結構化測試
uv run pytest tests/test_structured_query_parser.py -v
```

### 使用 pytest 運行 (推薦)

```bash
# 安裝測試依賴
uv sync --extra dev

# 運行所有測試
uv run pytest tests/

# 運行特定測試
uv run pytest tests/test_embedding_providers.py -v

# 運行時顯示輸出
uv run pytest tests/ -s --tb=short

# 生成覆蓋率報告
uv run pytest tests/ --cov=grag --cov-report=html
```

## 📋 測試分類說明

### `test_embedding_providers.py`

測試向量嵌入功能的各個方面：

**測試範圍:**
- 配置文件載入驗證
- Provider 工廠模式
- 嵌入服務集成
- 分塊嵌入處理
- Provider 工具函數

**所需配置:**
```env
EMBEDDING_PROVIDER=sentence_transformers
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384
```

**測試輸出示例:**
```
🚀 Running Embedding Providers Integration Tests

🧪 Testing configuration loading...
  EMBEDDING_PROVIDER: sentence_transformers
  EMBEDDING_MODEL: all-MiniLM-L6-v2
  ...
✅ Configuration loading test passed
```

🧪 測試1: LangChain文檔載入器
✅ 載入文檔成功: 3 個chunks
📏 合併後長度: 234 字符
```
### `test_langchain_ingestion.py`

測試數據處理管道的核心組件：

**測試範圍:**
- LangChain文檔載入器
- 文件處理策略決定
- 結構化文字回退處理
- 分塊服務功能

**特點:**
- 完全無外部依賴
- 使用臨時文件測試
- mock LangChain Docuemnts

**測試輸出示例:**
```
🚀 測試LangChain元件
🧪 測試1: LangChain文檔載入器
✅ 載入文檔成功: 3 個chunks
📏 合併後長度: 234 字符
```

### `test_structured_query_parser.py`

測試LLM驅動的結構化查詢解析功能：

**測試範圍:**
- 中英文查詢解析
- 查詢類型分類 (factual, analytical, visual, temporal, complex)
- 查詢意圖識別
- 約束條件解析
- 推理需求分析
- 響應格式處理
- 回退解析機制

**測試類型:**
- 單元測試: 使用mock LLM進行隔離測試
- 集成測試: 使用真實LLM進行端到端測試 (需要API key)

**測試輸出示例:**
```python
# 中文查詢解析測試
result = parser.parse_query("圖表顯示哪個月銷售最低？")
assert result.structured_query.query_type == QueryType.VISUAL
assert result.structured_query.intent.primary_action == PrimaryAction.FIND

# 英文查詢解析測試
result = parser.parse_query("What are the sales by region?")
assert result.structured_query.language == "en"
assert result.structured_query.query_type == QueryType.FACTUAL
```

### `test_unified_knowledge_system.py`

測試統一知識表示和Agent系統的核心組件：

**測試範圍:**
- 知識單元 (KnowledgeUnit) 創建和管理
- 統一證據 (UnifiedEvidence) 表示和處理
- 可追溯性信息 (TraceabilityInfo) 功能
- 智能路由器 (SmartRouter) 查詢路由邏輯
- 證據融合引擎 (EvidenceFusionEngine) 功能
- 來源可靠性權重計算
- 證據去重和矛盾檢測

**測試特點:**
- 完全無外部依賴的單元測試
- 測試統一知識模式的核心邏輯
- 驗證Agent系統的組件集成

**測試輸出示例:**
```python
# 知識單元創建測試
unit = KnowledgeUnit(
    knowledge_area_id="sales_q4",
    content="Q4 sales increased by 25%",
    modality=Modality.TEXT,
    source=SourceType.NEO4J
)
assert unit.get_confidence_level().value == "high"

# 證據融合測試
evidence_list = [/* 測試證據 */]
deduplicated = engine._deduplicate_evidence(evidence_list)
assert len(deduplicated) == 1  # 重複證據已被合併
```

### Agent測試腳本 (`scripts/test_agent.py`)

互動式Agent測試工具，專為測試Agentic RAG功能設計：

**功能特點:**
- 互動式查詢測試
- 詳細的執行日誌
- 系統狀態檢查
- 查詢規劃器測試
- 批量測試支持

**使用方法:**
```bash
# 互動模式
uv run python scripts/test_agent.py

# 命令行模式
uv run python scripts/test_agent.py "請介紹一下這個系統的主要功能"

# 在互動模式中:
# - 輸入查詢進行測試
# - 輸入 'test' 運行預設測試套件
# - 輸入 'quit' 退出
```

**測試輸出示例:**
```
🚀 GraphRAG Agent測試工具
🔧 初始化Agentic RAG Agent...
✅ Agent初始化成功
📊 系統狀態: operational
� 可用Agent: 5
�️ 可用工具: 5

🤖 測試查詢: 請介紹一下這個系統的主要功能
--------------------------------------------------
✅ 查詢成功
   查詢ID: factual_22129013
   查詢類型: factual
   信心分數: 0.00
   證據數量: 0
   執行時間: 0.34秒
```
==================================================
🧪 測試1: LangChain文檔載入器
✅ 載入文檔成功: 3 個chunks
📏 合併後長度: 234 字符
```

## 🔧 測試維護

### 添加新測試

1. **為新功能創建測試文件**
   ```python
   # tests/test_new_feature.py
   from grag.new_module import NewFeature

   def test_new_feature():
       feature = NewFeature()
       assert feature.working_condition()
   ```

2. **選擇測試類型**
   - 如果只測試一個函數 → 單元測試
   - 如果測試多組件交互 → 集成測試

### 測試約定

1. **檔案命名**: `test_*.py`
2. **函數命名**: `test_*()`
3. **測試文件位置**: `tests/` 目錄
4. **導入路徑**: 從專案根目錄開始

### CI/CD 集成

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]

jobs:
  test:
    steps:
    - name: Run tests
      run: |
        uv sync
        uv run pytest tests/ --cov=grag --cov-report=xml
```

## 🐛 常見問題

### 測試失敗 - 缺少依賴

```bash
ModuleNotFoundError: No module named 'sentence_transformers'
```

**解決方案:**
```bash
# 安裝開發依賴
uv sync --extra dev

# 或手動安裝
pip install sentence-transformers pytest
```

### 測試失敗 - 配置問題

```bash
AssertionError: Embedding provider should be configured
```

**解決方案:**
```bash
# 設置基本配置
export EMBEDDING_PROVIDER=sentence_transformers
export EMBEDDING_MODEL=all-MiniLM-L6-v2
export EMBEDDING_DIMENSION=384
```

### 測試失敗 - 頭緒鎖定問題

部分測試在運行時會發生 asyncio 事件循環衝突。

**解決方案:**
```bash
# 使用同步替代
uv run python -m pytest tests/ --tb=short -x
```

## 🎯 測試策略建議

### 未來測試路線圖

1. **API 測試**: 使用 httpx 或 FastAPI TestClient 測試REST端點
2. **資料庫測試**: 測試Neo4j和Supabase集成（使用測試資料庫）
3. **端到端測試**: 測試完整文件上傳到檢索的流程
4. **性能測試**: 測試不同負載下的處理速度
5. **錯誤處理測試**: 測試網路故障、檔案損壞等異常情況

### 測試品質指標

- **覆蓋率**: 目標 > 80%
- **執行時間**: 每個測試 < 30秒
- **CI通過率**: > 95%
- **無 flaky tests**: 測試結果應該穩定

## 📞 聯絡與支持

如果測試相關問題，歡迎：
- 查看已知問題: [GitHub Issues](issues)
- 提交新問題: [New Issue](new-issue)
- 貢獻測試: [PR Guidelines](pull-request)
