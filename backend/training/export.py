"""
export.py — Model export and loading utilities.

Provides functions for saving trained models in multiple formats
and loading them for inference.
"""

import os
from typing import Dict, List, Optional, Union
from pathlib import Path

import tensorflow as tf

from . import constants


class ExportModel(tf.Module):
    """
    Wrapper for exporting audio classification models with preprocessing baked in.

    Accepts either:
        - Raw waveform tensor with shape (batch, samples)
        - CSV data that has been converted to waveform
    """

    def __init__(
        self,
        model: tf.keras.Model,
        label_names: List[str],
        audio_length: int = None,
        frame_length: int = None,
        frame_step: int = None
    ):
        """
        Args:
            model: Trained Keras model expecting spectrogram input
            label_names: List of class label strings
            audio_length: Expected audio length in samples
            frame_length: STFT frame length
            frame_step: STFT frame step
        """
        super().__init__()
        self.model = model
        self._label_names = tf.constant(label_names)
        self._audio_length = audio_length or (constants.TIME_PERIOD * constants.SAMPLING_RATE)
        self._frame_length = frame_length or constants.FRAME_LENGTH
        self._frame_step = frame_step or constants.FRAME_STEP

        # Create concrete function for waveform input
        self.__call__.get_concrete_function(
            x=tf.TensorSpec(shape=[None, int(self._audio_length)], dtype=tf.float32)
        )

    @tf.function
    def __call__(self, x: tf.Tensor) -> dict:
        """
        Run inference on waveform input.

        Args:
            x: Waveform tensor of shape (batch, samples)

        Returns:
            dict with 'predictions', 'class_ids', 'class_names', 'probabilities'
        """
        # Convert waveform to spectrogram
        spectrogram = tf.signal.stft(x, frame_length=self._frame_length, frame_step=self._frame_step)
        spectrogram = tf.abs(spectrogram)
        spectrogram = spectrogram[..., tf.newaxis]

        # Run model
        logits = self.model(spectrogram, training=False)
        probabilities = tf.nn.softmax(logits, axis=-1)
        class_ids = tf.argmax(logits, axis=-1)
        class_names = tf.gather(self._label_names, class_ids)

        return {
            'predictions': logits,
            'probabilities': probabilities,
            'class_ids': class_ids,
            'class_names': class_names
        }


def save_model(
    model: tf.keras.Model,
    name: str,
    save_dir: str,
    formats: List[str] = None
) -> Dict[str, str]:
    """
    Save model weights in specified formats.

    Args:
        model: Trained Keras model
        name: Base name for saved files
        save_dir: Directory to save models
        formats: List of formats ('keras', 'h5', 'savedmodel'). Default: all three.

    Returns:
        dict: {format: path} for each saved format
    """
    if formats is None:
        formats = ['keras', 'h5', 'savedmodel']

    os.makedirs(save_dir, exist_ok=True)
    paths = {}

    if 'keras' in formats:
        path = os.path.join(save_dir, f'{name}.keras')
        model.save(path)
        paths['keras'] = path
        print(f"Keras format saved to: {path}")

    if 'h5' in formats:
        path = os.path.join(save_dir, f'{name}.h5')
        model.save(path)
        paths['h5'] = path
        print(f"H5 format saved to: {path}")

    if 'savedmodel' in formats:
        path = os.path.join(save_dir, f'{name}_savedmodel')
        model.export(path)
        paths['savedmodel'] = path
        print(f"SavedModel exported to: {path}")

    return paths


def save_serving_model(
    model: tf.keras.Model,
    label_names: List[str],
    save_dir: str,
    name: str = 'serving_model',
    audio_length: int = None
) -> str:
    """
    Save model with preprocessing baked in for production inference.

    Args:
        model: Trained Keras model
        label_names: List of class label strings
        save_dir: Directory to save model
        name: Name for the saved model directory
        audio_length: Expected audio length in samples

    Returns:
        str: Path to saved serving model
    """
    os.makedirs(save_dir, exist_ok=True)
    
    export = ExportModel(model, label_names, audio_length=audio_length)
    path = os.path.join(save_dir, f'{name}_serving')
    tf.saved_model.save(export, path)
    
    print(f"Serving model saved to: {path}")
    return path


def load_model(path: Union[str, Path]) -> tf.keras.Model:
    """
    Load a saved Keras model.

    Args:
        path: Path to saved model (.keras, .h5, or SavedModel directory)

    Returns:
        Loaded Keras model
    """
    path = str(path)
    
    if path.endswith('.keras') or path.endswith('.h5'):
        return tf.keras.models.load_model(path)
    else:
        # Assume SavedModel format
        return tf.keras.models.load_model(path)


def load_serving_model(path: Union[str, Path]):
    """
    Load a serving model with preprocessing baked in.

    Args:
        path: Path to saved serving model directory

    Returns:
        Loaded serving model callable
    """
    return tf.saved_model.load(str(path))
