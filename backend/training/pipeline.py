"""
pipeline.py — Phase 1: Data preparation pipeline.

Chains CSV loading -> WAV generation -> dataset creation -> spectrogram conversion.
"""

from typing import List, Tuple, Union

import numpy as np
import tensorflow as tf

from .config import DataConfig
from . import tools


def prepare_data(
    paths: Union[str, List[str]],
    config: DataConfig = None,
    verbose: bool = True
) -> Tuple[tf.data.Dataset, tf.data.Dataset, tf.data.Dataset, dict, tuple]:
    """
    Complete data preparation pipeline (Phase 1).

    Args:
        paths: Path(s) to CSV files or directories
        config: DataConfig with processing parameters (uses defaults if None)
        verbose: Print progress messages

    Returns:
        tuple: (train_spec_ds, val_spec_ds, test_spec_ds, metadata, input_shape)
    """
    if config is None:
        config = DataConfig()
    
    # Set seeds for reproducibility
    tf.random.set_seed(config.seed)
    np.random.seed(config.seed)
    
    if verbose:
        print("Phase 1: Data Preparation")
        print("=" * 60)
        print(f"Time period: {config.time_period}s")
        print(f"Sampling rate: {config.sampling_rate} Hz")
        print(f"Batch size: {config.batch_size}")
        print(f"Validation split: {config.validation_split}")
        print("=" * 60)
    
    # Step 1: Load and interpolate CSV files
    if verbose:
        print("\n[Step 1/4] Loading CSV files...")
    data = tools.read_csv_files(
        paths,
        time_period=config.time_period,
        sampling_rate=config.sampling_rate,
        verbose=verbose
    )
    
    # Step 2: Generate WAV tensors
    if verbose:
        print("[Step 2/4] Generating WAV tensors...")
    wav_files = tools.wav_generator(data, sampling_rate=config.sampling_rate)
    
    # Step 3: Create train/val/test datasets
    if verbose:
        print("[Step 3/4] Creating datasets...")
    train_ds, val_ds, test_ds, metadata = tools.create_datasets_from_wav_files(
        wav_files,
        validation_split=config.validation_split,
        batch_size=config.batch_size,
        seed=config.seed
    )
    
    # Step 4: Convert to spectrograms
    if verbose:
        print("[Step 4/4] Converting to spectrograms...")
    train_spec_ds, val_spec_ds, test_spec_ds, input_shape = tools.create_spectrogram_datasets(
        train_ds, val_ds, test_ds,
        frame_length=config.frame_length,
        frame_step=config.frame_step
    )
    
    if verbose:
        print("\n" + "=" * 60)
        print("Data Preparation Complete")
        print(f"Input shape: {input_shape}")
        print(f"Classes: {metadata['class_names']}")
        print(f"Train samples: {metadata['train_size']}")
        print(f"Validation samples: {metadata['val_size']}")
        print(f"Test samples: {metadata['test_size']}")
        print("=" * 60 + "\n")
    
    return train_spec_ds, val_spec_ds, test_spec_ds, metadata, input_shape
