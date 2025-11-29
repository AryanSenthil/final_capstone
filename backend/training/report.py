"""
report.py — Training report generation.

Generates comprehensive PDF reports from training results using LLM analysis.
"""

import io
import os
import sys
from contextlib import redirect_stdout
from datetime import datetime
from typing import Any, Callable, Optional, Union
from dataclasses import dataclass, field

from .config import TrainingResult, CNNConfig, ResNetConfig
from settings.constants import OPENAI_MODEL


@dataclass
class ReportMetadata:
    """Metadata for training report."""
    title: str
    architecture: str
    timestamp: str
    date: str
    time: str
    author: str = "Auto-generated"
    version: str = "1.0"


@dataclass 
class FullTrainingResult:
    """Extended training result with report artifacts."""
    result: TrainingResult
    terminal_output: str
    config: dict
    metadata: ReportMetadata
    report_path: Optional[str] = None
    analysis: Optional[Any] = None  # AnalysisResult


def capture_training(
    train_func: Callable,
    *args,
    **kwargs
) -> tuple[Any, str]:
    """
    Execute training function while capturing stdout.

    Args:
        train_func: Training function to execute (e.g., cnn.run_pipeline)
        *args, **kwargs: Arguments to pass to train_func

    Returns:
        tuple: (function_result, captured_stdout)
    """
    output_buffer = io.StringIO()
    
    # Capture stdout while still printing to console
    class TeeOutput:
        def __init__(self, buffer, original):
            self.buffer = buffer
            self.original = original
        
        def write(self, text):
            self.buffer.write(text)
            self.original.write(text)
        
        def flush(self):
            self.buffer.flush()
            self.original.flush()
    
    tee = TeeOutput(output_buffer, sys.stdout)
    old_stdout = sys.stdout
    sys.stdout = tee
    
    try:
        result = train_func(*args, **kwargs)
    finally:
        sys.stdout = old_stdout
    
    return result, output_buffer.getvalue()


def _generate_title_from_path(save_dir: str, api_key: str = None) -> str:
    """Use OpenAI to generate a professional title from the save directory name."""
    import os
    try:
        from openai import OpenAI
    except ImportError:
        # Fallback if OpenAI not available
        dir_name = os.path.basename(save_dir.rstrip('/'))
        return dir_name.replace('_', ' ').replace('-', ' ').title() + " Training Report"

    api_key = api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        dir_name = os.path.basename(save_dir.rstrip('/'))
        return dir_name.replace('_', ' ').replace('-', ' ').title() + " Training Report"

    try:
        client = OpenAI(api_key=api_key)
        dir_name = os.path.basename(save_dir.rstrip('/'))

        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You generate professional report titles. Respond with ONLY the title, nothing else."
                },
                {
                    "role": "user",
                    "content": f"Generate a professional training report title from this directory name: '{dir_name}'. Make it clean and formal, suitable for a machine learning research report. Include 'Training Report' at the end."
                }
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content.strip().strip('"')
    except Exception:
        dir_name = os.path.basename(save_dir.rstrip('/'))
        return dir_name.replace('_', ' ').replace('-', ' ').title() + " Training Report"


def _generate_filename_from_path(save_dir: str, api_key: str = None) -> str:
    """Use OpenAI to generate a short filename from the save directory name."""
    import os
    import re

    dir_name = os.path.basename(save_dir.rstrip('/'))
    fallback = dir_name.replace(' ', '_').lower() + "_report"

    try:
        from openai import OpenAI
    except ImportError:
        return fallback

    api_key = api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return fallback

    try:
        client = OpenAI(api_key=api_key)

        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You generate short filenames. Respond with ONLY the filename, no extension, no explanation. Use lowercase and underscores only."
                },
                {
                    "role": "user",
                    "content": f"Generate a short PDF filename (max 30 chars, no extension) from this folder name: '{dir_name}'. Keep the key identifier (like 'cnn5' or 'resnet2'). End with '_report'. Example: 'cnn5_report' or 'resnet2_report'."
                }
            ],
            temperature=0.2,
        )
        filename = response.choices[0].message.content.strip().strip('"').strip("'")
        # Sanitize: only allow lowercase, numbers, underscores
        filename = re.sub(r'[^a-z0-9_]', '_', filename.lower())
        # Ensure it ends with _report
        if not filename.endswith('_report'):
            filename = filename.rstrip('_') + '_report'
        return filename if filename else fallback
    except Exception:
        return fallback


