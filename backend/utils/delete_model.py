"""
Model deletion utilities.

This module provides comprehensive cleanup when a model is deleted,
including:
- Archiving reports before deletion (preserved in reports_archive/)
- Removing model directory and all files
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
REPORTS_ARCHIVE_DIR = BACKEND_DIR / "reports_archive"
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
        "reports_archived": 0,
        "training_jobs_cleaned": 0,
        "training_state_cleared": False,
        "tests_updated": 0,
        "errors": []
    }

    model_dir = MODELS_DIR / model_id

    # 1. Archive reports BEFORE deleting model directory
    try:
        archived_count = _archive_reports(model_id, model_dir)
        results["reports_archived"] = archived_count
    except Exception as e:
        results["errors"].append(f"Failed to archive reports: {str(e)}")

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

    # 5. Update tests that used this model (mark model as deleted)
    try:
        updated_count = _update_tests_for_deleted_model(model_id)
        results["tests_updated"] = updated_count
    except Exception as e:
        results["errors"].append(f"Failed to update tests: {str(e)}")

    return results


def _archive_reports(model_id: str, model_dir: Path) -> int:
    """
    Archive PDF reports from the model directory before deletion.
    Reports are copied to reports_archive/ with model name prefix.

    Args:
        model_id: The model name
        model_dir: Path to the model directory

    Returns:
        Number of reports archived
    """
    if not model_dir.exists():
        return 0

    # Create archive directory if it doesn't exist
    REPORTS_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    archived_count = 0

    # Find all PDF files in the model directory
    for pdf_file in model_dir.glob("*.pdf"):
        # Create archive filename with timestamp to avoid conflicts
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_name = f"{model_id}_{pdf_file.stem}_{timestamp}.pdf"
        archive_path = REPORTS_ARCHIVE_DIR / archive_name

        # Copy the report to archive
        shutil.copy2(pdf_file, archive_path)
        archived_count += 1

        # Also create a metadata file for the archived report
        metadata = {
            "original_model": model_id,
            "original_filename": pdf_file.name,
            "archived_at": datetime.now().isoformat(),
            "archive_path": str(archive_path)
        }

        metadata_path = archive_path.with_suffix(".json")
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

    return archived_count


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


def _update_tests_for_deleted_model(model_id: str) -> int:
    """
    Update test metadata to mark the model as deleted.
    Tests are preserved for historical reference, but model_name is updated.

    Args:
        model_id: The model name that was deleted

    Returns:
        Number of tests updated
    """
    metadata_dir = TEST_DATABASE_DIR / "metadata"
    if not metadata_dir.exists():
        return 0

    updated_count = 0

    for metadata_file in metadata_dir.glob("*.json"):
        try:
            with open(metadata_file, 'r') as f:
                test_data = json.load(f)

            if test_data.get("model_name") == model_id:
                # Mark model as deleted but preserve test data
                test_data["model_name"] = f"{model_id} [Deleted]"
                test_data["model_deleted"] = True
                test_data["model_deleted_at"] = datetime.now().isoformat()

                with open(metadata_file, 'w') as f:
                    json.dump(test_data, f, indent=2)

                updated_count += 1
        except Exception:
            # Skip files that can't be read
            continue

    return updated_count


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
