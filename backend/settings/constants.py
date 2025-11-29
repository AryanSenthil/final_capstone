"""
Main constants for the backend system.
These values rarely change and define core system parameters.
"""

from pathlib import Path

# Directory structure (relative to backend/)
BACKEND_DIR = Path(__file__).parent.parent  # backend/
DATABASE_DIR = BACKEND_DIR / "database"
RAW_DATABASE_DIR = BACKEND_DIR / "raw_database"
MODELS_DIR = BACKEND_DIR / "models"
REPORTS_DIR = BACKEND_DIR / "reports"

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

# AI/LLM settings
MAX_PREVIEW_ROWS = 10
OPENAI_MODEL = "gpt-5.1"

# Logging
LOG_FORMAT_OK = "[OK]"
LOG_FORMAT_SKIP = "[SKIP]"
LOG_FORMAT_ERROR = "[ERROR]"

# =============================================================================
# Training Module Constants
# =============================================================================

# Training Data Processing
TRAINING_TIME_PERIOD = 10          # seconds - total interpolation window
TRAINING_SAMPLING_RATE = 1600      # Hz - samples per second
TRAINING_INTERPOLATION_KIND = 'linear'
TRAINING_INTERPOLATION_FILL_VALUE = 'extrapolate'
TRAINING_RECURSIVE_SEARCH = True   # Search subdirectories for CSVs

# Spectrogram Parameters
FRAME_LENGTH = 255        # STFT frame length
FRAME_STEP = 128          # STFT frame step (hop length)

# Dataset Splitting
SEED = 42                 # Random seed for reproducibility
VALIDATION_SPLIT = 0.2    # Fraction reserved for val + test
BATCH_SIZE = 1            # Samples per batch