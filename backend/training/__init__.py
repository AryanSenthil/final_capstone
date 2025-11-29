"""
training — Neural network training module for spectrogram classification.

Models:
    - cnn: Convolutional Neural Network
    - resnet: Residual Network with skip connections

Usage:
    # Full pipeline
    from training.cnn import run_pipeline
    result = run_pipeline(paths=['./data/'], save_dir='./models/cnn')

    # Or step by step
    from training.pipeline import prepare_data
    from training.cnn import build_model, train, save

    train_ds, val_ds, test_ds, metadata, input_shape = prepare_data(paths)
    model = build_model(input_shape, metadata['num_classes'], train_ds)
    history = train(model, train_ds, val_ds)
    paths = save(model, metadata['class_names'], './models')

    # For graphs, import from the graphs module
    from graphs import plot_accuracy, plot_loss, plot_confusion_matrix
"""

from .config import (
    CNNConfig,
    ResNetConfig,
    DataConfig,
    TrainingResult
)

from .constants import (
    TIME_PERIOD,
    SAMPLING_RATE,
    FRAME_LENGTH,
    FRAME_STEP,
    SEED,
    VALIDATION_SPLIT,
    BATCH_SIZE
)

from .pipeline import prepare_data

from .export import (
    save_model,
    save_serving_model,
    load_model,
    load_serving_model
)

# Import model modules for direct access
from . import cnn
from . import resnet

# High-level runner
from .runner import (
    run_training,
    run_cnn,
    run_resnet,
    RunResult,
    capture_output,
)

# Report generation
from .report import (
    generate_report,
    generate_model_metadata,
    ReportMetadata,
    FullTrainingResult,
)

__all__ = [
    # Config classes
    'CNNConfig',
    'ResNetConfig', 
    'DataConfig',
    'TrainingResult',
    
    # Constants
    'TIME_PERIOD',
    'SAMPLING_RATE',
    'FRAME_LENGTH',
    'FRAME_STEP',
    'SEED',
    'VALIDATION_SPLIT',
    'BATCH_SIZE',
    
    # Pipeline
    'prepare_data',
    
    # Export
    'save_model',
    'save_serving_model',
    'load_model',
    'load_serving_model',
    
    # Model modules
    'cnn',
    'resnet',
    
    # High-level runner
    'run_training',
    'run_cnn',
    'run_resnet',
    'RunResult',
    'capture_output',
    
    # Report generation
    'generate_report',
    'generate_model_metadata',
    'ReportMetadata',
    'FullTrainingResult',
]
