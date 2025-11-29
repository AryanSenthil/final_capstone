"""
tools.py — Data pipeline functions for loading and processing sensor data.
"""

import os
from typing import List, Tuple, Union

import numpy as np
import pandas as pd
import tensorflow as tf

from . import constants
from . import utils


def process_csv_file(file_path: str) -> Tuple[list, str]:
    """
    Process a single CSV file containing classification label and time-current data.

    Expected format:
        - Row 1: classification label (string)
        - Row 2: header (Time(s), Current(A) or similar)
        - Rows 3+: time, current pairs (floats)

    Args:
        file_path: Path to CSV file

    Returns:
        tuple: (time_current_pairs, classification_label)
    """
    with open(file_path, 'r') as f:
        classification_label = f.readline().strip()
    
    df = pd.read_csv(file_path, skiprows=1)
    time_current_data = df.values
    time_current_pairs = [tuple(row) for row in time_current_data]
    
    return (time_current_pairs, classification_label)


def read_csv_files(
    paths: Union[str, List[str]],
    time_period: float = None,
    sampling_rate: int = None,
    verbose: bool = True
) -> list:
    """
    Read CSV(s), process/interpolate, and return data ready for modeling.

    Args:
        paths: Path to CSV file, directory, or list of paths
        time_period: Total time window (default from constants)
        sampling_rate: Samples per second (default from constants)
        verbose: Print progress messages

    Returns:
        list: [(time_current_pairs, label), ...] with regular spacing
    """
    if time_period is None:
        time_period = constants.TIME_PERIOD
    if sampling_rate is None:
        sampling_rate = constants.SAMPLING_RATE
    
    all_data = []

    if isinstance(paths, str):
        paths = [paths]
    
    for path in paths:
        if os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                for filename in files:
                    if filename.endswith(".csv"):
                        file_path = os.path.join(root, filename)
                        try:
                            all_data.append(process_csv_file(file_path))
                            if verbose:
                                print(f"[OK] Loaded: {file_path}")
                        except Exception as e:
                            if verbose:
                                print(f"[ERROR] Failed to load {file_path}: {str(e)}")
                        
        elif os.path.isfile(path) and path.endswith(".csv"):
            try:
                all_data.append(process_csv_file(path))
                if verbose:
                    print(f"[OK] Loaded: {path}")
            except Exception as e:
                if verbose:
                    print(f"[ERROR] Failed to load {path}: {str(e)}")
        else:
            if verbose:
                print(f"[WARNING] Skipping invalid path: {path}")

    if not all_data:
        raise ValueError("No valid CSV files were found in the provided paths.")

    interval = 1 / sampling_rate
    data_for_model = utils.interpolate_data(all_data, interval, time_period)
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"Total files loaded: {len(all_data)}")
        print(f"Total data points after interpolation: {len(data_for_model)}")
        print(f"{'='*60}\n")
    
    return data_for_model


def wav_generator(
    data: list,
    sampling_rate: int = None
) -> List[Tuple[tf.Tensor, str]]:
    """
    Generate WAV tensors from interpolated data.

    Args:
        data: [(time_current_pairs, label), ...] from read_csv_files
        sampling_rate: Audio sample rate (default from constants)

    Returns:
        list: [(wav_bytes_tensor, label), ...]
    """
    if sampling_rate is None:
        sampling_rate = constants.SAMPLING_RATE
    
    classification_data = utils.extract_data_and_type(data)
    
    normalized_data = [
        (utils.normalize_data(np.array(current_sequence)), label)
        for current_sequence, label in classification_data
    ]
    
    wav_files = [
        (utils.convert_to_wav(current_sequence, sampling_rate), label)
        for current_sequence, label in normalized_data
    ]
    
    return wav_files


