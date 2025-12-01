"""
Aryan Senthil's Chat Agent
==========================
A comprehensive agent for Aryan Senthil's sensor data application.
Uses direct Python function calls instead of HTTP API calls for fast execution.

Usage:
    from agent import list_datasets, start_training, run_inference
    # Call functions directly
"""

import os
import re
import json
import time
import shutil
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from openai import OpenAI

# Import settings and constants
from settings.constants import (
    BACKEND_DIR,
    DATABASE_DIR,
    RAW_DATABASE_DIR,
    MODELS_DIR,
    REPORTS_DIR,
    METADATA_FILENAME,
    OPENAI_MODEL,
)

# Initialize OpenAI client once
_openai_client = None

def _get_openai_client() -> OpenAI:
    """Get or create the OpenAI client."""
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _openai_client


# ============================================================================
# Helper Functions (from api.py)
# ============================================================================

def _format_file_size(size_bytes: int) -> str:
    """Convert bytes to human-readable size."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"


def _get_folder_size(folder_path: Path) -> int:
    """Calculate total size of all files in a folder."""
    total = 0
    for f in folder_path.iterdir():
        if f.is_file():
            total += f.stat().st_size
    return total


def _parse_measurement_type(measurement_type: str) -> tuple[str, str]:
    """Parse measurement type string like 'Current (pA)' into measurement and unit."""
    if "(" in measurement_type and ")" in measurement_type:
        measurement = measurement_type.split("(")[0].strip()
        unit = measurement_type.split("(")[1].replace(")", "").strip()
        return measurement, unit
    return measurement_type, ""


def _load_metadata(label_dir: Path) -> Optional[dict]:
    """Load metadata.json from a label directory."""
    metadata_path = label_dir / METADATA_FILENAME
    if metadata_path.exists():
        with open(metadata_path) as f:
            return json.load(f)
    return None


# ============================================================================
# Data Management Tools
# ============================================================================

def list_datasets() -> dict:
    """
    Get all processed datasets/labels in the database.

    Returns:
        dict: Contains 'status' and either 'datasets' list or 'error_message'.
              Each dataset has: id, label, chunks, measurement, unit, stats, description, etc.

    Use this to see what data is available for training.
    """
    try:
        datasets = []

        if not DATABASE_DIR.exists():
            return {"status": "success", "message": "No datasets found in database.", "datasets": [], "count": 0}

        for label_dir in DATABASE_DIR.iterdir():
            if label_dir.is_dir():
                metadata = _load_metadata(label_dir)
                if metadata:
                    measurement, unit = _parse_measurement_type(metadata.get("measurement_type", "Current (pA)"))
                    processing = metadata.get("processing", {})
                    dataset_info = metadata.get("dataset", {})
                    stats_info = metadata.get("sample_statistics", {})
                    ai_metadata = metadata.get("ai_metadata", {})
                    value_range = stats_info.get("value_range", [0, 0])
                    folder_size = _get_folder_size(label_dir)

                    datasets.append({
                        "id": label_dir.name,
                        "label": label_dir.name,
                        "chunks": dataset_info.get("total_chunks", 0),
                        "measurement": f"{measurement} ({unit})",
                        "folder_size": _format_file_size(folder_size),
                        "description": ai_metadata.get("description", "No AI description yet"),
                        "quality_score": ai_metadata.get("quality_score"),
                        "suggested_architecture": ai_metadata.get("suggested_architecture"),
                    })

        if not datasets:
            return {"status": "success", "message": "No datasets found in database.", "datasets": [], "count": 0}

        # Sort by folder name
        datasets.sort(key=lambda d: d["label"])
        return {"status": "success", "datasets": datasets, "count": len(datasets)}

    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def get_dataset_details(label_id: str) -> dict:
    """
    Get detailed information about a specific dataset.

    Args:
        label_id: The dataset label ID (e.g., "crushcore_0.75", "disbond_1.0")

    Returns:
        dict: Complete dataset info including statistics, file count, AI metadata,
              samples per chunk, duration, interpolation settings, etc.

    Use this to examine a dataset before training or to check processing parameters.
    """
    try:
        label_dir = DATABASE_DIR / label_id

        if not label_dir.exists():
            return {"status": "error", "error_message": f"Label '{label_id}' not found"}

        metadata = _load_metadata(label_dir)
        if not metadata:
            return {"status": "error", "error_message": f"Metadata not found for label '{label_id}'"}

        measurement, unit = _parse_measurement_type(metadata.get("measurement_type", "Current (pA)"))
        processing = metadata.get("processing", {})
        dataset_info = metadata.get("dataset", {})
        stats_info = metadata.get("sample_statistics", {})
        ai_metadata = metadata.get("ai_metadata", {})
        value_range = stats_info.get("value_range", [0, 0])
        folder_size = _get_folder_size(label_dir)

        return {
            "status": "success",
            "dataset": {
                "id": label_id,
                "label": label_id,
                "chunks": dataset_info.get("total_chunks", 0),
                "samples_per_chunk": dataset_info.get("samples_per_chunk", 101),
                "measurement": f"{measurement} ({unit})",
                "duration_per_chunk": f"{processing.get('time_length', 10.0)}s",
                "total_duration": f"{processing.get('time_length', 10.0)}s",
                "time_interval": f"{processing.get('interpolation_interval', 0.1)}s",
                "interpolation_interval": f"{processing.get('interpolation_interval', 0.1)}s",
                "folder_size": _format_file_size(folder_size),
                "source_file": metadata.get("source_folder", "unknown"),
                "last_updated": datetime.fromisoformat(metadata.get("generated_at", datetime.now().isoformat())).strftime("%b %d, %Y %H:%M:%S"),
                "stats": {
                    "min": value_range[0] if len(value_range) > 0 else 0,
                    "max": value_range[1] if len(value_range) > 1 else 0,
                    "sampling_rate": stats_info.get("original_sampling_rate", "N/A")
                },
                "ai_metadata": {
                    "description": ai_metadata.get("description"),
                    "category": ai_metadata.get("category"),
                    "quality_score": ai_metadata.get("quality_score"),
                    "suggested_architecture": ai_metadata.get("suggested_architecture")
                }
            }
        }

    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def browse_directories(path: Optional[str] = None) -> dict:
    """
    Browse directories on the server to find folders containing raw sensor data.

    Args:
        path: Directory path to browse. If None, starts at user's home directory.

    Returns:
        dict: List of files/folders with their paths and whether they are directories.

    Use this to navigate the file system and locate raw data folders for ingestion.
    """
    try:
        if not path:
            path = str(Path.home())

        target_path = Path(path)

        if not target_path.exists():
            return {"status": "error", "error_message": f"Path does not exist: {path}"}

        if not target_path.is_dir():
            return {"status": "error", "error_message": f"Path is not a directory: {path}"}

        items = []

        # Add parent directory option
        if target_path.parent != target_path:
            items.append({
                "name": "..",
                "path": str(target_path.parent),
                "is_directory": True
            })

        for item in sorted(target_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            # Skip hidden files/folders
            if item.name.startswith('.'):
                continue
            items.append({
                "name": item.name,
                "path": str(item),
                "is_directory": item.is_dir()
            })

        return {
            "status": "success",
            "current_path": path,
            "items": items
        }

    except PermissionError:
        return {"status": "error", "error_message": f"Permission denied: {path}"}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def suggest_label(folder_path: str) -> dict:
    """
    Use AI to suggest a classification label name based on folder path.

    Args:
        folder_path: Full path to the folder containing sensor data

    Returns:
        dict: Contains 'status' and 'suggested_label' with the suggested classification label.

    Helpful when ingesting new data - generates clean, descriptive labels like
    "crushcore_0.75" from folder names like "split_data_0.75_crushcore_test".
    """
    try:
        folder_name = Path(folder_path).name
        client = _get_openai_client()

        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": """You are a helper that generates classification labels for sensor data folders.
Given a folder path or name, extract a clean, descriptive label suitable for use in machine learning datasets.

Rules:
- Use only lowercase letters, numbers, underscores, and dots
- NO spaces - use underscores instead
- Keep it concise but descriptive
- Extract the key identifying information (material type, test condition, measurement value)
- Examples:
  - "split_data_0.75_crushcore" -> "0.75_crushcore"
  - "OneDrive_1_11-24-2025 copy/disbond_test_1.0" -> "disbond_1.0"
  - "normal_samples_batch2" -> "normal"
  - "impact_damage_severe" -> "impact_severe"

