"""Data ingestion service for end-to-end document processing pipeline"""

import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4
import asyncio
from concurrent.futures import ThreadPoolExecutor
import time

from .chunking_service import ChunkingService
from .embedding_service import EmbeddingService
from .llm_knowledge_extractor import LLMKnowledgeExtractor
from ..vision.vlm_service import VLMService
from ..langchain_loader import LangChainDocumentLoader, DocumentProcessingStrategy, StructuredTextFallback
from grag.core.config import settings
from grag.core.database_services import DatabaseManager
from grag.core.relationship_classifier import classify_relationship, DomainType
from grag.core.schemas.domain_relationships import DomainRelationshipRegistry, relationship_registry

logger = logging.getLogger(__name__)


class IngestionService:
    """End-to-end document ingestion pipeline"""

    @staticmethod
    def generate_smart_title(file_path: Path, content: str = "", max_length: int = 80) -> str:
        """Generate a meaningful title from file path and content

        Args:
            file_path: Original file path
            content: Extracted content (optional)
            max_length: Maximum title length

        Returns:
            Smart title for the document
        """
        # Start with filename and clean it
        filename = file_path.stem

        # Remove common temporary prefixes
        filename = re.sub(r'^(tmp|temp|upload)_?', '', filename, flags=re.IGNORECASE)
        filename = re.sub(r'^[a-f0-9]{8,}_?', '', filename)  # Remove UUID-like prefixes

        # Clean up filename
        filename = filename.replace('_', ' ').replace('-', ' ').strip()

        # Check if content is fallback/placeholder content
        content_clean = content.strip() if content else ""
        is_fallback_content = (
            'fallback' in content_clean.lower() or
            'content extraction failed' in content_clean.lower() or
            content_clean.startswith('PDF Document') or
            content_clean.startswith('Document:') or
            len(content_clean) < 20  # Too short to be meaningful
        )

        # If we have meaningful content (not fallback), try to extract title from it
        if content_clean and len(content_clean) > 50 and not is_fallback_content:
            # Extract first meaningful sentence or phrase
            sentences = re.split(r'[.!?]\s+', content_clean[:500])  # First 500 chars

            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) > 15 and len(sentence) < 120:  # Reasonable title length
                    # Check if it looks like a meaningful title
                    if (sentence[0].isupper() and
                        len(sentence.split()) >= 3 and  # At least 3 words
                        not sentence.lower().startswith(('the ', 'a ', 'an ', 'this ', 'these '))):
                        # Clean up the title
                        title = sentence[:max_length]
                        # Remove trailing punctuation that might make it look incomplete
                        title = re.sub(r'[,;:-]$', '', title.strip())
                        return title

            # If no good sentence found, extract meaningful keywords
            # Remove common stop words and get key phrases
            stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were'}
            words = [w for w in content_clean.split()[:15] if w.lower() not in stop_words and len(w) > 2]

            if len(words) >= 3:
                title = ' '.join(words[:8])  # Use first 8 meaningful words
                if len(title) > max_length:
                    title = title[:max_length].rsplit(' ', 1)[0]
                return title.capitalize()

        # Fallback to cleaned filename with better formatting
        if filename:
            # Try to make it more readable and meaningful
            # Handle common patterns like "Project_Report_2024" -> "Project Report 2024"
            words = re.findall(r'[A-Z][a-z]*|[a-z]+|\d+', filename)

            if len(words) > 1:
                # Capitalize each word and join
                title = ' '.join(word.capitalize() for word in words)
            else:
                title = filename.capitalize()

            # Add file extension context for clarity
            ext = file_path.suffix.upper()
            if ext == '.PDF':
                title = f"{title} (PDF)"
            elif ext == '.DOCX':
                title = f"{title} (Word)"
            elif ext == '.TXT':
                title = f"{title} (Text)"
            elif ext == '.MD':
                title = f"{title} (Markdown)"

            if len(title) > max_length:
                title = title[:max_length-3] + '...'

            return title

        # Final fallback with file type
        ext = file_path.suffix.upper() or 'FILE'
        return f"Document ({ext})"

    @staticmethod
    async def generate_llm_smart_title(file_path: Path, content: str = "", max_length: int = 80) -> str:
        """Generate intelligent title using LLM analysis of document content

        Args:
            file_path: Original file path
            content: Extracted content (optional)
            max_length: Maximum title length

        Returns:
            LLM-generated smart title for the document
        """
        try:
            from grag.core.llm_factory import LLMFactory
            from langchain_core.messages import HumanMessage

            # Prepare content sample for LLM analysis
            content_sample = content.strip()[:1500] if content else ""  # Use first 1500 chars

            # Skip LLM generation if content is too short or is fallback content
            is_fallback_content = (
                'fallback' in content.lower() or
                'content extraction failed' in content.lower() or
                content.startswith('PDF Document') or
                content.startswith('Document:') or
                len(content.strip()) < 50  # Too short for meaningful analysis
            )

            if not content_sample or is_fallback_content:
                # Fallback to rule-based title generation
                return IngestionService.generate_smart_title(file_path, content, max_length)

            # Create LLM prompt for title generation
            filename = file_path.name

            prompt = f"""分析這份文檔的內容，為其生成一個簡潔但信息豐富的標題。

文件名: {filename}
內容樣本: {content_sample}

要求:
1. 突出主要主題、設備名稱或核心內容
2. 包含關鍵識別信息（如批准號、公司名、產品名）
3. 如果是醫療/FDA相關文檔，提及關鍵醫療術語
4. 長度控制在{max_length // 2}個字符內（約{max_length // 6}個中文字）
5. 使用專業但易懂的語言
6. 標題應該能夠幫助用戶快速識別文檔內容

請只返回標題，不要包含其他解釋或標點符號。

生成標題："""

            # Get LLM instance and generate title
            llm = LLMFactory.create_default_llm()
            response = await llm.ainvoke([HumanMessage(content=prompt)])

            llm_title = response.content.strip()

            # Clean up the title
            # Remove quotes if present
            llm_title = llm_title.strip('"').strip("'").strip()

            # Remove common prefixes that LLM might add
            llm_title = re.sub(r'^(標題|Title|Document Title)[:\-]?\s*', '', llm_title, flags=re.IGNORECASE)

            # Ensure reasonable length
            if len(llm_title) > max_length:
                # Try to cut at word boundary
                llm_title = llm_title[:max_length-3] + "..."

            # Final validation - ensure we have a meaningful title
            if len(llm_title.strip()) < 5:
                # Fallback if LLM generated something too short
                return IngestionService.generate_smart_title(file_path, content, max_length)

            return llm_title

        except Exception as e:
            logger.warning(f"LLM title generation failed: {e}, falling back to rule-based generation")
            # Fallback to rule-based title generation
            return IngestionService.generate_smart_title(file_path, content, max_length)

    def __init__(self, use_llm_knowledge_extraction: bool = True):
        """Initialize ingestion service using environment configuration

        Args:
            use_llm_knowledge_extraction: Whether to use LLM-powered knowledge extraction
        """
        # Initialize components using environment settings
        self.vlm_service = VLMService(
            enable_pymupdf=True,  # PyMuPDF for complete extraction (highest priority)
            enable_vlm=True,      # VLM for enhancement
            enable_mineru=True,   # MinerU as fallback
            enable_ocr=True       # OCR as final fallback
        )

        self.chunking_service = ChunkingService()  # Uses settings.chunk_size, etc.
        self.embedding_service = EmbeddingService()  # Uses settings.embedding_model

        # Initialize knowledge extractors
        self.use_llm_knowledge_extraction = use_llm_knowledge_extraction
        if use_llm_knowledge_extraction:
            self.knowledge_extractor = LLMKnowledgeExtractor(use_llm=True)
            logger.info("Using LLM-powered knowledge extraction")
        else:
            self.knowledge_extractor = LLMKnowledgeExtractor(use_llm=False)  # Rule-based fallback
            logger.info("Using rule-based knowledge extraction")

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
            try:
                langchain_docs = await self.langchain_loader.load_document(file_path)
                combined_text = self.langchain_loader.combine_documents(langchain_docs)
                logger.info(f"Loaded document content: {len(combined_text)} characters from {len(langchain_docs)} chunks")
            except Exception as load_error:
                logger.warning(f"LangChain document loading failed: {load_error}")
                # Create fallback document with file path as content
                from langchain_core.documents import Document as LangchainDocument
                fallback_content = f"Document: {file_path.name}\nPath: {file_path}\nNote: Content extraction failed due to format incompatibility."
                langchain_docs = [LangchainDocument(page_content=fallback_content)]
                combined_text = fallback_content
                logger.info(f"Using fallback content: {len(combined_text)} characters")

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
            # 傳遞處理結果信息以存儲到Document節點
            processing_info = {
                "processing_method": "PyMuPDF" if vlm_output.metadata and vlm_output.metadata.get("processing_layer") == "PyMuPDF" else "VLM",
                "processing_quality": "高品質",
                "content_quality_score": 0.8,
                "vlm_provider": vlm_output.metadata.get("vlm_provider", "unknown") if vlm_output.metadata else "unknown",
                "vlm_success": True,
                "total_characters": len(vlm_output.ocr_text) if vlm_output.ocr_text else 0,
                "processing_layer": vlm_output.metadata.get("processing_layer", "unknown") if vlm_output.metadata else "unknown"
            }

            ingestion_results = await self._run_database_ingestion(
                file_id, enriched_chunks, knowledge_data, file_path, area_id, processing_info
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

            # Assess content quality
            content_quality = self._assess_content_quality(vlm_output, enriched_chunks)
            vlm_actually_successful = vlm_actually_successful and content_quality["is_acceptable"]

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
                "statistics": self._generate_statistics(enriched_chunks, knowledge_data, processing_time, vlm_output),
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
        """Enhanced VLM processing with fallback - 總是先提取完整文字，再用VLM增強"""
        try:
            # 首先進行完整的文字提取作為基礎
            logger.info(f"Extracting full text content from {file_path.name}")
            full_text_output = await self._extract_full_text_from_file(file_path, file_id, text)

            # 然後嘗試VLM增強
            try:
                logger.info(f"Attempting VLM enhancement for {file_path.name}")
                vlm_output = await self._run_vlm_processing(file_path, file_id, settings.knowledge_area_id)

                # 合併VLM結果和完整文字
                combined_output = self._merge_vlm_and_text(vlm_output, full_text_output)
                combined_output.metadata = combined_output.metadata or {}
                combined_output.metadata["processed_by"] = "vlm_enhanced_text"
                combined_output.metadata["full_text_extracted"] = True
                logger.info("VLM enhancement successful!")
                return combined_output

            except Exception as vlm_error:
                logger.warning(f"VLM enhancement failed: {vlm_error}, using full text extraction only")
                # VLM增強失敗，但我們有完整的文字
                full_text_output.metadata = full_text_output.metadata or {}
                full_text_output.metadata["processed_by"] = "text_only"
                full_text_output.metadata["vlm_enhancement_failed"] = str(vlm_error)
                return full_text_output

        except Exception as general_error:
            logger.error(f"All processing methods failed: {general_error}")
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

    async def _extract_full_text_from_file(self, file_path: Path, file_id: str, text: str):
        """Extract full text content from file for complete processing"""
        try:
            # Use LangChain loader to get complete text extraction
            langchain_docs = await self.langchain_loader.load_document(file_path)
            full_text = self.langchain_loader.combine_documents(langchain_docs)

            # Create a structured output with full text
            from grag.ingestion.vision.vlm_schemas import VLMOutput, VLMRegion

            regions = []
            if full_text:
                # Create a region for the full text content
                region = VLMRegion(
                    region_id=f"full_text_{file_id}",
                    modality="text",
                    description=full_text[:500] + "..." if len(full_text) > 500 else full_text,
                    bbox=[0, 0, 800, 600],  # Full document area
                    confidence=0.9,
                    page=1
                )
                regions.append(region)

            return VLMOutput(
                file_id=file_id,
                ocr_text=full_text,
                regions=regions,
                tables=[],
                charts=[],
                visual_facts=[],
                metadata={
                    "processing_layer": "FULL_TEXT_EXTRACTION",
                    "quality_level": "high",
                    "text_length": len(full_text)
                }
            )

        except Exception as e:
            logger.warning(f"Full text extraction failed: {e}, falling back to provided text")
            # Fallback to provided text
            from grag.ingestion.vision.vlm_schemas import VLMOutput, VLMRegion

            regions = []
            if text:
                region = VLMRegion(
                    region_id=f"text_fallback_{file_id}",
                    modality="text",
                    description=text[:500] + "..." if len(text) > 500 else text,
                    bbox=[0, 0, 800, 600],
                    confidence=0.7,
                    page=1
                )
                regions.append(region)

            return VLMOutput(
                file_id=file_id,
                ocr_text=text,
                regions=regions,
                tables=[],
                charts=[],
                visual_facts=[],
                metadata={
                    "processing_layer": "TEXT_FALLBACK",
                    "quality_level": "medium",
                    "text_length": len(text)
                }
            )

    def _merge_vlm_and_text(self, vlm_output, text_output):
        """Merge VLM analysis results with full text extraction"""
        # Use the full text content but enhance with VLM metadata
        merged_output = text_output.copy()

        # Keep VLM metadata if available
        if vlm_output.metadata:
            merged_output.metadata = {
                **merged_output.metadata,
                **vlm_output.metadata,
                "vlm_enhanced": True
            }

        # Add any visual facts from VLM analysis
        if vlm_output.visual_facts:
            merged_output.visual_facts = vlm_output.visual_facts

        # Add tables and charts from VLM if available
        if vlm_output.tables:
            merged_output.tables = vlm_output.tables
        if vlm_output.charts:
            merged_output.charts = vlm_output.charts

        return merged_output

    async def _create_fallback_output(self, text: str, file_id: str, file_path: Path, reason: str):
        """Create fallback output when all methods fail"""
        logger.warning(f"Creating fallback output due to: {reason}")

        # 使用結構化文字分析作為最終fallback
        from langchain_core.documents import Document as LangchainDocument
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

        processing_metadata = processing_metadata or {}
        processing_start = datetime.now()

        # Embed chunks with quality tracking
        logger.info("Running embedding generation...")
        embedded_chunks = self.embedding_service.embed_chunks(chunks)

        # Extract knowledge with enhanced error handling
        logger.info("Running knowledge extraction...")
        knowledge_data = await self._extract_knowledge_with_fallback(embedded_chunks, visual_facts)

        # Add traceability and quality assessment to each chunk
        for i, chunk in enumerate(embedded_chunks):
            from grag.core.schemas.unified_schemas import TraceabilityInfo, ExtractionMethod, Modality, SourceType

            chunk_traceability = TraceabilityInfo(
                source_type=SourceType.NEO4J,  # Chunks are stored in Neo4j
                source_id=chunk.get("chunk_id"),
                document_id=file_id if file_id else uuid4(),
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

        # Enhance knowledge data with traceability
        enhanced_entities = []
        for entity in knowledge_data.get("entities", []):
            # Ensure source_id is a valid UUID
            source_id = entity.get("entity_id")
            if not isinstance(source_id, UUID):
                try:
                    source_id = UUID(source_id)
                except (ValueError, TypeError):
                    source_id = uuid4()

            from grag.core.schemas.unified_schemas import TraceabilityInfo, ExtractionMethod, Modality, SourceType

            entity_traceability = TraceabilityInfo(
                source_type=SourceType.NEO4J,
                source_id=source_id,
                document_id=file_id if file_id else uuid4(),
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
            # Ensure source_id is a valid UUID
            source_id_str = f"{relation.get('source_id')}_{relation.get('target_id')}"
            try:
                source_id = UUID(source_id_str)
            except (ValueError, TypeError):
                source_id = uuid4()

            from grag.core.schemas.unified_schemas import TraceabilityInfo, ExtractionMethod, Modality, SourceType

            relation_traceability = TraceabilityInfo(
                source_type=SourceType.NEO4J,
                source_id=source_id,
                document_id=file_id if file_id else uuid4(),
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
            # Ensure source_id is a valid UUID
            source_id = fact.get("fact_id", f"visual_fact_{len(enhanced_visual_facts)}")
            if not isinstance(source_id, UUID):
                try:
                    source_id = UUID(source_id)
                except (ValueError, TypeError):
                    source_id = uuid4()

            from grag.core.schemas.unified_schemas import TraceabilityInfo, ExtractionMethod, Modality, SourceType

            fact_traceability = TraceabilityInfo(
                source_type=SourceType.SUPABASE,  # Visual facts come from VLM/vector processing
                source_id=source_id,
                document_id=file_id if file_id else uuid4(),
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

    async def _extract_knowledge_with_fallback(self,
                                             embedded_chunks: List[Dict[str, Any]],
                                             visual_facts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract knowledge using LLM first, then fallback to regex if needed"""
        logger.info(f"Starting knowledge extraction with {len(embedded_chunks)} chunks")

        try:
            # Try LLM extraction first
            all_llm_entities = []
            all_llm_relations = []

            for chunk in embedded_chunks:
                try:
                    # This now returns (entities, relations) tuple
                    chunk_result = await self.knowledge_extractor._extract_entities_with_llm(
                        chunk.get("content", ""), str(chunk.get("chunk_id", ""))
                    )

                    # Handle the tuple return
                    if isinstance(chunk_result, tuple) and len(chunk_result) == 2:
                        chunk_entities, chunk_relations = chunk_result
                        all_llm_entities.extend(chunk_entities)
                        all_llm_relations.extend(chunk_relations)
                    else:
                        logger.warning(f"Unexpected LLM result format for chunk {chunk.get('chunk_id')}: {type(chunk_result)}")

                except Exception as e:
                    logger.warning(f"LLM extraction failed for chunk {chunk.get('chunk_id')}: {e}")

            # If LLM extracted entities, use them
            if all_llm_entities:
                logger.info(f"LLM extracted {len(all_llm_entities)} entities and {len(all_llm_relations)} relations, using LLM results")
                # Get base knowledge structure using regex extractor
                knowledge_data = await self.knowledge_extractor.extract_knowledge(embedded_chunks, visual_facts)
                # Replace with LLM results
                knowledge_data["entities"] = all_llm_entities
                knowledge_data["relations"] = all_llm_relations
                logger.info(f"Returning LLM-enhanced knowledge data with {len(knowledge_data.get('entities', []))} entities and {len(knowledge_data.get('relations', []))} relations")
                return knowledge_data
            else:
                logger.info("LLM extraction returned no entities, falling back to regex")
                # Fallback to regex extraction
                knowledge_data = await self.knowledge_extractor.extract_knowledge(embedded_chunks, visual_facts)
                logger.info(f"Returning regex knowledge data with {len(knowledge_data.get('entities', []))} entities")
                return knowledge_data

        except Exception as e:
            logger.error(f"Critical error in knowledge extraction fallback: {e}")
            # Emergency fallback - return minimal valid structure
            logger.warning("Returning emergency fallback knowledge data")
            return {
                "entities": [],
                "relations": [],
                "events": [],
                "visual_facts": visual_facts or [],
                "metadata": {
                    "extraction_method": "emergency_fallback",
                    "error": str(e),
                    "timestamp": "unknown"
                }
            }


    async def _run_database_ingestion(self,
                                    file_id: str,
                                    chunks: List[Dict[str, Any]],
                                    knowledge_data: Dict[str, Any],
                                    file_path: Path,
                                    area_id: str,
                                    processing_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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
            neo4j_result = await self._ingest_neo4j(neo4j_data, processing_info)
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

    async def _ingest_neo4j(self, data: Dict[str, Any], processing_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Ingest knowledge graph data into Neo4j using synchronous methods"""
        try:
            from datetime import datetime

            # Generate LLM-smart title for the document
            file_path = Path(data["file_path"])
            # Try to get content from chunks for title generation
            sample_content = ""
            if data.get("chunks") and len(data["chunks"]) > 0:
                # Use first chunk content for title generation
                first_chunk = data["chunks"][0]
                if isinstance(first_chunk, dict) and "content" in first_chunk:
                    sample_content = first_chunk["content"][:1500]  # Use more content for LLM analysis

            # Try LLM-generated title first, fallback to rule-based if it fails
            smart_title = await self.generate_llm_smart_title(file_path, sample_content)

            # Extract processing information from data
            processing_method = data.get("processing_method", "VLM")
            processing_quality = data.get("processing_quality", "高品質")
            content_quality_score = data.get("content_quality_score", 0.8)
            vlm_provider = data.get("vlm_provider", "unknown")
            vlm_success = data.get("vlm_success", True)
            total_characters = data.get("total_characters", 0)
            processing_layer = data.get("processing_layer", "unknown")

            # Create Document node using synchronous method
            doc_data = {
                "document_id": data["file_id"],
                "title": smart_title,  # Use smart title instead of filename
                "source_path": data["file_path"],
                "hash": "",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "processing_method": processing_method,
                "processing_quality": processing_quality,
                "content_quality_score": content_quality_score,
                "vlm_provider": vlm_provider,
                "vlm_success": vlm_success,
                "total_characters": total_characters,
                "processing_layer": processing_layer
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

                    # Update chunk with vector_id if available
                    if "vector_id" in chunk:
                        await self._update_chunk_vector_id(chunk["chunk_id"], chunk["vector_id"])

            # Create Entity nodes and relationships
            entities_created = 0
            entity_relations_created = 0
            for entity_data in data.get("entities", []):
                try:
                    from grag.core.schemas.neo4j_schemas import EntityNode, Neo4jRelationship
                    from uuid import uuid4

                    # Ensure entity has an ID
                    entity_id = entity_data.get("entity_id")
                    if not entity_id:
                        entity_id = uuid4()

                    entity = EntityNode(
                        entity_id=entity_id,
                        name=entity_data["name"],
                        type=entity_data["type"],
                        description=entity_data.get("description", ""),
                        aliases=entity_data.get("aliases", [])
                    )

                    # Create entity node
                    created_entity_id = await self.db_manager.create_entity_node(entity)
                    entities_created += 1

                    # Create MENTIONED_IN relationships with chunks
                    chunk_ids = entity_data.get("chunk_ids", [])
                    if not chunk_ids and entity_data.get("chunk_id"):
                        chunk_ids = [entity_data["chunk_id"]]

                    for chunk_id in chunk_ids:
                        try:
                            # 使用domain-aware分類器選擇最適合的關係類型
                            chunk_content = ""
                            # 從chunks中找到對應的內容
                            for chunk in data["chunks"]:
                                if str(chunk.get("chunk_id", "")) == str(chunk_id):
                                    chunk_content = chunk.get("content", "")
                                    break

                            # 選擇關係類型（優先使用domain-specific，fallback到MENTIONED_IN）
                            relationship_type = await self._get_relationship_type_for_entity(
                                entity_data, chunk_content, data["area_id"]
                            )

                            relationship = Neo4jRelationship(
                                from_node="Entity",
                                to_node="Chunk",
                                relationship_type=relationship_type,
                                from_id=created_entity_id,
                                to_id=chunk_id
                            )
                            success = await self.db_manager.create_relationship(relationship)
                            if success:
                                entity_relations_created += 1
                                logger.info(f"Created {relationship_type} relationship between Entity {created_entity_id} and Chunk {chunk_id}")
                        except Exception as rel_error:
                            logger.warning(f"Failed to create Entity-Chunk relationship: {rel_error}")

                except Exception as entity_error:
                    logger.warning(f"Failed to create entity: {entity_error}")

            # Create Entity-Entity relationships from LLM-extracted relations
            entity_entity_relations_created = 0
            logger.info(f"Processing {len(data.get('relations', []))} extracted relations for Entity-Entity relationships")

            for relation_data in data.get("relations", []):
                try:
                    # Parse subject and object entities
                    subject_name = relation_data.get("subject", "").strip()
                    object_name = relation_data.get("object", "").strip()
                    predicate = relation_data.get("predicate", "").strip()

                    logger.debug(f"Processing relation: {subject_name} --{predicate}--> {object_name}")

                    if not subject_name or not object_name or not predicate:
                        logger.debug(f"Skipping incomplete relation: subject='{subject_name}', object='{object_name}', predicate='{predicate}'")
                        continue

                    # Find corresponding entity IDs by name (with improved matching)
                    subject_id = self._find_entity_id_by_name(subject_name, data["entities"])
                    object_id = self._find_entity_id_by_name(object_name, data["entities"])

                    logger.debug(f"Entity ID lookup: '{subject_name}' -> {subject_id}, '{object_name}' -> {object_id}")

                    if not subject_id:
                        logger.warning(f"Could not find entity ID for subject: '{subject_name}'")
                        continue
                    if not object_id:
                        logger.warning(f"Could not find entity ID for object: '{object_name}'")
                        continue
                    if subject_id == object_id:
                        logger.debug(f"Skipping self-relationship: {subject_name} -> {object_name}")
                        continue

                    # Get entity types for classification
                    subject_type = self._find_entity_type_by_name(subject_name, data["entities"])
                    object_type = self._find_entity_type_by_name(object_name, data["entities"])

                    logger.debug(f"Entity types: {subject_name}={subject_type}, {object_name}={object_type}")

                    # Use domain-aware classifier for Entity-Entity relationships
                    try:
                        relationship_type = await self._get_relationship_type_for_entities(
                            {"name": subject_name, "type": subject_type},
                            {"name": object_name, "type": object_type},
                            predicate,
                            data["area_id"]
                        )
                        logger.debug(f"Classified relationship type: {relationship_type}")
                    except Exception as classify_error:
                        logger.warning(f"Relationship classification failed: {classify_error}, using RELATED_TO")
                        relationship_type = "RELATED_TO"

                    relationship = Neo4jRelationship(
                        from_node="Entity",
                        to_node="Entity",
                        relationship_type=relationship_type,
                        from_id=subject_id,
                        to_id=object_id
                    )

                    success = await self.db_manager.create_relationship(relationship)
                    if success:
                        entity_entity_relations_created += 1
                        logger.info(f"✅ Created {relationship_type} relationship: {subject_name} -> {object_name}")
                    else:
                        logger.error(f"❌ Failed to create relationship in database: {subject_name} -> {object_name}")

                except Exception as rel_error:
                    logger.error(f"❌ Failed to create Entity-Entity relationship for {relation_data}: {rel_error}")
                    import traceback
                    logger.error(f"Stack trace: {traceback.format_exc()}")

            # Create Event nodes and relationships
            events_created = 0
            event_relations_created = 0
            for event_data in data.get("events", []):
                try:
                    from grag.core.schemas.neo4j_schemas import EventNode, Neo4jRelationship

                    # Ensure event has an ID
                    event_id = event_data.get("event_id")
                    if not event_id:
                        event_id = uuid4()

                    event = EventNode(
                        event_id=event_id,
                        type=event_data["type"],
                        timestamp=event_data.get("timestamp", ""),
                        description=event_data.get("description", "")
                    )

                    # Create event node
                    created_event_id = await self.db_manager.create_event_node(event)
                    events_created += 1

                    # Create PARTICIPATES_IN relationships with entities
                    entity_ids = event_data.get("entities_involved", [])
                    for entity_id in entity_ids:
                        try:
                            relationship = Neo4jRelationship(
                                from_node="Entity",
                                to_node="Event",
                                relationship_type="PARTICIPATES_IN",
                                from_id=entity_id,
                                to_id=created_event_id
                            )
                            success = await self.db_manager.create_relationship(relationship)
                            if success:
                                event_relations_created += 1
                        except Exception as rel_error:
                            logger.warning(f"Failed to create Entity-Event relationship: {rel_error}")

                except Exception as event_error:
                    logger.warning(f"Failed to create event: {event_error}")

            # Create VisualFact nodes and relationships
            visual_facts_created = 0
            visual_fact_relations_created = 0
            for fact_data in data.get("visual_facts", []):
                try:
                    from grag.core.schemas.neo4j_schemas import VisualFactNode, Neo4jRelationship
                    from uuid import uuid4

                    # Ensure visual fact has an ID
                    fact_id = fact_data.get("fact_id")
                    if not fact_id:
                        fact_id = uuid4()

                    # Ensure vector_id exists for VisualFact
                    vector_id = fact_data.get("vector_id")
                    if not vector_id:
                        # Skip visual facts without vector_id as they can't be properly stored
                        logger.warning(f"Skipping visual fact without vector_id: {fact_id}")
                        continue

                    fact = VisualFactNode(
                        fact_id=fact_id,
                        vector_id=vector_id,
                        region_id=fact_data.get("region_id", ""),
                        modality=fact_data.get("modality", "visual"),
                        description=fact_data.get("description", ""),
                        bbox=fact_data.get("bbox", []),
                        page=fact_data.get("page", 1)
                    )

                    # Create visual fact node
                    created_fact_id = await self.db_manager.create_visual_fact_node(fact)
                    visual_facts_created += 1

                    # Create MENTIONED_IN relationships with chunks
                    chunk_ids = fact_data.get("chunk_ids", [])
                    if not chunk_ids and fact_data.get("chunk_id"):
                        chunk_ids = [fact_data["chunk_id"]]

                    for chunk_id in chunk_ids:
                        try:
                            relationship = Neo4jRelationship(
                                from_node="VisualFact",
                                to_node="Chunk",
                                relationship_type="MENTIONED_IN",
                                from_id=created_fact_id,
                                to_id=chunk_id
                            )
                            success = await self.db_manager.create_relationship(relationship)
                            if success:
                                visual_fact_relations_created += 1
                        except Exception as rel_error:
                            logger.warning(f"Failed to create VisualFact-Chunk relationship: {rel_error}")

                except Exception as fact_error:
                    logger.warning(f"Failed to create visual fact: {fact_error}")

            return {
                "success": True,
                "document_created": 1,
                "chunks_created": chunks_created,
                "entities_created": entities_created,
                "events_created": events_created,
                "visual_facts_created": visual_facts_created,
                "entity_relations_created": entity_relations_created,
                "entity_entity_relations_created": entity_entity_relations_created,
                "event_relations_created": event_relations_created,
                "visual_fact_relations_created": visual_fact_relations_created
            }

        except Exception as e:
            logger.error(f"Neo4j ingestion failed: {e}")
            return {"success": False, "error": str(e)}

    async def _update_chunk_vector_id(self, chunk_id, vector_id):
        """Update a chunk node with its vector_id"""
        try:
            # Use synchronous Neo4j driver for this update
            from neo4j import GraphDatabase

            driver = GraphDatabase.driver(
                self.db_manager.neo4j_uri,
                auth=(self.db_manager.neo4j_user, self.db_manager.neo4j_password)
            )

            with driver.session() as session:
                session.run("""
                MATCH (c:Chunk {chunk_id: $chunk_id})
                SET c.vector_id = $vector_id
                """,
                chunk_id=str(chunk_id),
                vector_id=str(vector_id)
                )

            driver.close()
            logger.info(f"Updated chunk {chunk_id} with vector_id {vector_id}")

        except Exception as e:
            logger.error(f"Failed to update chunk {chunk_id} with vector_id: {e}")

    async def _ingest_pgvector(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Ingest vector data into pgvector using async methods"""
        try:
            from grag.core.schemas.pgvector_schemas import VectorInsert
            from uuid import UUID

            vectors_ingested = 0

            for vector_data in data["vectors"]:
                # Convert string IDs to UUID objects as required by VectorInsert
                try:
                    document_id = UUID(vector_data["document_id"]) if isinstance(vector_data["document_id"], str) else vector_data["document_id"]
                    chunk_id = UUID(vector_data["chunk_id"]) if vector_data.get("chunk_id") and isinstance(vector_data["chunk_id"], str) else vector_data.get("chunk_id")
                    fact_id = UUID(vector_data["fact_id"]) if vector_data.get("fact_id") and isinstance(vector_data["fact_id"], str) else vector_data.get("fact_id")
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid UUID format in vector data: {e}, skipping vector")
                    continue

                # Convert to VectorInsert format
                vector_insert = VectorInsert(
                    embedding=vector_data["embedding"],
                    document_id=document_id,
                    chunk_id=chunk_id,
                    fact_id=fact_id,
                    type=vector_data["type"],
                    page=vector_data["page"],
                    order=vector_data["order"]
                )

                # Insert vector record
                vector_id = await self.db_manager.insert_vector_record(vector_insert)
                if vector_id:
                    vectors_ingested += 1
                else:
                    logger.warning(f"Failed to insert vector record for chunk {chunk_id}")

            logger.info(f"Successfully ingested {vectors_ingested}/{len(data['vectors'])} vectors to pgvector")
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
                           processing_time: float,
                           vlm_output=None) -> Dict[str, Any]:
        """Generate comprehensive processing statistics"""

        chunk_sizes = [len(c["content"]) for c in chunks if "content" in c]

        # Calculate total characters from chunks or VLM output
        total_characters = sum(chunk_sizes)
        if vlm_output and hasattr(vlm_output, 'ocr_text') and vlm_output.ocr_text:
            # Prefer the total characters from VLM output if available
            total_characters = len(vlm_output.ocr_text)

        return {
            "processing_time_seconds": processing_time,
            "chunks": {
                "total": len(chunks),
                "avg_size": sum(chunk_sizes) / len(chunk_sizes) if chunk_sizes else 0,
                "total_characters": total_characters,
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

    def _classify_domain_from_content(self, content: str, area_id: str) -> DomainType:
        """增強版領域檢測 - 使用更多關鍵字和上下文分析"""
        content_lower = content.lower()
        area_id_lower = area_id.lower()

        logger.info(f"🔍 Enhanced domain classification - Area ID: '{area_id}', Content length: {len(content)}")
        logger.info(f"📄 Content sample: {content[:300]}...")

        # 1. 基於area_id的直接映射 (最高優先級)
        if "financial" in area_id_lower or "財報" in area_id_lower or "finance" in area_id_lower:
            logger.info("🎯 Detected FINANCIAL domain from area_id")
            return DomainType.FINANCIAL
        elif "medical" in area_id_lower or "醫療" in area_id_lower or "fda" in area_id_lower or "device" in area_id_lower:
            logger.info("🏥 Detected MEDICAL_DEVICE domain from area_id")
            return DomainType.MEDICAL_DEVICE
        elif "prospect" in area_id_lower or "客戶" in area_id_lower or "customer" in area_id_lower or "sales" in area_id_lower:
            logger.info("👥 Detected PROSPECT domain from area_id")
            return DomainType.PROSPECT
        elif "internal" in area_id_lower or "內部" in area_id_lower or "report" in area_id_lower:
            logger.info("🏢 Detected INTERNAL_REPORT domain from area_id")
            return DomainType.INTERNAL_REPORT

        # 2. 增強版關鍵字檢測 (加入更多專業術語)
        medical_keywords = [
            "fda", "device", "medical", "clinical", "approval", "regulation", "compliance",
            "drug", "pharmaceutical", "therapy", "treatment", "patient", "trial", "study",
            "adverse", "efficacy", "safety", "protocol", "submission", "clearance", "510k",
            "premarket", "postmarket", "recall", "warning", "indication", "contraindication"
        ]

        financial_keywords = [
            "revenue", "profit", "earnings", "financial", "quarter", "investment", "market",
            "quarterly", "annual", "fiscal", "income", "expense", "balance", "sheet", "cash",
            "flow", "asset", "liability", "equity", "dividend", "stock", "share", "valuation",
            "growth", "margin", "forecast", "projection", "trend", "analysis", "report"
        ]

        prospect_keywords = [
            "customer", "client", "prospect", "lead", "opportunity", "sales", "account",
            "contact", "relationship", "pipeline", "conversion", "acquisition", "retention",
            "satisfaction", "feedback", "requirement", "need", "demand", "budget", "roi",
            "contract", "negotiation", "proposal", "tender", "bid", "competition", "market"
        ]

        internal_keywords = [
            "internal", "confidential", "proprietary", "research", "development", "rd",
            "quality", "assurance", "control", "process", "procedure", "standard", "audit",
            "inspection", "testing", "validation", "verification", "performance", "metric",
            "kpi", "benchmark", "improvement", "efficiency", "optimization", "analysis"
        ]

        # 計算各領域得分 (加入權重)
        medical_score = sum(2 if kw in content_lower else 0 for kw in medical_keywords[:10]) + \
                       sum(1 if kw in content_lower else 0 for kw in medical_keywords[10:])
        financial_score = sum(2 if kw in content_lower else 0 for kw in financial_keywords[:10]) + \
                        sum(1 if kw in content_lower else 0 for kw in financial_keywords[10:])
        prospect_score = sum(2 if kw in content_lower else 0 for kw in prospect_keywords[:10]) + \
                        sum(1 if kw in content_lower else 0 for kw in prospect_keywords[10:])
        internal_score = sum(2 if kw in content_lower else 0 for kw in internal_keywords[:10]) + \
                        sum(1 if kw in content_lower else 0 for kw in internal_keywords[10:])

        # 3. 上下文模式檢測
        content_patterns = {
            "medical": [
                r'\b(fda|ema|cfda)\b.*\b(approval|clearance|submission)\b',
                r'\b(clinical trial|phase [123]|double.?blind)\b',
                r'\b(adverse event|side effect|contraindication)\b'
            ],
            "financial": [
                r'\b(q[1-4]|\bquarter\b).*(\d{4}|\breport\b)',
                r'\b(revenue|profit|earnings)\b.*(\$|€|¥|£)',
                r'\b(market share|market cap|valuation)\b'
            ],
            "prospect": [
                r'\b(customer|client)\b.*\b(requirement|need|demand)\b',
                r'\b(competition|competitor)\b.*\b(advantage|strength)\b',
                r'\b(pipeline|forecast|projection)\b.*\b(sales|revenue)\b'
            ]
        }

        # 檢查上下文模式
        import re
        for domain, patterns in content_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content_lower, re.IGNORECASE):
                    if domain == "medical":
                        medical_score += 5
                    elif domain == "financial":
                        financial_score += 5
                    elif domain == "prospect":
                        prospect_score += 5

        logger.info(f"📊 Enhanced keyword scores - Medical: {medical_score}, Financial: {financial_score}, Prospect: {prospect_score}, Internal: {internal_score}")

        # 4. 根據得分和閾值選擇領域
        scores = {
            "medical": medical_score,
            "financial": financial_score,
            "prospect": prospect_score,
            "internal": internal_score
        }

        max_domain = max(scores, key=scores.get)
        max_score = scores[max_domain]

        # 動態閾值：內容越長，要求的匹配分數越高
        base_threshold = 3 if len(content) < 1000 else 5 if len(content) < 5000 else 8
        context_bonus_threshold = 2  # 上下文模式匹配的額外分數

        if max_score >= base_threshold:
            domain_mapping = {
                "medical": DomainType.MEDICAL_DEVICE,
                "financial": DomainType.FINANCIAL,
                "prospect": DomainType.PROSPECT,
                "internal": DomainType.INTERNAL_REPORT
            }
            selected_domain = domain_mapping[max_domain]
            logger.info(f"🎯 Selected {selected_domain.value} domain (score: {max_score}, threshold: {base_threshold})")
            return selected_domain

        logger.info(f"📝 No domain detected with sufficient confidence (max score: {max_score}, threshold: {base_threshold}), using GENERAL")
        return DomainType.GENERAL

    async def _get_relationship_type_for_entity(self, entity_data: Dict[str, Any],
                                              chunk_content: str, area_id: str) -> str:
        """使用domain-aware分類器選擇最適合的實體-分塊關係類型"""
        try:
            # 確定領域類型
            domain_type = self._classify_domain_from_content(chunk_content, area_id)

            # 獲取該領域可用的關係類型
            available_relationships = relationship_registry.get_available_relationships(
                domain_type, "Entity", "Chunk"
            )

            # 如果沒有專用關係，使用MENTIONED_IN作為fallback
            if not available_relationships or "MENTIONED_IN" not in available_relationships:
                logger.info(f"No domain-specific relationships available for {domain_type}, using MENTIONED_IN")
                return "MENTIONED_IN"

            # 使用分類器選擇最適合的關係
            result = await classify_relationship(
                domain_type,
                {
                    "type": entity_data.get("type", "Entity"),
                    "name": entity_data.get("name", "")
                },
                {
                    "type": "Chunk",
                    "content": chunk_content[:200]  # 限制內容長度
                },
                chunk_content
            )

            selected_relationship = result.relationship_type
            logger.info(f"Selected relationship '{selected_relationship}' for entity '{entity_data.get('name', '')}' in domain '{domain_type}'")

            return selected_relationship

        except Exception as e:
            logger.warning(f"Relationship classification failed: {e}, falling back to MENTIONED_IN")
            return "MENTIONED_IN"

    async def _get_relationship_type_for_entities(self, subject_entity: Dict[str, Any],
                                                object_entity: Dict[str, Any],
                                                predicate: str, area_id: str) -> str:
        """使用domain-aware分類器選擇最適合的實體-實體關係類型"""
        try:
            # 確定領域類型 - 使用兩個實體的名稱和謂詞作為上下文
            context_content = f"{subject_entity.get('name', '')} {predicate} {object_entity.get('name', '')}"
            domain_type = self._classify_domain_from_content(context_content, area_id)

            # 獲取該領域可用的Entity-Entity關係類型
            available_relationships = relationship_registry.get_available_relationships(
                domain_type, "Entity", "Entity"
            )

            # 如果沒有專用關係，使用RELATED_TO作為fallback
            if not available_relationships:
                logger.info(f"No domain-specific Entity-Entity relationships available for {domain_type}, using RELATED_TO")
                return "RELATED_TO"

            # 使用分類器選擇最適合的關係
            result = await classify_relationship(
                domain_type,
                subject_entity,
                object_entity,
                predicate  # 將謂詞作為上下文傳遞
            )

            selected_relationship = result.relationship_type
            logger.info(f"Selected Entity-Entity relationship '{selected_relationship}' between '{subject_entity.get('name', '')}' and '{object_entity.get('name', '')}' in domain '{domain_type}'")

            return selected_relationship

        except Exception as e:
            logger.warning(f"Entity-Entity relationship classification failed: {e}, falling back to RELATED_TO")
            return "RELATED_TO"

    def _find_entity_id_by_name(self, name: str, entities: List[Dict[str, Any]]) -> Optional[str]:
        """根據名稱找到實體ID - 增強版匹配邏輯"""
        if not name:
            return None

        name_lower = name.lower().strip()
        name_normalized = self._normalize_entity_name(name_lower)

        logger.debug(f"Looking for entity: '{name}' -> normalized: '{name_normalized}'")

        # 首先嘗試精確匹配
        for entity in entities:
            entity_name = entity.get("name", "").lower().strip()
            if entity_name == name_lower:
                logger.debug(f"Exact match found: '{entity_name}' -> {entity.get('entity_id')}")
                return entity.get("entity_id")

            # 也檢查aliases
            aliases = entity.get("aliases", [])
            if aliases:
                for alias in aliases:
                    if alias.lower().strip() == name_lower:
                        logger.debug(f"Alias match found: '{alias}' -> {entity.get('entity_id')}")
                        return entity.get("entity_id")

        # 如果精確匹配失敗，嘗試模糊匹配
        for entity in entities:
            entity_name = entity.get("name", "").lower().strip()
            entity_normalized = self._normalize_entity_name(entity_name)

            # 檢查標準化後的匹配
            if entity_normalized == name_normalized:
                logger.debug(f"Normalized match found: '{entity_name}' -> '{entity_normalized}' -> {entity.get('entity_id')}")
                return entity.get("entity_id")

            # 檢查部分匹配 (對於較長的名稱)
            if len(name_normalized) > 3 and len(entity_normalized) > 3:
                if name_normalized in entity_normalized or entity_normalized in name_normalized:
                    logger.debug(f"Partial match found: '{name_normalized}' in '{entity_normalized}' -> {entity.get('entity_id')}")
                    return entity.get("entity_id")

        logger.debug(f"No match found for entity name: '{name}'")
        return None

    def _normalize_entity_name(self, name: str) -> str:
        """標準化實體名稱以改善匹配"""
        if not name:
            return ""

        # 移除常見的後綴和前綴
        name = re.sub(r'\b(the|and|or|of|in|on|at|to|for|by|with)\b', '', name, flags=re.IGNORECASE)

        # 移除特殊字符但保留空格
        name = re.sub(r'[^\w\s]', '', name)

        # 標準化空格
        name = ' '.join(name.split())

        return name.strip()

    def _find_entity_type_by_name(self, name: str, entities: List[Dict[str, Any]]) -> str:
        """根據名稱找到實體類型"""
        entity_id = self._find_entity_id_by_name(name, entities)
        if entity_id:
            for entity in entities:
                if entity.get("entity_id") == entity_id:
                    return entity.get("type", "Entity")

        return "Entity"  # 默認類型

    def _assess_content_quality(self, vlm_output, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Assess the quality of extracted content to determine if processing was successful"""
        assessment = {
            "is_acceptable": True,
            "quality_score": 0.8,
            "total_characters": 0,
            "issues": [],
            "recommendations": []
        }

        # Calculate total characters extracted
        total_chars = 0
        for chunk in chunks:
            content = chunk.get("content", "")
            total_chars += len(content)

        assessment["total_characters"] = total_chars

        # Quality assessment criteria
        if total_chars < 100:
            assessment["is_acceptable"] = False
            assessment["quality_score"] = 0.2
            assessment["issues"].append("insufficient_content")
            assessment["recommendations"].append("Content extraction yielded very little text (<100 chars)")
        elif total_chars < 500:
            assessment["quality_score"] = 0.5
            assessment["issues"].append("limited_content")
            assessment["recommendations"].append("Content extraction yielded limited text (<500 chars)")
        elif total_chars > 5000:
            assessment["quality_score"] = 0.9
            assessment["recommendations"].append("High-quality content extraction")

        # Check if content appears to be just basic metadata/titles
        if chunks:
            first_chunk_content = chunks[0].get("content", "").lower()
            basic_indicators = ["content:", "document", "file", "pdf", "page"]

            basic_content_score = 0
            for indicator in basic_indicators:
                if indicator in first_chunk_content:
                    basic_content_score += 0.2

            if basic_content_score > 0.4:  # More than 2 basic indicators
                assessment["is_acceptable"] = False
                assessment["quality_score"] = min(assessment["quality_score"], 0.3)
                assessment["issues"].append("basic_metadata_only")
                assessment["recommendations"].append("Only extracted basic metadata/titles, not actual content")

        # Check for repetitive or low-information content
        if len(chunks) > 1:
            contents = [chunk.get("content", "") for chunk in chunks]
            unique_contents = set(contents)
            if len(unique_contents) < len(chunks) * 0.5:  # Less than 50% unique content
                assessment["quality_score"] *= 0.8
                assessment["issues"].append("repetitive_content")

        return assessment
