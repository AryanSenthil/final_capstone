"""
Main constants for the backend system.
These values rarely change and define core system parameters.
"""

from pathlib import Path

# Directory structure (relative to backend/)
BACKEND_DIR = Path(__file__).parent.parent  # backend/
DATABASE_DIR = BACKEND_DIR / "database"
RAW_DATABASE_DIR = BACKEND_DIR / "raw_database"

# File patterns
CSV_FILE_PATTERN = "*.csv"
METADATA_FILENAME = "metadata.json"

# Chunk file naming
CHUNK_FILENAME_TEMPLATE = "{label}_{counter:04d}.csv"
CHUNK_COUNTER_START = 1

# Data validation
MIN_DATA_POINTS = 2
MIN_CHUNKS_REQUIRED = 0

# CSV structure defaults (used when auto-detection fails)
DEFAULT_TIME_COLUMN = 0
DEFAULT_VALUES_COLUMN = 1
DEFAULT_SKIP_ROWS = 0
DEFAULT_VALUES_LABEL = "Value"

# AI detection
MAX_PREVIEW_ROWS = 10
GPT_MODEL = "gpt-5.1"
GPT_MAX_TOKENS = 500

# Logging
LOG_FORMAT_OK = "[OK]"
LOG_FORMAT_SKIP = "[SKIP]"
LOG_FORMAT_ERROR = "[ERROR]"