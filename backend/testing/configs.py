"""
configs.py — Configurable parameters for inference.

These can be overridden at runtime.
All constants are imported from settings module for consistency.
"""

from dataclasses import dataclass, field
from typing import Optional, List
import numpy as np

# Import directly from settings module
from settings.constants import (
    DEFAULT_SKIP_ROWS,
    DEFAULT_TIME_COLUMN,
    DEFAULT_VALUES_COLUMN,
    DEFAULT_VALUES_LABEL,
    MAX_PREVIEW_ROWS,
    OPENAI_MODEL,
    TRAINING_SAMPLING_RATE,
)
from settings.configs import (
    DB_TIME_INTERVAL,
    DB_CHUNK_DURATION,
    DB_PADDING_DURATION,
    DB_INTERPOLATION_KIND,
    DB_INTERPOLATION_FILL_VALUE,
)

# Compute derived constants inline to avoid circular imports
SAMPLING_RATE = TRAINING_SAMPLING_RATE  # Use same rate as training (1600 Hz)
TOTAL_DURATION = DB_CHUNK_DURATION + 2 * DB_PADDING_DURATION  # 10s
AUDIO_LENGTH = int(TOTAL_DURATION * SAMPLING_RATE)  # 16000 samples per chunk
INTERPOLATION_KIND = DB_INTERPOLATION_KIND
INTERPOLATION_FILL_VALUE = DB_INTERPOLATION_FILL_VALUE
GPT_MODEL = OPENAI_MODEL


@dataclass
class InferenceConfig:
    """Configuration for inference pipeline."""

    # Stage 1: Coarse interpolation (0.1s) and chunking
    db_time_interval: float = DB_TIME_INTERVAL  # 0.1s
    chunk_duration: float = DB_CHUNK_DURATION   # 8s
    padding_duration: float = DB_PADDING_DURATION  # 1s

    # Stage 2: Fine interpolation to 1600 Hz
    sampling_rate: int = SAMPLING_RATE  # 1600 Hz

    # Interpolation
    interpolation_kind: str = INTERPOLATION_KIND
    interpolation_fill_value: float = INTERPOLATION_FILL_VALUE

    # GPT detection
    auto_detect: bool = True
    gpt_model: str = GPT_MODEL
    max_preview_rows: int = MAX_PREVIEW_ROWS

    # Output options
    verbose: bool = True

    @property
    def audio_length(self) -> int:
        """Calculate expected samples per chunk (with padding, matches training)."""
        # Total duration with padding: chunk_duration + 2 * padding_duration
        total_duration = self.chunk_duration + 2 * self.padding_duration  # 10s
        return int(total_duration * self.sampling_rate)  # 10s * 1600 = 16000


@dataclass
class CSVStructure:
    """Detected or default CSV structure."""
    
    skip_rows: int = DEFAULT_SKIP_ROWS
    time_column: int = DEFAULT_TIME_COLUMN
    values_column: int = DEFAULT_VALUES_COLUMN
    values_label: str = DEFAULT_VALUES_LABEL
    
    def to_dict(self) -> dict:
        return {
            "skip_rows": self.skip_rows,
            "time_column": self.time_column,
            "values_column": self.values_column,
            "values_label": self.values_label
        }
    
    @classmethod
    def from_dict(cls, d: dict) -> 'CSVStructure':
        return cls(
            skip_rows=d["skip_rows"],
            time_column=d["time_column"],
            values_column=d["values_column"],
            values_label=d["values_label"]
        )
    
    @classmethod
    def default(cls) -> 'CSVStructure':
        return cls()


@dataclass
class ProcessingMetadata:
    """Metadata from data processing."""

    source_file: str
    csv_structure: dict
    original_duration: float
    original_rate: float
    num_chunks: int
    samples_per_chunk: int
    chunk_duration: float
    target_rate: int
    padding_duration: float = DB_PADDING_DURATION
    db_time_interval: float = DB_TIME_INTERVAL


@dataclass
class InferenceResult:
    """Container for inference results."""
    
    predictions: np.ndarray           # Raw logits (num_chunks, num_classes)
    probabilities: np.ndarray         # Softmax probs (num_chunks, num_classes)
    class_ids: np.ndarray             # Predicted class indices (num_chunks,)
    class_names: List[str]            # Predicted class names (num_chunks,)
    metadata: ProcessingMetadata      # Processing metadata
    
    def summary(self) -> str:
        """Generate human-readable summary."""
        lines = [
            "=" * 50,
            "INFERENCE RESULTS",
            "=" * 50,
            f"Source: {self.metadata.source_file}",
            f"Chunks: {self.metadata.num_chunks}",
            "-" * 50
        ]
        
        for i, (name, probs) in enumerate(zip(self.class_names, self.probabilities)):
            max_prob = np.max(probs)
            lines.append(f"Chunk {i+1}: {name} (confidence: {max_prob:.1%})")
        
        lines.append("=" * 50)
        return "\n".join(lines)
    
    def get_majority_prediction(self) -> tuple:
        """
        Get the most common prediction across all chunks.
        
        Returns:
            Tuple of (class_name, count, percentage)
        """
        from collections import Counter
        counts = Counter(self.class_names)
        most_common = counts.most_common(1)[0]
        return (most_common[0], most_common[1], most_common[1] / len(self.class_names))
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "predictions": self.predictions.tolist(),
            "probabilities": self.probabilities.tolist(),
            "class_ids": self.class_ids.tolist(),
            "class_names": self.class_names,
            "metadata": {
                "source_file": self.metadata.source_file,
                "csv_structure": self.metadata.csv_structure,
                "original_duration": self.metadata.original_duration,
                "original_rate": self.metadata.original_rate,
                "num_chunks": self.metadata.num_chunks,
                "samples_per_chunk": self.metadata.samples_per_chunk,
                "chunk_duration": self.metadata.chunk_duration,
                "target_rate": self.metadata.target_rate,
                "padding_duration": self.metadata.padding_duration,
                "db_time_interval": self.metadata.db_time_interval
            }
        }