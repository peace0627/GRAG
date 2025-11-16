"""MinerU-based PDF processing for high-precision document parsing"""

import logging
from pathlib import Path
from typing import List, Optional, Tuple
import time
import tempfile

from .vlm_schemas import VLMOutput, VLMRegion, TableData, ChartData

logger = logging.getLogger(__name__)


class MinerUProcessor:
    """MinerU-powered document processing with advanced layout analysis"""

    def __init__(self,
                 output_format: str = "markdown",
                 enable_table_ocr: bool = True,
                 enable_bilingual: bool = True):
        """
        Initialize MinerU processor

        Args:
            output_format: "markdown" or "json"
            enable_table_ocr: Whether to enable OCR for tables
            enable_bilingual: Whether to enable bilingual processing
        """
        self.output_format = output_format
        self.enable_table_ocr = enable_table_ocr
        self.enable_bilingual = enable_bilingual

        # Import MinerU components (will be lazy loaded)
        self._mineru_components = None

    def _load_mineru(self):
        """Lazy load MinerU components"""
        if self._mineru_components is None:
            try:
                from mineru import MiningPipeline
                self._mineru_components = {
                    'MiningPipeline': MiningPipeline
                }
            except ImportError as e:
                logger.error(f"Failed to load MinerU: {e}")
                raise Exception("MinerU not available. Install with: pip install mineru")

    def process_document(self,
                        file_path: Path,
                        file_id: str,
                        area_id: Optional[str] = None) -> VLMOutput:
        """
        Process document using MinerU for high-precision layout analysis

        Args:
            file_path: Path to PDF file
            file_id: Unique file identifier
            area_id: Knowledge area identifier

        Returns:
            VLMOutput: Structured processing results
        """
        start_time = time.time()

        self._load_mineru()

        try:
            # Create temporary output directory
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_output_dir = Path(temp_dir) / "output"

                # Configure MinerU pipeline
                pipeline = self._mineru_components['MiningPipeline'](
                    output_dir=str(temp_output_dir),
                    layout_preprocess_model="yolo_v8_mfd",
                    do_table_recognition=self.enable_table_ocr,
                    do_formula_recognition=True,
                    do_ocr=True,
                    enable_bilingual=self.enable_bilingual,
                    language="en;ch_sim;ch_tra",
                    persist_result=True
                )

                # Process document
                result = pipeline(str(file_path))

                # Parse results
                output = self._parse_mineru_result(result, file_id, area_id)

                processing_time = time.time() - start_time
                output.processing_time = processing_time

                logger.info(f"MinerU processing completed for {file_id} in {processing_time:.2f}s")
                return output

        except Exception as e:
            logger.error(f"MinerU processing failed for {file_id}: {e}")
            # Return basic error output
            processing_time = time.time() - start_time
            return VLMOutput(
                file_id=file_id,
                area_id=area_id,
                processing_time=processing_time,
                metadata={"error": str(e), "processor": "mineru"}
            )

    def _parse_mineru_result(self, result: dict, file_id: str, area_id: Optional[str] = None) -> VLMOutput:
        """
        Parse MinerU output into our VLMOutput format

        Args:
            result: MinerU processing result
            file_id: File identifier
            area_id: Area identifier

        Returns:
            VLMOutput: Standardized output
        """
        # Extract text content
        ocr_text = self._extract_full_text(result)

        # Extract regions (text blocks, images, etc.)
        regions = self._extract_regions(result)

        # Extract tables
        tables = self._extract_tables(result)

        # Extract charts (MinerU may identify chart-like elements)
        charts = self._extract_charts(result)

        # Generate visual facts
        visual_facts = self._generate_visual_facts(regions, tables, charts)

        # Build metadata
        metadata = {
            "processor": "mineru",
            "mineru_version": result.get("version", "unknown"),
            "total_pages": len(result.get("pages", [])),
            "text_blocks": len(regions),
            "tables": len(tables),
            "charts": len(charts)
        }

        return VLMOutput(
            file_id=file_id,
            area_id=area_id,
            ocr_text=ocr_text,
            regions=regions,
            tables=tables,
            charts=charts,
            visual_facts=visual_facts,
            metadata=metadata
        )

    def _extract_full_text(self, result: dict) -> str:
        """Extract complete text content from MinerU result"""
        full_text = ""

        pages = result.get("pages", [])
        for page in pages:
            for block in page.get("blocks", []):
                if block.get("type") == "text":
                    text = block.get("text", "").strip()
                    if text:
                        full_text += text + "\n"

        return full_text.strip()

    def _extract_regions(self, result: dict) -> List[VLMRegion]:
        """Extract visual regions from MinerU result"""
        regions = []

        pages = result.get("pages", [])
        for page_idx, page in enumerate(pages):
            page_num = page_idx + 1

            for block in page.get("blocks", []):
                region_type = block.get("type", "unknown")

                # Map MinerU types to our modality
                modality_mapping = {
                    "text": "text",
                    "image": "image",
                    "table": "table",
                    "figure": "chart",
                    "formula": "text",  # Math formulas
                    "caption": "text"
                }

                modality = modality_mapping.get(region_type, "unknown")
                bbox = block.get("bbox", [0, 0, 100, 100])

                region = VLMRegion(
                    region_id=f"mineru_page_{page_num}_{len(regions)}",
                    modality=modality,
                    description=block.get("text", "")[:200] if block.get("text") else f"{region_type} region",
                    bbox=bbox,
                    confidence=block.get("confidence", 0.8),
                    page=page_num
                )

                regions.append(region)

        return regions

    def _extract_tables(self, result: dict) -> List[TableData]:
        """Extract table data from MinerU result"""
        tables = []

        pages = result.get("pages", [])
        for page_idx, page in enumerate(pages):
            page_num = page_idx + 1

            for table_idx, table_block in enumerate(page.get("tables", [])):
                # Assume tables come as structured data or HTML/markdown
                table_content = table_block.get("content", "")
                bbox = table_block.get("bbox", [0, 0, 100, 100])

                # If it's markdown format, extract as CSV-like
                csv_content = self._markdown_table_to_csv(table_content) if table_content else ""

                if csv_content or table_content:
                    table_data = TableData(
                        table_id=f"mineru_page_{page_num}_table_{table_idx}",
                        csv_content=csv_content or table_content,
                        bbox=bbox,
                        page=page_num
                    )
                    tables.append(table_data)

        return tables

    def _extract_charts(self, result: dict) -> List[ChartData]:
        """Extract chart/figure data from MinerU result"""
        charts = []

        pages = result.get("pages", [])
        for page_idx, page in enumerate(pages):
            page_num = page_idx + 1

            for figure_idx, figure_block in enumerate(page.get("figures", [])):
                figure_data = figure_block.get("data", {})
                bbox = figure_block.get("bbox", [0, 0, 100, 100])
                description = figure_block.get("caption", "Figure/Chart region")

                # Try to detect chart type from description or visual features
                chart_type = self._detect_chart_type(description)

                chart_data = ChartData(
                    chart_id=f"mineru_page_{page_num}_chart_{figure_idx}",
                    chart_type=chart_type,
                    description=description,
                    data_points=figure_data.get("data_points"),
                    bbox=bbox,
                    page=page_num
                )

                charts.append(chart_data)

        return charts

    def _generate_visual_facts(self, regions: List[VLMRegion],
                              tables: List[TableData],
                              charts: List[ChartData]) -> List[dict]:
        """Generate high-level visual facts from extracted elements"""
        visual_facts = []

        # Facts from regions
        for region in regions:
            if region.modality == "text" and region.description:
                fact = {
                    "entity": "document_content",
                    "value": region.description[:100] + "..." if len(region.description) > 100 else region.description,
                    "region": region.region_id,
                    "type": "mineru_text"
                }
                visual_facts.append(fact)

        # Facts from tables
        for table in tables:
            fact = {
                "entity": "table_detected",
                "value": f"Table with {table.csv_content.count(chr(10))} rows",
                "region": table.table_id,
                "type": "mineru_table"
            }
            visual_facts.append(fact)

        # Facts from charts
        for chart in charts:
            fact = {
                "entity": chart.chart_type,
                "value": chart.description,
                "region": chart.chart_id,
                "type": "mineru_chart"
            }
            visual_facts.append(fact)

        return visual_facts

    def _markdown_table_to_csv(self, markdown_table: str) -> str:
        """Convert markdown table to CSV format (simple implementation)"""
        if not markdown_table.strip():
            return ""

        lines = markdown_table.strip().split('\n')
        csv_rows = []

        # Skip header separator line
        for line in lines:
            if not line.startswith('|') or '---' in line:
                continue

            # Extract cells
            cells = [cell.strip() for cell in line.split('|')[1:-1]]
            csv_rows.append(cells)

        # Convert to CSV string
        import csv
        output = []
        for row in csv_rows:
            output.append(','.join(f'"{cell}"' for cell in row))
        return '\n'.join(output)

    def _detect_chart_type(self, description: str) -> str:
        """Simple chart type detection from description"""
        desc_lower = description.lower()
        if "bar" in desc_lower or "柱狀" in desc_lower:
            return "bar"
        elif "line" in desc_lower or "折線" in desc_lower:
            return "line"
        elif "pie" in desc_lower or "圓餅" in desc_lower:
            return "pie"
        else:
            return "figure"  # Generic figure/chart
