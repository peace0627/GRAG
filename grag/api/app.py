"""
FastAPI Application
GraphRAG系統的REST API服務
提供文件上傳、檢索、删除和管理功能
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from typing import List, Optional, Dict, Any
from pathlib import Path
import tempfile
import shutil
from datetime import datetime
import uuid
import time
from enum import Enum
from dataclasses import dataclass
import threading
import logging

# 配置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 非同步任務管理器
class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class ProcessingTask:
    """文件處理任務"""
    task_id: str
    filename: str
    file_path: Path
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0
    message: str = ""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    estimated_time: Optional[int] = None  # 估計剩餘時間（秒）

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "filename": self.filename,
            "status": self.status.value,
            "progress": self.progress,
            "message": self.message,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "result": self.result,
            "error": self.error,
            "estimated_time": self.estimated_time,
            "elapsed_time": (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        }

class TaskManager:
    """非同步任務管理器"""

    def __init__(self):
        self.tasks: Dict[str, ProcessingTask] = {}
        self.max_concurrent_tasks = 2
        self.active_tasks = 0
        self.task_timeout = 600  # 10分鐘超時
        self.cleanup_interval = 3600  # 1小時清理一次
        self._lock = threading.Lock()

        # 啟動清理線程
        self._cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
        self._cleanup_thread.start()

    def create_task(self, filename: str, file_path: Path) -> str:
        """創建新任務"""
        task_id = str(uuid.uuid4())
        task = ProcessingTask(
            task_id=task_id,
            filename=filename,
            file_path=file_path,
            status=TaskStatus.PENDING,
            message="任務已創建，等待處理"
        )

        with self._lock:
            self.tasks[task_id] = task

        return task_id

    def get_task(self, task_id: str) -> Optional[ProcessingTask]:
        """獲取任務狀態"""
        with self._lock:
            return self.tasks.get(task_id)

    def update_task_progress(self, task_id: str, progress: float, message: str):
        """更新任務進度"""
        with self._lock:
            task = self.tasks.get(task_id)
            if task:
                task.progress = progress
                task.message = message

    def start_task(self, task_id: str):
        """開始任務處理"""
        with self._lock:
            task = self.tasks.get(task_id)
            if task and task.status == TaskStatus.PENDING:
                task.status = TaskStatus.PROCESSING
                task.start_time = datetime.now()
                task.message = "開始處理文件..."
                self.active_tasks += 1

    def complete_task(self, task_id: str, result: Dict[str, Any]):
        """完成任務"""
        with self._lock:
            task = self.tasks.get(task_id)
            if task:
                task.status = TaskStatus.COMPLETED
                task.end_time = datetime.now()
                task.result = result
                task.progress = 100.0
                task.message = "處理完成"
                self.active_tasks -= 1

    def fail_task(self, task_id: str, error: str):
        """任務失敗"""
        with self._lock:
            task = self.tasks.get(task_id)
            if task:
                task.status = TaskStatus.FAILED
                task.end_time = datetime.now()
                task.error = error
                task.message = f"處理失敗: {error[:100]}"
                self.active_tasks -= 1

                # 清理臨時文件
                try:
                    if task.file_path.exists():
                        task.file_path.unlink(missing_ok=True)
                except Exception as e:
                    logger.warning(f"Failed to cleanup file for failed task {task_id}: {e}")

    def cancel_task(self, task_id: str):
        """取消任務"""
        with self._lock:
            task = self.tasks.get(task_id)
            if task and task.status in [TaskStatus.PENDING, TaskStatus.PROCESSING]:
                task.status = TaskStatus.CANCELLED
                task.end_time = datetime.now()
                task.message = "任務已取消"
                if task.status == TaskStatus.PROCESSING:
                    self.active_tasks -= 1

                # 清理臨時文件
                try:
                    if task.file_path.exists():
                        task.file_path.unlink(missing_ok=True)
                except Exception as e:
                    logger.warning(f"Failed to cleanup file for cancelled task {task_id}: {e}")

    def can_start_task(self) -> bool:
        """檢查是否可以開始新任務"""
        return self.active_tasks < self.max_concurrent_tasks

    def list_tasks(self, limit: int = 50) -> List[Dict[str, Any]]:
        """列出所有任務"""
        with self._lock:
            tasks = list(self.tasks.values())
            # 按開始時間降序排序
            tasks.sort(key=lambda x: x.start_time or datetime.min, reverse=True)
            return [task.to_dict() for task in tasks[:limit]]

    def _cleanup_worker(self):
        """清理過期任務的worker線程"""
        while True:
            try:
                current_time = datetime.now()
                with self._lock:
                    to_remove = []
                    for task_id, task in self.tasks.items():
                        # 清理完成/失敗的舊任務（保留24小時）
                        if task.end_time and (current_time - task.end_time).total_seconds() > 86400:
                            to_remove.append(task_id)
                        # 清理超時的處理中任務
                        elif (task.status == TaskStatus.PROCESSING and
                              task.start_time and
                              (current_time - task.start_time).total_seconds() > self.task_timeout):
                            self.fail_task(task_id, "處理超時")

                    for task_id in to_remove:
                        del self.tasks[task_id]

                time.sleep(self.cleanup_interval)
            except Exception as e:
                logger.error(f"Task cleanup error: {e}")
                time.sleep(60)  # 錯誤時等待1分鐘再試

# 全域任務管理器實例
task_manager = TaskManager()

# 導入核心服務
from grag.core.health_service import HealthService
from grag.core.database_services import DatabaseManager
from grag.ingestion.indexing.ingestion_service import IngestionService

# 導入Agent和API Schemas
from grag.agents.rag_agent import AgenticRAGAgent
from .schemas import (
    QueryRequest, QueryResponse, SystemStatusResponse
)

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

# 全域Agent實例 (懶加載)
_rag_agent: Optional[AgenticRAGAgent] = None

async def get_rag_agent() -> AgenticRAGAgent:
    """獲取或創建RAG Agent實例"""
    global _rag_agent
    if _rag_agent is None:
        try:
            _rag_agent = AgenticRAGAgent()
            # 測試Agent初始化
            await _rag_agent.get_system_status()
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initialize RAG Agent: {str(e)}"
            )
    return _rag_agent

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
            # Extract quality information for frontend display
            strategy = result.get("strategy_used", {})
            statistics = result.get("statistics", {})

            # Determine processing quality based on content assessment
            processing_quality = "高品質"
            content_quality_score = 0.8

            if statistics.get("total_characters", 0) < 100:
                processing_quality = "低品質"
                content_quality_score = 0.3
            elif statistics.get("total_characters", 0) < 500:
                processing_quality = "中品質"
                content_quality_score = 0.6

            # Determine processing method based on processing_layer
            processing_layer = strategy.get("processing_layer", "").lower()
            if processing_layer == "pymupdf":
                processing_method = "PyMuPDF"
                vlm_provider = "PyMuPDF"  # For PyMuPDF, set provider to PyMuPDF
            elif processing_layer == "vlm":
                processing_method = "VLM"
                vlm_provider = strategy.get("vlm_provider", "unknown")
            elif processing_layer in ["mineru", "ocr"]:
                processing_method = processing_layer.upper()
                vlm_provider = processing_layer.upper()
            elif processing_layer == "fallback_text_processing":
                processing_method = "文字處理"
                vlm_provider = "TextFallback"
            else:
                processing_method = "VLM" if strategy.get("vlm_used") else "文字處理"
                vlm_provider = strategy.get("vlm_provider", "unknown")

            return {
                "success": True,
                "message": f"File '{file.filename}' processed successfully",
                "document_id": result.get("file_id"),
                "processing_time": result.get("processing_time"),
                "processing_method": processing_method,
                "processing_quality": processing_quality,
                "content_quality_score": content_quality_score,
                "vlm_provider": vlm_provider,  # Use the processed vlm_provider
                "vlm_success": strategy.get("vlm_success"),
                "total_characters": statistics.get("total_characters", 0),
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
                        "error": "Unsupported file type"
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

@app.post("/upload/async")
async def upload_file_async(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    force_vlm: Optional[bool] = None
):
    """非同步上傳文件進行處理"""
    try:
        # 驗證文件類型
        allowed_extensions = ['.pdf', '.docx', '.txt', '.md']
        file_ext = Path(file.filename).suffix.lower()

        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
            )

        # 檢查文件大小 (限制為50MB)
        file_content = await file.read()
        file_size_mb = len(file_content) / (1024 * 1024)

        if file_size_mb > 50:
            raise HTTPException(
                status_code=400,
                detail=f"File too large: {file_size_mb:.1f}MB. Maximum allowed: 50MB"
            )

        # 檢查是否可以開始新任務
        if not task_manager.can_start_task():
            raise HTTPException(
                status_code=429,
                detail="Too many concurrent tasks. Please wait for current tasks to complete."
            )

        # 創建臨時文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            temp_file.write(file_content)
            temp_path = Path(temp_file.name)

        # 創建非同步任務
        task_id = task_manager.create_task(file.filename, temp_path)

        # 添加後台任務
        background_tasks.add_task(process_file_async, task_id, temp_path, force_vlm)

        return {
            "success": True,
            "message": f"File '{file.filename}' upload accepted for async processing",
            "task_id": task_id,
            "file_size_mb": round(file_size_mb, 2),
            "estimated_wait_time": "Processing will begin shortly"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Async upload failed: {str(e)}")

@app.get("/upload/status/{task_id}")
async def get_upload_status(task_id: str):
    """獲取上傳任務的狀態"""
    try:
        task = task_manager.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        return task.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get task status: {str(e)}")

@app.delete("/upload/cancel/{task_id}")
async def cancel_upload_task(task_id: str):
    """取消上傳任務"""
    try:
        task_manager.cancel_task(task_id)
        return {
            "success": True,
            "message": f"Task {task_id} cancelled successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel task: {str(e)}")

@app.get("/upload/tasks")
async def list_upload_tasks(limit: int = 20):
    """列出所有上傳任務"""
    try:
        tasks = task_manager.list_tasks(limit)
        return {
            "success": True,
            "tasks": tasks,
            "total": len(tasks)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list tasks: {str(e)}")

async def process_file_async(task_id: str, file_path: Path, force_vlm: Optional[bool] = None):
    """非同步處理文件的背景任務"""
    try:
        # 開始任務
        task_manager.start_task(task_id)

        # 更新進度：文件驗證完成
        task_manager.update_task_progress(task_id, 5, "文件驗證完成，開始初始化處理服務")

        # 初始化處理服務
        ingestion_service = IngestionService()

        # 更新進度：服務初始化完成
        task_manager.update_task_progress(task_id, 10, "處理服務初始化完成，開始文檔處理")

        # 估計處理時間 (基於文件大小)
        file_size = file_path.stat().st_size
        estimated_time = min(max(file_size / (1024 * 1024) * 30, 30), 300)  # 30秒到5分鐘

        # 更新進度：開始處理
        task_manager.update_task_progress(task_id, 15, f"開始處理文檔，預計需要約{estimated_time:.0f}秒")

        # 進行文件處理
        result = await ingestion_service.ingest_document_enhanced(
            file_path=file_path,
            force_vlm=force_vlm
        )

        # 更新進度：處理完成
        task_manager.update_task_progress(task_id, 95, "文檔處理完成，正在清理資源")

        # 清理臨時文件
        try:
            file_path.unlink(missing_ok=True)
        except Exception as e:
            logger.warning(f"Failed to cleanup temp file {file_path}: {e}")

        # 更新進度：清理完成
        task_manager.update_task_progress(task_id, 99, "資源清理完成")

        if result.get("success"):
            # 完成任務
            result_data = {
                "document_id": result.get("file_id"),
                "processing_time": result.get("processing_time"),
                "processing_method": result.get("strategy_used", {}).get("processing_layer", "unknown"),
                "vlm_provider": result.get("strategy_used", {}).get("vlm_provider", "unknown"),
                "total_characters": result.get("statistics", {}).get("total_characters", 0),
                "chunks_created": result.get("statistics", {}).get("chunks", {}).get("total", 0),
                "entities_extracted": result.get("metadata", {}).get("entities_extracted", 0),
                "relations_extracted": result.get("metadata", {}).get("relations_extracted", 0)
            }
            task_manager.complete_task(task_id, result_data)
            logger.info(f"Async processing completed for task {task_id}")
        else:
            # 任務失敗
            error_msg = result.get("error", "Processing failed")
            task_manager.fail_task(task_id, error_msg)
            logger.error(f"Async processing failed for task {task_id}: {error_msg}")

    except Exception as e:
        # 任務失敗
        error_msg = f"Unexpected error during async processing: {str(e)}"
        task_manager.fail_task(task_id, error_msg)
        logger.error(f"Async processing failed for task {task_id}: {error_msg}")

        # 清理臨時文件
        try:
            if file_path.exists():
                file_path.unlink(missing_ok=True)
        except Exception as cleanup_error:
            logger.warning(f"Failed to cleanup temp file {file_path} after error: {cleanup_error}")

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
        from .schemas import DocumentInfo, DocumentListResponse

        db_manager = get_database_manager()
        await db_manager.initialize()

        # Query documents from Neo4j with enhanced processing information
        raw_documents = await db_manager.list_documents(limit=limit, offset=offset)
        await db_manager.close()

        # Enhance documents with processing method information from database
        enhanced_documents = []
        for doc in raw_documents["documents"]:
            # Read actual processing information from Neo4j Document node
            processing_method = doc.get("processing_method", "未知")
            processing_quality = doc.get("processing_quality", "未知")
            content_quality_score = doc.get("content_quality_score", 0.5)
            vlm_provider = doc.get("vlm_provider", "未知")
            vlm_success = doc.get("vlm_success", False)
            total_characters = doc.get("total_characters", 0)
            processing_layer = doc.get("processing_layer", "未知")

            # Map processing_layer to processing_method for better display
            if processing_layer == "PyMuPDF":
                processing_method = "PyMuPDF"
            elif processing_layer in ["VLM", "MinerU", "OCR"]:
                processing_method = processing_layer
            elif processing_layer == "FALLBACK_TEXT_PROCESSING":
                processing_method = "文字處理"

            # Create enhanced document info with real database values
            doc_info = DocumentInfo(
                document_id=doc["document_id"],
                title=doc["title"],
                source_path=doc["source_path"],
                created_at=doc["created_at"],
                updated_at=doc["updated_at"],
                chunk_count=doc["chunk_count"],
                vector_count=doc["chunk_count"],  # Assume all chunks have vectors
                processing_method=processing_method,
                processing_quality=processing_quality,
                content_quality_score=content_quality_score,
                vlm_provider=vlm_provider,
                vlm_success=vlm_success,
                total_characters=total_characters
            )
            enhanced_documents.append(doc_info)

        response = DocumentListResponse(
            documents=enhanced_documents,
            pagination={
                "limit": limit,
                "offset": offset,
                "total": raw_documents["total"]
            }
        )

        return response

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

@app.post("/query")
async def rag_query(request: QueryRequest) -> QueryResponse:
    """執行Agentic RAG查詢"""
    try:
        # 獲取或初始化Agent
        agent = await get_rag_agent()

        # 執行查詢
        result = await agent.query(
            user_query=request.query,
            context=request.context
        )

        # 限制返回的evidence數量
        max_evidence = request.max_evidence or 10
        if len(result.get("evidence", [])) > max_evidence:
            result["evidence"] = result["evidence"][:max_evidence]

        # 如果不需要planning信息，移除它
        if not request.include_planning:
            result.pop("planning_info", None)

        # 轉換為響應模型
        return QueryResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        # 返回錯誤響應
        return QueryResponse(
            query_id=f"error_{hash(request.query)}",
            original_query=request.query,
            query_type="error",
            final_answer="",
            confidence_score=0.0,
            evidence_count=0,
            execution_time=0.0,
            success=False,
            error=str(e)
        )

@app.get("/system/status")
async def get_system_status() -> SystemStatusResponse:
    """獲取完整的系統狀態，包括Agent狀態"""
    try:
        # 基礎健康檢查
        base_status = health_service.get_system_status()

        # Agent狀態檢查
        agent_status = None
        try:
            agent = await get_rag_agent()
            agent_status = await agent.get_system_status()
        except Exception as e:
            agent_status = {"status": "error", "error": str(e)}

        # 提取services信息
        services_info = {
            "langchain": base_status.get("langchain", False),
            "vlm_configured": base_status.get("vlm_configured", False),
            "database": base_status.get("database", {}),
            "embedding_service": base_status.get("embedding_service", False)
        }

        # 創建響應對象
        response = SystemStatusResponse(
            status="operational" if base_status["overall_health"] in ["excellent", "good"] else "degraded",
            timestamp=base_status["timestamp"],
            overall_health=base_status["overall_health"],
            services=services_info,
            agents=agent_status
        )

        return response

    except Exception as e:
        # 調試信息
        import traceback
        error_details = f"{str(e)}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=f"System status check failed: {error_details}")

@app.post("/query/simple")
async def simple_rag_query(request: QueryRequest) -> QueryResponse:
    """執行簡化的RAG查詢 (SimpleRAGAgent)"""
    try:
        from grag.agents.rag_agent import SimpleRAGAgent

        # 初始化簡化Agent
        agent = SimpleRAGAgent()

        # 執行查詢
        result = await agent.query(request.query)

        # 轉換為響應模型
        return QueryResponse(
            query_id=result["query_id"],
            original_query=request.query,
            query_type="simple",
            final_answer=result["final_answer"],
            confidence_score=0.5,  # 簡化Agent沒有信心評分
            evidence_count=result["evidence_count"],
            execution_time=result["execution_time"],
            success=True
        )

    except Exception as e:
        return QueryResponse(
            query_id=f"error_simple_{hash(request.query)}",
            original_query=request.query,
            query_type="error",
            final_answer="",
            confidence_score=0.0,
            evidence_count=0,
            execution_time=0.0,
            success=False,
            error=str(e)
        )

@app.get("/graph")
async def get_knowledge_graph(limit: int = 100):
    """獲取完整的知識圖譜數據用於前端視覺化"""
    try:
        db_manager = get_database_manager()
        await db_manager.initialize()

        nodes = []
        edges = []

        # 1. 添加Document節點
        documents = await db_manager.list_documents(limit=limit, offset=0)
        for doc in documents["documents"]:
            smart_label = doc["title"]
            if smart_label and len(smart_label) > 50:
                smart_label = smart_label[:47] + "..."

            nodes.append({
                "id": doc["document_id"],
                "label": smart_label or f"Document {doc['document_id'][:8]}",
                "type": "entity",  # Document作為實體顯示
                "properties": {
                    "description": f"上傳時間: {datetime.fromisoformat(doc['created_at'].replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')}",
                    "chunk_count": doc["chunk_count"],
                    "source_path": doc["source_path"],
                    "original_title": doc["title"]
                }
            })

        # 2. 添加Chunk節點和Document-Chunk關係
        async with db_manager.neo4j_session() as session:
            # 查詢所有chunks
            result = await session.run("""
            MATCH (d:Document)-[:HAS_CHUNK]->(c:Chunk)
            RETURN d.document_id as doc_id, c.chunk_id as chunk_id, c.text as text, c.vector_id as vector_id
            LIMIT $limit
            """, limit=limit * 10)  # 每個文檔最多10個chunks

            records = await result.fetch(limit * 10)

            for record in records:
                chunk_id = str(record["chunk_id"])
                chunk_text = record["text"] or ""

                # 生成智能標籤
                if chunk_text and len(chunk_text.strip()) > 10:
                    label_text = chunk_text.strip()[:50]
                    if label_text.lower().startswith(('pdf document', 'document:', 'content:')):
                        words = label_text.split()
                        if len(words) > 3:
                            label_text = ' '.join(words[2:])

                    if len(label_text) > 30:
                        label_text = label_text[:27] + "..."
                else:
                    label_text = f"Chunk {chunk_id[:8]}..."

                # 添加Chunk節點
                nodes.append({
                    "id": chunk_id,
                    "label": label_text,
                    "type": "chunk",
                    "properties": {
                        "content": chunk_text[:200] + "..." if len(chunk_text) > 200 else chunk_text,
                        "vector_id": str(record["vector_id"]) if record["vector_id"] else None,
                        "chunk_id_short": chunk_id[:8]
                    }
                })

                # 添加Document到Chunk的邊
                edges.append({
                    "id": f"edge_{record['doc_id']}_{chunk_id}",
                    "source": str(record["doc_id"]),
                    "target": chunk_id,
                    "label": "contains",
                    "type": "contains"
                })

        # 3. 添加Entity節點和關係
        # 首先收集所有在關係中被引用的Entity ID，確保它們都被包含
        entity_ids_in_relations = set()
        async with db_manager.neo4j_session() as session:
            result = await session.run("""
            MATCH (e:Entity)-[r:MENTIONED_IN]->(c:Chunk)
            RETURN DISTINCT e.entity_id as entity_id
            LIMIT $limit
            """, limit=min(limit * 2, 400))

            records = await result.fetch(min(limit * 2, 400))
            for record in records:
                entity_ids_in_relations.add(str(record["entity_id"]))

        # 查詢所有相關的Entity節點
        entity_ids_list = list(entity_ids_in_relations)
        if entity_ids_list:
            async with db_manager.neo4j_session() as session:
                result = await session.run("""
                MATCH (e:Entity)
                WHERE e.entity_id IN $entity_ids
                RETURN e.entity_id as entity_id, e.name as name, e.type as type
                """, entity_ids=list(entity_ids_in_relations))

                records = await result.fetch(len(entity_ids_list))

                for record in records:
                    entity_id = str(record["entity_id"])
                    entity_name = record["name"]
                    entity_type = record["type"]

                    # 為實體名稱生成簡潔標籤
                    label = entity_name
                    if len(label) > 30:
                        label = label[:27] + "..."

                    nodes.append({
                        "id": entity_id,
                        "label": label,
                        "type": "entity",
                        "properties": {
                            "name": entity_name,
                            "entity_type": entity_type,
                            "description": f"{entity_type}: {entity_name}"
                        }
                    })

        # 4. 添加Entity-Chunk的MENTIONED_IN關係
        async with db_manager.neo4j_session() as session:
            result = await session.run("""
            MATCH (e:Entity)-[r:MENTIONED_IN]->(c:Chunk)
            RETURN e.entity_id as entity_id, c.chunk_id as chunk_id, r.confidence as confidence
            LIMIT $limit
            """, limit=min(limit * 5, 500))  # 每個節點最多5個關係

            records = await result.fetch(min(limit * 5, 500))

            for record in records:
                entity_id = str(record["entity_id"])
                chunk_id = str(record["chunk_id"])

                edges.append({
                    "id": f"mention_{entity_id}_{chunk_id}",
                    "source": entity_id,
                    "target": chunk_id,
                    "label": "mentioned in",
                    "type": "mentioned_in",
                    "properties": {
                        "confidence": float(record["confidence"]) if record["confidence"] else 0.8
                    }
                })

        # 5. 添加Event節點和關係 (如果有的話)
        async with db_manager.neo4j_session() as session:
            result = await session.run("""
            MATCH (ev:Event)
            RETURN ev.event_id as event_id, ev.type as type, ev.description as description
            LIMIT $limit
            """, limit=min(limit // 2, 50))  # 限制Event數量

            records = await result.fetch(min(limit // 2, 50))

            for record in records:
                event_id = str(record["event_id"])
                event_type = record["type"]
                description = record["description"] or ""

                # 生成簡潔標籤
                label = f"{event_type}"
                if len(description) > 20:
                    label += f": {description[:17]}..."

                nodes.append({
                    "id": event_id,
                    "label": label,
                    "type": "event",
                    "properties": {
                        "event_type": event_type,
                        "description": description
                    }
                })

        # 6. 添加Event相關的關係
        async with db_manager.neo4j_session() as session:
            result = await session.run("""
            MATCH (e:Entity)-[r:PARTICIPATES_IN]->(ev:Event)
            RETURN e.entity_id as entity_id, ev.event_id as event_id
            LIMIT $limit
            """, limit=min(limit * 2, 200))

            records = await result.fetch(min(limit * 2, 200))

            for record in records:
                entity_id = str(record["entity_id"])
                event_id = str(record["event_id"])

                edges.append({
                    "id": f"participates_{entity_id}_{event_id}",
                    "source": entity_id,
                    "target": event_id,
                    "label": "participates in",
                    "type": "participates_in"
                })

        await db_manager.close()

        # 統計信息
        node_counts = {}
        for node in nodes:
            node_type = node["type"]
            node_counts[node_type] = node_counts.get(node_type, 0) + 1

        edge_counts = {}
        for edge in edges:
            edge_type = edge["type"]
            edge_counts[edge_type] = edge_counts.get(edge_type, 0) + 1

        return {
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "node_types": node_counts,
                "edge_types": edge_counts,
                "timestamp": datetime.now().isoformat(),
                "data_sources": ["neo4j"]
            }
        }

    except Exception as e:
        import traceback
        error_details = f"{str(e)}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=f"Failed to get knowledge graph: {error_details}")

def main():
    """啟動FastAPI服務"""
    print("🚀 GraphRAG API服務啟動中...")
    print("📊 服務信息:")
    print("  - API地址: http://localhost:8000")
    print("  - 文檔地址: http://localhost:8000/docs")
    print()
    uvicorn.run("grag.api.app:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    main()
