"""Application constants and configuration values"""

# VLM Processing Configuration
DEFAULT_TIMEOUT = 120  # API request timeout in seconds
MAX_TOKENS = 4096  # Default max tokens for VLM requests
DEFAULT_TEMPERATURE = 0.1  # Low temperature for deterministic output

# Chunking Configuration
DEFAULT_CHUNK_SIZE = 1000
OVERLAP_SIZE = 200

# Quality Levels
QUALITY_LEVELS = ["high", "medium", "low", "unknown"]

# supported file extensions
SUPPORTED_EXTENSIONS = {
    "pdf": "pdf",
    "word": "docx",
    "text": "txt",
    "markdown": "md",
    "images": ["png", "jpg", "jpeg", "bmp", "tiff"]
}

# Processing Layer Names
PROCESSING_LAYERS = {
    "VLM": "Vision Language Model",
    "MINERU": "MinerU PDF Parser",
    "OCR": "Tesseract OCR",
    "FALLBACK_TEXT_PROCESSING": "Text Processing Fallback"
}

# API Error Messages (in English for consistency)
ERROR_MESSAGES = {
    "vlm_connection": "VLM service connection failed",
    "pdf_processing": "PDF processing error",
    "database_connection": "Database connection failed",
    "file_not_found": "File not found or inaccessible",
    "unsupported_format": "File format not supported",
    "processing_timeout": "Processing timeout exceeded"
}

# Default Quality Scores
DEFAULT_ENTITY_CONFIDENCE = 0.5
DEFAULT_RELATION_CONFIDENCE = 0.7
MIN_ENTITY_CONFIDENCE = 0.1

# Progress Update Intervals (for GUI)
PROGRESS_UPDATE_INTERVAL = 0.1  # seconds

# Supabase Vector Dimensions
VECTOR_DIMENSIONS = {
    "sentence_transformers": 384,
    "openai": 1536,  # ada-002
    "cohere": 1024
}

# Knowledge Extraction Limits
MAX_ENTITIES_PER_CHUNK = 50
MAX_RELATIONS_PER_CHUNK = 20

# Cache Configuration
CACHE_ENABLED = True
CACHE_TTL_SECONDS = 3600  # 1 hour
