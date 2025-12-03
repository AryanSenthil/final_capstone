"""
Model deletion utilities.

This module provides comprehensive cleanup when a model is deleted,
including:
- Removing model directory and all files (including reports)
- Deleting all tests that used this model
- Cleaning training job entries in training_jobs.json
- Clearing training state persistence if it references this model
"""

import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional

# Directory paths (relative to backend)
BACKEND_DIR = Path(__file__).parent.parent
MODELS_DIR = BACKEND_DIR / "models"
TRAINING_JOBS_PATH = BACKEND_DIR / "training_jobs.json"
TRAINING_PERSISTENCE_DIR = BACKEND_DIR / "training_persistence"
TEST_DATABASE_DIR = BACKEND_DIR / "test_database"


def delete_model_complete(model_id: str) -> dict:
    """
    Comprehensively delete a model and all related metadata.

    Args:
        model_id: The model name/ID to delete

    Returns:
        dict with deletion results including what was cleaned up
    """
    results = {
        "model_directory_deleted": False,
        "reports_deleted": 0,
        "training_jobs_cleaned": 0,
        "training_state_cleared": False,
        "tests_deleted": 0,
        "errors": []
    }

    model_dir = MODELS_DIR / model_id

    # 1. Count reports (they'll be deleted with model directory)
    try:
        if model_dir.exists():
            results["reports_deleted"] = len(list(model_dir.glob("*.pdf")))
    except Exception as e:
        results["errors"].append(f"Failed to count reports: {str(e)}")

    # 2. Delete model directory
    if model_dir.exists():
        try:
            shutil.rmtree(model_dir)
            results["model_directory_deleted"] = True
        except Exception as e:
            results["errors"].append(f"Failed to delete model directory: {str(e)}")
    else:
        results["errors"].append(f"Model directory not found: {model_dir}")

    # 3. Clean up training_jobs.json
    try:
        cleaned_count = _cleanup_training_jobs(model_id)
        results["training_jobs_cleaned"] = cleaned_count
    except Exception as e:
        results["errors"].append(f"Failed to clean training jobs: {str(e)}")

    # 4. Clear training state persistence if it references this model
    try:
        cleared = _clear_training_persistence(model_id)
        results["training_state_cleared"] = cleared
    except Exception as e:
        results["errors"].append(f"Failed to clear training persistence: {str(e)}")

    # 5. Delete tests that used this model
    try:
        deleted_count = _delete_tests_for_model(model_id)
        results["tests_deleted"] = deleted_count
    except Exception as e:
        results["errors"].append(f"Failed to delete tests: {str(e)}")

    return results


def _cleanup_training_jobs(model_id: str) -> int:
    """
    Remove all training job entries for a given model from training_jobs.json.

    Args:
        model_id: The model name to remove

    Returns:
        Number of jobs removed
    """
    if not TRAINING_JOBS_PATH.exists():
        return 0

    with open(TRAINING_JOBS_PATH, 'r') as f:
        jobs = json.load(f)

    # Find and remove jobs with this model name
    jobs_to_remove = []
    for job_id, job_data in jobs.items():
        if job_data.get("model_name") == model_id:
            jobs_to_remove.append(job_id)

    # Remove the jobs
    for job_id in jobs_to_remove:
        del jobs[job_id]

    # Write back if any were removed
    if jobs_to_remove:
        with open(TRAINING_JOBS_PATH, 'w') as f:
            json.dump(jobs, f, indent=2)

    return len(jobs_to_remove)


