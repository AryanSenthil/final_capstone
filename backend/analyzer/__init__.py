"""
analyzer — LLM-based training analysis.

Uses OpenAI API to generate intelligent analysis of ML training results.

Usage:
    from analyzer import analyze_training_results, generate_fallback_analysis

    # With API
    analysis = analyze_training_results(
        architecture="CNN",
        terminal_output=captured_output,
        result=training_result,
        config={"learning_rate": 0.001, ...}
    )

    # Without API (fallback)
    analysis = generate_fallback_analysis(
        architecture="CNN",
        result=training_result,
        config={"learning_rate": 0.001, ...}
    )

    print(analysis.executive_summary)
    print(analysis.recommendations)
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from package root
_package_root = Path(__file__).parent.parent
load_dotenv(_package_root / ".env")

from .agent import (
    analyze_training_results,
    generate_fallback_analysis,
    AnalysisResult,
)

__all__ = [
    "analyze_training_results",
    "generate_fallback_analysis",
    "AnalysisResult",
]
