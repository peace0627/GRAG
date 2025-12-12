"""Vision Language Model service for multimodal content analysis"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any
import time

from .ocr_processor import OCRProcessor
from .mineru_processor import MinerUProcessor
from .vlm_client import VLMClient
from .vlm_schemas import VLMOutput, VLMRegion

from grag.core.config import settings

logger = logging.getLogger(__name__)


class VLMService:
    """Service for vision-language model processing

    Processing order: VLM → MinerU → OCR (three-layer fallback)
    """

    def __init__(self, enable_pymupdf: bool = True, enable_vlm: bool = True, enable_mineru: bool = True, enable_ocr: bool = True):
        """
        Initialize VLMService with configurable processing layers

        Processing order: PyMuPDF → VLM → MinerU → OCR

        Args:
            enable_pymupdf: Enable PyMuPDF processing (highest priority for complete extraction)
            enable_vlm: Enable VLM processing (second priority)
            enable_mineru: Enable MinerU processing (third priority)
            enable_ocr: Enable OCR processing (final fallback)
        """
        # Initialize processors (lazy loading)
        self.pymupdf_processor = None  # PyMuPDF for complete extraction
        self.vlm_processor = None  # Placeholder for VLM (Qwen2VL, etc.)
        self.mineru_processor = None
        self.ocr_processor = None

        # Enable flags
        self.enable_pymupdf = enable_pymupdf
        self.enable_vlm = enable_vlm
        self.enable_mineru = enable_mineru
        self.enable_ocr = enable_ocr

        # Lazy load based on enable flags - PyMuPDF first
        if enable_pymupdf:
            try:
                # Lazy import to avoid module loading issues
                from .pymupdf_processor import PyMuPDFProcessor
                logger.info("🔄 Attempting to initialize PyMuPDF processor...")
                self.pymupdf_processor = PyMuPDFProcessor()
                logger.info("✅ PyMuPDF processor initialized successfully")
            except Exception as e:
                logger.error(f"❌ PyMuPDF processor initialization failed: {e}")
                logger.error(f"❌ Full traceback: {e.__class__.__name__}: {e}")
                import traceback
                logger.error(f"❌ Traceback: {traceback.format_exc()}")
                self.pymupdf_processor = None

        if enable_vlm:
            try:
                self.vlm_processor = self._load_vlm_processor()
            except Exception as e:
                logger.warning(f"VLM processor not available: {e}. VLM will be skipped.")

        if enable_mineru:
            try:
                self.mineru_processor = MinerUProcessor()
            except Exception as e:
                logger.warning(f"MinerU processor not available: {e}. MinerU will be skipped.")

        if enable_ocr:
            try:
                self.ocr_processor = OCRProcessor()
            except Exception as e:
                logger.warning(f"OCR processor not available: {e}. OCR will be skipped.")

    def process_document(self,
                        file_path: Path,
                        file_id: str,
                        area_id: Optional[str] = None) -> VLMOutput:
        """Process a document with vision-language analysis

        Processing order: PyMuPDF → VLM → MinerU → OCR (four-layer fallback)

        Args:
            file_path: Path to the document file
            file_id: Unique identifier for the file
            area_id: Knowledge area identifier (optional)

        Returns:
            VLMOutput: Structured results with OCR text, regions, tables, etc.
        """
        start_time = time.time()
        logger.info(f"Processing document: {file_path} with file_id: {file_id}")

        errors = []

        # Layer 1: Try PyMuPDF processing first (highest priority for complete extraction)
        if self.enable_pymupdf and self.pymupdf_processor:
            try:
                logger.info(f"Attempting PyMuPDF processing for {file_id} (complete extraction)")
                output = self.pymupdf_processor.process_document(file_path, file_id, area_id)
                processing_time = time.time() - start_time
                output.processing_time = processing_time
                output.metadata = output.metadata or {}
                output.metadata["processing_layer"] = "PyMuPDF"
                logger.info(f"PyMuPDF processing completed for {file_id} in {processing_time:.2f}s")
                return output
            except Exception as e:
                error_msg = f"PyMuPDF processing failed: {e}"
                logger.warning(error_msg)
                errors.append(error_msg)

        # Layer 2: Try VLM processing (for cases where PyMuPDF isn't suitable)
        if self.enable_vlm and self.vlm_processor:
            try:
                logger.info(f"Falling back to VLM processing for {file_id}")
                output = self.vlm_processor.process_document(file_path, file_id, area_id)
                processing_time = time.time() - start_time
                output.processing_time = processing_time
                output.metadata = output.metadata or {}
                output.metadata["processing_layer"] = "VLM"
                output.metadata["fallback_errors"] = errors
                logger.info(f"VLM processing completed for {file_id} in {processing_time:.2f}s")
                return output
            except Exception as e:
                error_msg = f"VLM processing failed: {e}"
                logger.warning(error_msg)
                errors.append(error_msg)

        # Layer 3: Try MinerU processing
        if self.enable_mineru and self.mineru_processor:
            try:
                logger.info(f"Falling back to MinerU processing for {file_id}")
                output = self.mineru_processor.process_document(file_path, file_id, area_id)
                processing_time = time.time() - start_time
                output.processing_time = processing_time
                output.metadata = output.metadata or {}
                output.metadata["processing_layer"] = "MinerU"
                output.metadata["fallback_errors"] = errors
                logger.info(f"MinerU processing completed for {file_id} in {processing_time:.2f}s")
                return output
            except Exception as e:
                error_msg = f"MinerU processing failed: {e}"
                logger.warning(error_msg)
                errors.append(error_msg)

        # Layer 4: Final fallback to OCR processing
        if self.enable_ocr and self.ocr_processor:
            try:
                logger.info(f"Falling back to OCR processing for {file_id}")
                output = self.ocr_processor.process_file(file_path, file_id, area_id)
                processing_time = time.time() - start_time
                output.processing_time = processing_time
                output.metadata = output.metadata or {}
                output.metadata["processing_layer"] = "OCR"
                output.metadata["fallback_errors"] = errors
                logger.info(f"OCR processing completed for {file_id} in {processing_time:.2f}s")
                return output
            except Exception as e:
                error_msg = f"OCR processing failed: {e}"
                logger.error(error_msg)
                errors.append(error_msg)

        # All processing layers failed - fallback to text processing
        processing_time = time.time() - start_time
        logger.warning(f"All processing layers failed for {file_id}, using fallback text processing")

        # Create minimal output indicating fallback text processing
        fallback_output = VLMOutput(
            file_id=file_id,
            area_id=area_id,
            ocr_text="Fallback text processing - All processing layers unavailable",
            regions=[],
            tables=[],
            charts=[],
            visual_facts=[],
            processing_time=processing_time,
            metadata={
                "fallback_errors": errors,
                "processing_layer": "FALLBACK_TEXT_PROCESSING",
                "quality_level": "basic"
            }
        )
        return fallback_output

    def _load_vlm_processor(self):
        """Load VLM processor using environment configuration

        Priority order: Ollama (if configured) → OpenAI → Qwen2VL

        Returns a VLMClient instance for vision processing
        """
        logger.info("Attempting to load VLM processor from environment config")

        # Priority 1: Ollama (check if specifically configured)
        if hasattr(settings, 'ollama_base_url') and settings.ollama_base_url:
            logger.info("Loading Ollama VLM client (user configured)")
            try:
                client = VLMClient(
                    api_type="ollama",
                    base_url=settings.ollama_base_url,
                    api_key=settings.ollama_api_key
                )
                # Verify the configured service is actually available
                if not client.is_available():
                    raise Exception(f"Configured Ollama service at {settings.ollama_base_url} is not available")
                logger.info(f"Configured Ollama service verified and available at {settings.ollama_base_url}")
                return client
            except Exception as e:
                logger.warning(f"Failed to create/load configured Ollama VLM client: {e}")
                # Fail fast - don't fallback to auto-detection when user explicitly configured
                raise Exception(f"User-configured Ollama service failed: {e}")

        # Priority 2: Ollama (auto-detection if no specific config)
        logger.info("Checking for local Ollama service")
        try:
            ollama_client = VLMClient(
                api_type="ollama",
                base_url=getattr(settings, 'ollama_base_url', "http://localhost:11434/v1"),
                api_key=getattr(settings, 'ollama_api_key', "ollama")
            )
            # Test if Ollama is available
            if ollama_client.is_available():
                logger.info("Local Ollama service detected and available")
                return ollama_client
        except Exception as e:
            logger.warning(f"Local Ollama service not available: {e}")

        # Priority 3: OpenAI API (VLM specific)
        if settings.vlm_openai_api_key:
            logger.info("Loading OpenAI VLM client")
            try:
                return VLMClient(
                    api_type="openai",
                    base_url="https://api.openai.com/v1",
                    api_key=settings.vlm_openai_api_key
                )
            except Exception as e:
                logger.warning(f"Failed to create OpenAI VLM client: {e}")
        elif settings.openai_api_key:
            # Fallback: use LLM API key if VLM specific key not set
            logger.info("Using LLM OpenAI API key for VLM (fallback)")
            try:
                return VLMClient(
                    api_type="openai",
                    base_url="https://api.openai.com/v1",
                    api_key=settings.openai_api_key
                )
            except Exception as e:
                logger.warning(f"Failed to create OpenAI VLM client with fallback key: {e}")

        # Note: Qwen2VL cloud service removed - using local Ollama only
        # for better privacy, cost control, and performance

        # No valid VLM configuration found
        raise Exception("No valid VLM configuration found. Available options:\n"
                       "1. Set OLLAMA_BASE_URL for Ollama service\n"
                       "2. Set OPENAI_API_KEY for OpenAI API\n"
                       "3. Set QWEN2VL_BASE_URL for Qwen2VL service\n"
                       "4. Ensure Ollama is running locally on port 11434")

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
        return {
            "supported_formats": ["pdf", "png", "jpg", "jpeg", "bmp", "tiff"],
            "processing_order": "PyMuPDF → VLM → MinerU → OCR",
            "pymupdf_enabled": self.enable_pymupdf and self.pymupdf_processor is not None,
            "vlm_enabled": self.enable_vlm and self.vlm_processor is not None,
            "mineru_enabled": self.enable_mineru and self.mineru_processor is not None,
            "ocr_enabled": self.enable_ocr and self.ocr_processor is not None,
            "fallback_layers": sum([
                self.enable_pymupdf and self.pymupdf_processor is not None,
                self.enable_vlm and self.vlm_processor is not None,
                self.enable_mineru and self.mineru_processor is not None,
                self.enable_ocr and self.ocr_processor is not None
            ])
        }