Return ONLY the label, nothing else."""
                },
                {
                    "role": "user",
                    "content": f"Generate a classification label for this folder: {folder_path}"
                }
            ],
            temperature=0.3
        )

        suggested_label = response.choices[0].message.content.strip()
        # Clean up the label
        suggested_label = re.sub(r'[^a-zA-Z0-9_.-]', '_', suggested_label)
        suggested_label = re.sub(r'_+', '_', suggested_label)
        suggested_label = suggested_label.strip('_')

        return {
            "status": "success",
            "suggested_label": suggested_label,
            "message": None
        }

    except Exception as e:
        # Fallback: extract from folder name using simple rules
        label = folder_name
        label = re.sub(r'^split_data_', '', label)
        label = re.sub(r'^data_', '', label)
        label = re.sub(r'[^a-zA-Z0-9_.-]', '_', label)
        label = re.sub(r'_+', '_', label)
        label = label.strip('_').lower()

        return {
            "status": "success",
            "suggested_label": label if label else "dataset",
            "message": f"Used fallback extraction: {str(e)}"
        }


def ingest_data(
    folder_path: str,
    label: str,
    time_interval: float = 0.1,
    chunk_duration: float = 8.0,
    padding: float = 1.0
) -> dict:
    """
    Process and ingest raw sensor data from a folder into the database.

    Args:
        folder_path: Full path to folder containing CSV files with sensor data
        label: Classification label for this data (e.g., "crushcore_0.75", "disbond_1.0")
        time_interval: Time interval for interpolation in seconds (default: 0.1)
        chunk_duration: Duration of each data chunk in seconds (default: 8.0)
        padding: Padding duration in seconds (default: 1.0)

    Returns:
        dict: Success status and message. Ingestion runs synchronously.

    AI metadata is automatically generated after completion.
    """
    try:
        from database_management import ingest_sensor_data
        from settings import configs

        folder = Path(folder_path)
        if not folder.exists():
            return {"status": "error", "error_message": f"Folder path does not exist: {folder_path}"}

        if not folder.is_dir():
            return {"status": "error", "error_message": f"Path is not a directory: {folder_path}"}

        # Validate label
        label = label.strip()
        if not label:
            return {"status": "error", "error_message": "Classification label cannot be empty"}

        # Run ingestion directly (synchronously for the agent)
        original_interval = configs.DB_TIME_INTERVAL
        original_chunk = configs.DB_CHUNK_DURATION
        original_padding = configs.DB_PADDING_DURATION

        try:
            configs.DB_TIME_INTERVAL = time_interval
            configs.DB_CHUNK_DURATION = chunk_duration
            configs.DB_PADDING_DURATION = padding

            ingest_sensor_data(folder_path, label)

            # Auto-generate AI metadata after ingestion
            generate_dataset_metadata(label)

        finally:
            # Restore original configs
            configs.DB_TIME_INTERVAL = original_interval
            configs.DB_CHUNK_DURATION = original_chunk
            configs.DB_PADDING_DURATION = original_padding

        return {
            "status": "success",
            "message": f"Data ingestion completed for label '{label}'",
            "label": label,
            "note": "Use list_datasets() to see the new dataset."
        }

    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def delete_dataset(label_id: str, delete_raw: bool = True) -> dict:
    """
    Delete a processed dataset and optionally its raw data.

    Args:
        label_id: The dataset label ID to delete (e.g., "crushcore_0.75")
        delete_raw: Whether to also delete the raw data folder (default: True)

    Returns:
        dict: Success status and deletion details.

    WARNING: This permanently removes data. Use with caution.
    """
    try:
        from database_management import delete_dataset as db_delete_dataset

        label_dir = DATABASE_DIR / label_id

        if not label_dir.exists():
            return {"status": "error", "error_message": f"Label '{label_id}' not found"}

        result = db_delete_dataset(label_id, delete_raw=delete_raw)

        if not result["success"]:
            return {"status": "error", "error_message": result["message"]}

        return {
            "status": "success",
            "message": f"Dataset '{label_id}' deleted successfully",
            "deleted_processed": result["deleted_processed"],
            "deleted_raw": result["deleted_raw"]
        }

    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def generate_dataset_metadata(label_id: str) -> dict:
    """
    Use AI to generate description, category, quality score, and training tips for a dataset.

    Args:
        label_id: The dataset label ID (e.g., "crushcore_0.75")

    Returns:
        dict: AI-generated metadata including description, category, quality_score,
              suggested_architecture, and training_tips.

    Analyzes dataset statistics and generates insights for better training decisions.
    """
    try:
        label_dir = DATABASE_DIR / label_id

        if not label_dir.exists():
            return {"status": "error", "error_message": f"Label '{label_id}' not found"}

        metadata = _load_metadata(label_dir)
        if not metadata:
            return {"status": "error", "error_message": f"Metadata not found for label '{label_id}'"}

        # Prepare context for GPT
        processing = metadata.get("processing", {})
        dataset_info = metadata.get("dataset", {})
        stats_info = metadata.get("sample_statistics", {})
        value_range = stats_info.get("value_range", [0, 0])

        context = f"""
Dataset Label: {label_id}
Source Folder: {metadata.get("source_folder", "unknown")}
Data Type: {metadata.get("data_type", "unknown")}
Measurement Type: {metadata.get("measurement_type", "unknown")}

Processing Parameters:
- Interpolation Interval: {processing.get("interpolation_interval", "N/A")}
- Chunk Duration: {processing.get("chunk_duration", "N/A")}s
- Time Length: {processing.get("time_length", "N/A")}s
- Interpolation Method: {processing.get("interpolation", "N/A")}

Dataset Statistics:
- Total Chunks: {dataset_info.get("total_chunks", 0)}
- Samples per Chunk: {dataset_info.get("samples_per_chunk", 0)}
- Source Files Count: {dataset_info.get("source_files_count", 0)}
- Folder Size: {dataset_info.get("folder_size_mb", 0):.2f} MB

Sample Statistics:
- Original Sampling Rate: {stats_info.get("original_sampling_rate", "N/A")}
- Value Range: [{value_range[0] if len(value_range) > 0 else 0}, {value_range[1] if len(value_range) > 1 else 0}]
- Mean: {stats_info.get("value_mean", 0):.4f}
- Std Dev: {stats_info.get("value_std", 0):.4f}
"""

        client = _get_openai_client()

        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": """You are an AI assistant specialized in analyzing sensor data datasets for machine learning.
Given dataset metadata, provide:
1. A concise description (2-3 sentences) explaining what this dataset represents
2. A category (e.g., "structural_damage", "material_testing", "vibration_analysis", "electrical_signal", etc.)
3. A quality score (0.0-1.0) based on data completeness, sample size, and statistics
4. A suggested architecture ("CNN" or "ResNet") based on the data characteristics
5. 2-3 training tips specific to this dataset

