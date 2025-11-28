"""
Dataset Deletion Module

Provides functionality to delete processed datasets and their associated raw data.
"""

import shutil
from pathlib import Path
from typing import Optional

from .constants import DATABASE_DIR, RAW_DATABASE_DIR, METADATA_FILENAME


def delete_dataset(
    label: str,
    delete_raw: bool = True
) -> dict:
    """
    Delete a processed dataset and optionally its raw data backup.

    Parameters
    ----------
    label : str
        The classification label of the dataset to delete
    delete_raw : bool
        If True, also delete the associated raw data from raw_database/
        Default is True

    Returns
    -------
    dict
        Result with keys:
        - success: bool
        - message: str
        - deleted_processed: bool
        - deleted_raw: bool
        - processed_path: str (if deleted)
        - raw_path: str (if deleted)

    Examples
    --------
    >>> delete_dataset("0.5crushcore")
    {'success': True, 'message': 'Dataset deleted successfully', ...}

    >>> delete_dataset("normal", delete_raw=False)
    {'success': True, 'message': 'Processed data deleted (raw data kept)', ...}
    """
    result = {
        "success": False,
        "message": "",
        "deleted_processed": False,
        "deleted_raw": False,
        "processed_path": None,
        "raw_path": None
    }

    # Check for processed data directory
    processed_dir = DATABASE_DIR / label

    if not processed_dir.exists():
        result["message"] = f"Dataset '{label}' not found in database"
        return result

    # Find associated raw data folder by checking metadata
    raw_dir = None
    if delete_raw:
        # Try to find raw data folder from metadata
        metadata_path = processed_dir / METADATA_FILENAME
        if metadata_path.exists():
            import json
            try:
                with open(metadata_path) as f:
                    metadata = json.load(f)
                source_folder = metadata.get("source_folder", "")
                if source_folder:
                    # Extract folder name from source path
                    source_name = Path(source_folder).name
                    potential_raw = RAW_DATABASE_DIR / source_name
                    if potential_raw.exists():
                        raw_dir = potential_raw
            except (json.JSONDecodeError, KeyError):
                pass

        # If not found via metadata, try common naming patterns
        if raw_dir is None:
            # Try split_data_{label} pattern
            for pattern in [f"split_data_{label}", label]:
                potential = RAW_DATABASE_DIR / pattern
                if potential.exists():
                    raw_dir = potential
                    break

    # Delete processed data
    try:
        shutil.rmtree(processed_dir)
        result["deleted_processed"] = True
        result["processed_path"] = str(processed_dir)
        print(f"[OK] Deleted processed data: {processed_dir}")
    except Exception as e:
        result["message"] = f"Failed to delete processed data: {str(e)}"
        return result

    # Delete raw data if requested and found
    if delete_raw and raw_dir:
        try:
            shutil.rmtree(raw_dir)
            result["deleted_raw"] = True
            result["raw_path"] = str(raw_dir)
            print(f"[OK] Deleted raw data: {raw_dir}")
        except Exception as e:
            print(f"[WARN] Failed to delete raw data: {str(e)}")
            # Don't fail the whole operation if raw deletion fails

    result["success"] = True
    if result["deleted_raw"]:
        result["message"] = f"Dataset '{label}' and associated raw data deleted successfully"
    else:
        result["message"] = f"Dataset '{label}' deleted successfully"

    return result


def get_dataset_info(label: str) -> Optional[dict]:
    """
    Get information about a dataset before deletion.

    Parameters
    ----------
    label : str
        The classification label of the dataset

    Returns
    -------
    dict or None
        Information about the dataset, or None if not found
    """
    processed_dir = DATABASE_DIR / label

    if not processed_dir.exists():
        return None

    # Count files
    csv_files = list(processed_dir.glob("*.csv"))

    # Calculate size
    total_size = sum(f.stat().st_size for f in processed_dir.iterdir() if f.is_file())

    return {
        "label": label,
        "chunks": len(csv_files),
        "size_bytes": total_size,
        "path": str(processed_dir)
    }
