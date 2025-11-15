"""Vision Language Model service for multimodal content analysis"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any
import time

from .ocr_processor import OCRProcessor
from .mineru_processor import MinerUProcessor
from .vlm_schemas import VLMOutput, VLMRegion

logger = logging.getLogger(__name__)


class VLMService:
    """Service for vision-language model processing

    Uses MinerU for high-precision PDF processing, OCR as fallback
    """

    def __init__(self, prefer_mineru: bool = True):
        """
        Initialize VLMService

        Args:
            prefer_mineru: Whether to prefer MinerU over OCR for PDF processing
        """
        self.ocr_processor = OCRProcessor()
        self.mineru_processor = MinerUProcessor() if prefer_mineru else None
        self.prefer_mineru = prefer_mineru

    def process_document(self,
                        file_path: Path,
                        file_id: str,
                        area_id: Optional[str] = None) -> VLMOutput:
        """Process a document with vision-language analysis

        Uses MinerU for high-precision PDF processing, OCR as fallback

        Args:
            file_path: Path to the document file
            file_id: Unique identifier for the file
            area_id: Knowledge area identifier (optional)

        Returns:
            VLMOutput: Structured results with OCR text, regions, tables, etc.
        """
        logger.info(f"Processing document: {file_path} with file_id: {file_id}")

        try:
            # Use MinerU for PDF processing if available and preferred
            if self.prefer_mineru and self.mineru_processor and file_path.suffix.lower() == '.pdf':
                try:
                    output = self.mineru_processor.process_document(file_path, file_id, area_id)
                    logger.info(f"MinerU document processing completed for {file_id}")
                except Exception as mineru_error:
                    logger.warning(f"MinerU processing failed, falling back to OCR: {mineru_error}")
                    output = self.ocr_processor.process_file(file_path, file_id, area_id)
            else:
                # Use OCR processor for images or when MinerU is disabled
                output = self.ocr_processor.process_file(file_path, file_id, area_id)

            logger.info(f"Document processing completed for {file_id} in {output.processing_time:.2f}s")
            return output

        except Exception as e:
            logger.error(f"Document processing failed for {file_id}: {e}")
            # Return minimal output on failure
            return VLMOutput(
                file_id=file_id,
                area_id=area_id,
                processing_time=0.0,
                metadata={"error": str(e)}
            )

    def _enhance_with_vlm(self, ocr_output: VLMOutput, file_path: Path) -> VLMOutput:
        """Enhance OCR output with actual VLM processing (placeholder for future)"""
        # Placeholder for future VLM integration
        # This would call actual VLM models like Qwen2VL for:
        # - Better region detection
        # - Chart analysis
        # - Semantic understanding
        # - Visual fact extraction

        logger.info("VLM enhancement not yet implemented - using OCR baseline")

        # For now, add some basic visual facts from regions
        visual_facts = []
        for region in ocr_output.regions:
            if region.modality == "text" and region.description:
                # Simple fact extraction placeholder
                fact = {
                    "entity": "document_content",
                    "value": region.description[:50] + "..." if len(region.description) > 50 else region.description,
                    "region": region.region_id,
                    "type": "text_extraction"
                }
                visual_facts.append(fact)

        enhanced_output = ocr_output.copy()
        enhanced_output.visual_facts = visual_facts

        return enhanced_output

    def process_image(self, image_path: Path, file_id: str) -> VLMOutput:
        """Process a single image with VLM analysis"""
        return self.process_document(image_path, file_id)

    def batch_process(self, file_paths: list[Path], file_ids: list[str]) -> list[VLMOutput]:
        """Batch process multiple documents"""
        results = []
        for file_path, file_id in zip(file_paths, file_ids):
            try:
                result = self.process_document(file_path, file_id)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to process {file_id}: {e}")
                # Add failed result
                results.append(VLMOutput(
                    file_id=file_id,
                    processing_time=0.0,
                    metadata={"error": str(e)}
                ))
        return results

    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        # Placeholder for future statistics tracking
        return {
            "supported_formats": ["pdf", "png", "jpg", "jpeg", "bmp", "tiff"],
            "vlm_enabled": False,
            "fallback_to_ocr": True
        }
