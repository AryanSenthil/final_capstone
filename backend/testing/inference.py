"""
inference.py — Main inference pipeline for raw sensor data.

Processes raw CSV files and returns model predictions without requiring labels.
Handles any duration input by splitting into TIME_PERIOD chunks.

Pipeline:
    Raw CSV → GPT structure detection → Chunk splitting → 
    Interpolation → Normalization → Waveform tensor → Model → Predictions

Usage:
    from testing import predict_from_csv
    
    results = predict_from_csv(
        csv_path="sensor_data.csv",
        model_path="path/to/model_serving"
    )
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import tensorflow as tf

from .constants import (
    DB_TIME_INTERVAL,
    DB_CHUNK_DURATION,
    DB_PADDING_DURATION,
    SAMPLING_RATE,
    AUDIO_LENGTH
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
    process_chunks,
    to_waveform_tensor
)


# =============================================================================
# Data Processing Pipeline
# =============================================================================
def process_csv_for_inference(
    csv_path: Union[str, Path],
    config: InferenceConfig = None
) -> Tuple[tf.Tensor, ProcessingMetadata]:
    """
    Process a raw CSV file into waveform tensors ready for model inference.
    
    Args:
        csv_path: Path to raw CSV file
        config: InferenceConfig with processing parameters
    
    Returns:
        Tuple of:
            - waveform_tensor: shape (num_chunks, AUDIO_LENGTH)
            - metadata: ProcessingMetadata with processing info
    """
    if config is None:
        config = InferenceConfig()
    
    csv_path = Path(csv_path)
    verbose = config.verbose
    
    if verbose:
        print("=" * 60)
        print("INFERENCE DATA PROCESSING (Two-Stage Pipeline)")
        print("=" * 60)
        print(f"Input file: {csv_path}")
        print(f"Stage 1: Interpolate @ {config.db_time_interval}s → {config.chunk_duration}s chunks")
        print(f"Stage 2: Resample to {config.sampling_rate} Hz → {config.audio_length} samples")
        print("=" * 60)

    # Step 1: Detect CSV structure
    if verbose:
        print("\n[Step 1/6] Detecting CSV structure...")

    if config.auto_detect:
        try:
            structure = detect_csv_structure(
                csv_path,
                gpt_model=config.gpt_model,
                max_preview_rows=config.max_preview_rows
            )
            if verbose:
                print(f"  [OK] Detected: skip_rows={structure.skip_rows}, "
                      f"time_col={structure.time_column}, "
                      f"values_col={structure.values_column}")
        except Exception as e:
            if verbose:
                print(f"  [WARN] GPT detection failed: {e}")
                print("  Using fallback structure...")
            structure = get_default_csv_structure()
    else:
        structure = get_default_csv_structure()
        if verbose:
            print(f"  Using default structure: {structure.to_dict()}")

    # Step 2: Read CSV
    if verbose:
        print("\n[Step 2/6] Reading CSV data...")

    time, values = read_raw_csv(csv_path, structure)
    total_duration = time[-1] - time[0]
    original_rate = len(time) / total_duration

    if verbose:
        print(f"  Samples: {len(time)}")
        print(f"  Duration: {total_duration:.2f}s")
        print(f"  Original rate: {original_rate:.1f} Hz")

    # Step 3: Stage 1 - Interpolate at 0.1s intervals
    if verbose:
        print("\n[Step 3/6] Stage 1: Interpolating at 0.1s intervals...")

    time_interp, values_interp = interpolate_raw_data(
        time, values,
        time_interval=config.db_time_interval
    )

    if verbose:
        print(f"  Interpolated samples: {len(time_interp)}")
        print(f"  New rate: {1.0/config.db_time_interval:.1f} Hz")

    # Step 4: Split into chunks with padding
    if verbose:
        print("\n[Step 4/6] Splitting into chunks with padding...")

    chunks = split_into_chunks(
        time_interp, values_interp,
        chunk_duration=config.chunk_duration,
        padding_duration=config.padding_duration,
        time_interval=config.db_time_interval
    )
    
    if verbose:
        print(f"  Created {len(chunks)} chunks of {config.chunk_duration}s each")
        print(f"  Padding: {config.padding_duration}s on each side")

    # Step 5: Stage 2 - Interpolate to 1600 Hz and normalize
    if verbose:
        print("\n[Step 5/6] Stage 2: Resampling to 1600 Hz and normalizing...")

    waveforms = process_chunks(
        chunks,
        chunk_duration=config.chunk_duration,
        padding_duration=config.padding_duration,
        sampling_rate=config.sampling_rate,
        verbose=verbose
    )

    # Step 6: Convert to tensor
    if verbose:
        print("\n[Step 6/6] Creating tensor...")

    waveform_tensor = to_waveform_tensor(waveforms)

    if verbose:
        print(f"  Tensor shape: {waveform_tensor.shape}")
        print(f"  Expected: ({len(chunks)}, {config.audio_length})")
        print("\n" + "=" * 60)
        print("PROCESSING COMPLETE")
        print("=" * 60)

    # Build metadata
    metadata = ProcessingMetadata(
        source_file=str(csv_path),
        csv_structure=structure.to_dict(),
        original_duration=total_duration,
        original_rate=original_rate,
        num_chunks=len(chunks),
        samples_per_chunk=config.audio_length,
        chunk_duration=config.chunk_duration,
        target_rate=config.sampling_rate,
        padding_duration=config.padding_duration,
        db_time_interval=config.db_time_interval
    )

    return waveform_tensor, metadata


# =============================================================================
# Model Inference
# =============================================================================
def load_serving_model(model_path: Union[str, Path]):
    """
    Load a serving model with preprocessing baked in.
    
    Args:
        model_path: Path to saved serving model directory
    
    Returns:
        Loaded serving model callable
    """
    return tf.saved_model.load(str(model_path))


def predict(
    waveform_tensor: tf.Tensor,
    model_path: Union[str, Path]
) -> Dict:
    """
    Run inference on waveform tensor using serving model.
    
    Args:
        waveform_tensor: Tensor of shape (batch_size, samples)
        model_path: Path to saved serving model directory
    
    Returns:
        Dict with predictions, probabilities, class_ids, class_names
    """
    # Load serving model
    model = load_serving_model(model_path)
    
    # Run inference
    result = model(waveform_tensor)
    
    # Convert tensors to numpy
    return {
        'predictions': result['predictions'].numpy(),
        'probabilities': result['probabilities'].numpy(),
        'class_ids': result['class_ids'].numpy(),
        'class_names': [name.decode('utf-8') for name in result['class_names'].numpy()]
    }


# =============================================================================
# High-Level API
# =============================================================================
def predict_from_csv(
    csv_path: Union[str, Path],
    model_path: Union[str, Path],
    auto_detect: bool = True,
    verbose: bool = True,
    log_to_database: bool = False,
    model_name: Optional[str] = None,
    model_version: Optional[str] = None,
    notes: Optional[str] = None,
    tags: Optional[List[str]] = None
) -> InferenceResult:
    """
    End-to-end inference from raw CSV to predictions.

    Args:
        csv_path: Path to raw sensor CSV file
        model_path: Path to saved serving model
        auto_detect: Use GPT for CSV structure detection
        verbose: Print progress messages
        log_to_database: If True, log this test to the test database
        model_name: Optional model name for database logging
        model_version: Optional model version for database logging
        notes: Optional notes about this test
        tags: Optional tags for categorization

    Returns:
        InferenceResult with predictions, probabilities, class_ids, class_names, metadata
    """
    # Create config
    config = InferenceConfig(
        auto_detect=auto_detect,
        verbose=verbose
    )

    # Process CSV to waveform tensor
    waveform_tensor, metadata = process_csv_for_inference(csv_path, config)

    if verbose:
        print(f"\nRunning inference on {metadata.num_chunks} chunks...")

    # Run model inference
    results = predict(waveform_tensor, model_path)

    # Create result object
    inference_result = InferenceResult(
        predictions=results['predictions'],
        probabilities=results['probabilities'],
        class_ids=results['class_ids'],
        class_names=results['class_names'],
        metadata=metadata
    )

    if verbose:
        print("\n" + "=" * 60)
        print("INFERENCE RESULTS")
        print("=" * 60)
        print(inference_result.summary())

    # Log to database if requested
    if log_to_database:
        from .test_database import log_test

        test_id = log_test(
            csv_path=csv_path,
            model_path=model_path,
            inference_result=inference_result,
            waveform_tensor=waveform_tensor,
            model_name=model_name,
            model_version=model_version,
            notes=notes,
            tags=tags,
            auto_detect_csv=auto_detect
        )

        if verbose:
            print(f"\n[Database] Test logged with ID: {test_id}")
            print(f"[Database] Location: test_database/")

    return inference_result


def predict_batch(
    csv_paths: List[Union[str, Path]],
    model_path: Union[str, Path],
    auto_detect: bool = True,
    verbose: bool = True,
    log_to_database: bool = False,
    model_name: Optional[str] = None,
    model_version: Optional[str] = None,
    tags: Optional[List[str]] = None
) -> List[Union[InferenceResult, Dict]]:
    """
    Run inference on multiple CSV files.

    Args:
        csv_paths: List of paths to raw sensor CSV files
        model_path: Path to saved serving model
        auto_detect: Use GPT for CSV structure detection
        verbose: Print progress messages
        log_to_database: If True, log all tests to the test database
        model_name: Optional model name for database logging
        model_version: Optional model version for database logging
        tags: Optional tags for categorization (applied to all tests)

    Returns:
        List of InferenceResult objects or error dicts
    """
    results = []

    for i, csv_path in enumerate(csv_paths):
        if verbose:
            print(f"\n[File {i+1}/{len(csv_paths)}] {csv_path}")

        try:
            result = predict_from_csv(
                csv_path,
                model_path,
                auto_detect=auto_detect,
                verbose=verbose,
                log_to_database=log_to_database,
                model_name=model_name,
                model_version=model_version,
                tags=tags
            )
            results.append(result)
        except Exception as e:
            error_result = {
                'status': 'error',
                'error': str(e),
                'source_file': str(csv_path)
            }
            results.append(error_result)
            if verbose:
                print(f"[ERROR] {e}")

    return results


# =============================================================================
# Testing Utilities (without model)
# =============================================================================
def test_processing(
    csv_path: Union[str, Path],
    auto_detect: bool = True,
    verbose: bool = True
) -> Tuple[tf.Tensor, ProcessingMetadata]:
    """
    Test the processing pipeline without running model inference.
    Useful for verifying data preparation is correct.
    
    Args:
        csv_path: Path to raw sensor CSV file
        auto_detect: Use GPT for CSV structure detection
        verbose: Print progress messages
    
    Returns:
        Tuple of (waveform_tensor, metadata)
    """
    config = InferenceConfig(
        auto_detect=auto_detect,
        verbose=verbose
    )
    return process_csv_for_inference(csv_path, config)