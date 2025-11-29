"""
Main configuration for the backend system.
These values can be adjusted between runs or for different experiments.
"""

# =============================================================================
# Database Management Module Configs
# =============================================================================

# Data processing parameters
DB_TIME_INTERVAL = 0.1  # seconds - interpolation time spacing
DB_CHUNK_DURATION = 8.0  # seconds - duration of each data chunk
DB_PADDING_DURATION = 1.0  # seconds - zero-padding on each side

# Interpolation settings
DB_INTERPOLATION_KIND = 'linear'  # scipy interp1d kind
DB_INTERPOLATION_BOUNDS_ERROR = False
DB_INTERPOLATION_FILL_VALUE = 0.0

# Auto-detection settings
DB_AUTO_DETECT_ENABLED = True  # Use GPT-5.1 to detect CSV structure

# Processing options
DB_RECURSIVE_SEARCH = True  # Search for CSV files recursively in subfolders
DB_COPY_RAW_DATA = True  # Copy raw data to raw_database/
DB_GENERATE_METADATA = True  # Generate metadata.json files
DB_APPEND_MODE = True  # Append to existing data (True) or overwrite (False)

# =============================================================================
# Training Module Configs
# =============================================================================

# CNN Training
CNN_EPOCHS = 1000
CNN_LEARNING_RATE = 1e-3
CNN_PATIENCE = 15
CNN_REDUCE_LR_PATIENCE = 5
CNN_REDUCE_LR_FACTOR = 0.5
CNN_MIN_LR = 1e-6
CNN_DROPOUT_CONV = 0.25
CNN_DROPOUT_DENSE = 0.5
CNN_RESIZE_SHAPE = (32, 32)
CNN_CONV1_FILTERS = 32
CNN_CONV2_FILTERS = 64
CNN_DENSE_UNITS = 128

# ResNet Training
RESNET_EPOCHS = 1000
RESNET_LEARNING_RATE = 1e-4
RESNET_PATIENCE = 20
RESNET_REDUCE_LR_PATIENCE = 7
RESNET_REDUCE_LR_FACTOR = 0.5
RESNET_MIN_LR = 1e-6
RESNET_DROPOUT = 0.6
RESNET_L2_REG = 0.01
RESNET_INITIAL_FILTERS = 16
RESNET_INITIAL_KERNEL = 5
RESNET_INITIAL_STRIDE = 2
RESNET_BLOCK_FILTERS = (16, 32, 32, 64)
RESNET_DOWNSAMPLE_BLOCKS = (False, True, False, True)