def _generate_model_name(save_dir: str, architecture: str, api_key: str = None) -> str:
    """Use OpenAI to generate a friendly model name from the folder name."""
    import os

    dir_name = os.path.basename(save_dir.rstrip('/'))
    fallback = dir_name.replace('_', ' ').replace('-', ' ').title()

    try:
        from openai import OpenAI
    except ImportError:
        return fallback

    api_key = api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return fallback

    try:
        client = OpenAI(api_key=api_key)

        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You generate short, clean model names. Respond with ONLY the name, nothing else."
                },
                {
                    "role": "user",
                    "content": f"Generate a short friendly name (max 4 words) for a {architecture} model from folder '{dir_name}'. Keep key identifiers like version numbers. Example: 'CNN v5' or 'ResNet Damage Detector'. No quotes in response."
                }
            ],
            temperature=0.3,
        )
        name = response.choices[0].message.content.strip().strip('"').strip("'")
        return name if name else fallback
    except Exception:
        return fallback


def generate_model_metadata(
    save_dir: str,
    architecture: str,
    test_accuracy: float,
    test_loss: float,
    training_time: float = 0.0,
    report_path: str = None,
    api_key: str = None,
) -> str:
    """
    Generate model_info.json with OpenAI-generated name.

    Args:
        save_dir: Model directory
        architecture: Model architecture ("CNN" or "ResNet")
        test_accuracy: Test accuracy (0-1)
        test_loss: Test loss value
        training_time: Training duration in seconds
        report_path: Path to PDF report (optional)
        api_key: OpenAI API key

    Returns:
        Path to generated model_info.json
    """
    import json

    # Generate friendly name using OpenAI
    name = _generate_model_name(save_dir, architecture, api_key=api_key)

    metadata = {
        "name": name,
        "architecture": architecture,
        "accuracy": test_accuracy,
        "test_accuracy": test_accuracy,  # Store both for clarity
        "loss": test_loss,
        "training_time": training_time,
        "created_at": datetime.now().isoformat(),
        "report_path": report_path,
    }

    info_path = os.path.join(save_dir, "model_info.json")
    with open(info_path, "w") as f:
        json.dump(metadata, f, indent=2)

    return info_path


def _build_history_rows(history: dict, max_rows: int = 20) -> list:
    """Build table rows from training history."""
    if not history:
        return [["Epoch", "No data available"]]

    metrics = list(history.keys())
    n_epochs = len(next(iter(history.values())))

    # Sample if too many epochs
    if n_epochs > max_rows:
        step = n_epochs // max_rows
        indices = list(range(0, n_epochs, step))
        if n_epochs - 1 not in indices:
            indices.append(n_epochs - 1)
    else:
        indices = list(range(n_epochs))

    header = ["Epoch"] + metrics
    rows = [header]

    for i in indices:
        row = [i + 1] + [
            f"{history[m][i]:.4f}" if isinstance(history[m][i], float) else history[m][i]
            for m in metrics
        ]
        rows.append(row)

    return rows


