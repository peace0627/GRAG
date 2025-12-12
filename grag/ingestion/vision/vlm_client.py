"""OpenAI-compatible Vision Language Model client

Supports OpenAI GPT-4V and Ollama-based vision models
"""

import base64
import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from uuid import uuid4

import requests

from grag.core.config import settings
from grag.core.constants import DEFAULT_TIMEOUT, MAX_TOKENS, DEFAULT_TEMPERATURE
from .vlm_schemas import VLMOutput, VLMRegion, TableData, ChartData

logger = logging.getLogger(__name__)


class VLMClient:
    """OpenAI-compatible VLM client for document analysis"""

    def __init__(self, api_type: str = "openai", base_url: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize VLM client

        Args:
            api_type: "openai" or "ollama"
            base_url: API base URL (defaults to settings)
            api_key: API key (defaults to settings)
        """
        self.api_type = api_type

        if api_type == "openai":
            self.base_url = base_url or settings.qwen2vl_base_url or "https://api.openai.com/v1"
            self.api_key = api_key or settings.openai_api_key
            self.model = "gpt-4o"  # GPT-4V capable model for OpenAI
        elif api_type == "ollama":
            self.base_url = base_url or "http://localhost:11434/v1"
            self.api_key = api_key or "ollama"
            self.model = settings.ollama_model  # Updated: uses qwen3-vl:235b-cloud
        else:
            raise ValueError(f"Unsupported API type: {api_type}")

    def process_image(self, image_path: Path, prompt: str = "") -> Dict[str, Any]:
        """
        Process a single image with VLM

        Args:
            image_path: Path to image file
            prompt: Custom prompt for analysis

        Returns:
            VLM response as dict
        """
        try:
            # Encode image to base64
            base64_image = self._encode_image_to_base64(image_path)

            # Create default prompt if not provided
            if not prompt:
                prompt = """
                請詳細分析這張圖片。描述你看到的內容，包括：
                1. 主要對象和元素
                2. 布局和結構
                3. 任何可識別的圖表、表格或數據
                4. 文字內容和標籤

                請用JSON格式輸出，包含以下字段：
                {
                    "description": "詳細描述",
                    "regions": [{"text": "...", "bbox": [x,y,w,h]}],
                    "tables": [{"headers": [...], "rows": [...]}],
                    "charts": [{"type": "...", "description": "..."}]
                }
                """

            # Send to VLM
            response = self._call_vision_api(prompt, base64_image)

            return response

        except Exception as e:
            logger.error(f"VLM image processing failed: {e}")
            raise Exception(f"VLM processing error: {e}")

    def process_document(self, file_path: Path, file_id: str, area_id: Optional[str] = None) -> VLMOutput:
        """
        Process a document file (converts to images if needed)

        Args:
            file_path: Path to document file
            file_id: Unique file identifier
            area_id: Knowledge area ID

        Returns:
            VLMOutput with structured results
        """
        import time
        start_time = time.time()

        try:
            suffix = file_path.suffix.lower()

            if suffix in ['.png', '.jpg', '.jpeg', '.bmp', '.tiff']:
                # Process single image
                result = self.process_image(file_path)
                output = self._parse_vlm_response(result, file_id, area_id)

            elif suffix == '.pdf':
                # Convert PDF first page to image and process
                result = self._process_pdf_as_image(file_path)
                output = self._parse_vlm_response(result, file_id, area_id)
                output.metadata["pdf_converted"] = True
                output.metadata["converted_pages"] = 1

            else:
                # For other document formats, try fallback processing
                logger.warning(f"VLM document processing not supported for {suffix}, trying OCR fallback")
                # This should be handled by VLMService fallback, but we'll raise here
                raise Exception(f"Document format {suffix} not directly supported by VLM")

            output.processing_time = time.time() - start_time
            output.metadata["vlm_model"] = self.model
            output.metadata["vlm_provider"] = self.api_type

            return output

        except Exception as e:
            logger.error(f"VLM document processing failed: {e}")
            raise Exception(f"VLM document processing failed: {e}")

    def _call_vision_api(self, prompt: str, base64_image: str) -> Dict[str, Any]:
        """Call the vision language model API"""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": MAX_TOKENS,
            "temperature": DEFAULT_TEMPERATURE  # More deterministic for document analysis
        }

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=DEFAULT_TIMEOUT  # Use centralized timeout constant
            )

            if response.status_code != 200:
                raise Exception(f"API error {response.status_code}: {response.text}")

            result = response.json()

            # Extract the content from the response
            content = result["choices"][0]["message"]["content"]
            logger.info("VLM API response received successfully")

            return {"content": content, "raw_response": result}

        except requests.exceptions.RequestException as e:
            logger.error(f"VLM API request failed: {e}")
            raise Exception(f"VLM API request failed: {e}")

    def _encode_image_to_base64(self, image_path: Path) -> str:
        """Convert image to base64 string"""
        try:
            with open(image_path, "rb") as image_file:
                encoded = base64.b64encode(image_file.read()).decode('utf-8')
            logger.info(f"Image encoded to base64: {image_path.name}")
            return encoded
        except Exception as e:
            logger.error(f"Failed to encode image {image_path}: {e}")
            raise Exception(f"Image encoding failed: {e}")

    def _process_pdf_as_image(self, pdf_path: Path) -> Dict[str, Any]:
        """Convert PDF first page to image and process with REAL VLM API"""
        import tempfile
        import logging

        try:
            logger.info(f"Converting PDF to image for VLM processing: {pdf_path.name}")

            # Convert PDF first page to image using pdf2image
            from pdf2image import convert_from_path

            # Get total pages first
            total_pages = len(convert_from_path(pdf_path, first_page=1, last_page=1))
            max_pages = min(3, total_pages)  # Limit to 3 pages max for efficiency

            # Convert first few pages for better content extraction
            images = convert_from_path(pdf_path, first_page=1, last_page=max_pages, dpi=150)

            if not images:
                raise Exception("Failed to convert PDF to image")

            first_page_image = images[0]

            # Save image to temporary file for base64 encoding
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_image:
                temp_image_path = Path(temp_image.name)
                first_page_image.save(temp_image_path, 'PNG')

            try:
                # Encode image to base64
                base64_image = self._encode_image_to_base64(temp_image_path)

                # Create VLM analysis prompt for document processing
                prompt = """
                請詳細分析這份文檔圖像。請提供以下信息：
                1. 文檔的整體內容和主題
                2. 主要文字內容和結構
                3. 任何表格、圖表或數據
                4. 重要的可視元素和佈局
                5. 文檔類型和目的

                請用JSON格式輸出，包含以下字段：
                {
                    "description": "文檔整體描述",
                    "document_type": "文檔類型",
                    "main_content": "主要內容摘要",
                    "regions": [{"text": "區域文字", "bbox": [x,y,w,h], "type": "text/table/chart"}],
                    "tables": [{"headers": [...], "rows": [...], "description": "..."}],
                    "charts": [{"type": "bar/line/pie", "description": "...", "data_points": [...]}],
                    "key_findings": ["重要發現1", "重要發現2"],
                    "visual_elements": ["圖表", "表格", "圖像"]
                }
                """

                # Call REAL VLM API through Ollama
                logger.info(f"Sending PDF page to VLM API (Ollama {self.model})")
                vlm_response = self._call_vision_api(prompt, base64_image)

                logger.info(f"Successfully processed PDF {pdf_path.name} with REAL VLM API")
                return vlm_response

            finally:
                # Clean up temporary image file
                temp_image_path.unlink(missing_ok=True)

        except Exception as e:
            error_msg = f"PDF to VLM processing failed: {e}"
            logger.error(error_msg)

            # Fallback: try basic text extraction + mock VLM response
            try:
                logger.info("Attempting fallback text extraction for PDF")
                import pdfplumber

                with pdfplumber.open(pdf_path) as pdf:
                    if len(pdf.pages) > 0:
                        first_page = pdf.pages[0]
                        page_text = first_page.extract_text() or ""
                        page_text = page_text.strip()[:2000]  # Limit text length

                        # Create fallback VLM response with extracted text
                        # Use actual extracted text as description, not fixed fallback message
                        actual_description = page_text[:500] + "..." if len(page_text) > 500 else page_text
                        if not actual_description.strip():
                            actual_description = f"PDF Document ({pdf_path.name}) - No readable text found"

                        fallback_response = {
                            "content": json.dumps({
                                "description": actual_description,
                                "document_type": "PDF Document",
                                "main_content": page_text[:1000] + "..." if len(page_text) > 1000 else page_text,
                                "regions": [{
                                    "text": page_text[:500] + "..." if len(page_text) > 500 else page_text,
                                    "bbox": [10, 10, 780, 580],
                                    "type": "text",
                                    "confidence": 0.7
                                }] if page_text else [],
                                "tables": [],
                                "charts": [],
                                "key_findings": [f"Text extracted from PDF using fallback method ({len(page_text)} chars)"],
                                "visual_elements": ["text"],
                                "processing_method": "pdfplumber_fallback"
                            }, ensure_ascii=False)
                        }

                        logger.info(f"Fallback text extraction successful for {pdf_path.name}")
                        return fallback_response

            except Exception as fallback_error:
                logger.error(f"Fallback text extraction also failed: {fallback_error}")

            # Final fallback - minimal response
            minimal_response = {
                "content": json.dumps({
                    "description": f"PDF {pdf_path.name} - VLM processing failed completely",
                    "document_type": "PDF Document",
                    "main_content": f"Unable to process PDF content due to: {str(e)}",
                    "regions": [],
                    "tables": [],
                    "charts": [],
                    "key_findings": ["Processing failed"],
                    "visual_elements": []
                })
            }

            return minimal_response

    def _parse_vlm_response(self, vlm_response: Dict[str, Any], file_id: str, area_id: Optional[str] = None) -> VLMOutput:
        """Parse VLM response into structured VLMOutput"""

        content = vlm_response.get("content", "")

        # Try to parse JSON response
        try:
            parsed_data = json.loads(content)
        except json.JSONDecodeError:
            # If not JSON, create basic text description
            parsed_data = {
                "description": content,
                "regions": [{"text": content[:200], "bbox": [0, 0, 100, 100]}],
                "tables": [],
                "charts": []
            }

        # Extract OCR text
        ocr_text = parsed_data.get("description", "")

        # Convert regions
        regions = []
        for region_data in parsed_data.get("regions", []):
            region = VLMRegion(
                region_id=str(uuid4()),
                modality="text",
                description=region_data.get("text", ""),
                bbox=region_data.get("bbox", [0, 0, 100, 100]),
                confidence=region_data.get("confidence", 0.8),
                page=region_data.get("page", 1)
            )
            regions.append(region)

        # Convert tables
        tables = []
        for table_data in parsed_data.get("tables", []):
            table = TableData(
                table_id=str(uuid4()),
                csv_content=json.dumps({
                    "headers": table_data.get("headers", []),
                    "rows": table_data.get("rows", [])
                }),
                bbox=[0, 0, 100, 100],  # Default bbox
                page=1  # Default page
            )
            tables.append(table)

        # Convert charts
        charts = []
        for chart_data in parsed_data.get("charts", []):
            chart = ChartData(
                chart_id=str(uuid4()),
                chart_type=chart_data.get("type", "unknown"),
                description=chart_data.get("description", ""),
                bbox=[0, 0, 100, 100],
                page=1
            )
            charts.append(chart)

        return VLMOutput(
            file_id=file_id,
            area_id=area_id,
            ocr_text=ocr_text,
            regions=regions,
            tables=tables,
            charts=charts,
            visual_facts=parsed_data.get("visual_facts", []),
            metadata={
                "vlm_parsed": True,
                "vlm_response_type": "structured" if parsed_data != content else "text"
            }
        )

    def is_available(self) -> bool:
        """Check if the VLM service is available"""
        try:
            if self.api_type == "ollama":
                # For Ollama, check /api/tags endpoint
                response = requests.get(f"{self.base_url.replace('/v1', '')}/api/tags", timeout=5)
                return response.status_code == 200
            elif self.api_type == "openai":
                # For OpenAI compatible services, try chat completions with a simple test
                payload = {
                    "model": self.model,
                    "messages": [{"role": "user", "content": "test"}],
                    "max_tokens": 1
                }
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload,
                    timeout=5
                )
                return response.status_code == 200
            else:
                # Fallback to basic health check
                response = requests.get(f"{self.base_url}/health", timeout=5)
                return response.status_code == 200
        except Exception as e:
            logger.debug(f"VLM service availability check failed: {e}")
            return False
