# Agentic RAG Core 架構說明

## 📖 概述

Agentic RAG Core 是 GraphRAG + LLM + VLM 系統的核心組件，實現了完整的智能檢索和推理功能。本模塊採用多代理架構，通過LangGraph協調各個專業代理來處理複雜的知識檢索任務。

## 🏗️ 架構總覽

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   User Query    │───▶│  Query Planner  │───▶│  Tool Agent     │
│                 │    │  (LangGraph)    │    │  (Execution)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │ Retrieval Agent │    │ Reasoning Agent │
                       │ (Multi-modal)   │    │ (Graph Logic)   │
                       └─────────────────┘    └─────────────────┘
                                │                        │
                                └───────┬────────────────┘
                                        ▼
                             ┌─────────────────┐
                             │ Final Answer    │
                             │ Generation      │
                             │ (LLM + Evidence)│
                             └─────────────────┘
```

## 🔧 核心組件

### 1. Query Planner (`planner.py`)
**負責**: 智能查詢分析和執行計劃生成

#### 主要功能
- **查詢分類**: 自動識別查詢類型 (factual, analytical, visual, temporal, complex)
- **計劃生成**: 基於查詢類型動態生成執行步驟
- **多模態檢測**: 識別是否需要視覺或時間相關處理

#### 查詢類型
```python
class QueryType(str, Enum):
    FACTUAL = "factual"          # 事實性問題 (What, When, Where)
    ANALYTICAL = "analytical"    # 分析性問題 (Why, How, Compare)
    VISUAL = "visual"           # 視覺相關問題 (需要圖表/圖片)
    TEMPORAL = "temporal"       # 時間相關問題
    COMPLEX = "complex"         # 複雜推理問題
```

#### 執行流程
1. **分析階段**: 使用LLM分析查詢結構
2. **分類階段**: 基於關鍵詞和內容分類
3. **計劃階段**: 生成具體執行步驟
4. **驗證階段**: 檢查計劃可行性

### 2. Retrieval Agent (`retrieval_agent.py`)
**負責**: 多模態信息檢索

#### 檢索策略
- **向量搜索**: 語義相似度檢索 (Supabase pgvector)
- **圖譜遍歷**: 關係和實體檢索 (Neo4j)
- **混合排序**: 合併多源結果

#### 支持的檢索類型
- **基本檢索**: 直接關鍵詞匹配
- **時間檢索**: 帶時間過濾的檢索
- **推理檢索**: 支持多跳關係的檢索
- **探索檢索**: 發現相關概念的檢索

### 3. Reasoning Agent (`reasoning_agent.py`)
**負責**: 知識圖譜推理和邏輯分析

#### 推理模式
- **實體關係推理**: 分析實體間的連接
- **路徑尋找**: 發現概念間的最短路徑
- **時間推理**: 處理時間序列和順序
- **因果推理**: 分析原因和結果關係

#### 推理算法
- **圖遍歷**: BFS/DFS 圖搜索
- **路徑分析**: 最短路徑和關聯路徑
- **模式匹配**: 圖模式識別和匹配

### 4. Tool Agent (`tool_agent.py`)
**負責**: 動態工具調用和執行協調

#### 工具系統
```python
class ToolType(str, Enum):
    VECTOR_SEARCH = "vector_search"
    GRAPH_TRAVERSAL = "graph_traversal"
    VLM_RERUN = "vlm_rerun"
    OCR_PROCESS = "ocr_process"
    TEXT_CHUNK = "text_chunk"
```

#### 執行流程
1. **工具選擇**: 基於查詢需求選擇合適工具
2. **參數準備**: 動態生成工具參數
3. **執行調用**: 異步執行工具
4. **結果收集**: 聚合工具輸出

### 5. Structured Query Parser (`query_parser.py`) ⭐ **新增**
**負責**: LLM驅動的查詢解析，將自然語言轉換為結構化JSON

#### 核心功能
- **多語言支持**: 自動檢測並處理中英文等多語言查詢
- **JSON結構化**: 將任意查詢轉換為標準化的結構化表示
- **LLM解析**: 使用GPT-4進行高準確率的查詢理解
- **Fallback機制**: LLM失敗時自動降級到關鍵詞匹配

#### 支持的查詢類型
- **factual**: 事實性問題 (What, When, Where)
- **analytical**: 分析性問題 (Why, How, Compare)
- **visual**: 視覺相關問題 (圖表, 圖片)
- **temporal**: 時間相關問題 (季度, 年份)
- **complex**: 複雜推理問題
- **causal**: 因果分析
- **comparative**: 比較分析
- **predictive**: 預測性問題

#### JSON輸出示例
```json
{
  "query_type": "visual",
  "intent": {
    "primary_action": "find",
    "target_metric": "sales",
    "group_by": "month",
    "visualization_preferred": true
  },
  "constraints": {
    "must_include": ["monthly_data"],
    "preferred_sources": ["charts"]
  },
  "reasoning_requirements": {
    "needs_comparison": true,
    "complexity_level": "medium"
  },
  "response_format": {
    "include_evidence": true,
    "preferred_style": "concise"
  }
}
```

### 6. Reflector Agent (`tool_agent.py`)
**負責**: 上下文驗證和補充查詢生成

#### 反思邏輯
- **上下文充足性檢查**: 評估收集的信息是否足夠
- **證據品質評估**: 分析證據的可靠性和相關性
- **差距識別**: 找出信息缺失的領域
- **補充建議**: 生成額外的查詢建議

## 📊 數據結構

### QueryState
完整的查詢執行狀態追蹤：

```python
class QueryState(BaseModel):
    query_id: str
    original_query: str
    query_type: QueryType
    current_plan: List[PlanStep]
    executed_steps: List[str]
    collected_evidence: List[Evidence]
    intermediate_results: Dict[str, Any]
    context: Dict[str, Any]
    final_answer: Optional[str]
    confidence_score: float
    needs_clarification: bool
    clarification_questions: List[str]
