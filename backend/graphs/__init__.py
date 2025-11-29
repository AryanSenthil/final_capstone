"""
graphs — Visualization module for training results.

All functions return base64-encoded PNG strings and optionally save to disk.
Separated from training module so styling can be modified independently.

Usage:
    from graphs import plot_accuracy, plot_loss, plot_confusion_matrix

    # Individual plots
    accuracy_b64 = plot_accuracy(history, save_path='./accuracy.png')

    # All at once
    from graphs import generate_all_graphs
    graphs_dict = generate_all_graphs(history, y_true, y_pred, class_names, save_dir='./plots')
"""

from .graphs import (
    plot_accuracy,
    plot_loss,
    plot_confusion_matrix,
    generate_all_graphs,
    get_graph_paths
)

__all__ = [
    'plot_accuracy',
    'plot_loss',
    'plot_confusion_matrix',
    'generate_all_graphs',
    'get_graph_paths'
]
