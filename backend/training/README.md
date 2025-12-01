# Training Module

This module is the core engine for machine learning model development within the application. It encapsulates the entire process of preparing data, defining model architectures, executing training runs, evaluating performance, and generating comprehensive reports.

## Overview

The `training` module provides a robust and extensible framework for developing damage detection models based on sensor data. It supports different neural network architectures, manages hyperparameters, integrates with data processing pipelines, and automates the generation of detailed training reports, including AI-powered analysis and visualizations.

## Key Components

### `runner.py`

This script serves as the primary entry point and orchestrator for training jobs. It provides a high-level interface to initiate a training run and handles various meta-tasks:

*   **Workflow Management**: Takes paths to data, a save directory, and a `model_type` (`cnn` or `resnet`), then orchestrates the entire training process.
*   **Output Capture**: Captures all `stdout` during training, ensuring that logs and progress messages are recorded and can be included in reports.
*   **Dynamic Model Loading**: Dynamically loads and utilizes the appropriate model definition (`cnn.py` or `resnet.py`) based on the specified architecture.
*   **Report & Metadata Generation**: After training, it triggers the creation of a comprehensive PDF report (using `report.py`) and a `model_info.json` file for model metadata. This often includes AI-powered analysis.

### `pipeline.py`

This script focuses exclusively on the *data preparation pipeline* for training. It takes raw data (processed by `database_management` and stored in `database`) and transforms it into a format directly consumable by the neural networks.

*   **`prepare_data` Function**: Orchestrates a multi-step data transformation:
    1.  Loads CSV data (typically spectrograms) from the `database`.
    2.  Generates "WAV tensors" as an intermediate representation.
    3.  Splits data into training, validation, and testing datasets for robust evaluation.
    4.  Converts the data into spectrograms, which are image-like representations suitable for CNNs and ResNets.
*   **Output**: Produces TensorFlow `tf.data.Dataset` objects ready for model consumption, along with metadata and the expected `input_shape`.

### `cnn.py` and `resnet.py`

These files define the specific neural network architectures and their associated training logic:

*   **`cnn.py`**: Implements a Convolutional Neural Network (CNN) for spectrogram classification. It defines:
    *   `build_model`: Constructs the CNN layers (convolutional, pooling, dense) as a `tf.keras.Model`.
    *   `train`: Compiles and trains the CNN model, incorporating callbacks like `EarlyStopping` and `ReduceLROnPlateau` to optimize the training process and prevent overfitting.
    *   `run_pipeline`: Executes the full CNN training pipeline, from data preparation to evaluation and saving.
*   **`resnet.py`**: Implements a Residual Network (ResNet) architecture. It leverages `residual_block` functions to build deeper networks with skip connections, which helps in training very deep models by mitigating the vanishing gradient problem. The overall `train`, `save`, and `run_pipeline` structure is similar to `cnn.py`, adapting for the ResNet architecture.

### `report.py`

This module is responsible for synthesizing all training-related information into a professional PDF report:

*   **LLM Integration**: Calls the `analyzer` module to generate AI-powered textual analysis of the training results (e.g., executive summaries, training dynamics, recommendations).
*   **PDF Generation**: Uses the `pdf_writer` module to construct the PDF document, embedding:
    *   AI analysis.
    *   Model and dataset information.
    *   Hyperparameter tables.
    *   Training curves (accuracy, loss) and confusion matrices (from the `graphs` module).
    *   A sampled history of training metrics.
*   **Metadata**: Generates `model_info.json` and `training_history.json` files that are saved alongside the trained model, providing easily accessible metadata.

### Supporting Files

*   `config.py`: Defines dataclass configurations (`DataConfig`, `CNNConfig`, `ResNetConfig`, `TrainingResult`) for managing data processing parameters and model hyperparameters.
*   `constants.py`: Contains fixed parameters for the training process.
*   `export.py`: Handles saving trained Keras models into various formats (H5, Keras, SavedModel, and serving models).
*   `tools.py`, `utils.py`: Contains various helper functions used across the training pipeline, such as data loading, WAV generation, dataset splitting, and spectrogram conversion.

## How It's Used

The `training` module is primarily invoked by the `agent` module in response to a user request to train a new machine learning model. The agent calls `runner.run_training` (or `runner.run_cnn`, `runner.run_resnet`) with specified parameters. The module then autonomously handles data preparation, model training, evaluation, saving of artifacts, and generation of a comprehensive report, which is ultimately stored in the `models` directory.
