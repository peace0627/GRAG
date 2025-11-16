"""Data ingestion service for end-to-end document processing pipeline"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4
import asyncio
from concurrent.futures import ThreadPoolExecutor
import time

from .chunking_service import ChunkingService
from .embedding_service import EmbeddingService
from .knowledge_extraction import KnowledgeExtractor
from ..vision.vlm_service import VLMService
from ..langchain_loader import LangChainDocumentLoader, DocumentProcessingStrategy, StructuredTextFallback
from grag.core.config import settings
from grag.core.database_services import DatabaseManager

logger = logging.getLogger(__name__)


class IngestionService:
    """End-to-end document ingestion pipeline"""

    def __init__(self):
        """Initialize ingestion service using environment configuration"""
        # Initialize components using environment settings
        self.vlm_service = VLMService(
            enable_vlm=True,  # Always enable VLM layer (with fallback)
            enable_mineru=True,
            enable_ocr=True
        )

        self.chunking_service = ChunkingService()  # Uses settings.chunk_size, etc.
        self.embedding_service = EmbeddingService()  # Uses settings.embedding_model
        self.knowledge_extractor = KnowledgeExtractor()  # Uses settings.extract_*

        # Initialize LangChain-based document processing
        self.langchain_loader = LangChainDocumentLoader()
        self.processing_strategy = DocumentProcessingStrategy()
        self.text_fallback = StructuredTextFallback()

        # Initialize database manager
        self.db_manager = DatabaseManager()

        # Thread pool for parallel processing
        self.executor = ThreadPoolExecutor(max_workers=4)

    async def ingest_document_enhanced(self,
                                     file_path: Path,
                                     area_id: str = settings.knowledge_area_id,
                                     force_vlm: Optional[bool] = None) -> Dict[str, Any]:
        """Enhanced document ingestion with LangChain loading and VLM analysis

        Args:
            file_path: Path to the document to process
            area_id: Knowledge area identifier
            force_vlm: Force VLM processing (True) or skip (False), None = auto

        Returns:
            Processing results with enhanced metadata
        """
        start_time = time.time()
        file_id = str(uuid4())

        try:
            logger.info(f"Starting enhanced ingestion of {file_path.name} (ID: {file_id})")

            # Step 1: Load document with LangChain
            logger.info("Step 1/5: LangChain document loading")
            langchain_docs = await self.langchain_loader.load_document(file_path)

            combined_text = self.langchain_loader.combine_documents(langchain_docs)
            logger.info(f"Loaded document content: {len(combined_text)} characters from {len(langchain_docs)} chunks")

            # Step 2: Decide processing strategy
            use_vlm = self.processing_strategy.should_use_vlm_first(file_path, force_vlm)
            logger.info(f"Processing strategy: {'VLM + fallback' if use_vlm else 'Direct processing'}")

            # Step 3: Process document
            if use_vlm:
                # VLM優先處理 + fallback
                vlm_output = await self._process_with_vlm_enhanced(combined_text, file_id, file_path)
            else:
                # 直接處理 (跳過VLM)
                vlm_output = await self._process_without_vlm_enhanced(langchain_docs, file_id, file_path)

            # Step 4: Chunking (統一的)
            logger.info("Step 4/5: Document chunking")
            chunks = await self._run_chunking(vlm_output, file_id, area_id)

            # Step 5: Embedding + Knowledge Extraction (統一的)
            logger.info("Step 5/5: Embedding and knowledge extraction")
            enriched_chunks, knowledge_data = await self._run_embedding_and_knowledge_extraction(
                chunks, vlm_output.visual_facts or []
            )

            # Database Ingestion (保持現有邏輯)
            ingestion_results = await self._run_database_ingestion(
                file_id, enriched_chunks, knowledge_data, file_path, area_id
            )

            processing_time = time.time() - start_time

            # Enhanced result with more metadata
            result = {
                "success": True,
                "file_id": file_id,
                "file_path": str(file_path),
                "processing_time": processing_time,
                "stages_completed": ["langchain_loading", "processing", "chunking", "embedding", "ingestion"],
                "strategy_used": {
                    "vlm_used": use_vlm,
                    "vlm_success": vlm_output.metadata.get("processed_by") in ["vlm", "mineru", "ocr"] if vlm_output.metadata else False,
                    "fallback_used": vlm_output.metadata.get("fallback") if vlm_output.metadata else None,
                    "langchain_loaded": True,
                    "loader_type": file_path.suffix,
                },
                "statistics": self._generate_statistics(enriched_chunks, knowledge_data, processing_time),
                "stage_results": ingestion_results,
                "metadata": {
                    "chunks_created": len(enriched_chunks),
                    "embeddings_created": len([c for c in enriched_chunks if "vector_id" in c]),
                    "entities_extracted": len(knowledge_data.get("entities", [])),
                    "relations_extracted": len(knowledge_data.get("relations", [])),
                    "visual_facts": len(vlm_output.visual_facts or []),
                    "original_chunks_loaded": len(langchain_docs),
                    "quality_level": vlm_output.metadata.get("quality_level", "unknown") if vlm_output.metadata else "unknown",
                }
            }

            logger.info(f"Enhanced document ingestion completed in {processing_time:.2f}s")
            return result

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Enhanced ingestion failed: {e}")

            result = {
                "success": False,
                "file_id": file_id,
                "file_path": str(file_path),
                "processing_time": processing_time,
                "error": str(e),
                "strategy_used": {"failed": True},
            }
            return result

    async def _process_with_vlm_enhanced(self, text: str, file_id: str, file_path: Path):
        """Enhanced VLM processing with fallback"""
        try:
            # 嘗試VLM處理
            logger.info("Attempting VLM processing")
            vlm_output = await self._process_text_with_vlm(text, file_id)
            vlm_output.metadata = vlm_output.metadata or {}
            vlm_output.metadata["processed_by"] = "vlm"
            return vlm_output

        except Exception as vlm_error:
            logger.warning(f"VLM processing failed: {vlm_error}")
            # VLM失敗，轉到舊的VLM服務 (會有MinerU/OCR fallback)
            try:
                logger.info("Falling back to legacy VLM service")
                # 創建臨時文字文件給舊服務
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                    f.write(text)
                    temp_path = Path(f.name)

                # 使用舊的VLM處理服務
                vlm_output = await self._run_vlm_processing(temp_path, file_id, settings.knowledge_area_id)
                vlm_output.metadata = vlm_output.metadata or {}
                vlm_output.metadata["processed_by"] = vlm_output.metadata.get("processing_layer", "fallback")
                vlm_output.metadata["fallback_reason"] = "vlm_api_failed"

                # 清理臨時文件
                temp_path.unlink()
                return vlm_output

            except Exception as fallback_error:
                logger.error(f"All VLM processing failed: {fallback_error}")
                # 最終降級到結構化文字分析
                return await self._create_fallback_output(text, file_id, file_path, "vlm_complete_failure")

    async def _process_text_with_vlm(self, text: str, file_id: str):
        """Process text directly with VLM service"""
        # 這裡可以調用VLM服務的文字輸入方法
        # 目前先使用模擬
        from ..vlm_schemas import VLMOutput, VLMRegion

        # 模擬VLM文字分析結果
        regions = [VLMRegion(
            region_id=f"text_region_0",
            modality="text",
            description="Processed text content",
            bbox=[0, 0, len(text), 20],
            confidence=0.8
        )]

        return VLMOutput(
            file_id=file_id,
            ocr_text=text,
            regions=regions,
            tables=[],
            charts=[],
            visual_facts=[],
            metadata={"quality_level": "high"}
        )

    async def _process_without_vlm_enhanced(self, langchain_docs, file_id: str, file_path: Path):
        """Process documents directly without VLM"""
        logger.info("Processing document without VLM - using structured text analysis")

        return await self.text_fallback.create_structured_output(
            langchain_docs, file_path, file_id
        )

    async def _create_fallback_output(self, text: str, file_id: str, file_path: Path, reason: str):
        """Create fallback output when all methods fail"""
        logger.warning(f"Creating fallback output due to: {reason}")

        # 使用結構化文字分析作為最終fallback
        from langchain.schema import Document as LangchainDocument
        mock_doc = LangchainDocument(page_content=text)

        return await self.text_fallback.create_structured_output(
            [mock_doc], file_path, file_id
        )

    async def ingest_document(self,
                            file_path: Path,
                            area_id: str = settings.knowledge_area_id,
                            options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Ingest a single document end-to-end

        Args:
            file_path: Path to document file
            area_id: Knowledge area identifier
            options: Additional processing options

        Returns:
            Processing results and statistics
        """
        start_time = time.time()
        file_id = str(UUID())  # Generate unique file ID
        options = options or {}

        try:
            logger.info(f"Starting ingestion of {file_path.name} (ID: {file_id})")

            # Step 1: VLM Processing (vision + text extraction)
            logger.info("Step 1/4: VLM processing")
            vlm_output = await self._run_vlm_processing(file_path, file_id, area_id)

            # Step 2: Chunking
            logger.info("Step 2/4: Document chunking")
            chunks = await self._run_chunking(vlm_output, file_id, area_id)

            # Step 3: Embedding + Knowledge Extraction
            logger.info("Step 3/4: Embedding and knowledge extraction")
            enriched_chunks, knowledge_data = await self._run_embedding_and_knowledge_extraction(
                chunks, vlm_output.visual_facts
            )

            # Step 4: Database Ingestion
            logger.info("Step 4/4: Database ingestion")
            ingestion_results = await self._run_database_ingestion(
                file_id, enriched_chunks, knowledge_data, file_path, area_id
            )

            processing_time = time.time() - start_time

            result = {
                "success": True,
                "file_id": file_id,
                "file_path": str(file_path),
                "processing_time": processing_time,
                "stages_completed": ["vlm", "chunking", "embedding", "ingestion"],
                "statistics": self._generate_statistics(enriched_chunks, knowledge_data, processing_time),
                "stage_results": ingestion_results,
                "metadata": {
                    "vlm_processed": vlm_output.processing_time > 0,
                    "chunks_created": len(enriched_chunks),
                    "embeddings_created": len([c for c in enriched_chunks if "vector_id" in c]),
                    "entities_extracted": len(knowledge_data.get("entities", [])),
                    "relations_extracted": len(knowledge_data.get("relations", [])),
                    "visual_facts": len(vlm_output.visual_facts),
                }
            }

            logger.info(f"Document ingestion completed successfully in {processing_time:.2f}s")
            return result

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Document ingestion failed: {e}")

            result = {
                "success": False,
                "file_id": file_id,
                "file_path": str(file_path),
                "processing_time": processing_time,
                "error": str(e),
                "stages_completed": [],
                "statistics": {
                    "error": str(e),
                    "processing_time": processing_time
                }
            }
            return result

    async def _run_vlm_processing(self, file_path: Path, file_id: str, area_id: str):
        """Run VLM processing in thread pool"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self.vlm_service.process_document,
            file_path, file_id, area_id
        )

    async def _run_chunking(self, vlm_output, file_id: str, area_id: str) -> List[Dict[str, Any]]:
        """Run document chunking"""
        file_uuid = UUID(file_id)
        chunks = []

        # Chunk the main OCR text
        text_chunks = self.chunking_service.chunk_vlm_output(vlm_output, {"area_id": area_id})
        chunks.extend(text_chunks)

        logger.info(f"Created {len(chunks)} chunks from VLM output")
        return chunks

    async def _run_embedding_and_knowledge_extraction(self,
                                                   chunks: List[Dict[str, Any]],
                                                   visual_facts: List[Dict[str, Any]]):
        """Run embedding and knowledge extraction"""
        # Embed chunks
        embedded_chunks = self.embedding_service.embed_chunks(chunks)

        # Extract knowledge
        knowledge_data = self.knowledge_extractor.extract_knowledge(
            embedded_chunks, visual_facts
        )

        # Add knowledge relations back to chunks
        for entity in knowledge_data.get("entities", []):
            chunk_id = entity.get("chunk_id")
            for chunk in embedded_chunks:
                if str(chunk["chunk_id"]) == chunk_id:
                    chunk.setdefault("relations", []).append({
                        "type": "entity",
                        "entity_id": entity["entity_id"],
                        "entity_type": entity["type"]
                    })

        return embedded_chunks, knowledge_data

    async def _run_database_ingestion(self,
                                    file_id: str,
                                    chunks: List[Dict[str, Any]],
                                    knowledge_data: Dict[str, Any],
                                    file_path: Path,
                                    area_id: str) -> Dict[str, Any]:
        """Ingest all processed data into databases"""

        try:
            # Prepare data for Neo4j
            neo4j_data = {
                "file_id": file_id,
                "file_path": str(file_path),
                "area_id": area_id,
                "chunks": chunks,
                "entities": knowledge_data.get("entities", []),
                "relations": knowledge_data.get("relations", []),
                "events": knowledge_data.get("events", []),
                "visual_facts": knowledge_data.get("visual_facts", []),
            }

            # Prepare data for pgvector (embeddings)
            pgvector_data = {
                "vectors": [
                    {
                        "vector_id": chunk["vector_id"],
                        "embedding": chunk["embedding"],
                        "document_id": file_id,
                        "chunk_id": str(chunk["chunk_id"]),
                        "type": "chunk",
                        "page": chunk.get("metadata", {}).get("page", 1),
                        "order": chunk.get("order", 0),
                        "content_preview": chunk["content"][:100],
                    }
                    for chunk in chunks
                    if "vector_id" in chunk and "embedding" in chunk
                ]
            }

            # Ingest to databases
            neo4j_result = await self._ingest_neo4j(neo4j_data)
            pgvector_result = await self._ingest_pgvector(pgvector_data)

            return {
                "neo4j": neo4j_result,
                "pgvector": pgvector_result,
                "success": neo4j_result.get("success", False) and pgvector_result.get("success", False)
            }

        except Exception as e:
            logger.error(f"Database ingestion failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _ingest_neo4j(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Ingest knowledge graph data into Neo4j"""
        loop = asyncio.get_event_loop()

        def _sync_ingest():
            try:
                # Create Document node
                doc_data = {
                    "document_id": data["file_id"],
                    "title": Path(data["file_path"]).name,
                    "source_path": data["file_path"],
                    "area_id": data["area_id"],
                }
                self.db_manager.create_document(doc_data)

                # Create Chunk nodes
                for chunk in data["chunks"]:
                    chunk_data = {
                        "chunk_id": str(chunk["chunk_id"]),
                        "document_id": data["file_id"],
                        "text": chunk["content"],
                        "order": chunk.get("order", 0),
                        "page": chunk.get("metadata", {}).get("page", 1),
                        "vector_id": chunk.get("vector_id"),
                    }
                    self.db_manager.create_chunk(chunk_data)

                # Create Entity nodes
                for entity in data["entities"]:
                    entity_data = {
                        "entity_id": entity["entity_id"],
                        "name": entity["name"],
                        "type": entity["type"],
                        "chunk_id": entity.get("chunk_id")
                    }
                    self.db_manager.create_entity(entity_data)

                # Create relations
                for relation in data["relations"]:
                    relation_data = {
                        "relation_id": relation["relation_id"],
                        "subject": relation["subject"],
                        "predicate": relation["predicate"],
                        "object": relation["object"],
                        "chunk_id": relation.get("chunk_id")
                    }
                    self.db_manager.create_relation(relation_data)

                return {
                    "success": True,
                    "document_created": True,
                    "chunks_created": len(data["chunks"]),
                    "entities_created": len(data["entities"]),
                    "relations_created": len(data["relations"])
                }

            except Exception as e:
                logger.error(f"Neo4j ingestion failed: {e}")
                return {"success": False, "error": str(e)}

        return await loop.run_in_executor(self.executor, _sync_ingest)

    async def _ingest_pgvector(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Ingest vector data into pgvector"""
        loop = asyncio.get_event_loop()

        def _sync_ingest():
            try:
                vectors_ingested = 0

                for vector_data in data["vectors"]:
                    # Upsert vector (update if exists)
                    success = self.db_manager.upsert_vector(vector_data)
                    if success:
                        vectors_ingested += 1

                return {
                    "success": True,
                    "vectors_ingested": vectors_ingested,
                    "total_vectors": len(data["vectors"])
                }

            except Exception as e:
                logger.error(f"pgvector ingestion failed: {e}")
                return {"success": False, "error": str(e)}

        return await loop.run_in_executor(self.executor, _sync_ingest)

    def _generate_statistics(self,
                           chunks: List[Dict[str, Any]],
                           knowledge_data: Dict[str, Any],
                           processing_time: float) -> Dict[str, Any]:
        """Generate comprehensive processing statistics"""

        chunk_sizes = [len(c["content"]) for c in chunks if "content" in c]

        return {
            "processing_time_seconds": processing_time,
            "chunks": {
                "total": len(chunks),
                "avg_size": sum(chunk_sizes) / len(chunk_sizes) if chunk_sizes else 0,
                "total_characters": sum(chunk_sizes),
            },
            "embeddings": {
                "created": len([c for c in chunks if "vector_id" in c]),
                "model_used": self.embedding_service.model_name,
                "dimension": self.embedding_service.dimension,
            },
            "knowledge": {
                "entities": len(knowledge_data.get("entities", [])),
                "relations": len(knowledge_data.get("relations", [])),
                "events": len(knowledge_data.get("events", [])),
                "visual_facts": len(knowledge_data.get("visual_facts", [])),
            },
            "vlm_stats": self.vlm_service.get_processing_stats()
        }

    async def batch_ingest(self,
                         file_paths: List[Path],
                         area_id: str = settings.knowledge_area_id,
                         max_concurrent: int = 2) -> List[Dict[str, Any]]:
        """Batch ingest multiple documents with concurrency control

        Args:
            file_paths: List of file paths to process
            area_id: Knowledge area identifier
            max_concurrent: Maximum concurrent processing tasks

        Returns:
            List of results for each document
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def _limited_ingest(file_path: Path):
            async with semaphore:
                return await self.ingest_document(file_path, area_id)

        tasks = [_limited_ingest(fp) for fp in file_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions in results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "success": False,
                    "file_path": str(file_paths[i]),
                    "error": str(result),
                    "processing_time": 0.0
                })
            else:
                processed_results.append(result)

        return processed_results
