"""
pdf_writer — PDF report generation for ML training runs.

Usage:
    from pdf_writer import TrainingReportWriter

    report = TrainingReportWriter("output.pdf", title="My Training Run")
    report.add_title(subtitle="CNN on Spectrogram Data")
    report.add_hyperparameters({"Learning Rate": 0.001, "Epochs": 100})
    report.add_image(accuracy_b64, caption="Accuracy Curve")
    report.generate()
"""

from .writer import TrainingReportWriter
from .styles import StyleSheet

__all__ = ["TrainingReportWriter", "StyleSheet"]