def generate_report(
    result: TrainingResult,
    terminal_output: str,
    architecture: str,
    config: Union[CNNConfig, ResNetConfig, dict],
    save_dir: str,
    report_name: str = "training_report",
    use_llm: bool = True,
    llm_model: str = None,
    api_key: Optional[str] = None,
    author: str = "Auto-generated",
) -> str:
    """
    Generate comprehensive PDF report from training results.

    Args:
        result: TrainingResult from training
        terminal_output: Captured stdout from training
        architecture: Model architecture name ("CNN" or "ResNet")
        config: Training config (CNNConfig, ResNetConfig, or dict)
        save_dir: Directory to save report
        report_name: Base name for report file
        use_llm: Whether to use LLM for analysis
        llm_model: OpenAI model to use
        api_key: OpenAI API key
        author: Report author name

    Returns:
        str: Path to generated PDF report
    """
    # Import here to avoid circular imports
    from pdf_writer import TrainingReportWriter
    from analyzer import analyze_training_results, generate_fallback_analysis

    if llm_model is None:
        llm_model = OPENAI_MODEL

    # Convert config to dict if needed
    if hasattr(config, '__dataclass_fields__'):
        config_dict = {k: getattr(config, k) for k in config.__dataclass_fields__}
    else:
        config_dict = dict(config)
    
    # Generate metadata
    now = datetime.now()
    metadata = ReportMetadata(
        title=f"{architecture} Training Report",
        architecture=architecture,
        timestamp=now.isoformat(),
        date=now.strftime("%B %d, %Y"),
        time=now.strftime("%H:%M:%S"),
        author=author,
    )
    
    # Get LLM analysis
    if use_llm:
        print(f"[INFO] Generating LLM analysis using {llm_model}...")
        try:
            analysis = analyze_training_results(
                architecture=architecture,
                terminal_output=terminal_output,
                result=result,
                config=config_dict,
                model=llm_model,
                api_key=api_key,
            )
            print("[OK] LLM analysis completed successfully")
        except Exception as e:
            print(f"[WARNING] LLM analysis failed: {e}")
            print("[INFO] Using fallback analysis...")
            analysis = generate_fallback_analysis(
                architecture=architecture,
                result=result,
                config=config_dict,
            )
    else:
        print("[INFO] LLM disabled, using template-based analysis")
        analysis = generate_fallback_analysis(
            architecture=architecture,
            result=result,
            config=config_dict,
        )
    
    # Build PDF
    os.makedirs(save_dir, exist_ok=True)
    report_path = os.path.join(save_dir, f"{report_name}.pdf")

    # Generate title from save_dir using LLM
    generated_title = _generate_title_from_path(save_dir, api_key=api_key)
    metadata.title = generated_title

    report = TrainingReportWriter(report_path, title=metadata.title)

    # Title page
    report.add_title(
        title=metadata.title,
        subtitle=f"Generated on {metadata.date} at {metadata.time}"
    )

    # Executive Summary
    report.add_analysis_section("Executive Summary", analysis.executive_summary)

    # Model Information - grouped with heading
    model_info = {
        "Architecture": architecture,
        "Input Shape": str(result.input_shape),
        "Number of Classes": result.metadata['num_classes'],
        "Class Names": ", ".join(result.metadata['class_names']),
    }
    report.add_section_with_table(
        "Model Information",
        [["Property", "Value"]] + [[k, str(v)] for k, v in model_info.items()],
        caption="Model Configuration"
    )

    # Dataset Information - grouped with heading
    dataset_info = {
        "Training Samples": result.metadata['train_size'],
        "Validation Samples": result.metadata['val_size'],
        "Test Samples": result.metadata['test_size'],
    }
    report.add_section_with_table(
        "Dataset Overview",
        [["Split", "Sample Count"]] + [[k, str(v)] for k, v in dataset_info.items()],
    )
    report.add_key_value_table(
        result.metadata['class_counts'],
        caption="Class Distribution"
    )

    # Hyperparameters - smart flow handles page breaks
    report.add_conditional_page_break(min_space=3.0)
    report.add_hyperparameters(config_dict)

    # Training Curves - both graphs on same page
    if result.graph_base64.get('accuracy') and result.graph_base64.get('loss'):
        report.add_dual_images(
            "Training Curves",
            result.graph_base64['accuracy'],
            result.graph_base64['loss'],
            caption1="Training and Validation Accuracy",
            caption2="Training and Validation Loss",
            max_width=5.0,
        )
    elif result.graph_base64.get('accuracy'):
        report.add_section_with_image(
            "Training Curves",
            result.graph_base64['accuracy'],
            caption="Training and Validation Accuracy"
        )
    elif result.graph_base64.get('loss'):
        report.add_section_with_image(
            "Training Curves",
            result.graph_base64['loss'],
            caption="Training and Validation Loss"
        )

    # Confusion Matrix - grouped with heading
    if result.graph_base64.get('confusion_matrix'):
        report.add_section_with_image(
            "Confusion Matrix",
            result.graph_base64['confusion_matrix'],
            caption="Test Set Confusion Matrix"
        )

    # Final Results - smart section grouping
    report.add_results_summary({
        "Test Accuracy": result.test_accuracy,
        "Test Loss": result.test_loss,
        "Total Epochs": len(result.history.get('loss', [])),
    })

    # Analysis Sections - conditional breaks for flow
    report.add_conditional_page_break(min_space=2.5)
    report.add_analysis_section("How Training Went", analysis.training_dynamics)
    report.add_analysis_section("Damage Categories", analysis.class_analysis)
    report.add_analysis_section("Recommendations", analysis.recommendations)
    report.add_analysis_section("Bottom Line", analysis.conclusion)

    # Training History (sampled) - smart table with heading
    report.add_section_with_table(
        "Training History",
        _build_history_rows(result.history, max_rows=15),
        caption="Training Metrics by Epoch (sampled)" if len(result.history.get('loss', [])) > 15 else "Training Metrics by Epoch"
    )
    
    # Generate PDF
    report.generate()
    
    print(f"[OK] Report generated: {report_path}")
    return report_path


