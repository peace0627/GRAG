"""Document chunking service using LlamaIndex text splitters"""

import logging
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4

from llama_index.core.node_parser import (
    SentenceSplitter,
    SimpleNodeParser,
    MarkdownNodeParser
)
from llama_index.core import Document

from grag.core.config import settings

logger = logging.getLogger(__name__)


class ChunkingService:
    """Intelligent text chunking for different document types"""

    def __init__(self):
        """Initialize chunking service using environment configuration"""
        # Load config from environment
        self.chunk_size = settings.chunk_size
        self.chunk_overlap = settings.chunk_overlap
        self.include_visual_chunks = settings.include_visual_chunks

        # Initialize different splitters
        self._sentence_splitter = SentenceSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )

        self._hierarchical_splitter = SimpleNodeParser(
            chunk_size=2048,
            chunk_overlap=self.chunk_overlap
        )

        self._markdown_splitter = MarkdownNodeParser()

    def chunk_text(self,
                  text: str,
                  document_id: UUID,
                  metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Chunk text based on content characteristics

        Args:
            text: Input text to chunk
            document_id: Source document UUID
            metadata: Additional metadata

        Returns:
            List of chunk dictionaries with content and metadata
        """
        try:
            text_length = len(text)
            logger.info(f"Chunking text of length {text_length} with chunk_size={self.chunk_size}")

            # If text is shorter than chunk_size, create single chunk
            if text_length <= self.chunk_size:
                chunk_id = uuid4()
                chunk_data = {
                    "chunk_id": chunk_id,
                    "document_id": document_id,
                    "content": text,
                    "order": 0,
                    "metadata": {
                        "chunk_size": text_length,
                        "source_document": str(document_id),
                        "processing_method": "single_chunk"
                    },
                    "relations": []
                }
                logger.info("Text shorter than chunk_size, created single chunk")
                return [chunk_data]

            # For longer texts, use LlamaIndex splitter
            # Create LlamaIndex Document
            doc = Document(
                text=text,
                metadata=metadata or {},
                id_=str(document_id)
            )

            # Choose splitter based on content analysis
            splitter = self._choose_splitter(text)

            # Process document
            nodes = splitter.get_nodes_from_documents([doc])

            logger.info(f"LlamaIndex splitter created {len(nodes)} nodes")

            # Convert to our format
            chunks = []
            for i, node in enumerate(nodes):
                chunk_id = uuid4()  # Generate unique chunk ID
                chunk_content = node.get_content()

                chunk_data = {
                    "chunk_id": chunk_id,
                    "document_id": document_id,
                    "content": chunk_content,
                    "order": i,
                    "metadata": {
                        "chunk_size": len(chunk_content),
                        "source_document": str(document_id),
                        "processing_method": "llamaindex"
                    },
                    "relations": []  # Will be filled by knowledge extraction
                }

                chunks.append(chunk_data)

            # If still only one chunk, force split by character count
            if len(chunks) == 1 and text_length > self.chunk_size * 2:
                logger.warning(f"LlamaIndex only created 1 chunk for {text_length} chars, force splitting")
                chunks = self._force_split_text(text, document_id, metadata)

            logger.info(f"Successfully chunked document {document_id} into {len(chunks)} chunks")
            return chunks

        except Exception as e:
            logger.error(f"Failed to chunk text: {e}")
            raise Exception(f"Text chunking failed: {e}")

    def _force_split_text(self, text: str, document_id: UUID, metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Force split text by character count when LlamaIndex fails"""
        chunks = []
        text_length = len(text)
        chunk_size = self.chunk_size
        overlap = self.chunk_overlap

        start = 0
        chunk_order = 0

        while start < text_length:
            end = min(start + chunk_size, text_length)

            # Try to find a good break point (sentence end)
            if end < text_length:
                # Look for sentence endings within the last 100 chars
                search_start = max(start + chunk_size - 100, start)
                sentence_end = text.rfind('.', search_start, end)
                if sentence_end != -1:
                    end = sentence_end + 1

            chunk_content = text[start:end]
            if chunk_content.strip():  # Only add non-empty chunks
                chunk_id = uuid4()
                chunk_data = {
                    "chunk_id": chunk_id,
                    "document_id": document_id,
                    "content": chunk_content,
                    "order": chunk_order,
                    "metadata": {
                        "chunk_size": len(chunk_content),
                        "source_document": str(document_id),
                        "processing_method": "force_split"
                    },
                    "relations": []
                }
                chunks.append(chunk_data)
                chunk_order += 1

            # Move start position with overlap
            start = end - overlap if overlap > 0 else end

        logger.info(f"Force split created {len(chunks)} chunks")
        return chunks

    def chunk_vlm_output(self,
                        vlm_output,
                        metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Chunk VLM processed output, preserving visual information

        Args:
            vlm_output: VLMOutput from vision processing
            metadata: Additional metadata

        Returns:
            List of enriched chunks with visual context
        """
        try:
            chunks = []

            if hasattr(vlm_output, 'ocr_text') and vlm_output.ocr_text:
                # Use main OCR text for chunking
                text = vlm_output.ocr_text.strip()
                if len(text) > 0:
                    logger.info(f"Chunking VLM output text of length {len(text)} with chunk_size={self.chunk_size}")

                    text_chunks = self.chunk_text(
                        text=text,
                        document_id=UUID(vlm_output.file_id) if isinstance(vlm_output.file_id, str) else vlm_output.file_id,
                        metadata={"vlm_processed": True, **(metadata or {})}
                    )
                    chunks.extend(text_chunks)
                    logger.info(f"Created {len(text_chunks)} text chunks from VLM output")
                else:
                    logger.warning("VLM output has empty ocr_text")

            # Add visual regions as separate chunks if enabled and informative
            if self.include_visual_chunks and hasattr(vlm_output, 'regions'):
                visual_chunks_created = 0
                for region in vlm_output.regions:
                    if region.confidence > 0.8 and len(region.description) > 100:
                        # Create additional chunk for significant visual regions
                        chunk_id = uuid4()
                        chunk_data = {
                            "chunk_id": chunk_id,
                            "document_id": UUID(vlm_output.file_id) if isinstance(vlm_output.file_id, str) else vlm_output.file_id,
                            "content": f"Visual region ({region.modality}): {region.description}",
                            "order": -1,  # Special order for visual chunks
                            "metadata": {
                                "chunk_size": len(region.description),
                                "source_document": vlm_output.file_id,
                                "processing_method": "vlm_visual",
                                "region_id": region.region_id,
                                "bbox": region.bbox,
                                "confidence": region.confidence
                            },
                            "relations": []
                        }
                        chunks.append(chunk_data)
                        visual_chunks_created += 1

                if visual_chunks_created > 0:
                    logger.info(f"Created {visual_chunks_created} visual chunks from VLM regions")

            logger.info(f"Successfully chunked VLM output into {len(chunks)} total chunks")
            return chunks

        except Exception as e:
            logger.error(f"Failed to chunk VLM output: {e}")
            raise Exception(f"VLM output chunking failed: {e}")

    def _choose_splitter(self, text: str):
        """Choose appropriate splitter based on text characteristics"""
        # Simple heuristic - can be enhanced
        if "```" in text or "##" in text:
            # Looks like markdown
            return self._markdown_splitter
        elif len(text.split()) > 1000:
            # Long document, use hierarchical
            return self._hierarchical_splitter
        else:
            # Standard text, use sentence splitter
            return self._sentence_splitter

    def get_chunk_statistics(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get statistics about chunked content

        Args:
            chunks: List of chunk dictionaries

        Returns:
            Statistics dictionary
        """
        if not chunks:
            return {"total_chunks": 0}

        sizes = [len(chunk["content"]) for chunk in chunks]

        return {
            "total_chunks": len(chunks),
            "avg_chunk_size": sum(sizes) / len(sizes),
            "min_chunk_size": min(sizes),
            "max_chunk_size": max(sizes),
            "total_characters": sum(sizes)
        }
