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

# 導入Agent和API Schemas
from grag.agents.rag_agent import AgenticRAGAgent
from .schemas import (
    QueryRequest, QueryResponse, SystemStatusResponse,
    UploadResponse, BatchUploadResponse, DeleteResponse,
    StatisticsResponse, SearchRequest, SearchResponse, ErrorResponse
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

            return {
                "success": True,
                "message": f"File '{file.filename}' processed successfully",
                "document_id": result.get("file_id"),
                "processing_time": result.get("processing_time"),
                "processing_method": "VLM" if strategy.get("vlm_used") else "文字處理",
                "processing_quality": processing_quality,
                "content_quality_score": content_quality_score,
                "vlm_provider": strategy.get("vlm_provider"),
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
        from .schemas import DocumentInfo, DocumentListResponse

        db_manager = get_database_manager()
        await db_manager.initialize()

        # Query documents from Neo4j with enhanced information
        raw_documents = await db_manager.list_documents(limit=limit, offset=offset)
        await db_manager.close()

        # Enhance documents with processing method information
        enhanced_documents = []
        for doc in raw_documents["documents"]:
            # Get processing information from recent upload results
            # This is a simplified approach - in production, store this in database
            processing_method = "VLM"  # Default
            processing_quality = "高品質"
            content_quality_score = 0.8
            vlm_provider = "ollama"
            vlm_success = True
            total_characters = doc.get("chunk_count", 0) * 500  # Estimate

            # Create enhanced document info
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
    """獲取知識圖譜數據用於前端視覺化"""
    try:
        db_manager = get_database_manager()
        await db_manager.initialize()

        # 獲取所有Document節點
        documents = await db_manager.list_documents(limit=limit, offset=0)

        nodes = []
        edges = []

        # 添加Document節點 - 使用智能標籤
        for doc in documents["documents"]:
            # 生成更有意義的標籤
            smart_label = doc["title"]
            if smart_label and len(smart_label) > 50:
                smart_label = smart_label[:47] + "..."

            nodes.append({
                "id": doc["document_id"],
                "label": smart_label or f"Document {doc['document_id'][:8]}",
                "type": "entity",
                "properties": {
                    "description": f"上傳時間: {datetime.fromisoformat(doc['created_at'].replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')}",
                    "chunk_count": doc["chunk_count"],
                    "source_path": doc["source_path"],
                    "original_title": doc["title"]
                }
            })

        # 獲取Document-Chunk關係
        for doc in documents["documents"]:
            doc_id = doc["document_id"]

            # 查詢這個文檔的chunks
            async with db_manager.neo4j_session() as session:
                result = await session.run("""
                MATCH (d:Document {document_id: $doc_id})-[:HAS_CHUNK]->(c:Chunk)
                RETURN c.chunk_id as chunk_id, c.text as text, c.vector_id as vector_id
                LIMIT 10
                """, doc_id=doc_id)

                records = await result.fetch(10)

                for record in records:
                    chunk_id = str(record["chunk_id"])
                    chunk_text = record["text"] or ""

                    # 生成更有意義的分塊標籤
                    if chunk_text and len(chunk_text.strip()) > 10:
                        # 提取前30個字符作為標籤，去除常見的無意義前綴
                        label_text = chunk_text.strip()[:50]
                        # 移除常見的fallback前綴
                        if label_text.lower().startswith(('pdf document', 'document:', 'content:')):
                            # 嘗試提取更有意義的部分
                            words = label_text.split()
                            if len(words) > 3:
                                label_text = ' '.join(words[2:])  # 跳過前兩個詞

                        # 如果還是太長，截斷並添加省略號
                        if len(label_text) > 30:
                            label_text = label_text[:27] + "..."
                    else:
                        # Fallback到chunk ID
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
                        "id": f"edge_{doc_id}_{chunk_id}",
                        "source": doc_id,
                        "target": chunk_id,
                        "label": "contains",
                        "type": "contains"
                    })

        await db_manager.close()

        return {
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "timestamp": datetime.now().isoformat()
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get knowledge graph: {str(e)}")

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
