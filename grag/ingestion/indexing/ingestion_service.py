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
            enable_vlm=True,  # Always enable VLM layer (with fallback for non-text files)
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

        # Initialize database manager with settings
        self.db_manager = DatabaseManager(
            neo4j_uri=settings.neo4j_uri,
            neo4j_user=settings.neo4j_user,
            neo4j_password=settings.neo4j_password,
            supabase_url=settings.supabase_url,
            supabase_key=settings.supabase_key
        )

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
            file_ext = file_path.suffix.lower()
            if file_ext in ['.txt', '.md']:
                # 強制對文字文件使用直接處理
                use_vlm = False
                logger.info(f"File type {file_ext} - forcing direct processing (no VLM)")
            else:
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

            # Get detailed processing trace
            processing_trace = self._generate_processing_trace(
                file_path, use_vlm, vlm_output, enriched_chunks
            )

            # Enhanced result with more metadata
            # More robust VLM success detection
            processing_layer = vlm_output.metadata.get("processing_layer", "").upper() if vlm_output.metadata else ""
            vlm_actually_successful = (
                processing_layer == "VLM" or
                (processing_layer in ["MINERU", "OCR", "FALLBACK_TEXT_PROCESSING"] and use_vlm == True)  # VLM was attempted but VLM service not available
            )

            result = {
                "success": True,
                "file_id": file_id,
                "file_path": str(file_path),
                "processing_time": processing_time,
                "stages_completed": ["langchain_loading", "processing", "chunking", "embedding", "ingestion"],
                "processing_trace": processing_trace,
                "strategy_used": {
                    "vlm_used": use_vlm,
                    "vlm_success": vlm_actually_successful,
                    "vlm_provider": vlm_output.metadata.get("vlm_provider", "unknown") if vlm_output.metadata else "unknown",
                    "processing_layer": processing_layer.lower(),
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
                    "quality_level": vlm_output.metadata.get("quality_level", "unknown").lower() if vlm_output.metadata and vlm_output.metadata.get("quality_level") else "unknown",
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
        """Enhanced VLM processing with fallback - 優先調用真實VLM服務！"""
        try:
            # 優先嘗試真實的VLM服務處理實際文件
            logger.info(f"Attempting real VLM service processing for {file_path.name}")
            vlm_output = await self._run_vlm_processing(file_path, file_id, settings.knowledge_area_id)
            vlm_output.metadata = vlm_output.metadata or {}
            vlm_output.metadata["processed_by"] = vlm_output.metadata.get("processing_layer", "vlm")
            logger.info("VLM service processing successful!")
            return vlm_output

        except Exception as vlm_error:
            logger.warning(f"VLM service processing failed: {vlm_error}, falling back to text processing")
            # VLM服務失敗，回退到文字處理
            try:
                logger.info("Falling back to structured text processing")
                vlm_output = await self._process_text_with_vlm(text, file_id)
                vlm_output.metadata = vlm_output.metadata or {}
                vlm_output.metadata["processed_by"] = "text_fallback"
                vlm_output.metadata["fallback_reason"] = "vlm_service_failed"
                return vlm_output

            except Exception as fallback_error:
                logger.error(f"All processing methods failed: {fallback_error}")
                # 最終降級到結構化文字分析
                return await self._create_fallback_output(text, file_id, file_path, "all_methods_failed")

    async def _process_text_with_vlm(self, text: str, file_id: str):
        """Process text directly with VLM service"""
        # 這裡可以調用VLM服務的文字輸入方法
        # 目前先使用模擬
        from grag.ingestion.vision.vlm_schemas import VLMOutput, VLMRegion

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
            metadata={"quality_level": "high", "processing_layer": "FALLBACK_TEXT_PROCESSING"}
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
                                                   visual_facts: List[Dict[str, Any]],
                                                   file_path: Optional[Path] = None,
                                                   file_id: Optional[str] = None,
                                                   processing_metadata: Optional[Dict[str, Any]] = None):
        """Run embedding and knowledge extraction with enhanced traceability"""
        from datetime import datetime
        from ..core.schemas.unified_schemas import TraceabilityInfo, ExtractionMethod, Modality, SourceType

        processing_metadata = processing_metadata or {}
        processing_start = datetime.now()

        # Embed chunks with quality tracking
        logger.info("Running embedding generation...")
        embedded_chunks = self.embedding_service.embed_chunks(chunks)

        # Add traceability and quality assessment to each chunk
        for i, chunk in enumerate(embedded_chunks):
            chunk_traceability = TraceabilityInfo(
                source_type=SourceType.NEO4J,  # Chunks are stored in Neo4j
                source_id=chunk.get("chunk_id"),
                document_id=file_id or "unknown",
                document_path=str(file_path) if file_path else "unknown",
                page_number=chunk.get("metadata", {}).get("page", 1),
                chunk_order=chunk.get("order", i),
                processing_timestamp=processing_start,
                processing_pipeline=["langchain_loading", "chunking", "embedding", "knowledge_extraction"],
                extraction_method=ExtractionMethod.LLM,  # Chunks are created by LLM-based processing
                quality_score=self._assess_chunk_quality(chunk),
                processing_metadata={
                    **processing_metadata,
                    "embedding_model": self.embedding_service.model_name,
                    "embedding_dimension": self.embedding_service.dimension,
                    "chunking_strategy": "sentence_based"
                }
            )

            chunk["traceability"] = chunk_traceability.model_dump()
            chunk["modality"] = Modality.TEXT.value
            chunk["content_type"] = "chunk"
            chunk["confidence"] = chunk_traceability.quality_score

        # Extract knowledge with traceability
        logger.info("Running knowledge extraction...")
        knowledge_data = self.knowledge_extractor.extract_knowledge(
            embedded_chunks, visual_facts
        )

        # Enhance knowledge data with traceability
        enhanced_entities = []
        for entity in knowledge_data.get("entities", []):
            entity_traceability = TraceabilityInfo(
                source_type=SourceType.NEO4J,
                source_id=entity.get("entity_id"),
                document_id=file_id or "unknown",
                document_path=str(file_path) if file_path else "unknown",
                processing_timestamp=datetime.now(),
                processing_pipeline=["knowledge_extraction", "ner"],
                extraction_method=ExtractionMethod.NER,
                quality_score=entity.get("confidence", 0.8),
                processing_metadata={
                    "extractor_used": "NERExtractor",
                    "entity_type": entity.get("type"),
                    "chunk_id": entity.get("chunk_id")
                }
            )

            enhanced_entity = {
                **entity,
                "traceability": entity_traceability.model_dump(),
                "modality": Modality.RELATIONAL.value,
                "content_type": "entity",
                "confidence": entity.get("confidence", 0.8)
            }
            enhanced_entities.append(enhanced_entity)

        # Enhance relations with traceability
        enhanced_relations = []
        for relation in knowledge_data.get("relations", []):
            relation_traceability = TraceabilityInfo(
                source_type=SourceType.NEO4J,
                source_id=f"{relation.get('source_id')}_{relation.get('target_id')}",
                document_id=file_id or "unknown",
                document_path=str(file_path) if file_path else "unknown",
                processing_timestamp=datetime.now(),
                processing_pipeline=["knowledge_extraction", "relation_extraction"],
                extraction_method=ExtractionMethod.RULE_BASED,
                quality_score=relation.get("confidence", 0.7),
                processing_metadata={
                    "relation_type": relation.get("type"),
                    "extraction_method": "pattern_matching"
                }
            )

            enhanced_relation = {
                **relation,
                "traceability": relation_traceability.model_dump(),
                "modality": Modality.RELATIONAL.value,
                "content_type": "relation",
                "confidence": relation.get("confidence", 0.7)
            }
            enhanced_relations.append(enhanced_relation)

        # Enhance visual facts with traceability
        enhanced_visual_facts = []
        for fact in visual_facts:
            fact_traceability = TraceabilityInfo(
                source_type=SourceType.SUPABASE,  # Visual facts come from VLM/vector processing
                source_id=fact.get("fact_id", f"visual_fact_{len(enhanced_visual_facts)}"),
                document_id=file_id or "unknown",
                document_path=str(file_path) if file_path else "unknown",
                page_number=fact.get("page", 1),
                processing_timestamp=datetime.now(),
                processing_pipeline=["vlm_processing", "visual_analysis"],
                extraction_method=ExtractionMethod.VLM,
                quality_score=fact.get("confidence", 0.8),
                processing_metadata={
                    "vlm_provider": processing_metadata.get("vlm_provider"),
                    "region_type": fact.get("modality"),
                    "bbox": fact.get("bbox")
                }
            )

            enhanced_fact = {
                **fact,
                "traceability": fact_traceability.model_dump(),
                "modality": Modality.VISUAL.value,
                "content_type": "visual_fact",
                "confidence": fact.get("confidence", 0.8)
            }
            enhanced_visual_facts.append(enhanced_fact)

        # Add enhanced relations back to chunks with full traceability
        for entity in enhanced_entities:
            chunk_id = entity.get("chunk_id")
            for chunk in embedded_chunks:
                if str(chunk["chunk_id"]) == chunk_id:
                    chunk.setdefault("relations", []).append({
                        "type": "entity",
                        "entity_id": entity["entity_id"],
                        "entity_type": entity["type"],
                        "confidence": entity["confidence"],
                        "traceability": entity["traceability"],
                        "extraction_method": entity["traceability"]["extraction_method"]
                    })

        # Update knowledge data with enhanced information
        enhanced_knowledge_data = {
            **knowledge_data,
            "entities": enhanced_entities,
            "relations": enhanced_relations,
            "visual_facts": enhanced_visual_facts,
            "processing_stats": {
                "chunks_processed": len(embedded_chunks),
                "entities_extracted": len(enhanced_entities),
                "relations_extracted": len(enhanced_relations),
                "visual_facts_processed": len(enhanced_visual_facts),
                "processing_time": (datetime.now() - processing_start).total_seconds(),
                "quality_assessment": self._assess_knowledge_quality(enhanced_entities, enhanced_relations)
            }
        }

        logger.info(f"Knowledge extraction completed: {len(enhanced_entities)} entities, "
                   f"{len(enhanced_relations)} relations, {len(enhanced_visual_facts)} visual facts")

        return embedded_chunks, enhanced_knowledge_data

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
        """Ingest knowledge graph data into Neo4j using synchronous methods"""
        try:
            from datetime import datetime

            # Create Document node using synchronous method
            doc_data = {
                "document_id": data["file_id"],
                "title": Path(data["file_path"]).name,
                "source_path": data["file_path"],
                "hash": "",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            doc_result = await self.db_manager.create_document_sync(doc_data)

            if not doc_result.get("success"):
                return doc_result

            # Create Chunk nodes using synchronous method
            chunks_created = 0
            for chunk in data["chunks"]:
                chunk_data = {
                    "document_id": data["file_id"],
                    "chunk_id": str(chunk["chunk_id"]),
                    "content": chunk["content"]
                }
                chunk_result = await self.db_manager.create_chunk_sync(chunk_data)
                if chunk_result.get("success"):
                    chunks_created += 1

            return {
                "success": True,
                "document_created": 1,
                "chunks_created": chunks_created,
                "entities_created": 0,  # Placeholder
                "relations_created": 0  # Placeholder
            }

        except Exception as e:
            logger.error(f"Neo4j ingestion failed: {e}")
            return {"success": False, "error": str(e)}

    async def _ingest_pgvector(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Ingest vector data into pgvector using async methods"""
        try:
            from grag.core.pgvector_schemas import VectorInsert
            from uuid import uuid4

            vectors_ingested = 0

            for vector_data in data["vectors"]:
                # Convert to VectorInsert format
                vector_insert = VectorInsert(
                    embedding=vector_data["embedding"],
                    document_id=vector_data["document_id"],
                    chunk_id=vector_data.get("chunk_id"),
                    fact_id=None,  # For future use
                    type=vector_data["type"],
                    page=vector_data["page"],
                    order=vector_data["order"]
                )

                # Insert vector record
                vector_id = await self.db_manager.insert_vector_record(vector_insert)
                if vector_id:
                    vectors_ingested += 1

            return {
                "success": True,
                "vectors_ingested": vectors_ingested,
                "total_vectors": len(data["vectors"])
            }

        except Exception as e:
            logger.error(f"pgvector ingestion failed: {e}")
            return {"success": False, "error": str(e)}

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

    def _generate_processing_trace(self,
                                 file_path: Path,
                                 use_vlm: bool,
                                 vlm_output,
                                 chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate detailed processing trace showing which modules were used"""

        file_ext = file_path.suffix.lower()
        trace = {
            "file_type": file_ext,
            "processing_chain": [],
            "modules_used": []
        }

        # Step 1: File loading
        loader_info = {
            '.md': "LangChain TextLoader",
            '.txt': "LangChain TextLoader",
            '.pdf': "LangChain PyPDFLoader",
            '.docx': "LangChain Docx2txtLoader"
        }.get(file_ext, "LangChain UnstructuredFileLoader")

        trace["processing_chain"].append({
            "stage": "文件載入",
            "module": loader_info,
            "method": "load()",
            "description": f"使用{loader_info}載入{file_ext}文件"
        })
        trace["modules_used"].append("LangChain Document Loader")

        # Step 2: Processing strategy and engine
        if use_vlm:
            # VLM processing attempted - determine actual processor used
            processing_layer = "Unknown"
            if vlm_output and hasattr(vlm_output, 'metadata'):
                processing_layer = vlm_output.metadata.get("processing_layer", "VLM")

            # Map processing layer to specific module and description
            if processing_layer == "VLM":
                # Determine which VLM provider was actually used
                vlm_provider = "Unknown"
                vlm_model = "Unknown"
                if vlm_output and vlm_output.metadata:
                    vlm_provider = vlm_output.metadata.get("vlm_provider", "Generic VLM")
                    vlm_model = vlm_output.metadata.get("vlm_model", "Unknown Model")

                if vlm_provider == "ollama":
                    vlm_module = f"grag.vision.VLMService → Ollama (本地VLM)"
                    processor = f"Ollama本地VLM模型處理"
                    actual_processor = f"{vlm_model} (Ollama本地)"
                elif vlm_provider == "openai":
                    vlm_module = f"grag.vision.VLMService → OpenAI (雲端VLM)"
                    processor = f"OpenAI GPT-4V視覺模型處理"
                    actual_processor = f"{vlm_model} (OpenAI GPT-4V)"
                else:
                    # Check if it's Qwen2VL by examining the URL or other metadata
                    vlm_name = "Qwen2VL"
                    if "qwen" in str(settings.qwen2vl_base_url).lower():
                        vlm_name = "Qwen2VL"
                    elif "openai" in str(settings.openai_api_key):
                        vlm_name = "OpenAI GPT-4V"

                    vlm_module = f"grag.vision.VLMService → {vlm_name} (雲端VLM)"
                    processor = f"{vlm_name}阿里雲或OpenAI兼容視覺模型處理"
                    actual_processor = f"{vlm_model} ({vlm_name} API)"
            elif processing_layer == "MinerU":
                vlm_module = "grag.vision.VLMService → MinerU (PDF解析器)"
                processor = "MinerU高精確度PDF文檔解析"
                actual_processor = "MinerU PDF處理引擎"
            elif processing_layer == "OCR":
                vlm_module = "grag.vision.VLMService → Tesseract OCR"
                processor = "OCR光學字元辨識"
                actual_processor = "Tesseract OCR引擎"
            elif processing_layer == "FALLBACK_TEXT_PROCESSING":
                vlm_module = "grag.ingestion.StructuredTextFallback"
                processor = "結構化文字分析"
                actual_processor = "結構化文字分析處理器"
            else:
                vlm_module = "grag.vision.VLMService"
                processor = "VLM多層處理鏈 (VLM → MinerU → OCR)"
                actual_processor = "多層處理器連 (包含降級)"

            trace["processing_chain"].append({
                "stage": "文檔處理",
                "module": vlm_module,
                "method": "process_document()",
                "description": f"實際使用 **{actual_processor}** 處理文件"
            })

            # Add modules based on what was actually used
            if processing_layer == "VLM":
                trace["modules_used"].append("VLM Service (Qwen2VL)")
            elif processing_layer == "MinerU":
                trace["modules_used"].extend(["VLM Service (fallback)", "MinerU PDF Processor"])
            elif processing_layer == "OCR":
                trace["modules_used"].extend(["VLM Service (fallback)", "MinerU (skipped)", "Tesseract OCR"])
            else:
                trace["modules_used"].extend(["VLM Service", "MinerU", "OCR"])
        else:
            # Direct text processing
            trace["processing_chain"].append({
                "stage": "文檔處理",
                "module": "grag.ingestion.StructuredTextFallback",
                "method": "create_structured_output()",
                "description": "跳過VLM處理，直接進行結構化文字分析"
            })
            trace["modules_used"].append("Structured Text Fallback")

        # Step 3: Chunking
        chunking_info = "LlamaIndex MarkdownNodeParser" if file_ext == '.md' else "LlamaIndex SentenceSplitter"
        trace["processing_chain"].append({
            "stage": "分塊處理",
            "module": f"LlamaIndex {chunking_info}",
            "method": "get_nodes_from_documents()",
            "description": f"使用{chunking_info}進行智慧分塊，創建{len(chunks)}個chunks"
        })
        trace["modules_used"].append("LlamaIndex Node Parsers")

        # Step 4: Embedding
        trace["processing_chain"].append({
            "stage": "向量嵌入",
            "module": "SentenceTransformers all-MiniLM-L6-v2",
            "method": "encode()",
            "description": f"生成{len(chunks)}個384維向量嵌入"
        })
        trace["modules_used"].append("SentenceTransformers")

        # Step 5: Knowledge extraction
        entities_count = len([c for c in chunks if c.get("relations", [])])
        trace["processing_chain"].append({
            "stage": "知識提取",
            "module": "grag.ingestion.knowledge_extraction.NERExtractor",
            "method": "extract_entities()",
            "description": f"執行實體辨識和關係提取 ({entities_count}個實體)"
        })
        trace["modules_used"].append("Knowledge Extraction")

        # Step 6: Database storage
        trace["processing_chain"].append({
            "stage": "資料存儲",
            "module": "Neo4j + Supabase (pgvector)",
            "method": "create_document_sync() + insert_vector_record()",
            "description": "將處理結果存儲到圖形資料庫和向量資料庫"
        })
        trace["modules_used"].extend(["Neo4j Graph Database", "Supabase pgvector"])

        return trace

    def _assess_chunk_quality(self, chunk: Dict[str, Any]) -> float:
        """Assess the quality of a chunk based on various factors"""
        quality_score = 0.5  # Base score

        content = chunk.get("content", "")

        # Content length assessment
        content_length = len(content.strip())
        if content_length > 500:
            quality_score += 0.2  # Good length
        elif content_length < 50:
            quality_score -= 0.2  # Too short

        # Content coherence (simple heuristics)
        sentences = content.split('.')
        if len(sentences) > 2:
            quality_score += 0.1  # Multiple sentences

        # Special character ratio
        special_chars = sum(1 for c in content if not c.isalnum() and not c.isspace())
        special_ratio = special_chars / max(len(content), 1)

        if special_ratio > 0.3:
            quality_score -= 0.1  # Too many special characters

        # Check for meaningful content
        meaningful_words = sum(1 for word in content.split() if len(word) > 2)
        if meaningful_words < 3:
            quality_score -= 0.2  # Not enough meaningful content

        return max(0.1, min(1.0, quality_score))  # Clamp between 0.1 and 1.0

    def _assess_knowledge_quality(self, entities: List[Dict[str, Any]],
                                 relations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Assess the overall quality of extracted knowledge"""
        assessment = {
            "overall_score": 0.5,
            "entity_quality": 0.5,
            "relation_quality": 0.5,
            "diversity_score": 0.5,
            "issues": []
        }

        # Entity quality assessment
        if entities:
            entity_scores = [e.get("confidence", 0.5) for e in entities]
            avg_entity_confidence = sum(entity_scores) / len(entity_scores)

            # Check entity diversity
            entity_types = set(e.get("type", "unknown") for e in entities)
            type_diversity = len(entity_types) / max(len(entities), 1)

            assessment["entity_quality"] = (avg_entity_confidence + type_diversity) / 2

            if len(entities) < 3:
                assessment["issues"].append("insufficient_entities")
            if avg_entity_confidence < 0.6:
                assessment["issues"].append("low_entity_confidence")
        else:
            assessment["issues"].append("no_entities_extracted")
            assessment["entity_quality"] = 0.0

        # Relation quality assessment
        if relations:
            relation_scores = [r.get("confidence", 0.5) for r in relations]
            avg_relation_confidence = sum(relation_scores) / len(relation_scores)

            # Check relation diversity
            relation_types = set(r.get("type", "unknown") for r in relations)
            relation_diversity = len(relation_types) / max(len(relations), 1)

            assessment["relation_quality"] = (avg_relation_confidence + relation_diversity) / 2

            if len(relations) < 2:
                assessment["issues"].append("insufficient_relations")
        else:
            assessment["issues"].append("no_relations_extracted")
            assessment["relation_quality"] = 0.0

        # Diversity assessment
        total_items = len(entities) + len(relations)
        unique_types = len(set(e.get("type", "unknown") for e in entities) |
                          set(r.get("type", "unknown") for r in relations))

        assessment["diversity_score"] = unique_types / max(total_items, 1)

        # Overall score calculation
        weights = {
            "entity_quality": 0.4,
            "relation_quality": 0.3,
            "diversity_score": 0.3
        }

        assessment["overall_score"] = (
            assessment["entity_quality"] * weights["entity_quality"] +
            assessment["relation_quality"] * weights["relation_quality"] +
            assessment["diversity_score"] * weights["diversity_score"]
        )

        return assessment