Respond in JSON format:
{
    "description": "...",
    "category": "...",
    "quality_score": 0.85,
    "suggested_architecture": "CNN",
    "training_tips": ["tip1", "tip2", "tip3"]
}"""
                },
                {
                    "role": "user",
                    "content": f"Analyze this sensor dataset and provide metadata:\n\n{context}"
                }
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)

        # Normalize suggested architecture
        suggested_arch = result.get("suggested_architecture", "CNN")
        if suggested_arch and isinstance(suggested_arch, str):
            suggested_arch_upper = suggested_arch.strip().upper()
            if "RESNET" in suggested_arch_upper:
                suggested_arch = "ResNet"
            else:
                suggested_arch = "CNN"
        else:
            suggested_arch = "CNN"

        # Save AI metadata back to the metadata.json file
        metadata["ai_metadata"] = {
            "description": result.get("description", ""),
            "category": result.get("category", ""),
            "quality_score": result.get("quality_score", 0.5),
            "suggested_architecture": suggested_arch,
            "training_tips": result.get("training_tips", []),
            "generated_at": datetime.now().isoformat()
        }

        metadata_path = label_dir / METADATA_FILENAME
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        return {
            "status": "success",
            "label_id": label_id,
            "description": result.get("description", ""),
            "category": result.get("category", ""),
            "quality_score": result.get("quality_score", 0.5),
            "suggested_architecture": suggested_arch,
            "training_tips": result.get("training_tips", [])
        }

    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def list_raw_folders() -> dict:
    """
    Get all raw data folders that have been imported but not yet processed.

    Returns:
        dict: List of folders with name, file count, size, and import date.

    Shows the raw_database contents before processing/ingestion.
    """
    try:
        folders = []

        if not RAW_DATABASE_DIR.exists():
            return {"status": "success", "message": "No raw folders found.", "folders": [], "count": 0}

        for folder_dir in RAW_DATABASE_DIR.iterdir():
            if folder_dir.is_dir():
                # Get files in folder
                files = []
                total_size = 0

                for csv_file in sorted(folder_dir.glob("*.csv")):
                    size = csv_file.stat().st_size
                    total_size += size
                    files.append({
                        "name": csv_file.name,
                        "size": _format_file_size(size)
                    })

                # Load metadata if exists
                metadata_path = folder_dir / METADATA_FILENAME
                import_date = datetime.now()
                if metadata_path.exists():
                    with open(metadata_path) as f:
                        raw_meta = json.load(f)
                        import_date = datetime.fromisoformat(raw_meta.get("imported_at", datetime.now().isoformat()))

                folders.append({
                    "id": folder_dir.name,
                    "name": folder_dir.name,
                    "file_count": len(files),
                    "size": _format_file_size(total_size),
                    "imported_date": import_date.strftime("%b %d, %Y")
                })

        if not folders:
            return {"status": "success", "message": "No raw folders found.", "folders": [], "count": 0}

        return {"status": "success", "folders": folders, "count": len(folders)}

    except Exception as e:
        return {"status": "error", "error_message": str(e)}


# ============================================================================
# Model Training Tools
# ============================================================================

def list_models() -> dict:
    """
    Get all trained models with their accuracy, architecture, and training details.

    Returns:
        dict: List of models with id, name, accuracy, loss, architecture, date, etc.

    Shows all models available for inference or analysis.
    """
    try:
        models = []

        if not MODELS_DIR.exists():
            return {"status": "success", "message": "No trained models found.", "models": [], "count": 0}

        for model_dir in MODELS_DIR.iterdir():
            if model_dir.is_dir() and not model_dir.name.startswith('.'):
                info_path = model_dir / "model_info.json"

                if info_path.exists():
                    with open(info_path) as f:
                        info = json.load(f)
                else:
                    # Skip models without info
                    continue

                test_acc = info.get('test_accuracy', info.get('accuracy', 0))
                training_time = info.get('training_time', 0.0)

                models.append({
                    "id": model_dir.name,
                    "name": info.get("name", model_dir.name),
                    "accuracy": f"{info.get('accuracy', 0) * 100:.1f}%",
                    "loss": f"{info.get('loss', 0):.4f}",
                    "architecture": info.get("architecture", "Unknown"),
                    "date": datetime.fromisoformat(info.get("created_at", datetime.now().isoformat())).strftime("%Y-%m-%d %H:%M:%S"),
                    "training_time": training_time,
                    "has_report": info.get("report_path") is not None
                })

        if not models:
            return {"status": "success", "message": "No trained models found.", "models": [], "count": 0}

        # Sort by date (newest first)
        models.sort(key=lambda m: m["date"], reverse=True)
        return {"status": "success", "models": models, "count": len(models)}

    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def get_model_details(model_id: str) -> dict:
    """
    Get detailed information about a specific trained model.

    Args:
        model_id: The model ID (folder name, e.g., "cnn_crushcore_disbond")

    Returns:
        dict: Complete model info including accuracy, loss, architecture, training_time,
              report_path, and path to model files.

    Use this to examine model performance before running inference.
    """
    try:
        model_dir = MODELS_DIR / model_id

        if not model_dir.exists():
            return {"status": "error", "error_message": f"Model '{model_id}' not found"}

        info_path = model_dir / "model_info.json"
        if not info_path.exists():
            return {"status": "error", "error_message": f"Model info not found for '{model_id}'"}

        with open(info_path) as f:
            info = json.load(f)

        test_acc = info.get('test_accuracy', info.get('accuracy', 0))
        training_time = info.get('training_time', 0.0)

        return {
            "status": "success",
            "model": {
                "id": model_id,
                "name": info.get("name", model_id),
                "accuracy": f"{info.get('accuracy', 0) * 100:.1f}%",
                "test_accuracy": f"{test_acc * 100:.1f}%",
                "loss": f"{info.get('loss', 0):.4f}",
                "architecture": info.get("architecture", "Unknown"),
                "date": datetime.fromisoformat(info.get("created_at", datetime.now().isoformat())).strftime("%Y-%m-%d %H:%M:%S"),
                "training_time_seconds": training_time,
                "path": str(model_dir),
                "report_path": info.get("report_path")
            }
        }

    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def suggest_model_name(labels: list, architecture: str) -> dict:
    """
    Use AI to suggest a model name based on selected labels and architecture.

    Args:
        labels: List of dataset labels that will be used for training
                (e.g., ["crushcore_0.75", "disbond_1.0"])
        architecture: Model architecture type ("CNN" or "ResNet")

    Returns:
        dict: Suggested model name that avoids conflicts with existing models.

    Generates concise, descriptive names like "cnn_crushcore_disbond".
    """
    try:
        # Get existing model names to avoid duplicates
        existing_names = set()
        if MODELS_DIR.exists():
            for model_dir in MODELS_DIR.iterdir():
                if model_dir.is_dir() and not model_dir.name.startswith('.'):
                    existing_names.add(model_dir.name.lower())

        client = _get_openai_client()
        existing_names_str = ", ".join(sorted(existing_names)) if existing_names else "none"

        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": f"""You are a helper that generates model names for neural network training.
Given a list of classification labels and architecture type, create a concise, descriptive model name.

Rules:
- Use only lowercase letters, numbers, and underscores
- NO spaces - use underscores instead
- Keep it short but descriptive (max 30 chars)
- Include the architecture type abbreviated (cnn, resnet)
- Include key info from the labels
- IMPORTANT: Do NOT use any of these existing names: [{existing_names_str}]
- If your preferred name already exists, append a number like _2, _3, etc.
- Examples:
  - labels: ["crushcore", "disbond"], arch: CNN -> "cnn_crushcore_disbond"
  - labels: ["normal", "impact_severe"], arch: ResNet -> "resnet_impact_classifier"
  - If "cnn_crushcore_disbond" exists -> "cnn_crushcore_disbond_2"

