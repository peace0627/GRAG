# LLM 配置指南

## 📖 概述

本專案實現了**集中式LLM配置管理系統**，支持多種LLM提供商和動態配置。系統通過 `grag/core/config.py` 和 `grag/core/llm_factory.py` 實現統一的LLM實例管理。

## 🏗️ 架構設計

### 配置層次結構
```
環境變數 (.env)
    ↓
Settings (config.py)
    ↓
LLMFactory (llm_factory.py)
    ↓
各Agent實例
```

### 核心組件

#### **1. Settings (config.py)**
集中定義所有LLM相關配置：
```python
class Settings(BaseSettings):
    # LLM 通用配置
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.1
    llm_max_tokens: int = 2000
    openai_api_key: str = ""

    # Agent專用配置
    planner_llm_model: str = "gpt-4o-mini"
    reasoner_llm_model: str = "gpt-4o-mini"
    answerer_llm_model: str = "gpt-4"
    query_parser_llm_model: str = "gpt-4o"

    # 特殊參數
    query_parser_temperature: float = 0.1
    answerer_temperature: float = 0.3
```

#### **2. LLMFactory (llm_factory.py)**
統一的LLM實例工廠：
```python
class LLMFactory:
    @staticmethod
    def create_planner_llm() -> ChatOpenAI:
        # 查詢規劃專用LLM

    @staticmethod
    def create_answerer_llm() -> ChatOpenAI:
        # 答案生成專用LLM

    # ... 其他工廠方法
```

## ⚙️ 基本配置

### 環境變數設定

#### **1. 創建 .env 文件**
```bash
cp .env.example .env
```

#### **2. 編輯環境變數**
```bash
# OpenAI 配置 (必需)
OPENAI_API_KEY=sk-your-openai-api-key-here

# LLM 通用設定
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
LLM_TEMPERATURE=0.1
LLM_MAX_TOKENS=2000

# Agent 專用模型設定
PLANNER_LLM_MODEL=gpt-4o-mini      # 查詢規劃
REASONER_LLM_MODEL=gpt-4o-mini     # 推理分析
ANSWERER_LLM_MODEL=gpt-4           # 答案生成
QUERY_PARSER_LLM_MODEL=gpt-4o      # 查詢解析

# 特殊溫度設定
QUERY_PARSER_TEMPERATURE=0.1       # 解析需要一致性
ANSWERER_TEMPERATURE=0.3           # 答案需要自然度
```

### 快速啟動配置

#### **最低配置 (開發測試用)**
```bash
# .env
OPENAI_API_KEY=sk-your-key
LLM_MODEL=gpt-3.5-turbo  # 節省成本
```

#### **推薦生產配置**
```bash
# .env
OPENAI_API_KEY=sk-your-key
LLM_MODEL=gpt-4o-mini
PLANNER_LLM_MODEL=gpt-4o-mini
REASONER_LLM_MODEL=gpt-4o-mini
ANSWERER_LLM_MODEL=gpt-4
QUERY_PARSER_LLM_MODEL=gpt-4o
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

## 🔧 進階配置

### 多提供商支持 (未來擴展)

#### **Anthropic Claude**
```python
# 計劃中的配置
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-api-your-key
LLM_MODEL=claude-3-sonnet-20240229
```

#### **本地 Ollama**
```python
# 計劃中的配置
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=llama2:7b
```

### 動態配置調整

#### **運行時調整**
```python
from grag.core.config import settings

# 根據負載動態調整
if high_load:
    settings.llm_model = "gpt-3.5-turbo"
    print("Switched to faster model due to high load")
```

#### **條件配置**
```python
# 根據查詢複雜度選擇模型
if query_complexity > 0.8:
    model = "gpt-4"
else:
    model = "gpt-4o-mini"
```

## 🧪 配置測試

### 測試 LLM 連線

#### **1. 單元測試**
```python
# tests/test_llm_config.py
import pytest
from grag.core.llm_factory import LLMFactory

def test_llm_creation():
    """測試LLM實例創建"""
    llm = LLMFactory.create_planner_llm()
    assert llm is not None
    assert hasattr(llm, 'invoke')

def test_llm_config():
    """測試配置正確性"""
    config = LLMFactory.get_llm_config_summary()
    assert config['provider'] == 'openai'
    assert 'agent_models' in config