def create_datasets_from_wav_files(
    wav_files: List[Tuple[tf.Tensor, str]],
    validation_split: float = None,
    batch_size: int = None,
    seed: int = None
) -> Tuple[tf.data.Dataset, tf.data.Dataset, tf.data.Dataset, dict]:
    """
    Create train, validation, and test datasets from in-memory WAV files.

    Args:
        wav_files: List of (wav_bytes, label) pairs
        validation_split: Fraction for val+test (default from constants)
        batch_size: Samples per batch (default from constants)
        seed: Random seed (default from constants)

    Returns:
        tuple: (train_ds, val_ds, test_ds, metadata)
    """
    if validation_split is None:
        validation_split = constants.VALIDATION_SPLIT
    if batch_size is None:
        batch_size = constants.BATCH_SIZE
    if seed is None:
        seed = constants.SEED
    
    class_names = sorted(set(label for _, label in wav_files))
    class_to_idx = {name: idx for idx, name in enumerate(class_names)}
    
    waveforms = []
    labels = []
    sample_rate = None
    
    for audio_binary, label in wav_files:
        waveform, sr = tf.audio.decode_wav(audio_binary)
        sample_rate = sr
        waveforms.append(tf.squeeze(waveform, axis=-1))
        labels.append(class_to_idx[label])
    
    waveforms = tf.stack(waveforms)
    labels = tf.constant(labels)
    
    dataset = tf.data.Dataset.from_tensor_slices((waveforms, labels))
    dataset = dataset.shuffle(len(wav_files), seed=seed)
    
    val_size = int(len(wav_files) * validation_split)
    train_size = len(wav_files) - val_size
    
    train_ds = dataset.take(train_size)
    val_ds = dataset.skip(train_size)
    
    test_ds = val_ds.shard(num_shards=2, index=0)
    val_ds = val_ds.shard(num_shards=2, index=1)
    
    test_size = val_size // 2
    val_size = val_size - test_size
    
    train_ds = train_ds.batch(batch_size).prefetch(tf.data.AUTOTUNE)
    val_ds = val_ds.batch(batch_size).prefetch(tf.data.AUTOTUNE)
    test_ds = test_ds.batch(batch_size).prefetch(tf.data.AUTOTUNE)
    
    class_counts = {name: 0 for name in class_names}
    for _, label in wav_files:
        class_counts[label] += 1
    
    metadata = {
        'sample_rate': int(sample_rate.numpy()),
        'audio_length': waveforms.shape[1],
        'class_names': class_names,
        'class_to_idx': class_to_idx,
        'num_classes': len(class_names),
        'train_size': train_size,
        'val_size': val_size,
        'test_size': test_size,
        'class_counts': class_counts
    }
    
    return train_ds, val_ds, test_ds, metadata


def create_spectrogram_datasets(
    train_ds: tf.data.Dataset,
    val_ds: tf.data.Dataset,
    test_ds: tf.data.Dataset,
    frame_length: int = None,
    frame_step: int = None
) -> Tuple[tf.data.Dataset, tf.data.Dataset, tf.data.Dataset, tuple]:
    """
    Convert waveform datasets to spectrogram datasets.

    Args:
        train_ds: Training waveform dataset
        val_ds: Validation waveform dataset
        test_ds: Test waveform dataset
        frame_length: STFT frame length (default from constants)
        frame_step: STFT frame step (default from constants)

    Returns:
        tuple: (train_spec_ds, val_spec_ds, test_spec_ds, input_shape)
    """
    if frame_length is None:
        frame_length = constants.FRAME_LENGTH
    if frame_step is None:
        frame_step = constants.FRAME_STEP
    
    @tf.function
    def get_spectrogram(waveform):
        spectrogram = tf.signal.stft(waveform, frame_length=frame_length, frame_step=frame_step)
        spectrogram = tf.abs(spectrogram)
        spectrogram = spectrogram[..., tf.newaxis]
        return spectrogram
    
    def apply_spectrogram(audio, label):
        return get_spectrogram(audio), label
    
    def make_spec_ds(ds):
        return ds.map(apply_spectrogram, num_parallel_calls=tf.data.AUTOTUNE)
    
    train_spec_ds = make_spec_ds(train_ds)
    val_spec_ds = make_spec_ds(val_ds)
    test_spec_ds = make_spec_ds(test_ds)
    
    for example_spectrogram, _ in train_spec_ds.take(1):
        input_shape = example_spectrogram.shape[1:]
    
    train_spec_ds = train_spec_ds.cache().shuffle(10000).prefetch(tf.data.AUTOTUNE)
    val_spec_ds = val_spec_ds.cache().prefetch(tf.data.AUTOTUNE)
    test_spec_ds = test_spec_ds.cache().prefetch(tf.data.AUTOTUNE)
    
    return train_spec_ds, val_spec_ds, test_spec_ds, input_shape
