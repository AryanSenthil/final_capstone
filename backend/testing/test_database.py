"""
test_database.py — Test tracking database system.

Automatically logs all test executions with:
- Raw CSV files (original sensor data)
- Processed chunk data references
- Metadata (model info, timestamps, predictions)
- Test configuration and results

Database Structure:
    test_database/
        ├── raw_csvs/           # Original CSV files
        │   └── YYYYMMDD_HHMMSS_<filename>.csv
        ├── processed_chunks/   # Processed chunk data
        │   └── YYYYMMDD_HHMMSS_<test_id>/
        │       ├── chunk_0.npy
        │       ├── chunk_1.npy
        │       └── ...
        ├── metadata/           # Test metadata JSON files
        │   └── YYYYMMDD_HHMMSS_<test_id>.json
        └── index.json          # Master index of all tests

Usage:
    from testing.test_database import TestDatabase, log_test

    # Option 1: Automatic logging (recommended)
    result = predict_from_csv(
        csv_path="sensor_data.csv",
        model_path="path/to/model",
        log_to_database=True  # Enable automatic logging
    )

    # Option 2: Manual logging
    db = TestDatabase()
    test_id = db.log_test(
        csv_path="sensor_data.csv",
        model_path="path/to/model",
        inference_result=result,
        waveform_tensor=waveform_tensor
    )
"""

import os
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Union
from dataclasses import dataclass, asdict

import numpy as np
import tensorflow as tf

from .configs import InferenceResult, ProcessingMetadata
from .constants import TEST_DATABASE_DIR, TEST_INDEX_FILE


# =============================================================================
# Database Configuration
# =============================================================================

@dataclass
class TestDatabaseConfig:
    """Configuration for test database."""

    # Database root directory (from settings)
    db_root: Path = TEST_DATABASE_DIR

    # Subdirectories
    raw_csvs_dir: str = "raw_csvs"
    processed_chunks_dir: str = "processed_chunks"
    metadata_dir: str = "metadata"

    # Index file (stored at backend root level, not inside db_root)
    index_file: Path = TEST_INDEX_FILE

    # Options
    save_processed_chunks: bool = True  # Whether to save processed chunk data
    compress_chunks: bool = True  # Use compressed .npz format

    def __post_init__(self):
        """Convert paths to Path if string."""
        if isinstance(self.db_root, str):
            self.db_root = Path(self.db_root)
        if isinstance(self.index_file, str):
            self.index_file = Path(self.index_file)


# =============================================================================
# Test Metadata Schema
# =============================================================================

@dataclass
class TestMetadata:
    """Complete metadata for a single test execution."""

    # Test identification
    test_id: str  # Format: YYYYMMDD_HHMMSS
    timestamp: str  # ISO format

    # Source data
    original_csv_path: str  # Original file path
    stored_csv_path: str  # Path in database

    # Model information
    model_path: str
    model_name: Optional[str] = None
    model_version: Optional[str] = None

    # Processing metadata
    processing_metadata: Dict = None  # From ProcessingMetadata

    # Inference results
    num_chunks: int = 0
    predictions: List[str] = None  # Class names per chunk
    probabilities: List[List[float]] = None  # Probabilities per chunk
    class_ids: List[int] = None  # Class IDs per chunk

    # Majority vote result
    majority_class: Optional[str] = None
    majority_count: Optional[int] = None
    majority_percentage: Optional[float] = None

    # Data references
    processed_chunks_dir: Optional[str] = None  # Path to saved chunks

    # Configuration
    auto_detect_csv: bool = True
    csv_structure: Dict = None

    # Additional notes
    notes: Optional[str] = None
    tags: List[str] = None

    def to_dict(self) -> Dict:
        """Convert to JSON-serializable dict."""
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict) -> 'TestMetadata':
        """Create from dict."""
        return cls(**d)


# =============================================================================
# Test Database
# =============================================================================

