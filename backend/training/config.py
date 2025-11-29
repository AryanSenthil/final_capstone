"""
config.py — Training hyperparameters and result containers.
"""

from dataclasses import dataclass, field
from typing import Optional
import numpy as np
import tensorflow as tf

from settings import configs


@dataclass
class CNNConfig:
    """Hyperparameters for CNN training."""

    # Training
    epochs: int = configs.CNN_EPOCHS
    learning_rate: float = configs.CNN_LEARNING_RATE

    # Early stopping
    patience: int = configs.CNN_PATIENCE
    reduce_lr_patience: int = configs.CNN_REDUCE_LR_PATIENCE
    reduce_lr_factor: float = configs.CNN_REDUCE_LR_FACTOR
    min_lr: float = configs.CNN_MIN_LR

    # Regularization
    dropout_conv: float = configs.CNN_DROPOUT_CONV
    dropout_dense: float = configs.CNN_DROPOUT_DENSE

    # Architecture
    resize_shape: tuple = configs.CNN_RESIZE_SHAPE
    conv1_filters: int = configs.CNN_CONV1_FILTERS
    conv2_filters: int = configs.CNN_CONV2_FILTERS
    dense_units: int = configs.CNN_DENSE_UNITS


@dataclass
class ResNetConfig:
    """Hyperparameters for ResNet training."""

    # Training
    epochs: int = configs.RESNET_EPOCHS
    learning_rate: float = configs.RESNET_LEARNING_RATE

    # Early stopping
    patience: int = configs.RESNET_PATIENCE
    reduce_lr_patience: int = configs.RESNET_REDUCE_LR_PATIENCE
    reduce_lr_factor: float = configs.RESNET_REDUCE_LR_FACTOR
    min_lr: float = configs.RESNET_MIN_LR

    # Regularization
    dropout: float = configs.RESNET_DROPOUT
    l2_reg: float = configs.RESNET_L2_REG

    # Architecture
    initial_filters: int = configs.RESNET_INITIAL_FILTERS
    initial_kernel: int = configs.RESNET_INITIAL_KERNEL
    initial_stride: int = configs.RESNET_INITIAL_STRIDE
    block_filters: tuple = configs.RESNET_BLOCK_FILTERS
    downsample_blocks: tuple = configs.RESNET_DOWNSAMPLE_BLOCKS


@dataclass
class TrainingResult:
    """Container for training outputs."""
    
    model: tf.keras.Model
    history: dict
    metadata: dict
    input_shape: tuple
    predictions: np.ndarray
    true_labels: np.ndarray
    test_accuracy: float
    test_loss: float
    model_paths: dict = field(default_factory=dict)
    graph_paths: dict = field(default_factory=dict)
    graph_base64: dict = field(default_factory=dict)


@dataclass
class DataConfig:
    """Configuration for data pipeline. Uses constants by default."""
    
    time_period: float = None
    sampling_rate: int = None
    frame_length: int = None
    frame_step: int = None
    seed: int = None
    validation_split: float = None
    batch_size: int = None
    
    def __post_init__(self):
        """Fill None values from constants."""
        from . import constants
        
        if self.time_period is None:
            self.time_period = constants.TIME_PERIOD
        if self.sampling_rate is None:
            self.sampling_rate = constants.SAMPLING_RATE
        if self.frame_length is None:
            self.frame_length = constants.FRAME_LENGTH
        if self.frame_step is None:
            self.frame_step = constants.FRAME_STEP
        if self.seed is None:
            self.seed = constants.SEED
        if self.validation_split is None:
            self.validation_split = constants.VALIDATION_SPLIT
        if self.batch_size is None:
            self.batch_size = constants.BATCH_SIZE