Return ONLY the model name, nothing else."""
                },
                {
                    "role": "user",
                    "content": f"Generate a model name for:\nLabels: {labels}\nArchitecture: {architecture}"
                }
            ],
            temperature=0.3
        )

        suggested_name = response.choices[0].message.content.strip()
        # Clean up the name
        suggested_name = re.sub(r'[^a-zA-Z0-9_]', '_', suggested_name)
        suggested_name = re.sub(r'_+', '_', suggested_name)
        suggested_name = suggested_name.strip('_').lower()

        # Double-check: if name still exists, append a number
        if suggested_name in existing_names:
            counter = 2
            base_name = suggested_name
            while f"{base_name}_{counter}" in existing_names:
                counter += 1
            suggested_name = f"{base_name}_{counter}"

        return {
            "status": "success",
            "suggested_name": suggested_name,
            "message": None
        }

    except Exception as e:
        # Fallback: generate simple name
        arch_short = architecture.lower()[:6]
        if labels:
            label_part = labels[0][:10].lower()
            name = f"{arch_short}_{label_part}_model"
        else:
            name = f"{arch_short}_model"

        name = re.sub(r'[^a-zA-Z0-9_]', '_', name)

        return {
            "status": "success",
            "suggested_name": name,
            "message": f"Used fallback: {str(e)}"
        }


# Training job storage (in-memory for the agent, syncs with training_jobs.json)
_TRAINING_JOBS_FILE = BACKEND_DIR / "training_jobs.json"

def _load_training_jobs() -> dict:
    """Load training jobs from disk."""
    if _TRAINING_JOBS_FILE.exists():
        try:
            with open(_TRAINING_JOBS_FILE) as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def _save_training_jobs(jobs: dict):
    """Save training jobs to disk."""
    with open(_TRAINING_JOBS_FILE, "w") as f:
        json.dump(jobs, f, indent=2)


def start_training(
    model_name: str,
    labels: list,
    architecture: str = "CNN",
    generate_report: bool = True,
    use_llm: bool = True
) -> dict:
    """
    Start training a neural network model on selected datasets.

    Args:
        model_name: Name for the model being trained (e.g., "my_classifier")
        labels: List of dataset labels to train on (e.g., ["crushcore_0.75", "disbond_1.0"])
        architecture: Model architecture - "CNN" or "ResNet" (default: "CNN")
        generate_report: Whether to generate a PDF training report (default: True)
        use_llm: Whether to use LLM for report insights (default: True)

    Returns:
        dict: Contains 'job_id' for tracking training progress.

    Training runs in background. Use get_training_status() to monitor progress.
    """
    try:
        # Validate labels exist
        for label in labels:
            label_dir = DATABASE_DIR / label
            if not label_dir.exists():
                return {"status": "error", "error_message": f"Label '{label}' not found"}

        # Create job ID
        job_id = str(uuid.uuid4())[:8]

        # Load existing jobs and add new one
        training_jobs = _load_training_jobs()
        training_jobs[job_id] = {
            "job_id": job_id,
            "model_name": model_name,
            "labels": labels,
            "architecture": architecture,
            "status": "pending",
            "current_step": 0,
            "current_epoch": None,
            "total_epochs": 50,
            "progress_message": "Initializing...",
            "error_message": None,
            "result": None,
            "created_at": datetime.now().isoformat(),
        }
        _save_training_jobs(training_jobs)

        # Start training in background thread
        def run_training_job():
            from training import run_training
            from training.config import CNNConfig, ResNetConfig
            import tensorflow as tf

            def update_job(updates: dict):
                jobs = _load_training_jobs()
                if job_id in jobs:
                    jobs[job_id].update(updates)
                    _save_training_jobs(jobs)

            # Epoch progress callback
            class EpochProgressCallback(tf.keras.callbacks.Callback):
                def __init__(self, total_epochs: int, update_fn):
                    super().__init__()
                    self.total_epochs = total_epochs
                    self.update_fn = update_fn

                def on_epoch_begin(self, epoch, logs=None):
                    self.update_fn({
                        "current_epoch": epoch + 1,
                        "total_epochs": self.total_epochs,
                        "progress_message": f"Training epoch {epoch + 1}/{self.total_epochs}..."
                    })

                def on_epoch_end(self, epoch, logs=None):
                    acc = logs.get('accuracy', 0) if logs else 0
                    val_acc = logs.get('val_accuracy', 0) if logs else 0
                    self.update_fn({
                        "current_epoch": epoch + 1,
                        "progress_message": f"Epoch {epoch + 1}/{self.total_epochs} - Acc: {acc:.3f}, Val Acc: {val_acc:.3f}"
                    })

            try:
                update_job({
                    "status": "preparing",
                    "current_step": 1,
                    "progress_message": "Preparing data..."
                })

                # Collect data paths
                data_paths = []
                for label in labels:
                    label_dir = DATABASE_DIR / label
                    if label_dir.exists():
                        data_paths.append(str(label_dir))

                if not data_paths:
                    raise ValueError("No data found for selected labels")

                # Create models directory
                MODELS_DIR.mkdir(parents=True, exist_ok=True)
                save_dir = str(MODELS_DIR / model_name)

                # Get config
                if architecture.lower() == "resnet":
                    config = ResNetConfig()
                else:
                    config = CNNConfig()
                total_epochs = config.epochs

                update_job({
                    "total_epochs": total_epochs,
                    "status": "building",
                    "current_step": 2,
                    "progress_message": "Building model..."
                })

                epoch_callback = EpochProgressCallback(total_epochs, update_job)

                update_job({
                    "status": "training",
                    "current_step": 3,
                    "progress_message": "Training model..."
                })

                # Run training
                result = run_training(
                    paths=data_paths,
                    save_dir=save_dir,
                    model_type=architecture.lower(),
                    model_name=model_name,
                    generate_report=generate_report,
                    use_llm=use_llm,
                    verbose=True,
                    extra_callbacks=[epoch_callback],
                )

                training_result = {
                    "accuracy": f"{result.training_result.test_accuracy * 100:.1f}%",
                    "loss": f"{result.training_result.test_loss:.4f}",
                    "model_path": save_dir,
                    "report_path": result.report_path,
                }

                update_job({
                    "status": "complete",
                    "current_step": 4,
                    "progress_message": "Training complete!",
                    "result": training_result,
                })

                # Save model metadata
                model_metadata = {
                    "name": model_name,
                    "architecture": architecture,
                    "accuracy": result.training_result.test_accuracy,
                    "loss": result.training_result.test_loss,
                    "labels": labels,
                    "created_at": datetime.now().isoformat(),
                    "report_path": result.report_path,
                    "training_time": result.training_result.training_time,
                }

                model_dir = Path(save_dir)
                model_dir.mkdir(parents=True, exist_ok=True)
                with open(model_dir / "model_info.json", "w") as f:
                    json.dump(model_metadata, f, indent=2)

            except Exception as e:
                update_job({
                    "status": "error",
                    "error_message": str(e),
                    "progress_message": f"Error: {str(e)}"
                })

        # Start background thread
        thread = threading.Thread(target=run_training_job, daemon=True)
        thread.start()

        return {
            "status": "success",
            "job_id": job_id,
            "message": f"Training started for model '{model_name}'",
            "note": "Use get_training_status(job_id) to monitor progress."
        }

    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def get_training_status(job_id: str) -> dict:
    """
    Check the status of a running training job.

    Args:
        job_id: The training job ID returned from start_training()

    Returns:
        dict: Training status including:
            - status: "pending", "preparing", "building", "training", "complete", or "error"
            - current_epoch / total_epochs: Progress through training
            - progress_message: Human-readable status
            - result: Final metrics when complete (accuracy, loss, paths)

    Poll this to get real-time training progress.
    """
    try:
        training_jobs = _load_training_jobs()

        if job_id not in training_jobs:
            return {"status": "error", "error_message": f"Training job '{job_id}' not found"}

        job = training_jobs[job_id]

        response = {
            "status": "success",
            "job_id": job["job_id"],
            "training_status": job["status"],
            "progress_message": job.get("progress_message", ""),
        }

        if job.get("current_epoch"):
            response["current_epoch"] = job["current_epoch"]
            response["total_epochs"] = job.get("total_epochs")

        if job.get("error_message"):
            response["error_message"] = job["error_message"]

        if job.get("result"):
            response["result"] = job["result"]

        return response

    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def wait_for_training(job_id: str, poll_interval: float = 5.0, max_wait: float = 3600.0) -> dict:
    """
    Wait for a training job to complete, polling for status updates.

    Args:
        job_id: The training job ID returned from start_training()
        poll_interval: Seconds between status checks (default: 5.0)
        max_wait: Maximum seconds to wait before timeout (default: 3600 = 1 hour)

    Returns:
        dict: Final training result with accuracy, loss, and model paths.

    This is a blocking operation that waits for training to finish.
    """
    start_time = time.time()

    while (time.time() - start_time) < max_wait:
        status = get_training_status(job_id)

        if status["status"] != "success":
            return status

        training_status = status.get("training_status", "")

        if training_status == "complete":
            return {
                "status": "success",
                "message": "Training completed successfully!",
                "result": status.get("result", {})
            }

        if training_status == "error":
            return {
                "status": "error",
                "error_message": status.get("error_message", "Training failed")
            }

        time.sleep(poll_interval)

    return {"status": "error", "error_message": f"Training timed out after {max_wait} seconds"}


def delete_model(model_id: str) -> dict:
    """
    Delete a trained model and all its associated files.

    Args:
        model_id: The model ID to delete (e.g., "cnn_crushcore_disbond")

    Returns:
        dict: Success status and message.

    WARNING: Permanently removes model, weights, graphs, and training history.
    """
    try:
        model_dir = MODELS_DIR / model_id

        if not model_dir.exists():
            return {"status": "error", "error_message": f"Model '{model_id}' not found"}

        # Remove the entire model directory
        shutil.rmtree(model_dir)

        return {
            "status": "success",
            "message": f"Model '{model_id}' deleted successfully"
        }

    except Exception as e:
        return {"status": "error", "error_message": str(e)}


# ============================================================================
# Inference/Testing Tools
# ============================================================================

# Test database instance (lazy loaded)
_test_database = None

def _get_test_database():
    """Get or create the test database instance."""
    global _test_database
    if _test_database is None:
        from testing import TestDatabase, TestDatabaseConfig
        config = TestDatabaseConfig(db_root=BACKEND_DIR / "test_database")
        _test_database = TestDatabase(config)
    return _test_database


def run_inference(
    csv_path: str,
    model_id: str,
    notes: Optional[str] = None,
    tags: Optional[list] = None,
    log_to_database: bool = True
) -> dict:
    """
    Run inference/prediction on a CSV file using a trained model.

    Args:
        csv_path: Full path to the CSV file to analyze
        model_id: The trained model ID to use for prediction (e.g., "cnn_crushcore_disbond")
        notes: Optional notes about this test
        tags: Optional tags for organizing tests (e.g., ["production", "validation"])
        log_to_database: Whether to save test results to database (default: True)

    Returns:
        dict: Prediction results including:
            - predictions: List of class predictions per chunk
            - probabilities: Confidence scores per class per chunk
            - majority_class: Final prediction (majority vote)
            - majority_confidence: Confidence of majority prediction

    Automatically chunks the CSV and runs prediction on each chunk.
    """
    try:
        from testing import predict_from_csv

        csv_file = Path(csv_path)
        if not csv_file.exists():
            return {"status": "error", "error_message": f"CSV file not found: {csv_path}"}

        model_dir = MODELS_DIR / model_id
        serving_model_path = model_dir / f"{model_id}_serving"

        # Fallback to check other naming patterns
        if not serving_model_path.exists():
            for item in model_dir.iterdir() if model_dir.exists() else []:
                if item.is_dir() and item.name.endswith("_serving"):
                    serving_model_path = item
                    break

        if not serving_model_path.exists():
            return {"status": "error", "error_message": f"Serving model not found for: {model_id}"}

        # Get model name
        model_info_path = model_dir / "model_info.json"
        model_name = model_id
        if model_info_path.exists():
            with open(model_info_path) as f:
                info = json.load(f)
                model_name = info.get("name", model_id)

        result = predict_from_csv(
            csv_path=str(csv_file),
            model_path=str(serving_model_path),
            auto_detect=True,
            verbose=False,
            log_to_database=log_to_database,
            model_name=model_name,
            notes=notes,
            tags=tags
        )

        majority_class, _, majority_confidence = result.get_majority_prediction()

        # Get test_id from database if logged
        test_id = None
        if log_to_database:
            db = _get_test_database()
            tests = db.list_tests(limit=1)
            if tests:
                test_id = tests[0]["test_id"]

        return {
            "status": "success",
            "test_id": test_id,
            "predictions": result.class_names,
            "num_chunks": len(result.class_names),
            "majority_class": majority_class,
            "majority_confidence": f"{majority_confidence:.1%}",
            "probabilities": result.probabilities.tolist()
        }

    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def list_tests(
    limit: Optional[int] = None,
    model_name: Optional[str] = None,
    tags: Optional[str] = None
) -> dict:
    """
    Get all inference test results with optional filtering.

    Args:
        limit: Maximum number of tests to return
        model_name: Filter by model name
        tags: Filter by tags (comma-separated string, e.g., "production,validation")

    Returns:
        dict: List of test summaries with test_id, timestamp, csv_filename,
              model_name, majority_class, confidence, etc.

    View all past inference runs for analysis or comparison.
    """
    try:
        db = _get_test_database()

        # Parse tags from comma-separated string
        tag_list = tags.split(",") if tags else None

        tests = db.list_tests(limit=limit, model_name=model_name, tags=tag_list)

        if not tests:
            return {"status": "success", "message": "No tests found.", "tests": [], "count": 0}

        summary = []
        for t in tests:
            avg_confidence = t.get("majority_confidence", 0.0) * 100

            summary.append({
                "test_id": t["test_id"],
                "timestamp": t["timestamp"],
                "csv_filename": t.get("csv_filename", ""),
                "model_name": t.get("model_name", ""),
                "num_chunks": t.get("num_chunks", 0),
                "majority_class": t.get("majority_class", ""),
                "confidence": f"{avg_confidence:.1f}%",
                "tags": t.get("tags", [])
            })

        return {"status": "success", "tests": summary, "count": len(summary)}

    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def get_test_details(test_id: str) -> dict:
    """
    Get detailed results for a specific inference test.

    Args:
        test_id: The test ID (UUID string)

    Returns:
        dict: Complete test info including per-chunk predictions, probabilities,
              majority vote analysis, csv paths, model info, and metadata.

    Use this to examine individual chunk predictions and confidence scores.
    """
    try:
        db = _get_test_database()
        metadata = db.get_test(test_id)

        return {
            "status": "success",
            "test": {
                "test_id": metadata.test_id,
                "timestamp": metadata.timestamp,
                "csv_path": metadata.original_csv_path,
                "model_name": metadata.model_name,
                "num_chunks": metadata.num_chunks,
                "predictions": metadata.predictions,
                "probabilities": metadata.probabilities,
                "majority_class": metadata.majority_class,
                "majority_count": metadata.majority_count,
                "majority_percentage": metadata.majority_percentage,
                "notes": metadata.notes,
                "tags": metadata.tags or []
            }
        }

    except ValueError as e:
        return {"status": "error", "error_message": str(e)}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def get_test_statistics() -> dict:
    """
    Get overall statistics about all inference tests.

    Returns:
        dict: Summary including total_tests, total_size_mb, unique_models,
              unique_tags, list of models used, and list of tags.

    High-level overview of testing activity and database usage.
    """
    try:
        db = _get_test_database()
        stats = db.get_stats()

        return {
            "status": "success",
            "statistics": stats
        }

    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def delete_test(test_id: str) -> dict:
    """
    Delete a test result and all its associated data.

    Args:
        test_id: The test ID to delete

    Returns:
        dict: Success status and message.

    WARNING: Permanently removes test data including CSV, chunks, and predictions.
    """
    try:
        db = _get_test_database()
        db.delete_test(test_id)

        return {
            "status": "success",
            "message": f"Test '{test_id}' deleted successfully"
        }

    except ValueError as e:
        return {"status": "error", "error_message": str(e)}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


# ============================================================================
# Enhanced Analysis Tools
# ============================================================================

def get_workflow_guidance(workflow: str) -> dict:
    """
    Get step-by-step guidance for common workflows.

    Args:
        workflow: The workflow to get guidance for. Options: "training", "inference",
                 "data_ingestion", "model_evaluation", "troubleshooting"

    Returns:
        dict: Step-by-step guidance for the requested workflow

    Helpful for users who need guidance on how to use the system effectively.
    """
    workflows = {
        "training": {
            "title": "Model Training Workflow",
            "steps": [
                "1. Check available datasets with list_datasets()",
                "2. Review dataset details to ensure quality with get_dataset_details(label_id)",
                "3. Generate AI metadata if needed with generate_dataset_metadata(label_id)",
                "4. Get a suggested model name with suggest_model_name(labels, architecture)",
                "5. Start training with start_training(model_name, labels, architecture)",
                "6. Monitor progress with get_training_status(job_id)",
                "7. Review the generated report in list_reports()"
            ],
            "tips": [
                "Use CNN for faster training on simpler patterns",
                "Use ResNet for more complex data or when CNN underfits",
                "Always check dataset quality scores before training"
            ]
        },
        "inference": {
            "title": "Running Inference Workflow",
            "steps": [
                "1. List available models with list_models()",
                "2. Review model accuracy with get_model_details(model_id)",
                "3. Ensure your CSV file path is correct",
                "4. Run prediction with run_inference(csv_path, model_id)",
                "5. Analyze results - check majority_class and confidence",
                "6. View past tests with list_tests()"
            ],
            "tips": [
                "Use models with >90% accuracy for production",
                "Add tags to organize tests for later analysis",
                "Check per-chunk predictions for anomalies"
            ]
        },
        "data_ingestion": {
            "title": "Data Ingestion Workflow",
            "steps": [
                "1. Browse to find your data folder with browse_directories(path)",
                "2. Get a suggested label with suggest_label(folder_path)",
                "3. Start ingestion with ingest_data(folder_path, label)",
                "4. Wait for processing (runs synchronously)",
                "5. Verify with list_datasets()",
                "6. Generate AI metadata with generate_dataset_metadata(label_id)"
            ],
            "tips": [
                "Use descriptive labels like 'crushcore_0.75' or 'disbond_test'",
                "Default chunk_duration of 8.0s works well for most data",
                "AI metadata helps understand data quality"
            ]
        },
        "model_evaluation": {
            "title": "Model Evaluation Workflow",
            "steps": [
                "1. List all models with list_models()",
                "2. Compare accuracy and loss across models",
                "3. Get detailed metrics with get_model_details(model_id)",
                "4. Review training reports with list_reports()",
                "5. Run inference on validation data",
                "6. Analyze test results with get_test_details(test_id)"
            ],
            "tips": [
                "Higher accuracy and lower loss = better model",
                "Check confusion matrix in reports for class-specific performance",
                "Test on data the model hasn't seen before"
            ]
        },
        "troubleshooting": {
            "title": "Troubleshooting Guide",
            "steps": [
                "1. Check system status with get_system_status()",
                "2. Verify dataset exists with list_datasets()",
                "3. Check model exists with list_models()",
                "4. Review training status if training failed",
                "5. Check test database stats with get_test_statistics()"
            ],
            "common_issues": [
                "Model not found: Check model_id matches exactly",
                "Training failed: Check GPU memory, reduce batch size",
                "Low accuracy: Try ResNet or add more training data"
            ]
        }
    }

    workflow_key = workflow.lower().replace(" ", "_")
    if workflow_key in workflows:
        return {"status": "success", "guidance": workflows[workflow_key]}
    else:
        return {
            "status": "success",
            "available_workflows": list(workflows.keys()),
            "message": f"Unknown workflow '{workflow}'. Available: {list(workflows.keys())}"
        }


def compare_models(model_ids: list) -> dict:
    """
    Compare multiple models side by side.

    Args:
        model_ids: List of model IDs to compare (e.g., ["cnn_model1", "resnet_model2"])

    Returns:
        dict: Comparison table of model metrics including accuracy, loss, architecture.

    Helpful for deciding which model to use for production.
    """
    if not model_ids:
        return {"status": "error", "error_message": "No model IDs provided"}

    comparisons = []
    for model_id in model_ids:
        result = get_model_details(model_id)
        if result["status"] == "success":
            model = result["model"]
            comparisons.append({
                "id": model_id,
                "name": model.get("name", model_id),
                "accuracy": model.get("accuracy"),
                "loss": model.get("loss"),
                "architecture": model.get("architecture"),
                "training_time": model.get("training_time_seconds"),
                "has_report": model.get("report_path") is not None
            })
        else:
            comparisons.append({
                "id": model_id,
                "error": result.get("error_message", "Model not found")
            })

    # Find best model by accuracy
    valid_models = [c for c in comparisons if "error" not in c]
    best_model = None
    if valid_models:
        try:
            best_model = max(valid_models,
                           key=lambda x: float(str(x.get("accuracy", "0")).replace("%", "")) if x.get("accuracy") else 0)
        except:
            pass

    return {
        "status": "success",
        "comparisons": comparisons,
        "best_model": best_model["id"] if best_model else None,
        "summary": f"Compared {len(model_ids)} models. Best: {best_model['name'] if best_model else 'N/A'}"
    }


def get_dataset_summary() -> dict:
    """
    Get a high-level summary of all datasets in the database.

    Returns:
        dict: Summary statistics including total datasets, total chunks, labels,
              average quality score, and suggested architectures.

    Useful for getting an overview of available training data.
    """
    result = list_datasets()
    if result["status"] != "success":
        return result

    datasets = result.get("datasets", [])
    if not datasets:
        return {"status": "success", "message": "No datasets in database", "summary": {}}

    total_chunks = sum(ds.get("chunks", 0) for ds in datasets)
    labels = [ds.get("label") for ds in datasets]
    quality_scores = [ds.get("quality_score") for ds in datasets if ds.get("quality_score")]

    summary = {
        "total_datasets": len(datasets),
        "total_chunks": total_chunks,
        "labels": labels,
        "average_quality_score": sum(quality_scores) / len(quality_scores) if quality_scores else None,
        "architectures_suggested": {
            "CNN": sum(1 for ds in datasets if ds.get("suggested_architecture") == "CNN"),
            "ResNet": sum(1 for ds in datasets if ds.get("suggested_architecture") == "ResNet")
        }
    }

    return {"status": "success", "summary": summary}


def get_training_recommendations(labels: list) -> dict:
    """
    Get AI-powered training recommendations for selected labels.

    Args:
        labels: List of dataset labels to analyze (e.g., ["crushcore_0.75", "disbond_1.0"])

    Returns:
        dict: Training recommendations including architecture, estimated time, tips.

    Helps users make informed decisions before starting training.
    """
    if not labels:
        return {"status": "error", "error_message": "No labels provided"}

    # Analyze each dataset
    total_chunks = 0
    quality_scores = []
    suggested_archs = []

    for label in labels:
        result = get_dataset_details(label)
        if result["status"] == "success":
            ds = result["dataset"]
            total_chunks += ds.get("chunks", 0)
            ai_meta = ds.get("ai_metadata", {})
            if ai_meta.get("quality_score"):
                quality_scores.append(ai_meta["quality_score"])
            if ai_meta.get("suggested_architecture"):
                suggested_archs.append(ai_meta["suggested_architecture"])

    # Generate recommendations
    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.5

    # Architecture recommendation
    if suggested_archs.count("ResNet") > suggested_archs.count("CNN"):
        recommended_arch = "ResNet"
        arch_reason = "Based on dataset complexity analysis"
    elif total_chunks < 100:
        recommended_arch = "CNN"
        arch_reason = "CNN recommended for smaller datasets"
    else:
        recommended_arch = "CNN"
        arch_reason = "CNN is generally faster and sufficient for most cases"

    recommendations = {
        "architecture": recommended_arch,
        "architecture_reason": arch_reason,
        "estimated_training_time": "5-15 minutes" if recommended_arch == "CNN" else "15-45 minutes",
        "data_quality": "Good" if avg_quality > 0.7 else "Moderate" if avg_quality > 0.4 else "Consider reviewing data",
        "total_samples": total_chunks,
        "tips": []
    }

    if total_chunks < 50:
        recommendations["tips"].append("Consider adding more data for better generalization")
    if avg_quality < 0.6:
        recommendations["tips"].append("Run generate_dataset_metadata() to understand data quality issues")
    if len(labels) < 2:
        recommendations["tips"].append("Training requires at least 2 classes (labels)")

    return {"status": "success", "recommendations": recommendations}


def explain_results(test_id: str) -> dict:
    """
    Get a detailed explanation of inference results.

    Args:
        test_id: The test ID to explain (UUID string from list_tests())

    Returns:
        dict: Human-readable explanation of the prediction results.

    Helps users understand model predictions and confidence levels.
    """
    result = get_test_details(test_id)
    if result["status"] != "success":
        return result

    test = result["test"]
    predictions = test.get("predictions", [])
    probabilities = test.get("probabilities", [])

    # Analyze predictions
    prediction_counts = {}
    for pred in predictions:
        prediction_counts[pred] = prediction_counts.get(pred, 0) + 1

    majority = test.get("majority_class")
    majority_pct = test.get("majority_percentage", 0)

    # Build explanation
    explanation = {
        "summary": f"The model classified this data as '{majority}' with {majority_pct:.1f}% of chunks agreeing.",
        "chunk_analysis": f"Out of {len(predictions)} chunks, {prediction_counts.get(majority, 0)} were classified as '{majority}'.",
        "confidence_analysis": "",
        "prediction_distribution": prediction_counts,
        "recommendation": ""
    }

    # Analyze confidence
    if probabilities:
        avg_confidence = sum(max(p) for p in probabilities) / len(probabilities)
        explanation["confidence_analysis"] = f"Average confidence across chunks: {avg_confidence*100:.1f}%"

        if avg_confidence > 0.9:
            explanation["recommendation"] = "High confidence result. The model is very certain about this classification."
        elif avg_confidence > 0.7:
            explanation["recommendation"] = "Moderate confidence. Result is likely accurate but consider verification."
        else:
            explanation["recommendation"] = "Low confidence. Consider running additional tests or reviewing the data quality."

    # Check for inconsistent predictions
    if len(prediction_counts) > 1:
        explanation["warning"] = f"Mixed predictions detected: {prediction_counts}. This may indicate edge case data or model uncertainty."

    return {"status": "success", "explanation": explanation}


# ============================================================================
# Reporting Tools
# ============================================================================

def get_model_graphs(model_id: str) -> dict:
    """
    Get training graphs (accuracy, loss, confusion matrix) for a trained model.

    Args:
        model_id: The model ID (folder name, e.g., "cnn_crushcore_disbond")

    Returns:
        dict: Contains base64-encoded PNG images for each graph type.
              Use this to show training visualizations to the user.

    The returned images include:
    - accuracy: Training/validation accuracy over epochs
    - loss: Training/validation loss over epochs
    - confusion_matrix: Heatmap of predictions vs actual labels
    """
    try:
        import base64

        model_dir = MODELS_DIR / model_id
        graphs_dir = model_dir / "graphs"

        if not model_dir.exists():
            return {"status": "error", "error_message": f"Model '{model_id}' not found"}

        graphs = {}

        if graphs_dir.exists():
            # Read accuracy graph
            accuracy_path = graphs_dir / "accuracy.png"
            if accuracy_path.exists():
                with open(accuracy_path, "rb") as f:
                    graphs["accuracy"] = base64.b64encode(f.read()).decode("utf-8")

            # Read loss graph
            loss_path = graphs_dir / "loss.png"
            if loss_path.exists():
                with open(loss_path, "rb") as f:
                    graphs["loss"] = base64.b64encode(f.read()).decode("utf-8")

            # Read confusion matrix
            matrix_path = graphs_dir / "confusion_matrix.png"
            if matrix_path.exists():
                with open(matrix_path, "rb") as f:
                    graphs["confusion_matrix"] = base64.b64encode(f.read()).decode("utf-8")

        if not graphs:
            return {
                "status": "success",
                "message": f"No training graphs found for model '{model_id}'",
                "graphs": {}
            }

        return {
            "status": "success",
            "model_id": model_id,
            "graphs": graphs,
            "artifacts": [
                {"type": "image", "name": "Training Accuracy", "data": graphs.get("accuracy"), "format": "png"} if graphs.get("accuracy") else None,
                {"type": "image", "name": "Training Loss", "data": graphs.get("loss"), "format": "png"} if graphs.get("loss") else None,
                {"type": "image", "name": "Confusion Matrix", "data": graphs.get("confusion_matrix"), "format": "png"} if graphs.get("confusion_matrix") else None,
            ]
        }

    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def get_report_url(model_id: str) -> dict:
    """
    Get the URL to view/download a training report PDF for a model.

    Args:
        model_id: The model ID (folder name, e.g., "cnn_crushcore_disbond")

    Returns:
        dict: Contains the report URL and metadata for displaying a "View Report" button.

    Returns an artifact that can be rendered as a clickable button in the chat UI.
    """
    try:
        model_dir = MODELS_DIR / model_id

        if not model_dir.exists():
            return {"status": "error", "error_message": f"Model '{model_id}' not found"}

        # Find PDF reports
        pdf_files = list(model_dir.glob("*.pdf"))

        if not pdf_files:
            return {
                "status": "success",
                "message": f"No training report found for model '{model_id}'",
                "has_report": False
            }

        report_file = pdf_files[0]
        # Use the correct endpoint format with path query parameter
        report_path = str(report_file.absolute())
        report_url = f"/api/training/report/download?path={report_path}"

        return {
            "status": "success",
            "model_id": model_id,
            "has_report": True,
            "report_name": report_file.name,
            "report_url": report_url,
            "artifacts": [
                {
                    "type": "report",
                    "name": f"Training Report: {model_id}",
                    "url": report_url,
                    "filename": report_file.name
                }
            ]
        }

    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def read_report(model_id: str) -> dict:
    """
    Read and extract the text content from a model's training report PDF.

    Args:
        model_id: The model ID (folder name, e.g., "cnn_crushcore_disbond")

    Returns:
        dict: Contains the extracted text content from the report.
              Use this to answer user questions about a specific training report.

    This tool allows you to read the full content of a training report so you can:
    - Answer questions about the model's performance
    - Explain insights and recommendations from the report
    - Summarize the training results
    - Compare metrics mentioned in the report
    """
    try:
        import fitz  # PyMuPDF

        model_dir = MODELS_DIR / model_id

        if not model_dir.exists():
            return {"status": "error", "error_message": f"Model '{model_id}' not found"}

        # Find PDF reports
        pdf_files = list(model_dir.glob("*.pdf"))

        if not pdf_files:
            return {
                "status": "error",
                "error_message": f"No training report found for model '{model_id}'"
            }

        report_file = pdf_files[0]

        # Extract text from PDF
        doc = fitz.open(str(report_file))
        text_content = []

        for page_num, page in enumerate(doc, 1):
            page_text = page.get_text()
            if page_text.strip():
                text_content.append(f"--- Page {page_num} ---\n{page_text}")

        doc.close()

        full_text = "\n\n".join(text_content)

        return {
            "status": "success",
            "model_id": model_id,
            "report_name": report_file.name,
            "content": full_text,
            "page_count": len(text_content)
        }

    except ImportError:
        return {
            "status": "error",
            "error_message": "PDF reading library (PyMuPDF) not installed. Run: pip install pymupdf"
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def list_reports() -> dict:
    """
    Get all training reports that have been generated.

    Returns:
        dict: List of reports with id, name, size, date, model_name, and path.

    PDF reports contain training metrics, graphs, insights, and recommendations.
    """
    try:
        reports = []

        # Check models directory for reports
        if MODELS_DIR.exists():
            for model_dir in MODELS_DIR.iterdir():
                if model_dir.is_dir():
                    # Try to load model info for training_time
                    training_time = None
                    model_info_path = model_dir / "model_info.json"
                    if model_info_path.exists():
                        try:
                            with open(model_info_path) as f:
                                model_info = json.load(f)
                                training_time = model_info.get("training_time")
                        except Exception:
                            pass

                    # Look for PDF reports
                    for pdf_file in model_dir.glob("*.pdf"):
                        stat = pdf_file.stat()
                        reports.append({
                            "id": pdf_file.stem,
                            "name": pdf_file.name,
                            "size": _format_file_size(stat.st_size),
                            "date": datetime.fromtimestamp(stat.st_mtime).strftime("%b %d, %Y %H:%M"),
                            "model_name": model_dir.name,
                            "path": str(pdf_file),
                            "training_time": training_time,
                        })

        if not reports:
            return {"status": "success", "message": "No reports found.", "reports": [], "count": 0}

        # Sort by date (newest first)
        reports.sort(key=lambda r: r["date"], reverse=True)
        return {"status": "success", "reports": reports, "count": len(reports)}

    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def get_system_status() -> dict:
    """
    Check the system status.

    Returns:
        dict: System health status including directory availability.

    Use this to verify the system is properly configured.
    """
    try:
        return {
            "status": "success",
            "system_status": "ok",
            "message": "System is running",
            "directories": {
                "database": DATABASE_DIR.exists(),
                "raw_database": RAW_DATABASE_DIR.exists(),
                "models": MODELS_DIR.exists(),
            }
        }

    except Exception as e:
        return {"status": "error", "error_message": str(e)}


# ============================================================================
# Agent Definition (for compatibility with ADK if needed)
# ============================================================================

SYSTEM_INSTRUCTION = """You are a friendly AI assistant for a sensor data application.
You help users manage their data, train AI models to detect damage, and test those models.

