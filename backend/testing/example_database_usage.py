"""
example_database_usage.py — Examples of using the test database.

This script demonstrates how to:
- Log tests automatically with predict_from_csv
- Query the test database
- Retrieve test data and metadata
- Manage the database
"""

from pathlib import Path
from testing import (
    predict_from_csv,
    TestDatabase,
    get_default_database
)


# =============================================================================
# Example 1: Automatic Test Logging
# =============================================================================
def example_automatic_logging():
    """Run a test with automatic database logging."""
    print("=" * 70)
    print("EXAMPLE 1: Automatic Test Logging")
    print("=" * 70)

    # Run inference with automatic database logging
    result = predict_from_csv(
        csv_path="path/to/sensor_data.csv",
        model_path="path/to/model_serving",
        log_to_database=True,  # Enable automatic logging
        model_name="ResNet50-v1",  # Optional: specify model name
        model_version="1.0.0",  # Optional: specify version
        notes="Testing new sensor configuration",  # Optional: add notes
        tags=["production", "sensor-v2"],  # Optional: add tags for filtering
        verbose=True
    )

    print("\n[Result] Test logged automatically!")
    print(f"[Result] Majority prediction: {result.get_majority_prediction()[0]}")
    print("\nDatabase saves:")
    print("  - Raw CSV file")
    print("  - Processed chunks (16000 samples each)")
    print("  - Complete metadata (model, timestamps, predictions)")


# =============================================================================
# Example 2: Querying the Database
# =============================================================================
def example_query_database():
    """Query and explore the test database."""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Querying the Database")
    print("=" * 70)

    # Get database instance
    db = get_default_database()

    # Get database statistics
    print("\n--- Database Statistics ---")
    stats = db.get_stats()
    print(f"Total tests: {stats['total_tests']}")
    print(f"Total size: {stats['total_size_mb']:.2f} MB")
    print(f"  - Raw CSVs: {stats['raw_csvs_size_mb']:.2f} MB")
    print(f"  - Processed chunks: {stats['chunks_size_mb']:.2f} MB")
    print(f"  - Metadata: {stats['metadata_size_mb']:.2f} MB")
    print(f"Unique models: {stats['unique_models']}")
    print(f"Models: {', '.join(stats['models'])}")
    print(f"Tags: {', '.join(stats['tags'])}")

    # List recent tests
    print("\n--- Recent Tests (last 5) ---")
    recent_tests = db.list_tests(limit=5)
    for test in recent_tests:
        print(f"\nTest ID: {test['test_id']}")
        print(f"  Timestamp: {test['timestamp']}")
        print(f"  CSV: {test['csv_filename']}")
        print(f"  Model: {test['model_name']}")
        print(f"  Chunks: {test['num_chunks']}")
        print(f"  Prediction: {test['majority_class']} ({test['majority_confidence']:.1%} confidence)")
        print(f"  Tags: {', '.join(test['tags'])}")

    # Filter by tags
    print("\n--- Production Tests ---")
    prod_tests = db.list_tests(tags=["production"])
    print(f"Found {len(prod_tests)} production tests")

    # Filter by model
    print("\n--- ResNet50-v1 Tests ---")
    resnet_tests = db.list_tests(model_name="ResNet50-v1")
    print(f"Found {len(resnet_tests)} tests with ResNet50-v1")


# =============================================================================
# Example 3: Retrieving Test Data
# =============================================================================
def example_retrieve_test_data():
    """Retrieve and analyze data from a specific test."""
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Retrieving Test Data")
    print("=" * 70)

    db = get_default_database()

    # Get the most recent test
    recent_tests = db.list_tests(limit=1)
    if not recent_tests:
        print("No tests in database yet!")
        return

    test_id = recent_tests[0]['test_id']
    print(f"\nRetrieving test: {test_id}")

    # Get complete metadata
    metadata = db.get_test(test_id)
    print("\n--- Test Metadata ---")
    print(f"Original CSV: {metadata.original_csv_path}")
    print(f"Model: {metadata.model_name} (v{metadata.model_version})")
    print(f"Timestamp: {metadata.timestamp}")
    print(f"Chunks: {metadata.num_chunks}")
    print(f"Majority prediction: {metadata.majority_class} ({metadata.majority_percentage:.1%})")
    print(f"Notes: {metadata.notes}")

    # Get paths to stored data
    csv_path = db.get_csv_path(test_id)
    chunks_dir = db.get_chunks_dir(test_id)

    print(f"\n--- Stored Data Locations ---")
    print(f"Raw CSV: {csv_path}")
    print(f"Processed chunks: {chunks_dir}")

    # Load a specific chunk
    if chunks_dir:
        chunk_0 = db.load_chunk(test_id, chunk_idx=0)
        print(f"\n--- Chunk 0 Data ---")
        print(f"Shape: {chunk_0.shape}")
        print(f"Min: {chunk_0.min():.4f}")
        print(f"Max: {chunk_0.max():.4f}")
        print(f"Mean: {chunk_0.mean():.4f}")
        print(f"Prediction: {metadata.predictions[0]}")
        print(f"Confidence: {max(metadata.probabilities[0]):.1%}")


