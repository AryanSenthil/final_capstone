# PDF Writer Module

This module is dedicated to generating professional, structured PDF reports for machine learning training runs. It brings together the training results, AI-powered analysis, and visualizations into a single, polished document.

## Overview

The `pdf_writer` module acts as the final step in the reporting pipeline. It takes various pieces of information—such as training history, final model metrics, AI-generated insights, and graphical plots—and arranges them into a well-formatted PDF file. This ensures that the complex outcomes of an ML training process are easily digestible and shareable for engineers and stakeholders who may not be ML experts.

## Key Components

### `writer.py`

This is the core logic for building the PDF documents. It leverages the powerful `ReportLab` library to programmatically construct PDF pages.

Key features of `writer.py`:

*   **Intelligent Layout Management**: It uses `ReportLab`'s `CondPageBreak` and `KeepTogether` mechanisms to ensure that related content (e.g., a heading and its associated table or image) is always kept together on the same page. This prevents awkward page breaks and enhances readability.
*   **Markdown-like Formatting**: It includes a custom function (`_markdown_to_reportlab`) that converts simplified markdown syntax (e.g., `**bold**`, `*italic*`) and other formatting conventions (like auto-bolding numbers and quoted terms) into `ReportLab`'s XML-style tags, making content easier to author.
*   **Content Integration**: It provides methods to seamlessly add diverse content types to the report:
    *   `add_title`, `add_heading`, `add_text` for structural and narrative content.
    *   `add_metric`, `add_metrics_inline` for presenting key numerical results.
    *   `add_table`, `add_key_value_table`, `add_hyperparameters`, `add_training_history` for structured data displays.
    *   `add_image`, `add_dual_images` for embedding base64-encoded graphs (typically from the `graphs` module).
    *   `add_analysis_section` for incorporating the AI-generated textual analysis from the `analyzer` module.
*   **Section Builders**: Higher-level functions like `add_section_with_table` and `add_section_with_image` encapsulate common report layouts, ensuring consistency and ease of use.

### `styles.py`

This file defines the visual aesthetics of the PDF reports. It centralizes all formatting configurations, promoting a consistent and branded look.

Key aspects of `styles.py`:

*   **Color Palette**: Defines a custom blue-themed color palette (`Colors` class) for use throughout the report, including text, backgrounds, borders, and table elements.
*   **Paragraph Styles**: Creates a comprehensive `StyleSheet` containing predefined `ParagraphStyle` objects for every type of text content (titles, headings, body text, captions, metrics, etc.). These styles control font, size, color, alignment, and spacing.

## How It's Used

The `pdf_writer` module is primarily invoked by the `training` module's reporting functions (e.g., `report.py`) after a model has been trained and analyzed. The workflow is typically:

1.  A training run completes, producing a training history and test results.
2.  The `analyzer` module generates AI-powered textual analysis from these results.
3.  The `graphs` module generates various plots (accuracy, loss, confusion matrix) as base64-encoded images.
4.  The `TrainingReportWriter` (from `writer.py`) is instantiated, and its methods are called sequentially to construct the report by adding sections, text, tables, analysis, and embedded graphs.
5.  Finally, the `generate()` method is called to build and save the complete PDF report in the designated model's directory within the `models` module.

This module is crucial for transforming raw data and complex machine learning outputs into actionable, understandable intelligence.
