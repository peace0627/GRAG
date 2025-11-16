"""LangChain-based document loader service with fallback strategies"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from uuid import uuid4
from datetime import datetime

from langchain_community.document_loaders import (
    Docx2txtLoader,
    PyPDFLoader,
    TextLoader,
    UnstructuredFileLoader
)
from langchain_core.documents import Document as LangchainDocument

from grag.ingestion.vision.vlm_schemas import VLMOutput, VLMRegion, TableData, ChartData
from grag.core.config import settings

logger = logging.getLogger(__name__)


class LangChainDocumentLoader:
    """LangChain-based document loading with intelligent format handling"""

    def __init__(self):
        self.loaders = {
            # Office documents
            '.docx': Docx2txtLoader,
            '.pdf': PyPDFLoader,
            '.txt': TextLoader,
            '.md': TextLoader,
            # Fallback for all other formats
            'fallback': UnstructuredFileLoader
        }

    async def load_document(self, file_path: Path) -> List[LangchainDocument]:
        """Load document using appropriate LangChain loader"""
        suffix = file_path.suffix.lower()

        try:
            if suffix in self.loaders:
                loader_class = self.loaders[suffix]
                loader = loader_class(str(file_path))
                documents = loader.load()

                # Add metadata
                for doc in documents:
                    doc.metadata.update({
                        "source_file": str(file_path),
                        "file_type": suffix,
                        "loaded_by": "langchain",
                        "loaded_at": datetime.now().isoformat()
                    })

                logger.info(f"Successfully loaded {len(documents)} documents from {file_path.name}")
                return documents

            else:
                # Use fallback loader
                loader = UnstructuredFileLoader(str(file_path))
                documents = loader.load()
                logger.info(f"Used fallback loader for {file_path.name}: {len(documents)} documents")
                return documents

        except Exception as e:
            logger.error(f"Failed to load document {file_path}: {e}")
            raise Exception(f"Document loading failed: {e}")

    def combine_documents(self, documents: List[LangchainDocument]) -> str:
        """Combine multiple LangChain documents into single text"""
        return "\n\n".join([doc.page_content for doc in documents])


class DocumentProcessingStrategy:
    """Determines optimal processing strategy for different document types"""

    def __init__(self):
        self.vlm_first_types = {'.docx', '.pdf'}  # Prefer VLM analysis
        self.direct_processing_types = {'.txt', '.md'}  # Can process directly
        self.image_types = {'.jpg', '.png', '.jpeg', '.tiff', '.bmp'}  # Images need VLM only

    def should_use_vlm_first(self, file_path: Path, use_vlm_override: Optional[bool] = None) -> bool:
        """Determine if document should prefer VLM processing"""
        if use_vlm_override is not None:
            return use_vlm_override

        suffix = file_path.suffix.lower()

        if suffix in self.vlm_first_types:
            return True
        elif suffix in self.direct_processing_types:
            return False
        else:
            # For unknown types, prefer VLM when available
            return True


class StructuredTextFallback:
    """Fallback processor that creates structured analysis from text when VLM fails"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def create_structured_output(self,
                                     langchain_docs: List[LangchainDocument],
                                     file_path: Path,
                                     file_id: str) -> VLMOutput:
        """Create structured VLM-like output from text documents when VLM fails"""

        # Combine all document content
        combined_text = "\n\n".join([doc.page_content for doc in langchain_docs])

        # Analyze document structure
        regions = self._analyze_document_structure(combined_text)
        tables = self._detect_table_content(combined_text)
        charts = []  # Text fallback doesn't detect charts

        # Create VLMOutput with metadata about fallback
        metadata = {
            "processed_by": "structured_text_fallback",
            "original_loader": "langchain",
            "quality_level": "medium",
            "fallback_reason": "vlm_unavailable",
            "capabilities": ["text_structure", "basic_tables"]
        }

        self.logger.info(f"Created structured output for {file_path.name} using text analysis: "
                        f"{len(regions)} regions, {len(tables)} tables")

        return VLMOutput(
            file_id=file_id,
            area_id=None,
            ocr_text=combined_text,
            regions=regions,
            tables=tables,
            charts=charts,
            processing_time=0.0,  # No external API call
            metadata=metadata
        )

    def _analyze_document_structure(self, text: str) -> List[VLMRegion]:
        """Analyze text structure to create regions similar to VLM output"""

        regions = []
        paragraphs = self._split_into_paragraphs(text)

        current_y = 0
        line_height = 20  # Approximate line height in pixels

        for i, paragraph in enumerate(paragraphs):
            if not paragraph.strip():
                continue

            # Determine content type
            content_type = self._classify_paragraph_type(paragraph)

            # Calculate approximate bounding box
            width = min(len(paragraph) * 8, 800)  # Rough character width estimate
            height = max(len(paragraph.split('\n')) * line_height, line_height)

            region = VLMRegion(
                region_id=f"structured_region_{i}",
                modality=content_type,
                description=self._create_region_description(paragraph),
                bbox=[0, current_y, width, current_y + height],
                confidence=0.7,  # Medium confidence for text analysis
                page=1
            )

            regions.append(region)
            current_y += height + 5  # Add some padding

        return regions

    def _detect_table_content(self, text: str) -> List[TableData]:
        """Detect and extract table-like content from text"""

        tables = []

        # Look for markdown tables
        if '|' in text and '\n|' in text:
            table_sections = self._extract_markdown_tables(text)
            for i, table_csv in enumerate(table_sections):
                try:
                    table_data = TableData(
                        table_id=f"markdown_table_{i}",
                        csv_content=table_csv,
                        bbox=[0, 0, 400, 200],  # Placeholder bbox
                        page=1,
                        metadata={"source": "text_analysis", "type": "markdown"}
                    )
                    tables.append(table_data)
                except Exception as e:
                    self.logger.warning(f"Failed to process table {i}: {e}")

        return tables

    def _split_into_paragraphs(self, text: str) -> List[str]:
        """Split text into logical paragraphs"""
        # Split by double newlines or other paragraph markers
        paragraphs = text.split('\n\n')

        # Further split by single newlines if they're clearly separating content
        processed_paragraphs = []
        for para in paragraphs:
            if len(para.strip()) > 100:  # Long paragraph, keep as is
                processed_paragraphs.append(para.strip())
            else:
                # Split into sentences
                sub_paras = [p.strip() for p in para.split('\n') if p.strip()]
                processed_paragraphs.extend(sub_paras)

        return [p for p in processed_paragraphs if p]

    def _classify_paragraph_type(self, paragraph: str) -> str:
        """Classify paragraph content type"""

        # Check for code blocks
        if '```' in paragraph or 'def ' in paragraph or 'import ' in paragraph:
            return "code"

        # Check for lists
        if any(paragraph.startswith(marker) for marker in ['- ', '* ', '• ', '1. ', '2. ']):
            return "list"

        # Check for headers
        if any(paragraph.startswith('#' + ' ' * i) for i in range(7)):
            return "header"

        # Check for table-like content
        if '|' in paragraph and len(paragraph.split('|')) > 3:
            return "table_row"

        # Default to text
        return "text"

    def _create_region_description(self, paragraph: str) -> str:
        """Create a description for the region"""
        # Truncate long paragraphs for the description
        if len(paragraph) > 150:
            return paragraph[:147] + "..."
        return paragraph

    def _extract_markdown_tables(self, text: str) -> List[str]:
        """Extract markdown table content as CSV"""

        import csv
        import io

        tables = []

        # Simple markdown table parser
        lines = text.split('\n')
        current_table = []

        for line in lines:
            line = line.strip()

            if '|' in line and len(line.split('|')) > 2:
                # Looks like a table row
                cells = [cell.strip() for cell in line.split('|')]
                # Remove empty first/last cells if present
                if cells and not cells[0]:
                    cells = cells[1:]
                if cells and not cells[-1]:
                    cells = cells[:-1]

                current_table.append(cells)
            else:
                # End of current table
                if current_table and len(current_table) > 1:  # At least header + 1 row
                    # Convert to CSV
                    output = io.StringIO()
                    writer = csv.writer(output)
                    writer.writerows(current_table)
                    tables.append(output.getvalue())

                current_table = []

        # Handle table at end of text
        if current_table and len(current_table) > 1:
            output = io.StringIO()
            csv.writer(output).writerows(current_table)
            tables.append(output.getvalue())

        return tables
