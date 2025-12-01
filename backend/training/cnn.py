"""
cnn.py — CNN architecture for spectrogram classification.

Provides:
    - build_model: Construct CNN architecture
    - train: Train the model
    - save: Save trained model
    - run_pipeline: Execute full training pipeline
"""

import os
from typing import List, Optional, Tuple, Union

import numpy as np
import tensorflow as tf
from keras import layers, models

from .config import CNNConfig, DataConfig, TrainingResult
from .pipeline import prepare_data
from .export import save_model, save_serving_model
import graphs


def build_model(
    input_shape: tuple,
    num_classes: int,
    train_ds: tf.data.Dataset = None,
    config: CNNConfig = None
) -> tf.keras.Model:
    """
    Build CNN model for spectrogram classification.

    Args:
        input_shape: Shape of input spectrograms (height, width, channels)
        num_classes: Number of output classes
        train_ds: Training dataset for normalization layer adaptation
        config: CNNConfig with architecture parameters

    Returns:
        Compiled Keras model (uncompiled, ready for training)
    """
    if config is None:
        config = CNNConfig()

    # Build normalization layer
    norm_layer = layers.Normalization()
    if train_ds is not None:
        norm_layer.adapt(data=train_ds.map(lambda spec, label: spec))

    model = models.Sequential([
        layers.Input(shape=input_shape),
        layers.Resizing(config.resize_shape[0], config.resize_shape[1]),
        norm_layer,
        layers.Conv2D(config.conv1_filters, 3, activation='relu'),
        layers.Conv2D(config.conv2_filters, 3, activation='relu'),
        layers.MaxPooling2D(),
        layers.Dropout(config.dropout_conv),
        layers.Flatten(),
        layers.Dense(config.dense_units, activation='relu'),
        layers.Dropout(config.dropout_dense),
        layers.Dense(num_classes),
    ])

    return model


def train(
    model: tf.keras.Model,
    train_ds: tf.data.Dataset,
    val_ds: tf.data.Dataset,
    config: CNNConfig = None,
    verbose: int = 1,
    extra_callbacks: list = None
) -> tf.keras.callbacks.History:
    """
    Train CNN model with early stopping and learning rate reduction.

    Args:
        model: Built Keras model
        train_ds: Training dataset
        val_ds: Validation dataset
        config: CNNConfig with training parameters
        verbose: Keras training verbosity (0, 1, or 2)

    Returns:
        Training history object
    """
    if config is None:
        config = CNNConfig()

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
    name: str = 'cnn_model',
    audio_length: int = None
) -> dict:
    """
    Save trained CNN model in multiple formats.

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
    model_name: str = 'cnn_model',
    data_config: DataConfig = None,
    model_config: CNNConfig = None,
    verbose: bool = True,
    extra_callbacks: list = None
) -> TrainingResult:
    """
    Execute complete CNN training pipeline.

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
        model_config: CNNConfig for model architecture and training
        verbose: Print progress messages

    Returns:
        TrainingResult with model, history, metrics, and paths
    """
    if data_config is None:
        data_config = DataConfig()
    if model_config is None:
        model_config = CNNConfig()

    # Phase 1: Data preparation
    if verbose:
        print("\n" + "=" * 60)
        print("CNN TRAINING PIPELINE")
        print("=" * 60)

    train_spec_ds, val_spec_ds, test_spec_ds, metadata, input_shape = prepare_data(
        paths, config=data_config, verbose=verbose
    )

    # Phase 2: Build model
    if verbose:
        print("\nPhase 2: Building CNN Model")
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

    result = TrainingResult(
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

    # Clean up GPU memory after training
    try:
        tf.keras.backend.clear_session()
        import gc
        gc.collect()
    except Exception:
        pass  # Non-fatal

    return result