class TestDatabase:
    """
    Manages test execution history and data storage.

    Automatically creates database structure and logs all test executions
    with complete metadata and data references.
    """

    def __init__(self, config: TestDatabaseConfig = None):
        """
        Initialize test database.

        Args:
            config: TestDatabaseConfig (uses default if None)
        """
        self.config = config or TestDatabaseConfig()
        self._initialize_database()

    def _initialize_database(self):
        """Create database directory structure if it doesn't exist."""
        # Create root directory
        self.config.db_root.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        self.raw_csvs_path = self.config.db_root / self.config.raw_csvs_dir
        self.processed_chunks_path = self.config.db_root / self.config.processed_chunks_dir
        self.metadata_path = self.config.db_root / self.config.metadata_dir

        self.raw_csvs_path.mkdir(exist_ok=True)
        self.processed_chunks_path.mkdir(exist_ok=True)
        self.metadata_path.mkdir(exist_ok=True)

        # Index file is stored at backend root level (not inside db_root)
        self.index_path = self.config.index_file
        if not self.index_path.exists():
            self._save_index([])

    def _generate_test_id(self) -> str:
        """Generate unique test ID based on timestamp."""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def _save_index(self, index: List[Dict]):
        """Save master index file."""
        with open(self.index_path, 'w') as f:
            json.dump(index, f, indent=2)

    def _load_index(self) -> List[Dict]:
        """Load master index file."""
        if not self.index_path.exists():
            return []
        with open(self.index_path, 'r') as f:
            return json.load(f)

    def _add_to_index(self, test_summary: Dict):
        """Add test summary to master index."""
        index = self._load_index()
        index.append(test_summary)
        self._save_index(index)

    def log_test(
        self,
        csv_path: Union[str, Path],
        model_path: Union[str, Path],
        inference_result: InferenceResult,
        waveform_tensor: Optional[tf.Tensor] = None,
        model_name: Optional[str] = None,
        model_version: Optional[str] = None,
        notes: Optional[str] = None,
        tags: Optional[List[str]] = None,
        auto_detect_csv: bool = True
    ) -> str:
        """
        Log a test execution to the database.

        Args:
            csv_path: Path to original CSV file
            model_path: Path to model used for inference
            inference_result: InferenceResult from predict_from_csv
            waveform_tensor: Optional processed waveform tensor to save
            model_name: Optional model name
            model_version: Optional model version
            notes: Optional notes about this test
            tags: Optional tags for categorization
            auto_detect_csv: Whether CSV structure was auto-detected

        Returns:
            test_id: Unique identifier for this test
        """
        csv_path = Path(csv_path)
        model_path = Path(model_path)

        # Generate test ID
        test_id = self._generate_test_id()
        timestamp = datetime.now().isoformat()

        # Copy raw CSV to database
        csv_filename = csv_path.name
        stored_csv_filename = f"{test_id}_{csv_filename}"
        stored_csv_path = self.raw_csvs_path / stored_csv_filename
        shutil.copy2(csv_path, stored_csv_path)

        # Save processed chunks if requested
        processed_chunks_dir_path = None
        if self.config.save_processed_chunks and waveform_tensor is not None:
            chunks_dir = self.processed_chunks_path / test_id
            chunks_dir.mkdir(exist_ok=True)
            processed_chunks_dir_path = str(chunks_dir.relative_to(self.config.db_root))

            # Save each chunk
            waveform_array = waveform_tensor.numpy()
            for i in range(waveform_array.shape[0]):
                chunk_data = waveform_array[i]
                if self.config.compress_chunks:
                    np.savez_compressed(chunks_dir / f"chunk_{i}.npz", data=chunk_data)
                else:
                    np.save(chunks_dir / f"chunk_{i}.npy", chunk_data)

        # Get majority prediction
        majority_class, majority_count, majority_pct = inference_result.get_majority_prediction()

        # Create metadata
        metadata = TestMetadata(
            test_id=test_id,
            timestamp=timestamp,
            original_csv_path=str(csv_path.absolute()),
            stored_csv_path=str(stored_csv_path.relative_to(self.config.db_root)),
            model_path=str(model_path.absolute()),
            model_name=model_name or model_path.name,
            model_version=model_version,
            processing_metadata=inference_result.metadata.__dict__,
            num_chunks=len(inference_result.class_names),
            predictions=inference_result.class_names,
            probabilities=inference_result.probabilities.tolist(),
            class_ids=inference_result.class_ids.tolist(),
            majority_class=majority_class,
            majority_count=majority_count,
            majority_percentage=majority_pct,
            processed_chunks_dir=processed_chunks_dir_path,
            auto_detect_csv=auto_detect_csv,
            csv_structure=inference_result.metadata.csv_structure,
            notes=notes,
            tags=tags or []
        )

        # Save metadata
        metadata_file = self.metadata_path / f"{test_id}.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata.to_dict(), f, indent=2)

        # Add to index
        test_summary = {
            "test_id": test_id,
            "timestamp": timestamp,
            "csv_filename": csv_filename,
            "model_name": metadata.model_name,
            "num_chunks": metadata.num_chunks,
            "majority_class": majority_class,
            "majority_confidence": majority_pct,
            "tags": tags or []
        }
        self._add_to_index(test_summary)

        return test_id

    def get_test(self, test_id: str) -> TestMetadata:
        """
        Retrieve test metadata by ID.

        Args:
            test_id: Test identifier

        Returns:
            TestMetadata object
        """
        metadata_file = self.metadata_path / f"{test_id}.json"
        if not metadata_file.exists():
            raise ValueError(f"Test {test_id} not found in database")

        with open(metadata_file, 'r') as f:
            data = json.load(f)

        return TestMetadata.from_dict(data)

    def list_tests(
        self,
        limit: Optional[int] = None,
        tags: Optional[List[str]] = None,
        model_name: Optional[str] = None
    ) -> List[Dict]:
        """
        List all tests with optional filtering.

        Args:
            limit: Maximum number of tests to return (most recent first)
            tags: Filter by tags (returns tests with ANY of these tags)
            model_name: Filter by model name

        Returns:
            List of test summaries
        """
        index = self._load_index()

        # Filter by tags
        if tags:
            index = [t for t in index if any(tag in t.get('tags', []) for tag in tags)]

        # Filter by model name
        if model_name:
            index = [t for t in index if t.get('model_name') == model_name]

        # Sort by timestamp (most recent first)
        index.sort(key=lambda x: x['timestamp'], reverse=True)

        # Apply limit
        if limit:
            index = index[:limit]

        return index

    def get_csv_path(self, test_id: str) -> Path:
        """Get path to raw CSV file for a test."""
        metadata = self.get_test(test_id)
        return self.config.db_root / metadata.stored_csv_path

    def get_chunks_dir(self, test_id: str) -> Optional[Path]:
        """Get path to processed chunks directory for a test."""
        metadata = self.get_test(test_id)
        if metadata.processed_chunks_dir:
            return self.config.db_root / metadata.processed_chunks_dir
        return None

    def load_chunk(self, test_id: str, chunk_idx: int) -> np.ndarray:
        """
        Load a specific processed chunk.

        Args:
            test_id: Test identifier
            chunk_idx: Chunk index (0-based)

        Returns:
            Chunk data as numpy array
        """
        chunks_dir = self.get_chunks_dir(test_id)
        if chunks_dir is None:
            raise ValueError(f"No processed chunks saved for test {test_id}")

        # Try compressed format first
        chunk_file_npz = chunks_dir / f"chunk_{chunk_idx}.npz"
        chunk_file_npy = chunks_dir / f"chunk_{chunk_idx}.npy"

        if chunk_file_npz.exists():
            return np.load(chunk_file_npz)['data']
        elif chunk_file_npy.exists():
            return np.load(chunk_file_npy)
        else:
            raise ValueError(f"Chunk {chunk_idx} not found for test {test_id}")

    def delete_test(self, test_id: str):
        """
        Delete a test and all its associated data.

        Args:
            test_id: Test identifier
        """
        metadata = self.get_test(test_id)

        # Delete raw CSV
        csv_path = self.config.db_root / metadata.stored_csv_path
        if csv_path.exists():
            csv_path.unlink()

        # Delete processed chunks directory
        if metadata.processed_chunks_dir:
            chunks_dir = self.config.db_root / metadata.processed_chunks_dir
            if chunks_dir.exists():
                shutil.rmtree(chunks_dir)

        # Delete metadata file
        metadata_file = self.metadata_path / f"{test_id}.json"
        if metadata_file.exists():
            metadata_file.unlink()

        # Remove from index
        index = self._load_index()
        index = [t for t in index if t['test_id'] != test_id]
        self._save_index(index)

    def get_stats(self) -> Dict:
        """
        Get database statistics.

        Returns:
            Dict with counts, storage size, etc.
        """
        index = self._load_index()

        # Count tests
        total_tests = len(index)

        # Calculate storage size
        def get_dir_size(path):
            total = 0
            for entry in path.rglob('*'):
                if entry.is_file():
                    total += entry.stat().st_size
            return total

        raw_csvs_size = get_dir_size(self.raw_csvs_path)
        chunks_size = get_dir_size(self.processed_chunks_path)
        metadata_size = get_dir_size(self.metadata_path)
        total_size = raw_csvs_size + chunks_size + metadata_size

        # Get unique models
        models = set(t.get('model_name') for t in index if t.get('model_name'))

        # Get unique tags
        all_tags = set()
        for t in index:
            all_tags.update(t.get('tags', []))

        return {
            'total_tests': total_tests,
            'total_size_bytes': total_size,
            'total_size_mb': total_size / (1024 * 1024),
            'raw_csvs_size_mb': raw_csvs_size / (1024 * 1024),
            'chunks_size_mb': chunks_size / (1024 * 1024),
            'metadata_size_mb': metadata_size / (1024 * 1024),
            'unique_models': len(models),
            'unique_tags': len(all_tags),
            'models': sorted(models),
            'tags': sorted(all_tags)
        }


# =============================================================================
# Helper Functions
# =============================================================================

def get_default_database() -> TestDatabase:
    """Get default test database instance."""
    return TestDatabase()


def log_test(
    csv_path: Union[str, Path],
    model_path: Union[str, Path],
    inference_result: InferenceResult,
    waveform_tensor: Optional[tf.Tensor] = None,
    **kwargs
) -> str:
    """
    Convenience function to log a test to the default database.

    Args:
        csv_path: Path to original CSV file
        model_path: Path to model used for inference
        inference_result: InferenceResult from predict_from_csv
        waveform_tensor: Optional processed waveform tensor to save
        **kwargs: Additional arguments passed to TestDatabase.log_test

    Returns:
        test_id: Unique identifier for this test
    """
    db = get_default_database()
    return db.log_test(
        csv_path=csv_path,
        model_path=model_path,
        inference_result=inference_result,
        waveform_tensor=waveform_tensor,
        **kwargs
    )
