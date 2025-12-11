# GraphRAG API 文檔

## 概覽

GraphRAG系統提供完整的RESTful API，用於Agentic RAG查詢、文件處理、檢索和管理操作。

**🎉 最新更新**: 已實現完整的Agentic RAG查詢功能，所有API端點測試通過。

## 基礎信息

- **基準URL**: `http://localhost:8000`
- **驗證**: 目前無驗證要求
- **格式**: JSON
- **編碼**: UTF-8

## 核心端點

### 健康檢查

#### GET /health

檢查系統各組件狀態。

**響應示例**:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-18T21:18:45.123456",
  "overall_health": "excellent",
  "services": {
    "langchain": true,
    "database": {
      "neo4j": true,
      "supabase": true
    },
    "embedding_service": true
  }
}
```

### 文件上傳

#### POST /upload/single

上傳單個文件進行處理。

**參數**:
- `file` (File): 上傳的文件
- `force_vlm` (Optional[bool]): 強制使用VLM處理

**支援的文件類型**: PDF, DOCX, TXT, MD

**響應示例**:
```json
{
  "success": true,
  "message": "File 'document.pdf' processed successfully",
  "data": {
    "document_id": "uuid-here",
    "chunks_created": 5,
    "embeddings_created": 5
  }
}
```

#### POST /upload/batch

批量上傳多個文件（最多10個）。

**參數**:
- `files` (List[File]): 上傳的文件列表
- `force_vlm` (Optional[bool]): 強制使用VLM處理

**響應示例**:
```json
{
  "success": true,
  "message": "Batch processing completed. Success: 3, Failed: 0",
  "results": [
    {
      "filename": "doc1.pdf",
      "success": true,
      "data": { "chunks_created": 5 }
    }
  ],
  "statistics": {
    "total_files": 3,
    "successful": 3,
    "failed": 0
  }
}
```

### 文件管理

#### DELETE /documents/{document_id}

删除指定的文檔及其所有關聯數據。

**參數**:
- `document_id` (path): 文檔UUID

**響應示例**:
```json
{
  "success": true,
  "message": "Document deleted successfully"
}
```

#### DELETE /documents/batch

批量删除多個文檔。

**請求體**:
```json
["uuid1", "uuid2", "uuid3"]
```

**響應示例**:
```json
{
  "success": true,
  "message": "Batch deletion completed. Success: 3, Failed: 0",
  "details": {
    "successful_deletions": 3,
    "failed_deletions": [],
    "total_requested": 3
  }
}
```

### 🤖 Agentic RAG 查詢 (核心功能)

#### POST /query

執行完整的Agentic RAG智能查詢，包含規劃、檢索、推理和最終回答生成。

**請求體**:
```json
{
  "query": "圖表顯示哪個月銷售最低？",
  "context": null,
  "max_evidence": 10,
  "include_planning": false
}
```

**參數**:
- `query` (string): 用戶查詢，必填
- `context` (object, 可選): 額外上下文信息
- `max_evidence` (int, 可選): 返回的最大證據數量，默認10
- `include_planning` (bool, 可選): 是否包含規劃信息，默認false

**響應示例**:
```json
{
  "query_id": "visual_-1182087",
  "original_query": "圖表顯示哪個月銷售最低？",
  "query_type": "visual",
  "final_answer": "根據提供的數據，2月份的銷售額最低。",
  "confidence_score": 0.85,
  "evidence_count": 3,
  "execution_time": 0.504,
  "needs_clarification": false,
  "clarification_questions": [],
  "evidence": [
    {
      "evidence_id": "ev_123",
      "source_type": "neo4j",
      "content": "銷售數據顯示2月份銷售額為150萬",
      "confidence": 0.9,
      "metadata": {}
    }
  ],
  "reflection": {
    "context_sufficient": true,
    "gaps_identified": [],
    "confidence_assessment": {
      "overall": 0.85
    }
  },
  "success": true
}
```

#### POST /query/simple

執行簡化的RAG查詢，使用SimpleRAGAgent快速回答簡單問題。

**請求體**:
```json
{
  "query": "What is GraphRAG?"
}
```

**響應示例**:
```json
{
  "query_id": "simple_123456",
  "original_query": "What is GraphRAG?",
  "query_type": "simple",
  "final_answer": "GraphRAG is a system that combines graph databases with retrieval-augmented generation...",
  "confidence_score": 0.5,
  "evidence_count": 2,
  "execution_time": 0.234,
  "success": true
}
```

#### GET /system/status

獲取完整的系統狀態，包括Agent狀態和所有服務健康信息。

**響應示例**:
```json
{
  "status": "operational",
  "timestamp": "2025-12-11T18:02:45.194545",
  "overall_health": "excellent",
  "services": {
    "langchain": true,
    "vlm_configured": true,
    "database": {
      "neo4j": true,
      "supabase": true
    },
    "embedding_service": true
  },
  "agents": {
    "status": "operational",
    "agents": {
      "planner": "ready",
      "retrieval": "ready",
      "reasoning": "ready",
      "tool_agent": "ready",
      "reflector": "ready"
    },
    "tools_available": 5,
    "database_status": {
      "neo4j": "connected",
      "supabase": "connected"
    },
    "llm_model": "gpt-4"
  }
}
```

### 系統信息

#### GET /statistics

獲取系統統計信息。

**響應示例**:
```json
{
  "success": true,
  "message": "Statistics not yet fully implemented",
  "placeholder_data": {
    "total_documents": 0,
    "total_chunks": 0,
    "total_vectors": 0
  }
}
```

## 錯誤處理

所有API都返回統一的錯誤格式：

```json
{
  "detail": "Error description"
}
```

常見HTTP狀態碼:
- `200`: 成功
- `400`: 請求參數錯誤
- `404`: 資源不存在
- `500`: 服務器內部錯誤

## 自動文檔

訪問 `http://localhost:8000/docs` 查看完整的互動式API文檔。

## 使用示例

### Python示例

```python
import requests

# 健康檢查
response = requests.get("http://localhost:8000/health")
print(response.json())

# 文件上傳
with open("document.pdf", "rb") as f:
    files = {"file": f}
    response = requests.post("http://localhost:8000/upload/single", files=files)
    print(response.json())
