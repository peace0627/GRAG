"""
FastAPI Application
GraphRAG系統的REST API服務
提供文件上傳、檢索、删除和管理功能
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from typing import List, Optional, Dict, Any
from pathlib import Path
import tempfile
import shutil
import json
from datetime import datetime

# 導入核心服務
from grag.core.health_service import HealthService
from grag.core.database_services import DatabaseManager
from grag.ingestion.indexing.ingestion_service import IngestionService

# 創建FastAPI應用
app = FastAPI(
    title="GraphRAG API",
    description="圖形化檢索增強生成系統的REST API",
    version="1.0.0"
)

# CORS設置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化核心服務
health_service = HealthService()

def get_database_manager():
    """獲取資料庫管理器實例"""
    from grag.core.config import settings
    return DatabaseManager(
        neo4j_uri=settings.neo4j_uri,
        neo4j_user=settings.neo4j_user,
        neo4j_password=settings.neo4j_password,
        supabase_url=settings.supabase_url,
        supabase_key=settings.supabase_key
    )

@app.get("/")
async def root():
    """API根端點"""
    return {"message": "GraphRAG API", "version": "1.0.0", "status": "running"}

@app.get("/health")
async def health_check():
    """系統健康檢查"""
    try:
        status = health_service.get_system_status()
        return {
            "status": "healthy",
            "timestamp": status["timestamp"],
            "overall_health": status["overall_health"],
            "services": status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@app.post("/upload/single")
async def upload_single_file(
    file: UploadFile = File(...),
    force_vlm: Optional[bool] = None
):
    """上傳單個文件進行處理"""
    try:
        # 驗證文件類型
        allowed_extensions = ['.pdf', '.docx', '.txt', '.md']
        file_ext = Path(file.filename).suffix.lower()

        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
            )

        # 創建臨時文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            shutil.copyfileobj(file.file, temp_file)
            temp_path = Path(temp_file.name)

        # 初始化處理服務
        ingestion_service = IngestionService()

        # 進行文件處理
        result = await ingestion_service.ingest_document_enhanced(
            file_path=temp_path,
            force_vlm=force_vlm
        )

        # 清理臨時文件
        temp_path.unlink(missing_ok=True)

        if result.get("success"):
            return {
                "success": True,
                "message": f"File '{file.filename}' processed successfully",
                "data": result
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Processing failed")
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.post("/upload/batch")
async def upload_batch_files(
    files: List[UploadFile] = File(...),
    force_vlm: Optional[bool] = None
):
    """批量上傳多個文件進行處理"""
    if len(files) > 10:  # 限制批次大小
        raise HTTPException(status_code=400, detail="Maximum 10 files per batch")

    results = []
    total_success = 0
    total_failed = 0

    try:
        ingestion_service = IngestionService()

        for file in files:
            try:
                # 驗證文件類型
                file_ext = Path(file.filename).suffix.lower()
                allowed_extensions = ['.pdf', '.docx', '.txt', '.md']

                if file_ext not in allowed_extensions:
                    results.append({
                        "filename": file.filename,
                        "success": False,
                        "error": f"Unsupported file type"
                    })
                    total_failed += 1
                    continue

                # 創建臨時文件
                with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
                    shutil.copyfileobj(file.file, temp_file)
                    temp_path = Path(temp_file.name)

                # 處理文件
                result = await ingestion_service.ingest_document_enhanced(
                    file_path=temp_path,
                    force_vlm=force_vlm
                )

                # 清理臨時文件
                temp_path.unlink(missing_ok=True)

                if result.get("success"):
                    results.append({
                        "filename": file.filename,
                        "success": True,
                        "data": result.get("metadata", {})
                    })
                    total_success += 1
                else:
                    results.append({
                        "filename": file.filename,
                        "success": False,
                        "error": result.get("error", "Processing failed")
                    })
                    total_failed += 1

            except Exception as e:
                results.append({
                    "filename": file.filename,
                    "success": False,
                    "error": str(e)
                })
                total_failed += 1

        return {
            "success": True,
            "message": f"Batch processing completed. Success: {total_success}, Failed: {total_failed}",
            "results": results,
            "statistics": {
                "total_files": len(files),
                "successful": total_success,
                "failed": total_failed
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch upload failed: {str(e)}")

@app.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """删除指定的文檔及其所有關聯數據"""
    try:
        from uuid import UUID
        doc_uuid = UUID(document_id)

        db_manager = get_database_manager()
        await db_manager.initialize()

        result = await db_manager.delete_document_cascade(doc_uuid)
        await db_manager.close()

        if result:
            return {
                "success": True,
                "message": f"Document {document_id} and all associated data deleted successfully"
            }
        else:
            raise HTTPException(status_code=404, detail="Document not found or deletion failed")

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deletion failed: {str(e)}")

@app.delete("/documents/batch")
async def delete_batch_documents(document_ids: List[str]):
    """批量删除多個文檔"""
    try:
        from uuid import UUID

        # 格式驗證
        doc_uuids = []
        for doc_id in document_ids:
            try:
                doc_uuids.append(UUID(doc_id))
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid document ID format: {doc_id}"
                )

        db_manager = get_database_manager()
        await db_manager.initialize()

        results = await db_manager.delete_documents_batch(doc_uuids)
        await db_manager.close()

        return {
            "success": True,
            "message": f"Batch deletion completed. Success: {results['successful_deletions']}, Failed: {len(results['failed_deletions'])}",
            "details": results
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch deletion failed: {str(e)}")

@app.get("/documents")
async def list_documents(limit: int = 50, offset: int = 0):
    """獲取已處理的文檔列表"""
    try:
        db_manager = get_database_manager()
        # 這裡可以實現索引查詢邏輯
        # 目前返回空的，因為需要修改DatabaseManager

        # 簡單的模擬回應
        return {
            "success": True,
            "documents": [],
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": 0
            },
            "message": "Document listing not yet implemented. Use database tools for now."
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")

@app.post("/search")
async def search_documents(query: str, limit: int = 10):
    """根據查詢搜索相關文檔"""
    try:
        # 這裡將實現RAG檢索邏輯
        # 結合Neo4j圖形查詢和Supabase向量檢索

        return {
            "success": True,
            "query": query,
            "results": [],
            "message": "Advanced search not yet implemented. Will integrate LangGraph + pgvector.",
            "metadata": {
                "limit": limit,
                "total_results": 0
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.get("/statistics")
async def get_statistics():
    """獲取系統統計信息"""
    try:
        # 這裡可以實現統計查詢邏輯
        # 查詢Neo4j和Supabase的數據量等

        return {
            "success": True,
            "message": "Statistics not yet fully implemented. Use database tools for detailed stats.",
            "placeholder_data": {
                "total_documents": 0,
                "total_chunks": 0,
                "total_vectors": 0
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")

def main():
    """啟動FastAPI服務"""
    import uvicorn
    print("🚀 GraphRAG API服務啟動中...")
    print("📊 服務信息:")
    print("  - API地址: http://localhost:8000")
    print("  - 文檔地址: http://localhost:8000/docs")
    print()
    uvicorn.run("grag.api.app:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    main()
