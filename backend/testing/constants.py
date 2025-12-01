"""
constants.py — Fixed processing parameters for inference.

These import from the main settings module for consistency.
"""

from settings.constants import (
    BACKEND_DIR,
    OPENAI_MODEL,
    FRAME_LENGTH,
    FRAME_STEP,
    MIN_DATA_POINTS,
    DEFAULT_TIME_COLUMN,
    DEFAULT_VALUES_COLUMN,
    DEFAULT_SKIP_ROWS,
    DEFAULT_VALUES_LABEL,
    MAX_PREVIEW_ROWS,
    TRAINING_SAMPLING_RATE,
)
from settings.configs import (
    DB_TIME_INTERVAL,
    DB_CHUNK_DURATION,
    DB_PADDING_DURATION,
    DB_INTERPOLATION_KIND,
    DB_INTERPOLATION_FILL_VALUE,
    DB_INTERPOLATION_BOUNDS_ERROR,
)

# =============================================================================
# Testing Module Directory Structure
# =============================================================================
TEST_DATABASE_DIR = BACKEND_DIR / "test_database"
TEST_UPLOADS_DIR = BACKEND_DIR / "test_uploads"
TEST_INDEX_FILE = BACKEND_DIR / "test_index.json"

# =============================================================================
# Stage 2: Training-style preprocessing (fine interpolation to 1600 Hz)
# =============================================================================
SAMPLING_RATE = TRAINING_SAMPLING_RATE  # Use same rate as training (1600 Hz)
# Total duration with padding: 8s + 2*1s = 10s
# Audio length: 10s * 1600 Hz = 16000 samples (padding NOT trimmed, matches training)
TOTAL_DURATION = DB_CHUNK_DURATION + 2 * DB_PADDING_DURATION  # 10s
AUDIO_LENGTH = int(TOTAL_DURATION * SAMPLING_RATE)  # 16000 samples per chunk

# =============================================================================
# Interpolation Settings (re-export for convenience)
# =============================================================================
INTERPOLATION_KIND = DB_INTERPOLATION_KIND
INTERPOLATION_FILL_VALUE = DB_INTERPOLATION_FILL_VALUE
INTERPOLATION_BOUNDS_ERROR = DB_INTERPOLATION_BOUNDS_ERROR

# =============================================================================
# GPT Settings (re-export for convenience)
# =============================================================================
GPT_MODEL = OPENAI_MODEL
