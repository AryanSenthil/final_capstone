# Testing Module

This module provides the essential infrastructure for evaluating trained machine learning models, primarily through running inference on new data and systematically logging the results. It's the critical link between a deployed model and understanding its real-world performance.

## Overview

The `testing` module facilitates the process of taking raw sensor data, preparing it for a model, getting predictions, and meticulously recording every aspect of that inference run. This robust logging capability enables:

*   **Performance Tracking**: Monitor how models perform over time and on different data subsets.
*   **Reproducibility**: Trace any prediction back to the exact input data, model, and configuration used.
*   **Auditing and Compliance**: Maintain a historical record of all model evaluations.
*   **Debugging**: Analyze inference failures or unexpected model behaviors.

## Key Components

### `inference.py`

This script is the main pipeline for running predictions. It handles the entire flow from raw CSV data to model output:

1.  **Flexible Data Preparation**:
    *   **CSV Structure Detection**: Can intelligently auto-detect the structure of input CSV files using an LLM, making it adaptable to various data formats.
    *   **Preprocessing**: Converts raw time-series data into the standardized waveform tensors required by the ML models. This involves interpolation, chunking, padding, and resampling, mirroring the process used during training.
2.  **Model Loading and Prediction**:
    *   Loads `SavedModel` formats of trained models (typically from the `models` directory) optimized for serving.
    *   Executes the model to generate class predictions, probabilities, and class IDs for each data chunk.
3.  **High-Level API**: Offers `predict_from_csv` for single-file inference and `predict_batch` for processing multiple files efficiently.
4.  **Integration with `test_database`**: Seamlessly logs comprehensive details of each inference run to the `test_database`, creating a permanent record.

### `test_database.py`

This script implements a persistent, file-system-based database specifically for storing the results and artifacts of inference tests.

Key aspects of `test_database.py`:

*   **Structured Storage**: Organizes test data within a `test_database/` directory, which contains:
    *   `raw_csvs/`: Copies of original CSV input files.
    *   `processed_chunks/`: Optional storage for the processed waveform data fed to the model (useful for detailed re-analysis).
    *   `metadata/`: Detailed JSON files containing all metadata for each test.
    *   `index.json`: A master index for quick lookup and summarization of all tests.
*   **Comprehensive Metadata (`TestMetadata`)**: Stores a rich set of information for each test, including:
    *   Test identifiers and timestamps.
    *   Paths to original and stored data.
    *   Details of the model used (name, version).
    *   Detailed `ProcessingMetadata` from the data preparation pipeline.
    *   Full inference results (per-chunk predictions, probabilities, majority class).
    *   User-defined notes and tags for categorization.
*   **Management API**: Provides a `TestDatabase` class with methods for:
    *   Logging new tests (`log_test`).
    *   Retrieving specific test results (`get_test`).
    *   Listing and filtering tests (`list_tests`).
    *   Deleting tests and their associated data (`delete_test`).
    *   Providing summary statistics of the entire test database (`get_stats`).

### Supporting Files

*   `configs.py`: Contains configurable parameters specific to the testing process, such as flags for auto-detection or saving processed chunks.
*   `constants.py`: Defines immutable constants like paths to the test database directories.
*   `utils.py`: Provides helper functions that support the data processing and logging operations within the module.
*   `example_database_usage.py`: Demonstrates how to interact with the test database.

## How It's Used

The `testing` module is typically invoked when a user wants to evaluate a model's performance on new, unseen data. The `agent` module often orchestrates this by calling `predict_from_csv` or `predict_batch` and ensuring that `log_to_database=True` is set, thereby creating a permanent record of the inference result within the `test_database`. This makes the `testing` module indispensable for continuous validation and monitoring of the deployed machine learning models.
