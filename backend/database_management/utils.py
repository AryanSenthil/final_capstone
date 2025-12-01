"""
Utility functions for database management.
Contains AI tools for data structure detection and metadata generation.
"""

import json
import os
from pathlib import Path
from typing import Dict, List
from datetime import datetime
from openai import OpenAI
import numpy as np
import pandas as pd
from dotenv import load_dotenv

from settings.constants import MAX_PREVIEW_ROWS, OPENAI_MODEL

# Load environment variables from .env file
load_dotenv()


def detect_csv_structure(file_path: Path, max_preview_rows: int = None) -> Dict[str, any]:
    """
    Use GPT-5.1 to automatically detect CSV structure.

    Parameters
    ----------
    file_path : Path
        Path to the CSV file to analyze
    max_preview_rows : int, optional
        Number of rows to send to GPT. If None, uses constant.

    Returns
    -------
    Dict with keys: time_column, values_column, values_label, skip_rows
    """
    if max_preview_rows is None:
        max_preview_rows = MAX_PREVIEW_ROWS

    def _smart_fallback_detection(file_path: Path) -> Dict:
        """
        Intelligent fallback that analyzes the CSV to make better guesses.
        Much better than hardcoded defaults.
        """
        try:
            # Try reading with different skip values
            for skip in [0, 1, 2]:
                try:
                    df = pd.read_csv(file_path, skiprows=skip, nrows=20)
                    if len(df.columns) >= 2:
                        # Check if columns are numeric
                        numeric_cols = []
                        for i, col in enumerate(df.columns):
                            try:
                                pd.to_numeric(df[col], errors='raise')
                                numeric_cols.append(i)
                            except (ValueError, TypeError):
                                continue

                        if len(numeric_cols) >= 2:
                            # First numeric column is likely time, second is values
                            time_col = numeric_cols[0]
                            value_col = numeric_cols[1]

                            # Try to get a label from column header
                            value_label = str(df.columns[value_col])
                            if value_label.startswith("Unnamed"):
                                value_label = "Value"

                            return {
                                "skip_rows": skip,
                                "time_column": time_col,
                                "values_column": value_col,
                                "values_label": value_label
                            }
                except Exception:
                    continue
        except Exception as e:
            print(f"[WARN] Smart fallback detection failed: {e}")

        # Ultimate fallback - simple defaults
        return {
            "skip_rows": 0,
            "time_column": 0,
            "values_column": 1,
            "values_label": "Value"
        }

    def _validate_structure(structure: Dict) -> Dict:
        """Validate and sanitize the structure dict."""
        result = {}

        # Validate skip_rows: must be non-negative integer
        try:
            skip_rows = int(structure.get("skip_rows", 0))
            result["skip_rows"] = max(0, min(skip_rows, 100))  # Cap at 100 rows
        except (ValueError, TypeError):
            result["skip_rows"] = 0

        # Validate time_column: must be non-negative integer
        try:
            time_col = int(structure.get("time_column", 0))
            result["time_column"] = max(0, min(time_col, 100))  # Cap at column 100
        except (ValueError, TypeError):
            result["time_column"] = 0

        # Validate values_column: must be non-negative integer, different from time
        try:
            values_col = int(structure.get("values_column", 1))
            values_col = max(0, min(values_col, 100))
            # Ensure values column is different from time column
            if values_col == result["time_column"]:
                values_col = result["time_column"] + 1
            result["values_column"] = values_col
        except (ValueError, TypeError):
            result["values_column"] = 1 if result["time_column"] != 1 else 0

        # Validate values_label: must be a string
        values_label = structure.get("values_label", "Value")
        if not isinstance(values_label, str) or not values_label.strip():
            values_label = "Value"
        result["values_label"] = values_label[:100]  # Cap length

        return result

    # Try to read file
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()[:max_preview_rows + 10]
    except (IOError, UnicodeDecodeError) as e:
        print(f"[WARN] Could not read CSV file: {e}")
        return _smart_fallback_detection(file_path)

    preview_text = ''.join(lines)

    # Check if OpenAI is available
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[INFO] OpenAI API key not set, using automatic detection")
        return _smart_fallback_detection(file_path)

    prompt = f"""Analyze this CSV data sample and determine its structure:

```
{preview_text}
```

I need you to identify:
1. How many rows to skip (headers, metadata, etc.) before the actual time-series data starts
2. Which column contains TIME data (0-indexed)
3. Which column contains the VALUES to analyze (typically voltage, current, sensor reading)
4. What label best describes the values column

Requirements:
- Time column should have monotonically increasing numerical values
- Values column should contain the measurement data (not time, not indices)
- Skip rows should account for any non-data rows at the start

Respond with ONLY a JSON object (no markdown, no explanation):
{{
    "skip_rows": <integer>,
    "time_column": <integer>,
    "values_column": <integer>,
    "values_label": "<descriptive label with units>"
}}"""

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a data analyst expert at detecting CSV file structures. Respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            timeout=30.0  # 30 second timeout
        )

        # Safely extract response
        if not response.choices or len(response.choices) == 0:
            raise ValueError("No response from OpenAI")

        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from OpenAI")

        response_text = content.strip()
        response_text = response_text.replace("```json", "").replace("```", "").strip()
        structure = json.loads(response_text)

        # Validate the structure
        structure = _validate_structure(structure)

    except json.JSONDecodeError as e:
        print(f"[WARN] Could not parse AI response as JSON: {e}, using smart fallback")
        structure = _smart_fallback_detection(file_path)
    except Exception as e:
        # Fallback to smart detection if AI fails
        print(f"[WARN] AI CSV detection failed: {e}, using smart fallback")
        structure = _smart_fallback_detection(file_path)

    # Final validation
    required_keys = ["skip_rows", "time_column", "values_column", "values_label"]
    if not all(k in structure for k in required_keys):
        print("[WARN] Structure missing required keys, using smart fallback")
        structure = _smart_fallback_detection(file_path)

    return structure