# =============================================================================
# Example 4: Batch Processing with Logging
# =============================================================================
def example_batch_processing():
    """Process multiple CSV files and log all tests."""
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Batch Processing with Logging")
    print("=" * 70)

    from testing import predict_batch

    csv_files = [
        "path/to/test1.csv",
        "path/to/test2.csv",
        "path/to/test3.csv"
    ]

    # Process all files and log to database
    results = predict_batch(
        csv_paths=csv_files,
        model_path="path/to/model_serving",
        log_to_database=True,
        model_name="ResNet50-v1",
        tags=["batch-test", "validation"],
        verbose=True
    )

    print(f"\n[Result] Processed {len(results)} files")
    print("[Result] All tests logged to database")


# =============================================================================
# Example 5: Custom Database Location
# =============================================================================
def example_custom_database():
    """Use a custom database location."""
    print("\n" + "=" * 70)
    print("EXAMPLE 5: Custom Database Location")
    print("=" * 70)

    from testing import TestDatabaseConfig

    # Create custom database configuration
    custom_config = TestDatabaseConfig(
        db_root=Path("/path/to/custom/test_db"),
        save_processed_chunks=True,
        compress_chunks=True
    )

    # Create database with custom config
    db = TestDatabase(config=custom_config)

    print(f"Database location: {db.config.db_root}")
    print(f"Save chunks: {db.config.save_processed_chunks}")
    print(f"Compress chunks: {db.config.compress_chunks}")


# =============================================================================
# Example 6: Database Management
# =============================================================================
def example_database_management():
    """Manage database entries."""
    print("\n" + "=" * 70)
    print("EXAMPLE 6: Database Management")
    print("=" * 70)

    db = get_default_database()

    # List all tests
    all_tests = db.list_tests()
    print(f"Total tests: {len(all_tests)}")

    # Delete a specific test (example - commented out for safety)
    # test_id = "20241129_143022"
    # db.delete_test(test_id)
    # print(f"Deleted test: {test_id}")

    # Get tests from a specific model
    model_tests = db.list_tests(model_name="ResNet50-v1")
    print(f"\nTests with ResNet50-v1: {len(model_tests)}")

    # Get tests with specific tags
    validation_tests = db.list_tests(tags=["validation"])
    print(f"Validation tests: {len(validation_tests)}")


# =============================================================================
# Example 7: Analyzing Test History
# =============================================================================
def example_analyze_history():
    """Analyze test history for patterns."""
    print("\n" + "=" * 70)
    print("EXAMPLE 7: Analyzing Test History")
    print("=" * 70)

    db = get_default_database()

    # Get all tests
    all_tests = db.list_tests()

    # Analyze predictions
    from collections import Counter

    all_predictions = []
    for test_summary in all_tests:
        test_id = test_summary['test_id']
        metadata = db.get_test(test_id)
        all_predictions.append(metadata.majority_class)

    # Count prediction distribution
    prediction_counts = Counter(all_predictions)

    print("\n--- Prediction Distribution ---")
    for class_name, count in prediction_counts.most_common():
        percentage = count / len(all_predictions) * 100
        print(f"{class_name}: {count} tests ({percentage:.1f}%)")

    # Analyze confidence scores
    confidences = []
    for test_summary in all_tests:
        test_id = test_summary['test_id']
        metadata = db.get_test(test_id)
        confidences.append(metadata.majority_percentage)

    import numpy as np
    print("\n--- Confidence Score Statistics ---")
    print(f"Mean confidence: {np.mean(confidences):.1%}")
    print(f"Median confidence: {np.median(confidences):.1%}")
    print(f"Min confidence: {np.min(confidences):.1%}")
    print(f"Max confidence: {np.max(confidences):.1%}")


# =============================================================================
# Main
# =============================================================================
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("TEST DATABASE USAGE EXAMPLES")
    print("=" * 70)
    print("\nThis script demonstrates various ways to use the test database.")
    print("Uncomment the examples you want to run.\n")

    # Uncomment to run examples:
    # example_automatic_logging()
    # example_query_database()
    # example_retrieve_test_data()
    # example_batch_processing()
    # example_custom_database()
    # example_database_management()
    # example_analyze_history()

    print("\n" + "=" * 70)
    print("See the function definitions above for usage patterns.")
    print("=" * 70)
