# Database Management Module

This module is the data engineering engine of the application. It contains the scripts and logic for the entire lifecycle of the sensor data, from initial ingestion and processing to eventual deletion.

## Overview

The primary responsibility of this module is to execute the ETL (Extract, Transform, Load) pipeline that converts raw sensor data into the structured, analysis-ready format used by the `database` module. It's the bridge between messy, real-world data and the clean, standardized datasets required for machine learning.

## Key Components

### `ingest_sensor_data.py`

This is the main script for the data ingestion pipeline. It's a sophisticated process that performs several crucial steps:

1.  **Backup Raw Data**: It first copies the original, untouched data to the `raw_database` directory for archival and reproducibility.
2.  **Auto-Detect Structure**: It leverages a Large Language Model (LLM) to intelligently inspect a sample CSV file and determine its structure (e.g., which columns contain time and value data, how many header rows to skip). This makes the pipeline resilient to minor changes in the input data format.
3.  **Transform and Standardize**: It reads the raw data and applies a series of transformations:
    *   **Chunking**: The continuous time-series data is split into smaller, uniform-sized chunks, which become the individual samples for the ML model.
    *   **Padding**: Zero-padding is added to the beginning and end of each chunk.
    *   **Interpolation**: The data is interpolated to a fixed time interval, ensuring that every sample has the exact same number of data points, a critical requirement for many neural network architectures.
4.  **Load Processed Data**: The transformed data chunks are saved as individual CSV files into a new, labeled directory in the `database` module.
5.  **Generate Metadata**: It creates the detailed `metadata.json` files for both the raw backup and the processed dataset. This metadata captures everything from processing parameters to AI-generated quality scores and training tips.

### `delete_dataset.py`

This script manages the other end of the data lifecycle. It provides a clean way to remove a dataset from the system. It not only deletes the processed data directory from `database` but also attempts to find and remove the corresponding original data from `raw_database`, ensuring that a deletion is complete.

### Supporting Files

*   `configs.py`: Contains configurable parameters for the ingestion pipeline, such as the default time interval, chunk duration, and whether to use the LLM for auto-detection.
*   `constants.py`: Defines fixed constants used throughout the module, such as directory paths and filenames.
*   `utils.py`: Contains helper functions used by the main scripts, such as the function that calls the LLM for CSV structure detection.

## How It's Used

This module is not typically run on its own but is called by the `agent` when the user requests to ingest new data. For example, when a user tells the agent, "ingest data from this folder," the agent calls the `ingest_data` tool, which in turn executes the `ingest_sensor_data.py` script with the appropriate parameters.