def _clear_training_persistence(model_id: str) -> bool:
    """
    Clear training state persistence if it references the deleted model.
    This resets the training UI to a clean state.

    Args:
        model_id: The model name to check for

    Returns:
        True if persistence was cleared, False otherwise
    """
    state_path = TRAINING_PERSISTENCE_DIR / "state.json"
    result_path = TRAINING_PERSISTENCE_DIR / "result.json"

    if not state_path.exists():
        return False

    # Check if current state references this model
    with open(state_path, 'r') as f:
        state = json.load(f)

    if state.get("model_name") != model_id:
        return False

    # Clear the state
    empty_state = {
        "model_name": "",
        "selected_labels": [],
        "architecture": "CNN",
        "status": "idle",
        "job_id": None,
        "last_updated": datetime.now().isoformat()
    }

    with open(state_path, 'w') as f:
        json.dump(empty_state, f, indent=2)

    # Also clear result if it exists
    if result_path.exists():
        empty_result = {
            "result": None,
            "status": "idle",
            "job_id": None,
            "last_updated": datetime.now().isoformat()
        }
        with open(result_path, 'w') as f:
            json.dump(empty_result, f, indent=2)

    return True


def _delete_tests_for_model(model_id: str) -> int:
    """
    Delete all tests associated with a model.

    Args:
        model_id: The model name that was deleted

    Returns:
        Number of tests deleted
    """
    metadata_dir = TEST_DATABASE_DIR / "metadata"
    processed_chunks_dir = TEST_DATABASE_DIR / "processed_chunks"
    raw_csvs_dir = TEST_DATABASE_DIR / "raw_csvs"

    if not metadata_dir.exists():
        return 0

    deleted_count = 0
    tests_to_delete = []

    # Find all tests that used this model
    for metadata_file in metadata_dir.glob("*.json"):
        try:
            with open(metadata_file, 'r') as f:
                test_data = json.load(f)

            if test_data.get("model_name") == model_id:
                test_id = metadata_file.stem
                tests_to_delete.append(test_id)
        except Exception:
            continue

    # Delete each test's files
    for test_id in tests_to_delete:
        try:
            # Delete metadata file
            metadata_file = metadata_dir / f"{test_id}.json"
            if metadata_file.exists():
                metadata_file.unlink()

            # Delete processed chunks directory
            chunks_dir = processed_chunks_dir / test_id
            if chunks_dir.exists():
                shutil.rmtree(chunks_dir)

            # Delete raw CSV file
            raw_csv = raw_csvs_dir / f"{test_id}.csv"
            if raw_csv.exists():
                raw_csv.unlink()

            deleted_count += 1
        except Exception:
            continue

    # Update test_index.json if it exists
    test_index_path = BACKEND_DIR / "test_index.json"
    if test_index_path.exists():
        try:
            with open(test_index_path, 'r') as f:
                test_index = json.load(f)

            # Filter out deleted tests
            test_index = [t for t in test_index if t.get("test_id") not in tests_to_delete]

            with open(test_index_path, 'w') as f:
                json.dump(test_index, f, indent=2)
        except Exception:
            pass

    return deleted_count


def get_model_dependencies(model_id: str) -> dict:
    """
    Get a summary of what depends on a model before deletion.
    Useful for showing the user what will be affected.

    Args:
        model_id: The model name to check

    Returns:
        dict with counts of dependencies
    """
    dependencies = {
        "training_jobs": 0,
        "tests": 0,
        "is_current_training_state": False
    }

    # Count training jobs
    if TRAINING_JOBS_PATH.exists():
        with open(TRAINING_JOBS_PATH, 'r') as f:
            jobs = json.load(f)
        dependencies["training_jobs"] = sum(
            1 for job in jobs.values() if job.get("model_name") == model_id
        )

    # Count tests
    metadata_dir = TEST_DATABASE_DIR / "metadata"
    if metadata_dir.exists():
        for metadata_file in metadata_dir.glob("*.json"):
            try:
                with open(metadata_file, 'r') as f:
                    test_data = json.load(f)
                if test_data.get("model_name") == model_id:
                    dependencies["tests"] += 1
            except Exception:
                continue

    # Check training state
    state_path = TRAINING_PERSISTENCE_DIR / "state.json"
    if state_path.exists():
        with open(state_path, 'r') as f:
            state = json.load(f)
        dependencies["is_current_training_state"] = state.get("model_name") == model_id

    return dependencies
