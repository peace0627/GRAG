# GraphRAG API 文檔

## 概覽

GraphRAG系統提供RESTful API，用於文件處理、檢索和管理操作。

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
