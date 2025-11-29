"""
agent.py — LLM-based training analysis agent.

Calls OpenAI API to generate intelligent analysis of training results.
"""

import os
import re
from typing import Any, Optional
from dataclasses import dataclass

from .prompt import TRAINING_ANALYSIS_PROMPT
from settings.constants import OPENAI_MODEL


@dataclass
class AnalysisResult:
    """Container for LLM analysis output."""
    executive_summary: str
    training_dynamics: str
    class_analysis: str
    recommendations: str
    conclusion: str
    full_text: str


def analyze_training_results(
    architecture: str,
    terminal_output: str,
    result: Any,  # TrainingResult
    config: dict,
    model: str = None,
    api_key: Optional[str] = None,
) -> AnalysisResult:
    """
    Analyze training results using LLM.

    Args:
        architecture: Model architecture name (e.g., "CNN", "ResNet")
        terminal_output: Captured stdout from training
        result: TrainingResult object
        config: Hyperparameters dict
        model: OpenAI model to use
        api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)

    Returns:
        AnalysisResult with parsed sections
    """
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("openai package required. Install with: pip install openai")
    
    api_key = api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OpenAI API key required. Set OPENAI_API_KEY environment variable.")

    if model is None:
        model = OPENAI_MODEL

    print(f"[DEBUG] Using model: {model}")
    print("[DEBUG] Creating OpenAI client...")
    client = OpenAI(api_key=api_key)
    print("[DEBUG] Client created, extracting metrics...")

    # Extract history stats
    history = result.history
    epochs_run = len(history.get('loss', []))
    
    # Find best epoch (lowest val_loss)
    val_losses = history.get('val_loss', [])
    best_epoch = val_losses.index(min(val_losses)) + 1 if val_losses else epochs_run
    
    # Format hyperparameters
    hyperparam_str = "\n".join([f"- {k}: {v}" for k, v in config.items()])
    
    # Extract metric values
    initial_train_loss = history['loss'][0] if history.get('loss') else 0
    final_train_loss = history['loss'][-1] if history.get('loss') else 0
    initial_val_loss = history['val_loss'][0] if history.get('val_loss') else 0
    final_val_loss = history['val_loss'][-1] if history.get('val_loss') else 0
    initial_train_acc = history['accuracy'][0] if history.get('accuracy') else 0
    final_train_acc = history['accuracy'][-1] if history.get('accuracy') else 0
    initial_val_acc = history['val_accuracy'][0] if history.get('val_accuracy') else 0
    final_val_acc = history['val_accuracy'][-1] if history.get('val_accuracy') else 0

    # Calculate deltas
    delta_train_loss = final_train_loss - initial_train_loss
    delta_val_loss = final_val_loss - initial_val_loss
    delta_train_acc = final_train_acc - initial_train_acc
    delta_val_acc = final_val_acc - initial_val_acc

    # Gaps between different accuracy measures
    train_val_gap = final_train_acc - final_val_acc  # Training vs Validation
    train_test_gap = final_train_acc - result.test_accuracy  # Training vs Test
    val_test_gap = final_val_acc - result.test_accuracy  # Validation vs Test

    print("[DEBUG] Building prompt...")
    # Build prompt
    prompt = TRAINING_ANALYSIS_PROMPT.format(
        architecture=architecture,
        input_shape=result.input_shape,
        num_classes=result.metadata['num_classes'],
        class_names=", ".join(result.metadata['class_names']),
        train_size=result.metadata['train_size'],
        val_size=result.metadata['val_size'],
        test_size=result.metadata['test_size'],
        class_counts=result.metadata['class_counts'],
        hyperparameters=hyperparam_str,
        terminal_output=_truncate_output(terminal_output, max_lines=100),
        test_accuracy=result.test_accuracy,
        test_accuracy_pct=result.test_accuracy * 100,
        test_loss=result.test_loss,
        epochs_run=epochs_run,
        best_epoch=best_epoch,
        initial_train_loss=initial_train_loss,
        final_train_loss=final_train_loss,
        initial_val_loss=initial_val_loss,
        final_val_loss=final_val_loss,
        initial_train_acc=initial_train_acc,
        final_train_acc=final_train_acc,
        final_train_acc_pct=final_train_acc * 100,
        initial_val_acc=initial_val_acc,
        final_val_acc=final_val_acc,
        final_val_acc_pct=final_val_acc * 100,
        delta_train_loss=delta_train_loss,
        delta_val_loss=delta_val_loss,
        delta_train_acc=delta_train_acc,
        delta_val_acc=delta_val_acc,
        train_val_gap=train_val_gap,
        train_test_gap=train_test_gap,
        val_test_gap=val_test_gap,
    )
    print(f"[DEBUG] Prompt built, length: {len(prompt)} chars")

    # Call OpenAI
    print(f"[INFO] Calling {model} for analysis (this may take a minute)...")
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are writing a training report for engineers. Be concise and practical."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
        )
        print("[OK] LLM response received")
    except Exception as e:
        print(f"[ERROR] LLM call failed: {e}")
        raise

    full_text = response.choices[0].message.content
    
    # Parse sections
    sections = _parse_sections(full_text)
    
    return AnalysisResult(
        executive_summary=sections.get("executive_summary", ""),
        training_dynamics=sections.get("training_dynamics", ""),
        class_analysis=sections.get("class_analysis", ""),
        recommendations=sections.get("recommendations", ""),
        conclusion=sections.get("conclusion", ""),
        full_text=full_text,
    )


