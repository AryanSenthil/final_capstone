"""
resnet.py — ResNet architecture for spectrogram classification.

Implements residual blocks with skip connections:
    H(x) = F(x) + x

Provides:
    - build_model: Construct ResNet architecture
    - train: Train the model
    - save: Save trained model
    - run_pipeline: Execute full training pipeline
"""

import os
from typing import List, Optional, Tuple, Union

import numpy as np
import tensorflow as tf
from keras import layers, models

from .config import ResNetConfig, DataConfig, TrainingResult
from .pipeline import prepare_data
from .export import save_model, save_serving_model
import graphs


def residual_block(
    x: tf.Tensor,
    filters: int,
    downsample: bool = False
) -> tf.Tensor:
    """
    Build a single residual block.

    Implements: H(x) = F(x) + x
    where F(x) is two conv layers with batch normalization.

    Args:
        x: Input tensor
        filters: Number of filters for conv layers
        downsample: If True, use stride=2 to reduce spatial dimensions

    Returns:
        Output tensor after residual connection
    """
    stride = 2 if downsample else 1
    shortcut = x

    # F(x): two conv layers
    f_x = layers.Conv2D(filters, 3, strides=stride, padding='same')(x)
    f_x = layers.BatchNormalization()(f_x)
    f_x = layers.ReLU()(f_x)
    f_x = layers.Conv2D(filters, 3, padding='same')(f_x)
    f_x = layers.BatchNormalization()(f_x)

    # Match dimensions for skip connection if needed
    if downsample or shortcut.shape[-1] != filters:
        shortcut = layers.Conv2D(filters, 1, strides=stride, padding='same')(shortcut)
        shortcut = layers.BatchNormalization()(shortcut)

    # H(x) = F(x) + x
    h_x = layers.Add()([f_x, shortcut])
    h_x = layers.ReLU()(h_x)

    return h_x


def build_model(
    input_shape: tuple,
    num_classes: int,
    train_ds: tf.data.Dataset = None,
    config: ResNetConfig = None
) -> tf.keras.Model:
    """
    Build ResNet model for spectrogram classification.

    Args:
        input_shape: Shape of input spectrograms (height, width, channels)
        num_classes: Number of output classes
        train_ds: Not used for ResNet (included for consistent interface)
        config: ResNetConfig with architecture parameters

    Returns:
        Keras model (uncompiled)
    """
    if config is None:
        config = ResNetConfig()

    inputs = layers.Input(shape=input_shape)

    # Initial convolution
    x = layers.Conv2D(
        config.initial_filters,
        config.initial_kernel,
        strides=config.initial_stride,
        padding='same'
    )(inputs)
    x = layers.BatchNormalization()(x)
    x = layers.ReLU()(x)

    # Residual blocks
    for filters, downsample in zip(config.block_filters, config.downsample_blocks):
        x = residual_block(x, filters=filters, downsample=downsample)

    # Classification head
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dropout(config.dropout)(x)
    outputs = layers.Dense(
        num_classes,
        kernel_regularizer=tf.keras.regularizers.l2(config.l2_reg)
    )(x)

    model = models.Model(inputs, outputs)

    return model


def train(
    model: tf.keras.Model,
    train_ds: tf.data.Dataset,
    val_ds: tf.data.Dataset,
    config: ResNetConfig = None,
    verbose: int = 1,
    extra_callbacks: list = None
) -> tf.keras.callbacks.History:
    """
    Train ResNet model with early stopping and learning rate reduction.

    Args:
        model: Built Keras model
        train_ds: Training dataset
        val_ds: Validation dataset
        config: ResNetConfig with training parameters
        verbose: Keras training verbosity (0, 1, or 2)
        extra_callbacks: Additional Keras callbacks to use during training

    Returns:
        Training history object
    """
    if config is None:
        config = ResNetConfig()

    # Compile model
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=config.learning_rate),
        loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
        metrics=['accuracy']
    )

    # Define callbacks - optimize for accuracy metrics
    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor='val_accuracy',
            mode='max',
            patience=config.patience,
            restore_best_weights=True,
            verbose=1
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor='accuracy',
            mode='max',
            factor=config.reduce_lr_factor,
            patience=config.reduce_lr_patience,
            min_lr=config.min_lr,
            verbose=1
        )
    ]

    # Add extra callbacks if provided
    if extra_callbacks:
        callbacks.extend(extra_callbacks)

    # Train
    history = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=config.epochs,
        callbacks=callbacks,
        verbose=verbose
    )

    return history


