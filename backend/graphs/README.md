# Graphs Module

This module is dedicated to creating all the essential visualizations required to evaluate and understand the performance of a trained machine learning model.

## Overview

A model's performance can't be fully understood by looking at a single number like accuracy. This module provides the tools to generate standard, easily interpretable plots that reveal the dynamics of the training process and the nuances of the model's predictive behavior. It uses the popular `matplotlib` and `seaborn` libraries to create high-quality visualizations.

## Key Functions

The module provides functions to generate three critical plots:

*   `plot_accuracy`: This function plots the model's **training accuracy** versus its **validation accuracy** over each epoch. This is one of the most important plots for diagnosing issues. For example, a large and growing gap between the training and validation accuracy is a classic sign of overfitting.
*   `plot_loss`: Similar to the accuracy plot, this function plots the **training loss** and **validation loss** over time. This shows how well the model is learning to minimize its errors. A validation loss that starts to increase while the training loss continues to decrease is another clear indicator of overfitting.
*   `plot_confusion_matrix`: This function generates a heatmap that provides a detailed breakdown of the model's predictions versus the actual labels. It's invaluable for understanding *what kind* of mistakes the model is making (e.g., is it frequently confusing "crushcore" with "disbond"?).

## Dual Output: Files and Base64

A key feature of this module is its dual-output capability. Each plotting function can:

1.  **Save the graph to a file**: If a `save_path` is provided, the function will save the generated plot as a PNG image. This is useful for creating a permanent record of training artifacts.
2.  **Return a base64 string**: The function also returns the image as a base64-encoded string. This is extremely useful for embedding the graphs directly into other documents without needing to manage separate image files. For example, the `pdf_writer` module uses these base64 strings to embed the graphs directly into the final PDF training report.

## How It's Used

This module is typically called by the `training` module's `report.py` script at the end of a training run. The `generate_all_graphs` function is called with the training history and test results. The returned dictionary of base64-encoded graphs is then passed to the `pdf_writer` to be included in the final report, creating a seamless and automated reporting pipeline.
