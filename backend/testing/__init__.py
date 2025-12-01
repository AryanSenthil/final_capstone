"""
testing — Inference module for sensor data classification.

Processes raw CSV files and returns model predictions without requiring labels.
Self-contained module with no dependencies on other project modules.

Usage:
    from testing import predict_from_csv
    
    # Single file inference
    result = predict_from_csv(
        csv_path="sensor_data.csv",
        model_path="path/to/model_serving"
    )
    print(result.summary())
    
    # Batch inference
    from testing import predict_batch
    results = predict_batch(
        csv_paths=["file1.csv", "file2.csv"],
        model_path="path/to/model_serving"
    )
    
    # Test processing only (no model needed)
    from testing import test_processing
    waveform, metadata = test_processing("sensor_data.csv")

Requirements:
    - OpenAI API key in .env file (for auto CSV structure detection)
    - Trained serving model from training module
"""

from .constants import (
    DB_TIME_INTERVAL,
    DB_CHUNK_DURATION,
    DB_PADDING_DURATION,
    SAMPLING_RATE,
    AUDIO_LENGTH,
    TOTAL_DURATION,
    FRAME_LENGTH,
    FRAME_STEP
)

from .configs import (
    InferenceConfig,
    CSVStructure,
    ProcessingMetadata,
    InferenceResult
)

from .utils import (
    detect_csv_structure,
    get_default_csv_structure,
    read_raw_csv,
    interpolate_raw_data,
    split_into_chunks,
    interpolate_chunk_to_1600hz,
    normalize_data,
    to_waveform_tensor,
    process_chunks
)

from .inference import (
    process_csv_for_inference,
    load_serving_model,
    predict,
    predict_from_csv,
    predict_batch,
    test_processing
)

from .test_database import (
    TestDatabase,
    TestDatabaseConfig,
    TestMetadata,
    log_test,
    get_default_database
)


__all__ = [
    # Constants
    'DB_TIME_INTERVAL',
    'DB_CHUNK_DURATION',
    'DB_PADDING_DURATION',
    'SAMPLING_RATE',
    'AUDIO_LENGTH',
    'TOTAL_DURATION',
    'FRAME_LENGTH',
    'FRAME_STEP',

    # Config classes
    'InferenceConfig',
    'CSVStructure',
    'ProcessingMetadata',
    'InferenceResult',

    # Utils
    'detect_csv_structure',
    'get_default_csv_structure',
    'read_raw_csv',
    'interpolate_raw_data',
    'split_into_chunks',
    'interpolate_chunk_to_1600hz',
    'normalize_data',
    'to_waveform_tensor',
    'process_chunks',

    # Inference
    'process_csv_for_inference',
    'load_serving_model',
    'predict',
    'predict_from_csv',
    'predict_batch',
    'test_processing',

    # Test Database
    'TestDatabase',
    'TestDatabaseConfig',
    'TestMetadata',
    'log_test',
    'get_default_database',
]