def save(
    model: tf.keras.Model,
    label_names: List[str],
    save_dir: str,
    name: str = 'resnet_model',
    audio_length: int = None
) -> dict:
    """
    Save trained ResNet model in multiple formats.

    Args:
        model: Trained Keras model
        label_names: List of class name strings
        save_dir: Directory to save models
        name: Base name for saved files
        audio_length: Audio length for serving model

    Returns:
        dict: Paths to saved models
    """
    paths = save_model(model, name, save_dir)
    paths['serving'] = save_serving_model(
        model, label_names, save_dir, name, audio_length
    )
    return paths


def run_pipeline(
    paths: Union[str, List[str]],
    save_dir: str,
    model_name: str = 'resnet_model',
    data_config: DataConfig = None,
    model_config: ResNetConfig = None,
    verbose: bool = True,
    extra_callbacks: list = None
) -> TrainingResult:
    """
    Execute complete ResNet training pipeline.

    Phases:
        1. Data preparation (CSV -> WAV -> Spectrogram datasets)
        2. Model construction
        3. Training
        4. Save model and graphs

    Args:
        paths: Path(s) to CSV files or directories
        save_dir: Directory to save model and graphs
        model_name: Base name for saved model files
        data_config: DataConfig for data pipeline
        model_config: ResNetConfig for model architecture and training
        verbose: Print progress messages

    Returns:
        TrainingResult with model, history, metrics, and paths
    """
    if data_config is None:
        data_config = DataConfig()
    if model_config is None:
        model_config = ResNetConfig()

    # Phase 1: Data preparation
    if verbose:
        print("\n" + "=" * 60)
        print("RESNET TRAINING PIPELINE")
        print("=" * 60)

    train_spec_ds, val_spec_ds, test_spec_ds, metadata, input_shape = prepare_data(
        paths, config=data_config, verbose=verbose
    )

    # Phase 2: Build model
    if verbose:
        print("\nPhase 2: Building ResNet Model")
        print("-" * 40)

    model = build_model(
        input_shape=input_shape,
        num_classes=metadata['num_classes'],
        train_ds=train_spec_ds,
        config=model_config
    )

    if verbose:
        model.summary()

    # Phase 3: Train
    if verbose:
        print("\nPhase 3: Training")
        print("-" * 40)

    import time
    start_time = time.time()

    history = train(
        model, train_spec_ds, val_spec_ds,
        config=model_config,
        verbose=1 if verbose else 0,
        extra_callbacks=extra_callbacks
    )

    training_time = time.time() - start_time

    # Evaluate on test set
    if verbose:
        print("\nEvaluating on test set...")

    test_results = model.evaluate(test_spec_ds, return_dict=True, verbose=0)

    # Get predictions for confusion matrix
    y_pred = model.predict(test_spec_ds, verbose=0)
    y_pred_classes = tf.argmax(y_pred, axis=1).numpy()
    y_true = tf.concat(list(test_spec_ds.map(lambda s, lab: lab)), axis=0).numpy()

    if verbose:
        print(f"Test Loss: {test_results['loss']:.4f}")
        print(f"Test Accuracy: {test_results['accuracy']:.4f}")

    # Phase 4: Save model
    if verbose:
        print("\nPhase 4: Saving Model")
        print("-" * 40)

    os.makedirs(save_dir, exist_ok=True)
    model_paths = save(
        model, metadata['class_names'], save_dir, model_name,
        audio_length=metadata['audio_length']
    )

    # Generate and save graphs
    if verbose:
        print("\nGenerating graphs...")

    graph_dir = os.path.join(save_dir, 'graphs')
    graph_base64 = graphs.generate_all_graphs(
        history=history.history,
        y_true=y_true,
        y_pred=y_pred_classes,
        class_names=metadata['class_names'],
        save_dir=graph_dir
    )
    graph_paths = graphs.get_graph_paths(graph_dir)

    if verbose:
        print(f"Graphs saved to: {graph_dir}")
        print("\n" + "=" * 60)
        print("TRAINING COMPLETE")
        print("=" * 60)

    return TrainingResult(
        model=model,
        history=history.history,
        metadata=metadata,
        input_shape=input_shape,
        predictions=y_pred_classes,
        true_labels=y_true,
        test_accuracy=test_results['accuracy'],
        test_loss=test_results['loss'],
        training_time=training_time,
        model_paths=model_paths,
        graph_paths=graph_paths,
        graph_base64=graph_base64
    )