```

### Evidence
證據對象，確保可追溯性：

```python
class Evidence(BaseModel):
    evidence_id: str
    source_type: str  # neo4j, pgvector, vlm
    content: str
    confidence: float
    metadata: Dict[str, Any]
    source_document: Optional[str]
    page_number: Optional[int]
```

## 🔄 執行流程

### 標準查詢流程
1. **查詢接收**: 用戶提交查詢
2. **計劃生成**: Planner 分析並生成執行計劃
3. **工具執行**: Tool Agent 按步驟執行檢索
4. **推理增強**: Reasoning Agent 處理複雜查詢
5. **上下文反思**: Reflector 評估信息完整性
6. **答案生成**: LLM 基於證據生成最終答案

### 異常處理流程
- **澄清請求**: 當信息不足時生成補充問題
- **降級策略**: 切換到簡化檢索模式
- **錯誤恢復**: 記錄錯誤並繼續執行

## 🎯 性能指標

### 準確率指標
- **查詢分類準確率**: >85%
- **檢索召回率**: >80%
- **答案相關性**: >75%

### 性能指標
- **簡單查詢響應時間**: <5秒
- **複雜查詢響應時間**: <15秒
- **並發處理能力**: 10+ 並發查詢

### 品質指標
- **證據覆蓋率**: 每個答案至少1個證據
- **信心評分範圍**: 0.0-1.0 (量化評估)
- **錯誤率**: <5%

## 🔌 擴展機制

### 添加新工具
```python
# 1. 在 ToolType 枚舉中添加新類型
NEW_TOOL = "new_tool"

# 2. 在 ToolAgent 中實現執行邏輯
async def _execute_new_tool(self, parameters, query_state):
    # 實現工具邏輯
    pass

# 3. 註冊到工具映射
self.tool_registry[ToolType.NEW_TOOL] = self._execute_new_tool
```

### 添加新推理模式
```python
# 在 ReasoningAgent 中添加新方法
async def _new_reasoning_mode(self, query, context):
    # 實現新的推理邏輯
    pass
```

## 🧪 測試策略

### 單元測試
- 各組件獨立功能測試
- Mock 外部依賴 (Neo4j, Supabase, LLM)

### 集成測試
- 端到端查詢流程測試
- 多代理協作測試

### 性能測試
- 負載測試和壓力測試
- 記憶體和CPU使用監控

## 🚀 使用示例

### 基本查詢
```python
from grag.agents import AgenticRAGAgent

agent = AgenticRAGAgent()
result = await agent.query("What are the sales figures for Q4?")

print(f"Answer: {result['final_answer']}")
print(f"Confidence: {result['confidence_score']}")
print(f"Evidence count: {result['evidence_count']}")
```

### 自定義配置
```python
from grag.agents import AgenticRAGAgent
from langchain_openai import ChatOpenAI

# 自定義LLM
llm = ChatOpenAI(model="gpt-4", temperature=0.1)
agent = AgenticRAGAgent(llm=llm)

result = await agent.query("Analyze the relationship between revenue and costs")
```

## 🔍 監控和調試

### 日誌記錄
- 每個代理操作的詳細日誌
- 性能指標追蹤
- 錯誤和異常記錄

### 狀態檢查
```python
status = await agent.get_system_status()
print(f"System operational: {status['status']}")
print(f"Available tools: {status['tools_available']}")
```

### 查詢追蹤
每個查詢包含完整的執行追蹤：
- 計劃生成過程
- 每個工具的執行結果
- 推理過程
- 最終答案生成依據

---

*文檔版本: 1.0*
*最後更新: 2025-12-02*
