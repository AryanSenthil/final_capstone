# Settings Module

This module centralizes all configuration parameters and invariant constants used throughout the backend system. Its purpose is to provide a single, organized place to manage values that define the system's behavior, making the application easier to configure, maintain, and adapt to different environments or experimental needs.

## Overview

The `settings` module is crucial for promoting good software engineering practices by separating configuration details from core logic. It splits settings into two distinct categories:

1.  **`constants.py`**: For values that are fundamental to the system's operation and are expected to remain fixed or change very rarely (e.g., directory paths, core naming conventions).
2.  **`configs.py`**: For values that are more likely to be adjusted between different runs, experiments, or deployments (e.g., hyperparameters for model training, data processing parameters).

## Key Components

### `constants.py`

This file defines immutable or rarely changing values that are essential for the system's functionality. Examples include:

*   **Directory Structure**: Base paths for the `database`, `raw_database`, `models`, and `reports` directories, ensuring consistent file location across the application.
*   **File Naming Conventions**: Standardized patterns for CSV files, metadata JSON files (`metadata.json`), and processed data chunks.
*   **Default Values**: Fallback values for data parsing (e.g., default CSV column indices) used when automatic detection mechanisms fail.
*   **AI/LLM Configuration**: Specifies the particular OpenAI model (`OPENAI_MODEL`) to be used for LLM-powered features.
*   **Training Parameters**: Fundamental parameters for data preprocessing during training, such as target `TRAINING_TIME_PERIOD`, `TRAINING_SAMPLING_RATE`, and `SPECTROGRAM` settings (`FRAME_LENGTH`, `FRAME_STEP`).
*   **Machine Learning Constants**: Values like `SEED` for reproducibility, `VALIDATION_SPLIT` for dataset partitioning, and `BATCH_SIZE`.

### `configs.py`

This file contains values that are designed to be tunable. These settings typically control the behavior of specific modules and are often modified during development, experimentation, or deployment. Examples include:

*   **Database Management Parameters**:
    *   `DB_TIME_INTERVAL`, `DB_CHUNK_DURATION`, `DB_PADDING_DURATION`: Control the interpolation and chunking of sensor data during ingestion.
    *   `DB_INTERPOLATION_KIND`: Defines the type of interpolation used.
    *   `DB_AUTO_DETECT_ENABLED`: A boolean flag to enable/disable the LLM-based CSV structure auto-detection.
    *   `DB_COPY_RAW_DATA`, `DB_GENERATE_METADATA`, `DB_APPEND_MODE`: Control how raw data is handled and how processed data interacts with existing datasets.
*   **Model Training Hyperparameters**:
    *   `CNN_EPOCHS`, `CNN_LEARNING_RATE`, `CNN_PATIENCE`, `CNN_DROPOUT_CONV`, `CNN_RESIZE_SHAPE`, etc.: Detailed settings for configuring Convolutional Neural Network (CNN) models.
    *   `RESNET_EPOCHS`, `RESNET_LEARNING_RATE`, `RESNET_PATIENCE`, `RESNET_DROPOUT`, `RESNET_L2_REG`, etc.: Detailed settings for configuring Residual Network (ResNet) models.

## How It's Used

Other modules import variables directly from `settings.configs` or `settings.constants` as needed. This ensures that all parts of the application operate with a consistent set of parameters. For example, the `database_management` module uses `DB_TIME_INTERVAL` from `configs.py`, while the `agent` module uses `OPENAI_MODEL` from `constants.py`.