def run_pipeline_with_report(
    pipeline_func: Callable,
    paths: list,
    save_dir: str,
    architecture: str,
    model_name: str = None,
    config: Any = None,
    use_llm: bool = True,
    llm_model: str = None,
    api_key: Optional[str] = None,
    author: str = "Auto-generated",
    verbose: bool = True,
) -> FullTrainingResult:
    """
    Run training pipeline and generate report in one call.

    Args:
        pipeline_func: Training pipeline function (cnn.run_pipeline or resnet.run_pipeline)
        paths: Data paths
        save_dir: Directory to save everything
        architecture: Model name ("CNN" or "ResNet")
        model_name: Name for saved model files
        config: Model config
        use_llm: Use LLM for analysis
        llm_model: OpenAI model
        api_key: OpenAI API key
        author: Report author
        verbose: Print progress

    Returns:
        FullTrainingResult with all artifacts
    """
    if model_name is None:
        model_name = f"{architecture.lower()}_model"
    
    # Capture training
    result, terminal_output = capture_training(
        pipeline_func,
        paths=paths,
        save_dir=save_dir,
        model_name=model_name,
        model_config=config,
        verbose=verbose,
    )
    
    # Get config dict
    if config is None:
        if architecture.upper() == "CNN":
            config = CNNConfig()
        else:
            config = ResNetConfig()
    
    if hasattr(config, '__dataclass_fields__'):
        config_dict = {k: getattr(config, k) for k in config.__dataclass_fields__}
    else:
        config_dict = dict(config)
    
    # Generate report name using OpenAI
    report_name = _generate_filename_from_path(save_dir, api_key=api_key)

    report_path = generate_report(
        result=result,
        terminal_output=terminal_output,
        architecture=architecture,
        config=config,
        save_dir=save_dir,
        report_name=report_name,
        use_llm=use_llm,
        llm_model=llm_model,
        api_key=api_key,
        author=author,
    )

    # Generate model_info.json for frontend
    generate_model_metadata(
        save_dir=save_dir,
        architecture=architecture,
        test_accuracy=result.test_accuracy,
        test_loss=result.test_loss,
        report_path=report_path,
        api_key=api_key,
    )

    # Create metadata
    now = datetime.now()
    metadata = ReportMetadata(
        title=f"{architecture} Training Report",
        architecture=architecture,
        timestamp=now.isoformat(),
        date=now.strftime("%B %d, %Y"),
        time=now.strftime("%H:%M:%S"),
        author=author,
    )
    
    return FullTrainingResult(
        result=result,
        terminal_output=terminal_output,
        config=config_dict,
        metadata=metadata,
        report_path=report_path,
    )
