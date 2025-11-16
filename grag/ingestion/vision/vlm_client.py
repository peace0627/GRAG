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

from ..config import settings
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
            self.model = "gpt-4o"  # GPT-4V capable model
        elif api_type == "ollama":
            self.base_url = base_url or "http://localhost:11434/v1"
            self.api_key = api_key or "ollama"
            self.model = "llava"  # Default Ollama vision model
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
            if file_path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.bmp', '.tiff']:
                # Process single image
                result = self.process_image(file_path)
                output = self._parse_vlm_response(result, file_id, area_id)

            else:
                # For PDFs or other documents, we'd need to convert pages to images
                # This is a simplified implementation
                logger.warning(f"VLM direct document processing not implemented for {file_path.suffix}")
                raise Exception("Direct document processing not implemented")

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
            "max_tokens": 4096,
            "temperature": 0.1  # More deterministic for document analysis
        }

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=120  # 2 minutes timeout for vision processing
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
            # Simple health check
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
