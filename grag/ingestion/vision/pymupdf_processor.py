"""PyMuPDF-based PDF processing for complete content extraction"""

import logging
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
import time
import tempfile
import json

import fitz  # PyMuPDF

from .vlm_schemas import VLMOutput, VLMRegion, TableData, ChartData

logger = logging.getLogger(__name__)


class PyMuPDFProcessor:
    """PyMuPDF-powered document processing for complete PDF content extraction"""

    def __init__(self,
                 extract_tables: bool = True,
                 extract_images: bool = True,
                 preserve_layout: bool = True):
        """
        Initialize PyMuPDF processor

        Args:
            extract_tables: Whether to extract tables
            extract_images: Whether to extract images
            preserve_layout: Whether to preserve text layout
        """
        self.extract_tables = extract_tables
        self.extract_images = extract_images
        self.preserve_layout = preserve_layout

        # Test PyMuPDF availability
        try:
            test_doc = fitz.open()
            test_doc.close()
            logger.info("✅ PyMuPDF processor initialized successfully")
        except Exception as e:
            logger.error(f"❌ PyMuPDF initialization failed: {e}")
            raise Exception(f"PyMuPDF not available: {e}")

    def process_document(self,
                        file_path: Path,
                        file_id: str,
                        area_id: Optional[str] = None) -> VLMOutput:
        """
        Process PDF document using PyMuPDF for complete content extraction

        Args:
            file_path: Path to PDF file
            file_id: Unique file identifier
            area_id: Knowledge area identifier

        Returns:
            VLMOutput: Structured processing results with complete content
        """
        start_time = time.time()

        try:
            logger.info(f"Processing PDF with PyMuPDF: {file_path.name}")

            # Open PDF document
            doc = fitz.open(str(file_path))

            # Extract all text content
            full_text = self._extract_all_text(doc)

            # Extract structured regions
            regions = self._extract_text_regions(doc)

            # Extract tables
            tables = self._extract_tables(doc) if self.extract_tables else []

            # Extract images and charts
            images_and_charts = self._extract_images_and_charts(doc) if self.extract_images else []

            # Close document
            doc.close()

            # Generate visual facts
            visual_facts = self._generate_visual_facts(regions, tables, images_and_charts)

            # Build metadata
            metadata = {
                "processor": "pymupdf",
                "total_pages": len(regions) if regions else 1,
                "text_length": len(full_text),
                "tables_extracted": len(tables),
                "images_extracted": len(images_and_charts),
                "quality_level": "high",
                "processing_method": "complete_extraction"
            }

            processing_time = time.time() - start_time

            logger.info(f"PyMuPDF processing completed for {file_id} in {processing_time:.2f}s")
            logger.info(f"Extracted {len(full_text)} characters, {len(tables)} tables, {len(images_and_charts)} images")

            return VLMOutput(
                file_id=file_id,
                area_id=area_id,
                ocr_text=full_text,
                regions=regions,
                tables=tables,
                charts=images_and_charts,  # Using charts field for images
                visual_facts=visual_facts,
                processing_time=processing_time,
                metadata=metadata
            )

        except Exception as e:
            logger.error(f"PyMuPDF processing failed for {file_id}: {e}")
            processing_time = time.time() - start_time

            # Return basic error output
            return VLMOutput(
                file_id=file_id,
                area_id=area_id,
                processing_time=processing_time,
                metadata={"error": str(e), "processor": "pymupdf"}
            )

    def _extract_all_text(self, doc) -> str:
        """Extract all text from PDF document"""
        full_text = ""

        for page_num in range(len(doc)):
            page = doc[page_num]

            if self.preserve_layout:
                # Preserve text layout using blocks
                text = page.get_text("text", flags=fitz.TEXT_PRESERVE_WHITESPACE)
            else:
                # Simple text extraction
                text = page.get_text("text")

            if text.strip():
                if full_text:  # Add page separator
                    full_text += f"\n\n--- Page {page_num + 1} ---\n\n"
                full_text += text

        return full_text.strip()

    def _extract_text_regions(self, doc) -> List[VLMRegion]:
        """Extract text regions with position information"""
        regions = []

        for page_num in range(len(doc)):
            page = doc[page_num]

            # Get text blocks with position information
            blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]

            for block_idx, block in enumerate(blocks):
                if block["type"] == 0:  # Text block
                    bbox = block["bbox"]
                    text_content = ""

                    # Extract text from lines
                    for line in block["lines"]:
                        line_text = ""
                        for span in line["spans"]:
                            line_text += span["text"]
                        text_content += line_text + " "
                        text_content = text_content.strip()

                    if text_content.strip():
                        region = VLMRegion(
                            region_id=f"page_{page_num + 1}_block_{block_idx}",
                            modality="text",
                            description=text_content[:200] + "..." if len(text_content) > 200 else text_content,
                            bbox=list(bbox),
                            confidence=0.95,
                            page=page_num + 1
                        )
                        regions.append(region)

        return regions

    def _extract_tables(self, doc) -> List[TableData]:
        """Extract tables from PDF document"""
        tables = []

        for page_num in range(len(doc)):
            page = doc[page_num]

            # Find tables on the page
            try:
                # Use PyMuPDF's table finding capabilities
                tabs = page.find_tables()

                for tab_idx, tab in enumerate(tabs):
                    # Convert table to CSV-like format
                    table_data = tab.extract()
                    csv_content = self._table_to_csv(table_data)

                    if csv_content and len(table_data) > 1:  # Ensure it's a real table
                        bbox = tab.bbox  # Get table bounding box

                        table_obj = TableData(
                            table_id=f"table_page_{page_num + 1}_{tab_idx}",
                            csv_content=csv_content,
                            bbox=list(bbox) if bbox else [0, 0, 400, 200],
                            page=page_num + 1
                        )
                        tables.append(table_obj)

            except Exception as e:
                logger.warning(f"Table extraction failed on page {page_num + 1}: {e}")
                continue

        return tables

    def _extract_images_and_charts(self, doc) -> List[ChartData]:
        """Extract images and identify potential charts"""
        images_and_charts = []

        for page_num in range(len(doc)):
            page = doc[page_num]

            # Get all images on the page
            image_list = page.get_images(full=True)

            for img_idx, img in enumerate(image_list):
                try:
                    xref = img[0]
                    base_image = doc.extract_image(xref)

                    if base_image:
                        image_bytes = base_image["image"]
                        image_ext = base_image["ext"]

                        # Save image to temporary file to analyze
                        with tempfile.NamedTemporaryFile(suffix=f'.{image_ext}', delete=False) as temp_img:
                            temp_img.write(image_bytes)
                            temp_img_path = Path(temp_img.name)

                        # Basic image analysis
                        image_info = self._analyze_image(temp_img_path, page_num + 1, img_idx)

                        if image_info:
                            images_and_charts.append(image_info)

                        # Clean up temp file
                        temp_img_path.unlink(missing_ok=True)

                except Exception as e:
                    logger.warning(f"Image extraction failed on page {page_num + 1}, img {img_idx}: {e}")
                    continue

        return images_and_charts

    def _analyze_image(self, image_path: Path, page_num: int, img_idx: int) -> Optional[ChartData]:
        """Analyze extracted image to determine if it's a chart or regular image"""
        try:
            # For now, treat all images as figures/charts
            # In a more advanced implementation, you could use ML to classify images
            chart_data = ChartData(
                chart_id=f"image_page_{page_num}_{img_idx}",
                chart_type="figure",  # Could be enhanced to detect chart types
                description=f"Image/Figure extracted from page {page_num}",
                bbox=[0, 0, 300, 200],  # Placeholder bbox
                page=page_num
            )
            return chart_data

        except Exception as e:
            logger.warning(f"Image analysis failed: {e}")
            return None

    def _table_to_csv(self, table_data: List[List[str]]) -> str:
        """Convert table data to CSV format"""
        if not table_data or len(table_data) < 2:
            return ""

        import csv
        output = []
        for row in table_data:
            # Clean and escape row data
            cleaned_row = []
            for cell in row:
                if cell is None:
                    cell = ""
                cleaned_row.append(str(cell).strip())
            output.append(cleaned_row)

        # Convert to CSV string
        csv_output = []
        for row in output:
            csv_output.append(','.join(f'"{cell}"' for cell in row))
        return '\n'.join(csv_output)

    def _generate_visual_facts(self, regions: List[VLMRegion],
                              tables: List[TableData],
                              images_and_charts: List[ChartData]) -> List[dict]:
        """Generate visual facts from extracted elements"""
        visual_facts = []

        # Facts from text regions
        for region in regions[:10]:  # Limit to first 10 regions to avoid too many facts
            if region.modality == "text" and region.description:
                fact = {
                    "entity": "document_content",
                    "value": region.description[:100] + "..." if len(region.description) > 100 else region.description,
                    "region": region.region_id,
                    "type": "pymupdf_text",
                    "page": region.page
                }
                visual_facts.append(fact)

        # Facts from tables
        for table in tables:
            fact = {
                "entity": "table_detected",
                "value": f"Table with structured data (CSV format)",
                "region": table.table_id,
                "type": "pymupdf_table",
                "page": table.page
            }
            visual_facts.append(fact)

        # Facts from images/charts
        for item in images_and_charts:
            fact = {
                "entity": item.chart_type,
                "value": item.description,
                "region": item.chart_id,
                "type": "pymupdf_image",
                "page": item.page
            }
            visual_facts.append(fact)

        return visual_facts

    def get_document_info(self, file_path: Path) -> Dict[str, Any]:
        """Get basic document information"""
        try:
            doc = fitz.open(str(file_path))
            info = {
                "page_count": len(doc),
                "metadata": doc.metadata,
                "is_encrypted": doc.is_encrypted
            }
            doc.close()
            return info
        except Exception as e:
            logger.error(f"Failed to get document info: {e}")
            return {"error": str(e)}
