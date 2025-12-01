"""
utils.py — Utility functions for inference pipeline.

Contains:
    - GPT-based CSV structure detection
    - Data processing helpers (interpolation, normalization)
    - Tensor conversion utilities
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Tuple, Union

import numpy as np
import pandas as pd
import tensorflow as tf
from scipy.interpolate import interp1d
from openai import OpenAI
from dotenv import load_dotenv

from .constants import (
    DB_TIME_INTERVAL,
    DB_CHUNK_DURATION,
    DB_PADDING_DURATION,
    SAMPLING_RATE,
    AUDIO_LENGTH,
    INTERPOLATION_KIND,
    INTERPOLATION_FILL_VALUE,
    INTERPOLATION_BOUNDS_ERROR,
    GPT_MODEL,
    MAX_PREVIEW_ROWS,
    DEFAULT_SKIP_ROWS,
    DEFAULT_TIME_COLUMN,
    DEFAULT_VALUES_COLUMN,
    DEFAULT_VALUES_LABEL,
    MIN_DATA_POINTS
)

from .configs import CSVStructure

# Load environment variables from .env
load_dotenv()


# =============================================================================
# GPT-Based CSV Structure Detection
# =============================================================================
def detect_csv_structure(
    file_path: Union[str, Path],
    gpt_model: str = GPT_MODEL,
    max_preview_rows: int = MAX_PREVIEW_ROWS
) -> CSVStructure:
    """
    Use GPT to automatically detect CSV structure.
    
    Args:
        file_path: Path to the CSV file to analyze
        gpt_model: OpenAI model to use
        max_preview_rows: Number of rows to send to GPT
    
    Returns:
        CSVStructure with detected parameters
    
    Raises:
        ValueError: If OPENAI_API_KEY not found or GPT response invalid
    """
    file_path = Path(file_path)
    
    # Read preview of file
    with open(file_path, 'r') as f:
        lines = f.readlines()[:max_preview_rows + 10]
    
    preview_text = ''.join(lines)
    
    prompt = f"""Analyze this CSV data sample and determine its structure:

```
{preview_text}
```

I need you to identify:
1. How many rows to skip (headers, metadata, etc.) before the actual time-series data starts
2. Which column contains TIME data (0-indexed)
3. Which column contains the VALUES to analyze (typically voltage, current, sensor reading)
4. What label best describes the values column

Requirements:
- Time column should have monotonically increasing numerical values
- Values column should contain the measurement data (not time, not indices)
- Skip rows should account for any non-data rows at the start

Respond with ONLY a JSON object (no markdown, no explanation):
{{
    "skip_rows": <integer>,
    "time_column": <integer>,
    "values_column": <integer>,
    "values_label": "<descriptive label with units>"
}}"""

    # Get API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment. Check your .env file.")
    
    # Call OpenAI API
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=gpt_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_completion_tokens=200
    )
    
    # Parse response
    response_text = response.choices[0].message.content.strip()
    response_text = response_text.replace("```json", "").replace("```", "").strip()
    
    try:
        structure_dict = json.loads(response_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse GPT response as JSON: {e}")
    
    # Validate required keys
    required_keys = ["skip_rows", "time_column", "values_column", "values_label"]
    if not all(k in structure_dict for k in required_keys):
        raise ValueError(f"Missing required keys in GPT response. Got: {structure_dict.keys()}")
    
    return CSVStructure(
        skip_rows=structure_dict["skip_rows"],
        time_column=structure_dict["time_column"],
        values_column=structure_dict["values_column"],
        values_label=structure_dict["values_label"]
    )


def get_default_csv_structure() -> CSVStructure:
    """Return default CSV structure as fallback."""
    return CSVStructure(
        skip_rows=DEFAULT_SKIP_ROWS,
        time_column=DEFAULT_TIME_COLUMN,
        values_column=DEFAULT_VALUES_COLUMN,
        values_label=DEFAULT_VALUES_LABEL
    )


# =============================================================================
# CSV Reading
# =============================================================================
def read_raw_csv(
    file_path: Union[str, Path],
    structure: CSVStructure
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Read raw CSV file using detected structure.

    Args:
        file_path: Path to CSV file
        structure: CSVStructure with skip_rows, time_column, values_column

    Returns:
        Tuple of (time_array, values_array)

    Raises:
        ValueError: If data is invalid or insufficient
    """
    df = pd.read_csv(
        file_path,
        skiprows=structure.skip_rows,
        header=None
    )

    # Check if first row contains header strings (non-numeric data)
    # This handles cases where skip_rows didn't catch the header
    try:
        # Try to convert first value in time column to float
        first_time_value = df.iloc[0, structure.time_column]
        if isinstance(first_time_value, str):
            # Try to parse as float
            float(first_time_value)
    except (ValueError, TypeError):
        # First row is likely a header, skip it
        df = df.iloc[1:].reset_index(drop=True)

    if len(df) < MIN_DATA_POINTS:
        raise ValueError(f"Insufficient data points: {len(df)} < {MIN_DATA_POINTS}")

    time = df.iloc[:, structure.time_column].values.astype(np.float64)
    values = df.iloc[:, structure.values_column].values.astype(np.float64)

    return time, values


