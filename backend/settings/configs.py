"""
Main configuration for the backend system.
These values can be adjusted between runs or for different experiments.
"""

# Data processing parameters
TIME_INTERVAL = 0.1  # seconds - interpolation time spacing
CHUNK_DURATION = 8.0  # seconds - duration of each data chunk
PADDING_DURATION = 1.0  # seconds - zero-padding on each side

# Interpolation settings
INTERPOLATION_KIND = 'linear'  # scipy interp1d kind
INTERPOLATION_BOUNDS_ERROR = False
INTERPOLATION_FILL_VALUE = 0.0

# Auto-detection settings
AUTO_DETECT_ENABLED = True  # Use GPT-5.1 to detect CSV structure

# Processing options
RECURSIVE_SEARCH = True  # Search for CSV files recursively in subfolders
COPY_RAW_DATA = True  # Copy raw data to raw_database/
GENERATE_METADATA = True  # Generate metadata.json files
APPEND_MODE = True  # Append to existing data (True) or overwrite (False)