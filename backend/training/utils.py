"""
utils.py — Low-level helper functions for data processing.
"""

import numpy as np
import tensorflow as tf
from scipy.interpolate import interp1d

from . import constants


def interpolate_data(
    data: list,
    interval: float,
    period: float
) -> list:
    """
    Interpolate time-current data at regular intervals using linear interpolation.

    Args:
        data: [(time_current_pairs, label), ...] where time_current_pairs is list[(time, current)]
        interval: Time interval between interpolated points (1/sampling_rate)
        period: Total time period for interpolation

    Returns:
        list: [(new_time_current, label), ...] with regular spacing
    """
    interpolated_data = []

    for time_current, label in data:
        time_vals, current_vals = zip(*time_current)

        interpolation_func = interp1d(
            time_vals,
            current_vals,
            kind=constants.INTERPOLATION_KIND,
            fill_value=constants.INTERPOLATION_FILL_VALUE
        )
        
        max_time = interval * (round(period / interval))
        new_time = np.arange(0, max_time, interval)
        new_current = interpolation_func(new_time)

        new_time_current = list(zip(new_time, new_current))
        interpolated_data.append((new_time_current, label))
    
    return interpolated_data


def extract_data_and_type(data_list: list) -> list:
    """
    Extract current sequences and labels from time-current data.

    Args:
        data_list: [(time_current_pairs, label), ...]

    Returns:
        list: [(current_sequence, label), ...]
    """
    new_data = []
    for time_current, label in data_list:
        current_data = [v for _, v in time_current]
        new_data.append((current_data, label))
    return new_data


def normalize_data(data: np.ndarray) -> np.ndarray:
    """
    Normalize input array to [-1, 1] range by max absolute value.

    Args:
        data: Array to normalize

    Returns:
        Normalized array
    """
    max_val = np.max(np.abs(data))
    if max_val == 0:
        return data
    return data / max_val


def convert_to_wav(
    normalized_data: np.ndarray,
    sample_rate: int
) -> tf.Tensor:
    """
    Convert normalized data into WAV-encoded audio tensor.

    Args:
        normalized_data: Sequence of floats in [-1, 1]
        sample_rate: Audio sample rate in Hz

    Returns:
        WAV-encoded bytes tensor
    """
    sample_rate_tensor = tf.cast(sample_rate, tf.int32)
    audio_tensor = tf.convert_to_tensor(normalized_data, dtype=tf.float32)
    audio_tensor = tf.reshape(audio_tensor, (-1, 1))
    return tf.audio.encode_wav(audio_tensor, sample_rate_tensor)


def get_spectrogram(
    waveform: tf.Tensor,
    frame_length: int = None,
    frame_step: int = None
) -> tf.Tensor:
    """
    Convert waveform to spectrogram via STFT.

    Args:
        waveform: Audio tensor
        frame_length: STFT frame length (default from constants)
        frame_step: STFT frame step (default from constants)

    Returns:
        Spectrogram tensor with shape (..., height, width, 1)
    """
    if frame_length is None:
        frame_length = constants.FRAME_LENGTH
    if frame_step is None:
        frame_step = constants.FRAME_STEP
    
    spectrogram = tf.signal.stft(waveform, frame_length=frame_length, frame_step=frame_step)
    spectrogram = tf.abs(spectrogram)
    spectrogram = spectrogram[..., tf.newaxis]
    return spectrogram