## CRITICAL: Use Simple, Non-Technical Language

This app is for users with NO coding or machine learning experience. Always use plain English.

### Terminology Rules - ALWAYS translate technical terms:

| NEVER SAY (Technical) | ALWAYS SAY (User-Friendly) |
|----------------------|---------------------------|
| chunks | files or samples |
| inference | testing or analyzing |
| ingest / ingestion | import or add or prepare |
| preprocessing | preparing |
| dataset | data or data collection |
| architecture | model type |
| metadata | information |
| epoch | (don't mention) |
| validation split | (don't mention) |
| batch size | (don't mention) |
| sampling rate | (don't mention) |
| spectrogram | (don't mention) |
| tensor | (don't mention) |
| CSV file | data file or file |
| classification | category or type |
| accuracy/loss metrics | how well it performs |

Examples:
- BAD: "This dataset contains 78 chunks"
- GOOD: "This data collection has 78 files"

- BAD: "Running inference on your data"
- GOOD: "Testing your data" or "Analyzing your data"

- BAD: "Ingesting the raw sensor data with preprocessing"
- GOOD: "Importing and preparing your data"

- BAD: "The model achieved 85.3% accuracy with 0.42 loss"
- GOOD: "The model performs well - it correctly identifies damage 85% of the time"

## CRITICAL: Never Show File Paths

NEVER display system paths like "/home/ari/Documents/..." or anything with /backend/, /models/, etc.

- BAD: "Model saved to /home/ari/Documents/final_capstone/backend/models/cnnfier"
- GOOD: "Your model 'cnnfier' has been saved and is ready to use!"

**Exception**: If the user provides a path, just confirm: "I'll prepare the data from the folder you specified."

## CRITICAL: Never Mention Technical Settings

Do NOT mention or ask about:
- Time intervals, chunk durations, padding
- Sampling rates, Hz values
- Epochs, validation splits, batch sizes
- Any other technical parameters

Just use defaults silently.

- BAD: "I'll use time_interval=0.1s, chunk_duration=8.0s"
- GOOD: "I'll prepare this data for you."

- BAD: "Training with 1000 epochs at 1600Hz sampling rate"
- GOOD: "Starting training now. This will take a few minutes."

## Ask Simple Clarifying Questions

When information is missing, ask in plain language:

1. **Model type not specified**: "Would you like to use CNN (faster, good for most cases) or ResNet (more powerful but slower)?"
2. **Model name not given**: "What would you like to name this model?" (or suggest one)
3. **Data label not given**: "What category should I label this data as?" (or suggest one)
4. **Which model to test with**: "Which model would you like to use for testing?"

## What You Can Help With

### Managing Data
- Show what data is available
- Find new data folders on the computer
- Import and prepare new sensor data
- Remove data that's no longer needed

### Training Models
- Show trained models and how well they perform
- Help name new models
- Train new CNN or ResNet models
- Track training progress
- Show training reports

### Testing
- Test new files using trained models
- Show test history and results
- Explain what the results mean

## Typical Workflows

### Training a New Model
1. Show available data
2. Ask: CNN or ResNet?
3. Ask: What name?
4. Start training
5. **CRITICAL - When training completes, ALWAYS do ALL of the following:**
   - Tell the user the training is complete with the accuracy (e.g., "Great news! Your model finished training with 95% accuracy!")
   - **IMMEDIATELY** use `get_model_graphs(model_id)` to show the training graphs (accuracy, loss, confusion matrix)
   - **IMMEDIATELY** use `get_report_url(model_id)` to provide the View Report button
   - After showing graphs and report, say something like: "You can click 'View' on the report to see detailed insights. Would you like me to explain anything about the results, or are you ready to test this model with some data?"

### Testing Data
1. Show available models
2. Ask which model to use
3. Run the test
4. Explain results clearly
5. After explaining, suggest: "Would you like to test another file, or see the model's training details?"

### Adding New Data
1. User provides folder location
2. Suggest a category name
3. Confirm with user
4. Import the data
5. Confirm it's ready
6. Suggest next step: "Your data is ready! Would you like to train a model using this data?"

## Keep It Simple
- CNN = faster, good for most cases
- ResNet = more powerful, takes longer
- Training takes a few minutes
- Always explain results in plain terms

## Showing Graphs and Reports
When the user asks to see training graphs, model performance, or results:
- Use `get_model_graphs(model_id)` to retrieve training visualization images
- Use `get_report_url(model_id)` to provide a View Report button in the chat
- These tools return "artifacts" that will be displayed as images or clickable buttons in the chat

For example:
- "Show me how the model trained" → use get_model_graphs
- "Let me see the training report" → use get_report_url
- "Show the accuracy graph" → use get_model_graphs

## Reading and Answering Questions About Reports
When users want to know more about a training report or ask questions about it:
- Use `read_report(model_id)` to read the full text content of the PDF report
- After reading, you can answer specific questions about:
  - Model performance and accuracy
  - Insights and recommendations from the report
  - Training metrics and statistics
  - Any other details mentioned in the report
- This is useful when users say things like:
  - "What does the report say about accuracy?"
  - "Summarize the training report"
  - "What recommendations does the report have?"
  - "Tell me about the model's performance"

## Proactive Guidance
Be a helpful guide throughout the user's workflow. You are their AI assistant that helps them through the entire machine learning pipeline!

**IMPORTANT: Always suggest logical next steps:**
- After training completes: Always show the graphs AND provide the report button, then offer to explain or answer questions. Say: "Click 'View' to see the full report in the chat, or ask me any questions about the results!"
- After showing graphs: Ask if they'd like to see the detailed report or have any questions
- After showing a report: Offer to explain any part of it or answer questions about the model's performance
- After a test/inference: Explain the results clearly, then suggest: "Would you like to test another file or train a new model?"
- If the user seems stuck: Suggest next steps based on context (e.g., "Would you like to test this model with some data?")
- When user asks about a report: Use `read_report(model_id)` to read the report content, then answer their questions based on what's in the report

**Pipeline Flow Suggestions:**
1. New user → Suggest checking available data or importing new data
2. Has data, no models → Suggest training a model
3. Has trained model → Suggest testing with new data or viewing reports
4. After testing → Explain results and suggest next actions

## Handling File References
When users attach files or reference file paths in their messages:
- The file paths will be provided in the message
- Use the appropriate tool based on context (run_inference for testing, browse_directories for exploring)
- Acknowledge the files they referenced before performing actions

Be helpful, friendly, and guide users step by step.
When something goes wrong, explain simply and suggest what to try next."""


# Define all tools for the agent
ALL_TOOLS = [
    # Data Management
    list_datasets,
    get_dataset_details,
    browse_directories,
    suggest_label,
    ingest_data,
    delete_dataset,
    generate_dataset_metadata,
    list_raw_folders,

    # Model Training
    list_models,
    get_model_details,
    suggest_model_name,
    start_training,
    get_training_status,
    wait_for_training,
    delete_model,

    # Inference/Testing
    run_inference,
    list_tests,
    get_test_details,
    get_test_statistics,
    delete_test,

    # Enhanced Analysis
    get_workflow_guidance,
    compare_models,
    get_dataset_summary,
    get_training_recommendations,
    explain_results,

    # Reporting & System
    get_model_graphs,
    get_report_url,
    read_report,
    list_reports,
    get_system_status,
]


# Optional: Create ADK agent if google.adk is available
try:
    from google.adk.agents import LlmAgent
    from google.adk.models.lite_llm import LiteLlm

    root_agent = LlmAgent(
        name="damage_lab_agent",
        model=LiteLlm(model="openai/gpt-5.1"),
        description=(
            "AI assistant for Aryan Senthil's sensor data application."
            "Manages sensor datasets, trains neural network models for damage detection, "
            "and runs inference on new data."
        ),
        instruction=SYSTEM_INSTRUCTION,
        tools=ALL_TOOLS,
    )
except ImportError:
    # ADK not available, that's fine - functions can still be used directly
    root_agent = None


# ============================================================================
# CLI Runner (Optional)
# ============================================================================

def run_cli():
    """Simple CLI interface for testing the agent."""
    print("=" * 60)
    print("Aryan Senthil's Chat Agent")
    print("=" * 60)
    print("Type 'quit' or 'exit' to stop.")
    print("Type 'help' for available commands.\n")

    # Check system status
    status = get_system_status()
    if status["status"] == "success":
        print(f"System status: {status['system_status']}")
    else:
        print(f"Warning: {status.get('error_message', 'Unknown error')}")
    print()

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ['quit', 'exit']:
                print("Goodbye!")
                break

            if user_input.lower() == 'help':
                print("\nAvailable actions:")
                print("  - 'list datasets' or 'show data'")
                print("  - 'list models' or 'show models'")
                print("  - 'list tests' or 'show tests'")
                print("  - 'check status' or 'system status'")
                print("  - Ask about training, inference, or data management")
                print()
                continue

            # For a full agent experience, you would use the ADK runner here
            print("\n[Use with ADK Runner or chat_api for full agent capabilities]")
            print("Functions available: list_datasets(), list_models(), run_inference(), etc.\n")

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    run_cli()