```

#### **2. 連線測試**
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

#### **3. 運行測試**
```bash
# 測試LLM配置
uv run python scripts/test_llm_connectivity.py

# 運行單元測試
uv run pytest tests/test_llm_config.py -v
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

## 🔍 故障排除

### 常見問題

#### **1. API 金鑰錯誤**
```bash
# 檢查環境變數
echo $OPENAI_API_KEY

# 驗證金鑰格式
# 應該以 sk- 開頭
```

#### **2. 模型不可用**
```python
# 檢查可用模型
from grag.core.llm_factory import LLMFactory
config = LLMFactory.get_llm_config_summary()
print("Available models:", config['agent_models'])
```

#### **3. 速率限制**
```python
# 檢查API限制
# OpenAI: RPM (requests per minute) 和 TPM (tokens per minute)

# 解決方案: 降低並發或升級計劃
```

#### **4. 連線超時**
```python
# 檢查網路連線
curl -I https://api.openai.com/v1/models

# 檢查代理設定
unset HTTPS_PROXY HTTP_PROXY  # 如果有代理干擾
```

### 調試技巧

#### **啟用詳細日誌**
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# 查看LLM調用詳情
from langchain.callbacks import get_openai_callback
```

#### **測試特定Agent**
```python
# 測試單個Agent的LLM配置
from grag.agents import QueryPlanner

planner = QueryPlanner()
# 檢查LLM配置
print(f"Model: {planner.llm.model_name}")
print(f"Temperature: {planner.llm.temperature}")
```

## 📊 配置最佳實踐

### 成本優化

#### **模型選擇策略**
```python
# 根據任務複雜度選擇模型
def select_model_for_task(task_complexity: float):
    if task_complexity > 0.8:
        return "gpt-4"          # 複雜任務
    elif task_complexity > 0.5:
        return "gpt-4o"         # 中等任務
    else:
        return "gpt-4o-mini"    # 簡單任務
```

#### **快取策略**
```python
# 快取常用查詢結果
@lru_cache(maxsize=1000)
def cached_llm_call(query: str, model: str):
    return llm.invoke(query)
```

### 性能優化

#### **並發控制**
```python
# 限制並發LLM調用
from asyncio import Semaphore
llm_semaphore = Semaphore(5)  # 最多5個並發

async def controlled_llm_call(query):
    async with llm_semaphore:
        return await llm.invoke(query)
```

#### **批次處理**
```python
# 批次處理多個查詢
async def batch_process(queries, batch_size=5):
    results = []
    for i in range(0, len(queries), batch_size):
        batch = queries[i:i+batch_size]
        batch_results = await asyncio.gather(*[
            llm.invoke(query) for query in batch
        ])
        results.extend(batch_results)
    return results
```

## 🔄 配置更新

### 熱重載配置
```python
# 重新載入配置 (開發時使用)
from grag.core.config import settings
settings.__init__()  # 重新初始化

# 或者重新啟動應用
```

### 版本控制配置
```bash
# 儲存配置快照
cp .env .env.backup

# 比較配置差異
diff .env .env.production
```

## 📋 配置檢查清單

### 部署前檢查
- [ ] OPENAI_API_KEY 已設定且有效
- [ ] LLM_MODEL 在可用列表中
- [ ] Agent專用模型已配置
- [ ] Temperature 值在合理範圍 (0.0-1.0)
- [ ] LLM連線測試通過
- [ ] Token限制不會超標

### 監控檢查
- [ ] Token使用量在預算內
- [ ] API調用成功率 > 99%
- [ ] 平均回應時間 < 10秒
- [ ] 錯誤率 < 1%

## 🎯 總結

### 核心原則
1. **集中管理**: 所有LLM配置統一管理
2. **靈活配置**: 支持多種提供商和模型
3. **成本意識**: 根據任務選擇合適模型
4. **監控第一**: 完整的使用量和性能監控

### 配置等級建議
- **開發環境**: gpt-3.5-turbo (成本優先)
- **測試環境**: gpt-4o-mini (平衡性能)
- **生產環境**: gpt-4o/gpt-4 (品質優先)

### 維護建議
- 定期檢查token使用量
- 監控API限速和錯誤
- 根據使用模式調整配置
- 保持配置文檔同步更新

---

*配置版本: 1.0*
*最後更新: 2025-12-02*
*適用專案: GraphRAG + LLM + VLM*
