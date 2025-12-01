"""
runner.py — High-level training workflow with stdout capture and report generation.

Provides a clean interface for:
1. Running training with captured output
2. Generating AI-powered reports
3. Saving everything together
"""

import io
import os
import sys
from datetime import datetime
from typing import Optional, Union, List
from dataclasses import dataclass, field

from settings.constants import OPENAI_MODEL


@dataclass
class RunResult:
    """Extended result including captured output and report path."""
    training_result: 'TrainingResult'  # From config.py
    training_log: str
    report_path: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


def capture_output(func, *args, **kwargs):
    """
    Run a function and capture its stdout while still printing to console.
    
    Args:
        func: Function to execute
        *args, **kwargs: Arguments to pass to function
    
    Returns:
        tuple: (function_result, captured_stdout_string)
    """
    buffer = io.StringIO()
    
    class TeeOutput:
        def __init__(self, buf, original):
            self.buf = buf
            self.original = original
        
        def write(self, text):
            self.buf.write(text)
            self.original.write(text)
        
        def flush(self):
            self.buf.flush()
            self.original.flush()
    
    tee = TeeOutput(buffer, sys.stdout)
    old_stdout = sys.stdout
    sys.stdout = tee
    
    try:
        result = func(*args, **kwargs)
    finally:
        sys.stdout = old_stdout
    
    return result, buffer.getvalue()


def run_training(
    paths: Union[str, List[str]],
    save_dir: str,
    model_type: str = "cnn",
    model_name: Optional[str] = None,
    data_config=None,
    model_config=None,
    generate_report: bool = True,
    use_llm: bool = True,
    llm_model: str = None,
    api_key: Optional[str] = None,
    author: str = "Auto-generated",
    verbose: bool = True,
    extra_callbacks: list = None,
) -> RunResult:
    """
    Complete training workflow with report generation.

    Args:
        paths: Path(s) to CSV data files or directories
        save_dir: Directory to save all outputs
        model_type: "cnn" or "resnet"
        model_name: Base name for saved files (defaults to model_type)
        data_config: DataConfig for data pipeline
        model_config: CNNConfig or ResNetConfig
        generate_report: If True, generate PDF report after training
        use_llm: If True, use LLM for AI analysis in report
        llm_model: OpenAI model to use (uses OPENAI_MODEL from settings)
        api_key: API key for LLM (or set OPENAI_API_KEY env var)
        author: Author name for report
        verbose: Print progress messages

    Returns:
        RunResult with training_result, captured log, and report path
    """
    # Import here to avoid circular imports
    from . import cnn, resnet
    from .config import CNNConfig, ResNetConfig, DataConfig
    from .report import generate_report as gen_report, generate_model_metadata

    if llm_model is None:
        llm_model = OPENAI_MODEL

    # Select model module
    if model_type.lower() == "resnet":
        module = resnet
        default_config = ResNetConfig()
        architecture = "ResNet"
    else:
        module = cnn
        default_config = CNNConfig()
        architecture = "CNN"
    
    model_name = model_name or f"{model_type}_model"
    
    # Use provided configs or defaults
    if data_config is None:
        data_config = DataConfig()
    if model_config is None:
        model_config = default_config
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"TRAINING RUN: {architecture}")
        print(f"Save directory: {save_dir}")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"{'='*60}\n")
    
    # Run training with stdout capture
    training_result, training_log = capture_output(
        module.run_pipeline,
        paths=paths,
        save_dir=save_dir,
        model_name=model_name,
        data_config=data_config,
        model_config=model_config,
        verbose=True,  # Always verbose inside capture
        extra_callbacks=extra_callbacks,
    )
    
    # Generate friendly model name first (used for both report and metadata)
    from .report import _generate_model_name, _generate_filename_from_model_name
    friendly_name = _generate_model_name(save_dir, architecture, api_key=api_key)

    # Generate report if requested
    report_path = None
    if generate_report:
        try:
            if verbose:
                print("\nGenerating PDF report...")

            # Use model name for report filename
            report_name = _generate_filename_from_model_name(friendly_name)

            report_path = gen_report(
                result=training_result,
                terminal_output=training_log,
                architecture=architecture,
                config=model_config,
                save_dir=save_dir,
                report_name=report_name,
                model_name=friendly_name,
                use_llm=use_llm,
                llm_model=llm_model,
                api_key=api_key,
                author=author,
            )

        except ImportError as e:
            if verbose:
                print(f"[WARNING] Report dependencies missing: {e}")
                print("[INFO] Install with: pip install reportlab openai")
        except Exception as e:
            if verbose:
                print(f"[WARNING] Report generation failed: {e}")

    # Generate model metadata (model_info.json) for frontend
    try:
        if verbose:
            print("Generating model metadata...")

        # Get labels from training result metadata
        labels = training_result.metadata.get('class_names', []) if training_result.metadata else []

        metadata_path = generate_model_metadata(
            save_dir=save_dir,
            architecture=architecture,
            test_accuracy=training_result.test_accuracy,
            test_loss=training_result.test_loss,
            training_time=training_result.training_time,
            history=training_result.history,
            report_path=report_path,
            api_key=api_key,
            model_name=friendly_name,
            labels=labels,
        )

        if verbose:
            print(f"[OK] Metadata saved: {metadata_path}")
    except Exception as e:
        if verbose:
            print(f"[WARNING] Metadata generation failed: {e}")

    # Create run result
    run_result = RunResult(
        training_result=training_result,
        training_log=training_log,
        report_path=report_path,
    )
    
    if verbose:
        print(f"\n{'='*60}")
        print("TRAINING COMPLETE")
        print(f"Test Accuracy: {training_result.test_accuracy:.4f}")
        print(f"Test Loss: {training_result.test_loss:.4f}")
        print(f"Model saved: {save_dir}")
        if report_path:
            print(f"Report saved: {report_path}")
        print(f"{'='*60}\n")
    
    return run_result


def run_cnn(
    paths: Union[str, List[str]],
    save_dir: str,
    **kwargs
) -> RunResult:
    """Convenience function for CNN training."""
    return run_training(paths, save_dir, model_type="cnn", **kwargs)


def run_resnet(
    paths: Union[str, List[str]],
    save_dir: str,
    **kwargs
) -> RunResult:
    """Convenience function for ResNet training."""
    return run_training(paths, save_dir, model_type="resnet", **kwargs)
