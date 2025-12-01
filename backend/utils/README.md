# Utils Module

This module serves as a collection of general-purpose utility scripts and helper functions that support various system-wide operations, particularly those involving cleanup, maintenance, and cross-module interactions.

## Overview

The `utils` module is designed to house standalone, reusable functions that don't fit neatly into the scope of other major modules but are necessary for the overall health and functionality of the backend system. Its current primary function is robust model deletion, demonstrating a commitment to system cleanliness and data integrity.

## Key Components

### `delete_model.py`

This script provides a comprehensive and safe mechanism for deleting a trained machine learning model from the system. It ensures that all associated artifacts and references are properly handled, preventing stale data and orphaned files.

Key functionalities include:

*   **Comprehensive Deletion**: The `delete_model_complete` function orchestrates the removal of a model's directory from the `models/` folder.
*   **Report Archiving**: Crucially, it archives any associated PDF reports into a `reports_archive/` directory before the model's main folder is deleted. This preserves valuable historical analysis without cluttering the active `models/` directory.
*   **Training Job Cleanup**: It removes all entries related to the deleted model from `training_jobs.json`, maintaining an accurate record of active and completed training tasks.
*   **Training State Management**: If the deleted model was actively referenced in the `training_persistence/state.json` (which tracks the current training session's UI state), that state is reset to prevent inconsistencies.
*   **Test Record Update**: Historical test records in the `test_database/` are *not* deleted. Instead, they are intelligently updated to reflect that the model used for that test has been removed (e.g., by appending "[Deleted]" to the model name). This ensures that the history of past inference runs remains intact and meaningful.
*   **Dependency Checking (`get_model_dependencies`)**: Provides a way to identify what other parts of the system (e.g., active training jobs, past tests) depend on a given model before it is deleted. This allows for better user communication and decision-making.

## How It's Used

The `delete_model.py` script is typically invoked by the `agent` module when a user requests to delete a specific model. The agent uses the functions within this script to perform a thorough cleanup, ensuring that the system remains tidy and consistent. Its robust handling of dependencies and historical data makes it an indispensable tool for managing the lifecycle of machine learning models.