def _truncate_output(output: str, max_lines: int = 100) -> str:
    """Truncate terminal output to avoid token limits."""
    lines = output.strip().split('\n')
    if len(lines) <= max_lines:
        return output
    
    # Keep first and last portions
    half = max_lines // 2
    truncated = lines[:half] + ["\n... [truncated] ...\n"] + lines[-half:]
    return '\n'.join(truncated)


def _parse_sections(text: str) -> dict:
    """Parse sections from LLM response separated by --- delimiters."""
    # Expected section order from simplified prompt (5 sections)
    section_keys = [
        "executive_summary",      # Summary
        "training_dynamics",      # How Training Went
        "class_analysis",         # Performance by Damage Type
        "recommendations",        # Recommendations
        "conclusion",             # Bottom Line
    ]

    # Split by --- delimiter (with optional whitespace)
    parts = re.split(r'\n\s*---\s*\n', text.strip())

    sections = {}
    for i, part in enumerate(parts):
        content = part.strip()
        if not content:
            continue
        if i < len(section_keys):
            sections[section_keys[i]] = content

    # If no sections found (LLM used headers instead), try header-based parsing
    if not sections or len(sections) < 3:
        sections = _parse_sections_by_headers(text)

    return sections


def _parse_sections_by_headers(text: str) -> dict:
    """Fallback: Parse sections by markdown headers."""
    sections = {}
    current_section = None
    current_content = []

    section_map = {
        "executive summary": "executive_summary",
        "training dynamics": "training_dynamics",
        "generalization": "performance_analysis",
        "performance analysis": "performance_analysis",
        "class": "class_analysis",
        "architecture": "architecture_eval",
        "hyperparameter": "architecture_eval",
        "recommendations": "recommendations",
        "conclusion": "conclusion",
    }

    for line in text.split('\n'):
        if line.startswith('###') or line.startswith('## ') or line.startswith('# '):
            if current_section:
                sections[current_section] = '\n'.join(current_content).strip()

            header = line.lstrip('#').strip().lower()
            current_section = None
            for key, value in section_map.items():
                if key in header:
                    current_section = value
                    break
            current_content = []
        else:
            current_content.append(line)

    if current_section:
        sections[current_section] = '\n'.join(current_content).strip()

    return sections


def generate_fallback_analysis(
    architecture: str,
    result: Any,
    config: dict,
) -> AnalysisResult:
    """
    Generate basic analysis without LLM (fallback when API unavailable).

    Args:
        architecture: Model architecture name
        result: TrainingResult object
        config: Hyperparameters dict

    Returns:
        AnalysisResult with template-based content
    """
    history = result.history
    epochs_run = len(history.get('loss', []))
    
    # Determine if overfitting
    final_train_acc = history['accuracy'][-1] if history.get('accuracy') else 0
    final_val_acc = history['val_accuracy'][-1] if history.get('val_accuracy') else 0
    gap = final_train_acc - final_val_acc
    
    if gap > 0.15:
        overfit_status = "shows signs of overfitting"
    elif gap < 0.05:
        overfit_status = "shows good generalization"
    else:
        overfit_status = "shows mild overfitting"
    
    executive = (
        f"The {architecture} model was trained for {epochs_run} epochs on spectrogram data "
        f"for damage classification. The model achieved {result.test_accuracy:.2%} test accuracy "
        f"and {overfit_status} with a train-validation accuracy gap of {gap:.2%}."
    )
    
    dynamics = (
        f"Training completed in {epochs_run} rounds. "
        f"The loss decreased from {history['loss'][0]:.4f} to {history['loss'][-1]:.4f}, "
        f"showing the model learned to recognize patterns in the data. "
        f"The gap between training and test accuracy ({gap:.1%}) suggests {overfit_status}."
    )

    class_analysis = (
        f"The dataset contains {result.metadata['num_classes']} damage categories: "
        f"{', '.join(result.metadata['class_names'])}. "
        f"Sample distribution: {result.metadata['class_counts']}."
    )

    recommendations = (
        "**1. Collect More Data**\n\n"
        "More training samples generally improve model accuracy, especially for underrepresented categories.\n\n"
        "**2. Review Misclassified Samples**\n\n"
        "Look at examples where the model made mistakes to understand what's confusing it.\n\n"
        "**3. Adjust Training Settings**\n\n"
        "If training stopped early, consider running for more rounds. If accuracy is unstable, try smaller learning steps."
    )

    # Determine readiness
    if result.test_accuracy >= 0.95:
        readiness = "The model is ready for use with high confidence"
    elif result.test_accuracy >= 0.90:
        readiness = "The model is ready for use with moderate confidence"
    elif result.test_accuracy >= 0.85:
        readiness = "The model needs some improvement before production use"
    else:
        readiness = "The model needs significant improvement"

    conclusion = (
        f"{readiness} based on {result.test_accuracy:.1%} test accuracy. "
        f"The main focus should be on collecting more training data for better performance."
    )

    full_text = f"""
## Summary
{executive}

## How Training Went
{dynamics}

## Damage Categories
{class_analysis}

## Recommendations
{recommendations}

## Bottom Line
{conclusion}
"""

    return AnalysisResult(
        executive_summary=executive,
        training_dynamics=dynamics,
        class_analysis=class_analysis,
        recommendations=recommendations,
        conclusion=conclusion,
        full_text=full_text.strip(),
    )
