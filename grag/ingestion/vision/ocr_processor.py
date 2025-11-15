"""OCR processing using pdfplumber and pytesseract"""

import logging
from pathlib import Path
from typing import List, Optional, Tuple
import time
import io
import csv

import pdfplumber
from PIL import Image
import pytesseract

from .vlm_schemas import TableData, VLMOutput, VLMRegion, ChartData

logger = logging.getLogger(__name__)


class OCRProcessor:
    """OCR processing for documents and images"""

    def __init__(self, tesseract_config: str = '--oem 3 --psm 6'):
        self.tesseract_config = tesseract_config

    def process_file(self, file_path: Path, file_id: str, area_id: Optional[str] = None) -> VLMOutput:
        """Process a file and extract OCR content, tables, and basic structure"""
        start_time = time.time()

        if file_path.suffix.lower() == '.pdf':
            result = self._process_pdf(file_path)
        elif file_path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.bmp', '.tiff']:
            result = self._process_image(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_path.suffix}")

        processing_time = time.time() - start_time

        return VLMOutput(
            file_id=file_id,
            area_id=area_id,
            ocr_text=result['ocr_text'],
            regions=result['regions'],
            tables=result['tables'],
            charts=result['charts'],
            processing_time=processing_time,
            metadata=result['metadata']
        )

    def _process_pdf(self, file_path: Path) -> dict:
        """Process PDF file with pdfplumber for text, tables, and OCR fallback"""
        ocr_text = ""
        regions = []
        tables = []
        charts = []  # Basic OCR won't detect charts
        metadata = {"source": "pdfplumber"}

        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    # Extract text
                    page_text = page.extract_text() or ""
                    ocr_text += page_text

                    # Extract tables
                    page_tables = page.extract_tables()
                    for table_idx, table in enumerate(page_tables):
                        if table:
                            csv_content = self._table_to_csv(table)
                            if csv_content:
                                table_data = TableData(
                                    table_id=f"table_{page_num}_{table_idx}",
                                    csv_content=csv_content,
                                    bbox=page.bbox,
                                    page=page_num
                                )
                                tables.append(table_data)

                    # Create text regions for each page
                    if page_text.strip():
                        region = VLMRegion(
                            region_id=f"page_{page_num}",
                            modality="text",
                            description=f"Page {page_num} text content",
                            bbox=list(page.bbox),
                            page=page_num
                        )
                        regions.append(region)

            # Note: OCR fallback for PDFs not implemented yet due to fitz dependency
            # If needed, implement with proper PDF-to-image conversion

        except Exception as e:
            logger.warning(f"pdfplumber processing failed: {e}")
            metadata["error"] = str(e)

        return {
            "ocr_text": ocr_text,
            "regions": regions,
            "tables": tables,
            "charts": charts,
            "metadata": metadata
        }

    def _process_image(self, file_path: Path) -> dict:
        """Process image file with OCR"""
        try:
            image = Image.open(file_path)
            ocr_text = pytesseract.image_to_string(image, config=self.tesseract_config)

            # Create single text region
            width, height = image.size
            region = VLMRegion(
                region_id="image_1",
                modality="text",
                description="Full image OCR content",
                bbox=[0, 0, width, height],
                page=1
            )

            return {
                "ocr_text": ocr_text,
                "regions": [region],
                "tables": [],
                "charts": [],
                "metadata": {"source": "tesseract", "image_size": [width, height]}
            }

        except Exception as e:
            logger.error(f"Image processing failed: {e}")
            return {
                "ocr_text": "",
                "regions": [],
                "tables": [],
                "charts": [],
                "metadata": {"error": str(e)}
            }


    def _table_to_csv(self, table: List[List[str]]) -> str:
        """Convert table data to CSV format"""
        if not table:
            return ""

        import csv
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerows(table)
        return output.getvalue()

    def extract_tables_from_pdf(self, file_path: Path) -> List[TableData]:
        """Extract tables from PDF specifically"""
        tables = []

        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    page_tables = page.extract_tables()
                    for table_idx, table in enumerate(page_tables):
                        csv_content = self._table_to_csv(table)
                        if csv_content:
                            table_data = TableData(
                                table_id=f"table_{page_num}_{table_idx}",
                                csv_content=csv_content,
                                bbox=list(page.bbox),
                                page=page_num
                            )
                            tables.append(table_data)
        except Exception as e:
            logger.error(f"Table extraction failed: {e}")

        return tables
