# 🔗 GraphRAG + LLM + VLM 專案 (GRAG)

<div align="center">

![GRAG Logo](https://img.shields.io/badge/GRAG-Agentic_RAG-blue?style=for-the-badge)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-brightgreen.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

一個整合**知識圖譜**、**視覺語言模型 (VLM/Qwen2VL)** 和**大語言模型 (LLM)** 的高階 Agentic RAG 系統。

支援多模態查詢、自主推理和動態知識圖譜，實現 Agent 自助規劃、跨模態檢索和事實檢查。

[🚀 快速開始](#快速安裝) • [📖 使用說明](#使用說明) • [🏗️ 架構說明](#架構說明) • [🔧 故障排除](#故障排除)

</div>

---

## 🎯 專案目標

建立一個**企業級的智能問答系統**，能夠：

- 🤖 **Agentic RAG**: 自助規劃和推理能力
- 🎨 **多模態理解**: 處理文本、圖片、圖表、文檔
- 🧠 **知識圖譜**: 實體關係圖和動態知識連接
- 🔍 **混合檢索**: 向量搜索 + 圖形查詢 + VLM分析
- 🛡️ **事實檢查**: 確保回答的準確性和可靠性

## 🏗️ 技術架構

### 架構總覽
```
                   ┌──────────────────────────────────┐
                   │           Documents              │
                   │   (PDF / Image / Report / OCR)   │
                   └──────────────────────────────────┘
                                   │
              ┌────────────────────┴────────────────────┐
              │                                         │
              ▼                                         ▼
  (A1) VLM Parsing                            (A2) Text Chunking
    Qwen2VL / OCR / Chart Parser                   LlamaIndex
              │                                         │
              ▼                                         ▼
      ┌──────────────────┐                    ┌──────────────────┐
      │   vlm_regions    │                    │  text_chunks     │
      │ (bbox, caption)  │                    │ (chunks, meta)   │
      └──────────────────┘                    └──────────────────┘
              │                                         │
              ▼                                         ▼
        (A3) Embedding (Unified Multimodal Embeddings: text + vision)
              │                                         │
              ▼                                         ▼
        ┌──────────────────────────────────────────────────────┐
        │                 Supabase pgvector (vectors)          │
        │ text / visual / OCR embeddings + metadata            │
        └──────────────────────────────────────────────────────┘
              │                                         │
              ▼                                         ▼
 (A4) Create VisualFact nodes                    (A5) Create Entity/Event nodes
              │                                         │
              └───────────────► Neo4j Knowledge Graph ◄─┘
                                 (GraphRAG DB)
```

### 模組結構
```
grag/
├── core/               # 🔧 核心服務
│   ├── config.py       # 環境配置管理
│   ├── database_services.py  # 資料庫服務 (Neo4j + Supabase)
│   ├── neo4j_schemas.py      # Neo4j 數據模式
│   └── pgvector_schemas.py   # Supabase 向量模式
├── agents/             # 🤖 Agentic RAG 邏輯
│   ├── planner.py      # 查詢規劃
│   ├── retrieval.py    # 多源檢索
│   └── reasoning.py    # 推理引擎
├── ingestion/          # 📥 數據引入
│   ├── langchain_loader.py     # LangChain 文件載入器
│   ├── vision/         # 📸 多模態處理
│   └── indexing/       # 📚 索引和向量化
├── retrieval/          # 🔍 檢索引擎
│   ├── hybrid_search.py         # 混合搜索 (向量+圖譜)
│   └── query_engine.py          # 查詢引擎
├── api/                # 🌐 後端 API (FastAPI)
├── frontend/           # 💻 前端介面 (Streamlit)
├── project/            # 📝 專案管理
├── tests/              # 🧪 測試套件
└── database/           # 🗃️ 資料庫配置
    ├── neo4j/          # Neo4j Docker配置
    ├── supabase/       # Supabase建表腳本
    └── docs/           # 資料庫架構文檔
```

## 🚀 快速安裝

### 環境要求
- **Python**: ≥ 3.10
- **Node.js**: ≥ 16 (前端開發選用)
- **Docker**: 用於Neo4j資料庫
- **Supabase**: 向量資料庫 (雲端)

### 安裝步驟

#### 1. 複製專案
```bash
git clone <repository-url>
cd grag
```

#### 2. 環境設定
```bash
# 複製環境模板
cp .env.example .env

# 編輯環境變數
nano .env
```

#### 3. 安裝依賴
```bash
# 使用 uv (推薦 - 更快)
uv sync

# 或使用 pip
pip install -r requirements.txt
```

#### 4. 啟動資料庫
```bash
# Neo4j (Docker)
uv run database/neo4j/docker/start-neo4j-manual.sh

# 或使用 docker-compose
cd database/neo4j/docker
docker-compose up -d neo4j
```

#### 5. 初始化Supabase
1. 前往 [Supabase Dashboard](https://supabase.com)
2. 建立新專案
3. 執行建表腳本：
   ```bash
   # 在Supabase SQL Editor中執行
   cat database/supabase/supabase-setup.sql
   ```

#### 6. 設定環境變數
編輯 `.env` 文件：
```bash
# Neo4j
NEO4J_URI=neo4j://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key

# 可選: VLM配置
OPENAI_API_KEY=sk-your-openai-key
QWEN2VL_BASE_URL=https://api.qwen2vl.com
```

#### 7. 啟動應用程式
```bash
# 啟動前端介面
uv run streamlit run grag/frontend/app.py --server.port 8501

# 或啟動後端API
uv run fastapi run grag/api/main.py
```

## 📖 使用說明

### 🎨 Web介面 (Streamlit)

1. **啟動介面**: http://localhost:8501
2. **上傳文檔**: 支援 PDF、Word (.docx)、Markdown (.md)、純文字 (.txt)
3. **策略選擇**:
   - **自動判斷**: 系統根據文件類型選擇最佳處理策略
   - **強制開啟VLM**: 對所有文件使用多層VLM處理 (會嘗試降級)
   - **強制關閉**: 跳過VLM，只使用基本文字處理
4. **查看結果**: 包含處理時間、統計數據和詳細軌跡

### 🔧 處理器總覽

| 文件類型 | 處理器 | 特點 |
|---------|--------|------|
| `.pdf` | VLM → MinerU → OCR 降級 | 完整圖像分析 + 結構化解析 |
| `.docx` | VLM → 結構化文字處理 | VLM可用時智慧處理，不可用時安全降級 |
| `.md` | 直接文字處理 | Markdown語義分塊 |
| `.txt` | 直接文字處理 | 標準句子分割 |
| 影像 | VLM處理鏈 | 多層降級策略 |

### 🧪 測試範例

```python
from grag.ingestion.indexing.ingestion_service import IngestionService

# 初始化服務
service = IngestionService()

# 處理文檔
result = await service.ingest_document_enhanced(
    file_path="path/to/document.pdf",
    force_vlm=None  # None=自動判斷, True=VLM優先, False=文字優先
)

# 查看結果
print(f"處理成功: {result['success']}")
print(f"生成分塊: {result['metadata']['chunks_created']}")
print(f"處理時間: {result['processing_time']}秒")

# 查看使用模組軌跡
trace = result['processing_trace']
for step in trace['processing_chain']:
    print(f"{step['stage']}: {step['module']}")
```

### 🗃️ 資料庫查詢

#### Neo4j (圖形檢索)
```cypher
// 查詢實體及其關係
MATCH (e:Entity)-[r]->(other)
WHERE e.name CONTAINS "關鍵詞"
RETURN e, r, other LIMIT 10;
```

#### Supabase (向量相似性)
```sql
-- 相似性搜索 (使用pgvector)
SELECT content, 1 - (embedding <=> '[384維查詢向量]') as similarity
FROM vectors
ORDER BY similarity DESC
LIMIT 10;
```

## 🔧 故障排除

### 常見問題

#### ❗ Neo4j連線失敗
```bash
# 檢查Neo4j狀態
docker ps | grep neo4j

# 重啟Neo4j
cd database/neo4j/docker
./start-neo4j-manual.sh
```

#### ❗ Supabase權限錯誤
```bash
# 檢查並執行權限腳本
# 在Supabase SQL Editor中執行:
cat database/supabase/supabase-setup.sql
```

#### ❗ VLM服務不可用
```bash
# VLM服務失敗是正常的行為 - 系統會自動降級
# 檢查.env中是否設定了有效的API金鑰
echo $OPENAI_API_KEY
```

#### ❗ 記憶體不足
```bash
# 增加Docker記憶體限制
docker system prune  # 清理Docker
```

### 日誌檢視
```bash
# 查看應用程式日誌
uv run streamlit run grag/frontend/app.py --logger.level=debug

# 查看資料庫日誌
docker logs neo4j-grag
```

## 🔬 開發與擴充

### 添加新處理器

```python
# grag/ingestion/vision/new_processor.py
from .vlm_schemas import VLMOutput

class NewProcessor:
    def process_document(self, file_path, file_id, area_id) -> VLMOutput:
        # 實作新處理邏輯
        pass
```

### 自訂嵌入模型

```python
# grag/ingestion/indexing/providers/embedding_providers.py
class CustomEmbeddingProvider(BaseEmbeddingProvider):
    # 實作新的嵌入提供者
    pass
```

## 📊 效能指標

### 處理速度 (測試環境)
- **PDF (多圖表)**: ~3-8秒
- **Word文檔**: ~1-3秒
- **Markdown**: ~0.5-1秒
- **純文字**: ~0.3-0.8秒

### 品質指標
- **實體辨識正確率**: >85%
- **分塊語義完整性**: >90%
- **向量搜尋準確率**: >88%

## 🤝 貢獻指南

1. Fork 本專案
2. 建立功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 建立 Pull Request

## 📄 授權條款

此專案採用 MIT 授權條款 - 詳見 [LICENSE](LICENSE) 文件

## 🙏 鳴謝

- **Neo4j**: 圖形資料庫支援
- **Supabase**: 向量資料庫和API俱樂部
- **LangChain**: 文件處理框架
- **LlamaIndex**: RAG和索引框架
- **Sentence Transformers**: 嵌入模型

## 📞 聯絡方式

如果您有任何問題或建議，請：

- 建立 [GitHub Issue](https://github.com/your-repo/issues)
- 發送郵件至: grag-support@example.com

---

<div align="center">

**享受您的 Agentic RAG 智慧問答系統！** 🚀✨

*打造於 Neo4j + LangChain + Streamlit + Supabase pgvector*

</div>
