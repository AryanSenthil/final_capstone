"""
Aryan Senthil's Chat Agent Package
"""

from .damage_lab_agent import (
    # Agent
    root_agent,
    SYSTEM_INSTRUCTION,
    ALL_TOOLS,

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
)

__all__ = [
    "root_agent",
    "SYSTEM_INSTRUCTION",
    "ALL_TOOLS",
    "list_datasets",
    "get_dataset_details",
    "browse_directories",
    "suggest_label",
    "ingest_data",
    "delete_dataset",
    "generate_dataset_metadata",
    "list_raw_folders",
    "list_models",
    "get_model_details",
    "suggest_model_name",
    "start_training",
    "get_training_status",
    "wait_for_training",
    "delete_model",
    "run_inference",
    "list_tests",
    "get_test_details",
    "get_test_statistics",
    "delete_test",
    "get_workflow_guidance",
    "compare_models",
    "get_dataset_summary",
    "get_training_recommendations",
    "explain_results",
    "get_model_graphs",
    "get_report_url",
    "read_report",
    "list_reports",
    "get_system_status",
]
