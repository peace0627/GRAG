"""Data ingestion service for end-to-end document processing pipeline"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from uuid import UUID
import asyncio
from concurrent.futures import ThreadPoolExecutor
import time

from .chunking_service import ChunkingService
from .embedding_service import EmbeddingService
from .knowledge_extraction import KnowledgeExtractor
from ..vision.vlm_service import VLMService
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

        # Initialize database manager
        self.db_manager = DatabaseManager()

        # Thread pool for parallel processing
        self.executor = ThreadPoolExecutor(max_workers=4)

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
