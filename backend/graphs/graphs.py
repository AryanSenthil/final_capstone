"""
graphs.py — Visualization module for training results.

All functions return base64-encoded PNG strings and optionally save to disk.
"""

import base64
import io
import os
from typing import Dict, List, Optional

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns


def _fig_to_base64(fig: plt.Figure) -> str:
    """Convert matplotlib figure to base64-encoded PNG string."""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode('utf-8')
    buf.close()
    return b64


def _save_fig(fig: plt.Figure, save_path: str) -> None:
    """Save figure to disk."""
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    fig.savefig(save_path, dpi=150, bbox_inches='tight')


def plot_accuracy(
    history: dict,
    save_path: Optional[str] = None,
    figsize: tuple = (8, 6)
) -> str:
    """
    Plot training and validation accuracy over epochs.

    Args:
        history: Training history dict with 'accuracy' and 'val_accuracy' keys
        save_path: Optional path to save PNG file
        figsize: Figure size in inches

    Returns:
        Base64-encoded PNG string
    """
    fig, ax = plt.subplots(figsize=figsize)
    
    epochs = range(1, len(history['accuracy']) + 1)
    
    ax.plot(epochs, history['accuracy'], 'b-', label='Training', linewidth=2)
    ax.plot(epochs, history['val_accuracy'], 'r-', label='Validation', linewidth=2)
    
    ax.set_xlabel('Epoch', fontsize=12)
    ax.set_ylabel('Accuracy', fontsize=12)
    ax.set_title('Model Accuracy', fontsize=14)
    ax.legend(loc='lower right', fontsize=10)
    ax.grid(True, alpha=0.3)
    
    # Set y-axis limits
    ax.set_ylim([0, 1.05])
    
    b64 = _fig_to_base64(fig)
    
    if save_path:
        _save_fig(fig, save_path)
    
    plt.close(fig)
    return b64


def plot_loss(
    history: dict,
    save_path: Optional[str] = None,
    figsize: tuple = (8, 6)
) -> str:
    """
    Plot training and validation loss over epochs.

    Args:
        history: Training history dict with 'loss' and 'val_loss' keys
        save_path: Optional path to save PNG file
        figsize: Figure size in inches

    Returns:
        Base64-encoded PNG string
    """
    fig, ax = plt.subplots(figsize=figsize)
    
    epochs = range(1, len(history['loss']) + 1)
    
    ax.plot(epochs, history['loss'], 'b-', label='Training', linewidth=2)
    ax.plot(epochs, history['val_loss'], 'r-', label='Validation', linewidth=2)
    
    ax.set_xlabel('Epoch', fontsize=12)
    ax.set_ylabel('Loss', fontsize=12)
    ax.set_title('Model Loss', fontsize=14)
    ax.legend(loc='upper right', fontsize=10)
    ax.grid(True, alpha=0.3)
    
    b64 = _fig_to_base64(fig)
    
    if save_path:
        _save_fig(fig, save_path)
    
    plt.close(fig)
    return b64


def plot_confusion_matrix(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    class_names: List[str],
    save_path: Optional[str] = None,
    figsize: tuple = (8, 6)
) -> str:
    """
    Plot confusion matrix heatmap.

    Args:
        y_true: Ground truth labels (1D array of class indices)
        y_pred: Predicted labels (1D array of class indices)
        class_names: List of class name strings
        save_path: Optional path to save PNG file
        figsize: Figure size in inches

    Returns:
        Base64-encoded PNG string
    """
    import tensorflow as tf
    
    # Compute confusion matrix
    confusion_mtx = tf.math.confusion_matrix(y_true, y_pred).numpy()
    
    fig, ax = plt.subplots(figsize=figsize)
    
    sns.heatmap(
        confusion_mtx,
        xticklabels=class_names,
        yticklabels=class_names,
        annot=True,
        fmt='g',
        cmap='Blues',
        ax=ax
    )
    
    ax.set_xlabel('Predicted', fontsize=12)
    ax.set_ylabel('Actual', fontsize=12)
    ax.set_title('Confusion Matrix', fontsize=14)
    
    # Rotate x labels if many classes
    if len(class_names) > 4:
        plt.xticks(rotation=45, ha='right')
        plt.yticks(rotation=0)
    
    b64 = _fig_to_base64(fig)
    
    if save_path:
        _save_fig(fig, save_path)
    
    plt.close(fig)
    return b64


def generate_all_graphs(
    history: dict,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    class_names: List[str],
    save_dir: Optional[str] = None,
    figsize: tuple = (8, 6)
) -> Dict[str, str]:
    """
    Generate all training graphs (accuracy, loss, confusion matrix).

    Args:
        history: Training history dict
        y_true: Ground truth labels
        y_pred: Predicted labels
        class_names: List of class name strings
        save_dir: Optional directory to save PNG files
        figsize: Figure size in inches

    Returns:
        dict: {'accuracy': base64, 'loss': base64, 'confusion_matrix': base64}
    """
    save_paths = {}
    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
        save_paths = {
            'accuracy': os.path.join(save_dir, 'accuracy.png'),
            'loss': os.path.join(save_dir, 'loss.png'),
            'confusion_matrix': os.path.join(save_dir, 'confusion_matrix.png')
        }
    
    graphs = {
        'accuracy': plot_accuracy(
            history,
            save_path=save_paths.get('accuracy'),
            figsize=figsize
        ),
        'loss': plot_loss(
            history,
            save_path=save_paths.get('loss'),
            figsize=figsize
        ),
        'confusion_matrix': plot_confusion_matrix(
            y_true,
            y_pred,
            class_names,
            save_path=save_paths.get('confusion_matrix'),
            figsize=figsize
        )
    }
    
    return graphs


def get_graph_paths(save_dir: str) -> Dict[str, str]:
    """
    Return expected paths for saved graphs.

    Args:
        save_dir: Directory where graphs are saved

    Returns:
        dict: {'accuracy': path, 'loss': path, 'confusion_matrix': path}
    """
    return {
        'accuracy': os.path.join(save_dir, 'accuracy.png'),
        'loss': os.path.join(save_dir, 'loss.png'),
        'confusion_matrix': os.path.join(save_dir, 'confusion_matrix.png')
    }