def generate_database_metadata(
    label: str,
    csv_files: List[Path],
    source_folder: Path,
    database_label_dir: Path,
    time_column: int,
    values_column: int,
    values_label: str,
    skip_rows: int,
    time_interval: float,
    chunk_duration: float,
    padding_duration: float,
    total_chunks: int,
    chunk_range: tuple
) -> Dict:
    """
    Generate metadata for processed database folder.

    Returns metadata dict suitable for scientists viewing the data.
    """
    # Sample first CSV to get additional info
    sample_file = csv_files[0]
    df = pd.read_csv(sample_file, skiprows=skip_rows, header=None)

    time = df.iloc[:, time_column].values
    values = df.iloc[:, values_column].values

    # Calculate folder size
    folder_size_bytes = sum(f.stat().st_size for f in database_label_dir.glob("*.csv"))

    metadata = {
        "generated_at": datetime.now().isoformat(),
        "classification_label": label,
        "source_folder": source_folder.name,

        # Data description
        "data_type": f"Time-series: {values_label}",
        "measurement_type": values_label,

        # Processing parameters
        "processing": {
            "interpolation_interval": time_interval,
            "chunk_duration": chunk_duration,
            "padding_duration": padding_duration,
            "interpolation": "linear",
            "time_length": chunk_duration + 2 * padding_duration
        },

        # CSV structure
        "source_csv_structure": {
            "time_column": time_column,
            "values_column": values_column,
            "skip_rows": skip_rows
        },

        # Dataset statistics
        "dataset": {
            "total_chunks": total_chunks,
            "chunk_range": f"{label}_{chunk_range[0]:04d} to {label}_{chunk_range[1]:04d}",
            "source_files_count": len(csv_files),
            "samples_per_chunk": int((chunk_duration + 2 * padding_duration) / time_interval) + 1,
            "folder_size_bytes": folder_size_bytes,
            "folder_size_mb": round(folder_size_bytes / (1024 * 1024), 2)
        },

        # Sample statistics from first file
        "sample_statistics": {
            "original_sampling_rate": f"{1.0 / np.mean(np.diff(time)):.2f} Hz",
            "value_range": [float(np.min(values)), float(np.max(values))],
            "value_mean": float(np.mean(values)),
            "value_std": float(np.std(values))
        }
    }

    return metadata


def generate_raw_database_metadata(
    import_folder_name: str,
    source_path: Path,
    csv_files: List[Path],
    subfolder_structure: List[str]
) -> Dict:
    """
    Generate metadata for raw_database imported folder.
    
    Returns metadata dict describing the imported raw data.
    """
    # Get file statistics
    file_sizes = [f.stat().st_size for f in csv_files]
    
    metadata = {
        "imported_at": datetime.now().isoformat(),
        "import_folder_name": import_folder_name,
        "source_path": str(source_path),
        
        # Structure
        "structure": {
            "total_csv_files": len(csv_files),
            "subfolders": subfolder_structure,
            "subfolder_count": len(subfolder_structure)
        },
        
        # File statistics
        "file_statistics": {
            "total_size_bytes": sum(file_sizes),
            "total_size_mb": sum(file_sizes) / (1024 * 1024),
            "average_file_size_bytes": np.mean(file_sizes),
            "largest_file_bytes": max(file_sizes),
            "smallest_file_bytes": min(file_sizes)
        },
        
        # Sample file info (from first file)
        "sample_file": {
            "name": csv_files[0].name,
            "size_bytes": csv_files[0].stat().st_size,
            "relative_path": str(csv_files[0].relative_to(source_path))
        }
    }
    
    return metadata


def save_metadata(metadata: Dict, output_path: Path) -> None:
    """Save metadata dict to JSON file."""
    with open(output_path, 'w') as f:
        json.dump(metadata, indent=2, fp=f)
    
    print(f"✓ Saved metadata: {output_path}")