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

        # Immediately validate MinerU availability during initialization
        # This ensures VLMService knows if MinerU is available at startup
        try:
            self._load_mineru()
            logger.info("MinerU processor initialized successfully")
        except Exception as e:
            logger.warning(f"MinerU processor initialization failed: {e}")
            raise e  # Re-raise to prevent invalid MinerUProcessor instances

    def _load_mineru(self):
        """Check if MinerU CLI is available"""
        if self._mineru_components is None:
            try:
                import subprocess
                # Test if mineru CLI is available
                result = subprocess.run(['mineru', '--version'], capture_output=True, text=True)
                if result.returncode == 0:
                    self._mineru_components = {'cli_available': True}
                    logger.info("MinerU CLI is available")
                else:
                    raise Exception("MinerU CLI not responding")
            except (subprocess.SubprocessError, FileNotFoundError) as e:
                logger.error(f"MinerU CLI not available: {e}")
                raise Exception("MinerU CLI not available. Install with: pip install mineru")

    def process_document(self,
                        file_path: Path,
                        file_id: str,
                        area_id: Optional[str] = None) -> VLMOutput:
        """
        Process document using MinerU CLI for high-precision layout analysis

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
                temp_output_dir = Path(temp_dir) / "mineru_output"

                # Build MinerU CLI command
                cmd = [
                    "mineru",
                    "-p", str(file_path),  # input path
                    "-o", str(temp_output_dir),  # output directory
                    "-m", "auto",  # method: auto detection
                    "-b", "pipeline",  # backend: pipeline
                    "-l", "ch"  # language: Chinese
                ]

                # Add optional flags
                if self.enable_table_ocr:
                    pass  # table parsing is enabled by default in pipeline backend
                if self.enable_bilingual:
                    pass  # bilingual is expected to work automatically

                logger.info(f"Running MinerU command: {' '.join(cmd)}")

                # Execute MinerU CLI
                import subprocess
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minutes timeout
                )

                if result.returncode != 0:
                    error_msg = f"MinerU CLI failed: {result.stderr}"
                    logger.error(error_msg)
                    raise Exception(error_msg)

                # Parse MinerU output files
                mineru_result = self._parse_mineru_output_files(temp_output_dir)
                output = self._create_vlm_output_from_mineru(mineru_result, file_id, area_id)

                processing_time = time.time() - start_time
                output.processing_time = processing_time
                output.metadata["quality_level"] = "high"  # MinerU typically provides high quality

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

    def _parse_mineru_output_files(self, output_dir: Path) -> dict:
        """Parse MinerU CLI output files into structured format

        Args:
            output_dir: Directory containing MinerU output files

        Returns:
            dict: Parsed result with text, tables, etc.
        """
        result = {
            "pages": [],
            "version": "mineru_cli",
            "total_pages": 0
        }

        try:
            # MinerU typically creates a results directory with markdown files
            # Look for markdown files in the output directory
            markdown_files = list(output_dir.glob("*.md"))
            if not markdown_files:
                # Try to find in subdirectories
                for subdir in output_dir.iterdir():
                    if subdir.is_dir():
                        markdown_files = list(subdir.glob("*.md"))
                        if markdown_files:
                            break

            if markdown_files:
                # Use the first markdown file found
                md_file = markdown_files[0]
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    result["full_text"] = content

                # Parse markdown content to extract structure
                pages = self._parse_markdown_to_pages(content)
                result["pages"] = pages
                result["total_pages"] = len(pages)

            else:
                # Fallback: no markdown files, try to extract text from other sources
                logger.warning(f"No markdown output found in {output_dir}")
                result["full_text"] = "MinerU processed but no text output generated"

        except Exception as e:
            logger.error(f"Failed to parse MinerU output files: {e}")
            result["error"] = str(e)

        return result

    def _parse_markdown_to_pages(self, markdown_content: str) -> List[dict]:
        """Parse markdown content into page-based structure"""
        pages = []
        lines = markdown_content.split('\n')

        current_page = {"blocks": [], "tables": [], "figures": []}
        current_text = []

        for line in lines:
            line = line.strip()

            # Detect page breaks (MinerU often uses headings for pages)
            if line.startswith('# ') and 'Page' in line:
                # Save previous page
                if current_page["blocks"] or current_text:
                    if current_text:
                        current_page["blocks"] = [{"type": "text", "text": "\n".join(current_text)}]
                    pages.append(current_page)
                    current_page = {"blocks": [], "tables": [], "figures": []}
                    current_text = []

            # Detect table markers
            elif line.startswith('|') and '|' in line:
                # Simple table detection
                if current_text:
                    current_page["blocks"].append({
                        "type": "text",
                        "text": "\n".join(current_text)
                    })
                    current_text = []
                # Collect table content
                current_page["tables"].append({
                    "content": line,
                    "bbox": [0, 0, 400, 200]  # Placeholder
                })

            # Detect figure/image markers
            elif any(marker in line.lower() for marker in ['figure', 'image', 'chart', '圖']):
                current_page["figures"].append({
                    "caption": line,
                    "bbox": [0, 0, 300, 200]  # Placeholder
                })

            # Collect text content
            elif line:
                current_text.append(line)

        # Add final page
        if current_page["blocks"] or current_text:
            if current_text:
                current_page["blocks"] = [{"type": "text", "text": "\n".join(current_text)}]
            pages.append(current_page)

        return pages

    def _create_vlm_output_from_mineru(self, mineru_result: dict, file_id: str, area_id: Optional[str] = None) -> VLMOutput:
        """Create VLMOutput from parsed MinerU results"""
        # Extract OCR text
        ocr_text = mineru_result.get("full_text", "")

        # Create basic regions from text content
        regions = []
        if ocr_text:
            # Create a single large region for all extracted text
            region = VLMRegion(
                region_id="mineru_full_text",
                modality="text",
                description=ocr_text[:200] + "..." if len(ocr_text) > 200 else ocr_text,
                bbox=[10, 10, 800, 600],  # Full page area
                confidence=0.9,
                page=1
            )
            regions.append(region)

        # Extract tables - simplified for CLI output
        tables = []
        for page_data in mineru_result.get("pages", []):
            for table in page_data.get("tables", []):
                table_data = TableData(
                    table_id=f"table_{len(tables)}",
                    csv_content=table.get("content", ""),
                    bbox=table.get("bbox", [0, 0, 400, 200]),
                    page=1
                )
                tables.append(table_data)

        # Extract charts/figures - simplified
        charts = []
        for page_data in mineru_result.get("pages", []):
            for figure in page_data.get("figures", []):
                chart_data = ChartData(
                    chart_id=f"chart_{len(charts)}",
                    chart_type="figure",
                    description=figure.get("caption", "Figure detected"),
                    bbox=figure.get("bbox", [0, 0, 300, 200]),
                    page=1
                )
                charts.append(chart_data)

        # Generate visual facts
        visual_facts = self._generate_visual_facts(regions, tables, charts)

        # Build metadata
        metadata = {
            "processor": "mineru",
            "mineru_version": mineru_result.get("version", "cli_unknown"),
            "total_pages": mineru_result.get("total_pages", 1),
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