# =============================================================================
# Data Processing
# =============================================================================
def interpolate_raw_data(
    time: np.ndarray,
    values: np.ndarray,
    time_interval: float = DB_TIME_INTERVAL
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Stage 1: Interpolate raw data at coarse intervals (0.1s).
    This matches the database ingestion preprocessing.

    Args:
        time: Raw time array
        values: Raw values array
        time_interval: Interpolation spacing (default: 0.1s)

    Returns:
        Tuple of (interpolated_time, interpolated_values)
    """
    # Normalize time to start at 0
    time_normalized = time - time[0]
    total_duration = time_normalized[-1]

    # Create uniform time grid at 0.1s intervals
    new_time = np.arange(0, total_duration, time_interval)

    # Interpolate values
    interpolator = interp1d(
        time_normalized,
        values,
        kind=INTERPOLATION_KIND,
        bounds_error=INTERPOLATION_BOUNDS_ERROR,
        fill_value=INTERPOLATION_FILL_VALUE
    )
    new_values = interpolator(new_time)

    return new_time, new_values


def split_into_chunks(
    time: np.ndarray,
    values: np.ndarray,
    chunk_duration: float = DB_CHUNK_DURATION,
    padding_duration: float = DB_PADDING_DURATION,
    time_interval: float = DB_TIME_INTERVAL
) -> List[Tuple[np.ndarray, np.ndarray]]:
    """
    Split time-series data into fixed-duration chunks with padding.
    Uses 0.1s time interval for padding (matches database pipeline).

    Args:
        time: Time array (already interpolated at 0.1s)
        values: Values array
        chunk_duration: Duration of each chunk in seconds (default: 8s)
        padding_duration: Zero-padding on each side in seconds (default: 1s)
        time_interval: Time spacing for padding points (default: 0.1s)

    Returns:
        List of (time_with_padding, values_with_padding) tuples

    Raises:
        ValueError: If data is invalid or insufficient for one chunk
    """
    # Calculate sampling rate from data
    dt = np.mean(np.diff(time))
    if dt <= 0:
        raise ValueError("Invalid time intervals (non-positive dt)")

    sampling_rate = 1.0 / dt
    samples_per_chunk = int(chunk_duration * sampling_rate)

    if samples_per_chunk <= 0:
        raise ValueError("Invalid chunk size")

    num_chunks = int(np.floor(len(time) / samples_per_chunk))

    if num_chunks == 0:
        actual_duration = time[-1] - time[0]
        raise ValueError(
            f"Insufficient data for one chunk. "
            f"Need {chunk_duration}s but only have {actual_duration:.2f}s"
        )

    # Calculate total duration with padding
    total_duration = chunk_duration + 2 * padding_duration
    # Use 0.1s interval for padding points
    num_padding_points = int(padding_duration / time_interval)

    chunks = []
    for i in range(num_chunks):
        chunk_start = i * samples_per_chunk
        chunk_end = chunk_start + samples_per_chunk

        if chunk_end > len(time):
            break

        time_chunk = time[chunk_start:chunk_end]
        values_chunk = values[chunk_start:chunk_end]

        # Normalize time to start at 0
        time_chunk_normalized = time_chunk - time_chunk[0]

        # Create padding regions at 0.1s intervals
        # Start padding: 0 to padding_duration (zeros)
        start_padding_time = np.arange(0, padding_duration, time_interval)
        start_padding_values = np.zeros(len(start_padding_time))

        # Data region: shift by padding_duration
        data_time = time_chunk_normalized + padding_duration

        # End padding: after data to total_duration (zeros)
        end_padding_start = padding_duration + chunk_duration
        end_padding_time = np.arange(end_padding_start, total_duration + time_interval, time_interval)
        end_padding_values = np.zeros(len(end_padding_time))

        # Concatenate all regions
        time_with_padding = np.concatenate([
            start_padding_time,
            data_time,
            end_padding_time
        ])

        values_with_padding = np.concatenate([
            start_padding_values,
            values_chunk,
            end_padding_values
        ])

        chunks.append((time_with_padding, values_with_padding))

    return chunks


def interpolate_chunk_to_1600hz(
    time: np.ndarray,
    values: np.ndarray,
    chunk_duration: float = DB_CHUNK_DURATION,
    padding_duration: float = DB_PADDING_DURATION,
    sampling_rate: int = SAMPLING_RATE
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Stage 2: Interpolate a padded chunk to 1600 Hz.
    This matches the training preprocessing.

    Args:
        time: Time array with padding (from split_into_chunks, at 0.1s intervals)
        values: Values array with padding
        chunk_duration: Duration of data chunk in seconds (default: 8s)
        padding_duration: Zero-padding on each side in seconds (default: 1s)
        sampling_rate: Target sampling rate (default: 1600 Hz)

    Returns:
        Tuple of (interpolated_time, interpolated_values)
    """
    # Calculate total duration with padding
    total_duration = chunk_duration + 2 * padding_duration
    time_interval = 1.0 / sampling_rate  # 0.000625s for 1600 Hz

    # Create target time array at 1600 Hz
    interpolated_time = np.arange(0, total_duration, time_interval)

    # Create interpolation function
    interpolator = interp1d(
        time,
        values,
        kind=INTERPOLATION_KIND,
        bounds_error=INTERPOLATION_BOUNDS_ERROR,
        fill_value=INTERPOLATION_FILL_VALUE
    )

    # Interpolate to 1600 Hz
    interpolated_values = interpolator(interpolated_time)

    return interpolated_time, interpolated_values


def normalize_data(data: np.ndarray) -> np.ndarray:
    """
    Normalize array to [-1, 1] range by max absolute value.
    
    Args:
        data: Input array
    
    Returns:
        Normalized array
    """
    max_val = np.max(np.abs(data))
    if max_val == 0:
        return data
    return data / max_val


# =============================================================================
# Tensor Conversion
# =============================================================================
def to_waveform_tensor(waveforms: List[np.ndarray]) -> tf.Tensor:
    """
    Convert list of waveforms to batched tensor.
    
    Args:
        waveforms: List of numpy arrays, each shape (samples,)
    
    Returns:
        Tensor of shape (batch_size, samples)
    """
    stacked = np.stack(waveforms, axis=0)
    return tf.convert_to_tensor(stacked, dtype=tf.float32)


def process_chunks(
    chunks: List[Tuple[np.ndarray, np.ndarray]],
    chunk_duration: float = DB_CHUNK_DURATION,
    padding_duration: float = DB_PADDING_DURATION,
    sampling_rate: int = SAMPLING_RATE,
    verbose: bool = False
) -> List[np.ndarray]:
    """
    Process all chunks: interpolate to 1600 Hz and normalize.
    Padding is kept (not trimmed) to match training preprocessing.

    Args:
        chunks: List of (time_with_padding, values_with_padding) tuples (at 0.1s intervals)
        chunk_duration: Duration of data chunk in seconds (default: 8s)
        padding_duration: Zero-padding on each side in seconds (default: 1s)
        sampling_rate: Target sampling rate (default: 1600 Hz)
        verbose: Print progress

    Returns:
        List of processed waveform arrays (normalized, with padding)
    """
    waveforms = []
    total_duration = chunk_duration + 2 * padding_duration  # 10s
    expected_samples = int(total_duration * sampling_rate)  # 16000

    for i, (t_chunk, v_chunk) in enumerate(chunks):
        # Stage 2: Interpolate to 1600 Hz (keeps padding)
        interpolated_time, interpolated_values = interpolate_chunk_to_1600hz(
            t_chunk, v_chunk,
            chunk_duration=chunk_duration,
            padding_duration=padding_duration,
            sampling_rate=sampling_rate
        )

        # Normalize to [-1, 1] (keep padding, don't trim)
        normalized = normalize_data(interpolated_values)

        # Ensure exact sample count
        if len(normalized) != expected_samples:
            if verbose:
                print(f"  [WARN] Chunk {i+1}: Got {len(normalized)} samples, expected {expected_samples}. Adjusting...")
            if len(normalized) > expected_samples:
                normalized = normalized[:expected_samples]
            else:
                normalized = np.pad(normalized, (0, expected_samples - len(normalized)))

        waveforms.append(normalized)

        if verbose:
            print(f"  Chunk {i+1}: {len(normalized)} samples, "
                  f"range [{normalized.min():.3f}, {normalized.max():.3f}]")

    return waveforms