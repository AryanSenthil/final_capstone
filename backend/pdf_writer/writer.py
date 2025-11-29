"""
writer.py — PDF report generation using ReportLab.

TrainingReportWriter builds structured PDF reports for ML training runs
with intelligent layout management and proper page flow.
"""

import re
import base64
import io
from typing import Optional, Any, List, Tuple

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
    Flowable,
    CondPageBreak,
)

from .styles import StyleSheet, Colors


class TrainingReportWriter:
    """Builder for ML training report PDFs with intelligent layout management."""

    MARGIN = 0.75 * inch

    def __init__(
        self,
        output_path: str,
        title: str = "Training Report",
        page_size: str = "letter",
    ):
        self.output_path = output_path
        self.title = title
        self.page_size = letter if page_size == "letter" else A4

        self.story: list = []
        self.styles = StyleSheet()
        self.figure_num = 0
        self.table_num = 0

        self._setup_doc()

    def _setup_doc(self) -> None:
        self.doc = SimpleDocTemplate(
            self.output_path,
            pagesize=self.page_size,
            leftMargin=self.MARGIN,
            rightMargin=self.MARGIN,
            topMargin=self.MARGIN,
            bottomMargin=self.MARGIN,
            title=self.title,
        )
        self._page_width = self.page_size[0] - 2 * self.MARGIN
        self._page_height = self.page_size[1] - 2 * self.MARGIN

    # ==================== MARKDOWN CONVERSION ====================

    def _markdown_to_reportlab(self, text: str) -> str:
        """Convert markdown formatting to ReportLab XML tags."""
        # Escape XML special characters first
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")

        # Bold: **text** or __text__
        text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'__(.+?)__', r'<b>\1</b>', text)

        # Italic: *text* or _text_ (careful not to match inside words)
        text = re.sub(r'(?<![*\w])\*([^*\n]+?)\*(?![*\w])', r'<i>\1</i>', text)
        text = re.sub(r'(?<![_\w])_([^_\n]+?)_(?![_\w])', r'<i>\1</i>', text)

        # Bold all numbers (integers, decimals, percentages, with optional signs)
        # Matches: 123, 0.95, 95%, 0.9567, -0.5, +10, 1,234, etc.
        text = re.sub(
            r'(?<![<\w])([+-]?\d+(?:,\d{3})*(?:\.\d+)?%?)(?![>\w])',
            r'<b>\1</b>',
            text
        )

        # Bold quoted labels/terms (class names like "crushcore", "disbond")
        text = re.sub(r'"([^"]+)"', r'<b>"\1"</b>', text)
        text = re.sub(r"'([^']+)'", r"<b>'\1'</b>", text)

        # Convert bullet points
        lines = text.split('\n')
        converted_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('- '):
                converted_lines.append('    • ' + stripped[2:])
            elif stripped.startswith('• '):
                converted_lines.append('    ' + stripped)
            elif re.match(r'^\d+\.\s', stripped):
                # Numbered list - indent
                converted_lines.append('    ' + stripped)
            else:
                converted_lines.append(line)

        return '\n'.join(converted_lines)

    # ==================== SPACE CALCULATION ====================

    def _get_element_height(self, element: Flowable) -> float:
        """Calculate the height an element will occupy."""
        if hasattr(element, 'wrap'):
            try:
                _, height = element.wrap(self._page_width, self._page_height)
                return height
            except:
                return 20  # Default fallback
        return 0

    def _get_elements_height(self, elements: List[Flowable]) -> float:
        """Calculate total height of multiple elements."""
        total = 0
        for elem in elements:
            total += self._get_element_height(elem)
        return total

    def _estimate_remaining_space(self) -> float:
        """Estimate remaining space on current page."""
        total_height = self._get_elements_height(self.story)
        pages_used = total_height / self._page_height
        current_page_usage = (pages_used % 1) * self._page_height
        remaining = self._page_height - current_page_usage
        return remaining

    def _needs_page_break(self, needed_height: float, min_space: float = 2.5 * inch) -> bool:
        """Check if we need a page break before adding content."""
        remaining = self._estimate_remaining_space()
        # Break if we can't fit content and have less than min_space
        return remaining < min_space and remaining < needed_height

    # ==================== CORE CONTENT METHODS ====================

    def add_title(self, title: Optional[str] = None, subtitle: Optional[str] = None) -> "TrainingReportWriter":
        elements = [
            Paragraph(title or self.title, self.styles.title)
        ]
        if subtitle:
            elements.append(Spacer(1, 6))
            elements.append(Paragraph(subtitle, self.styles.subtitle))
        elements.append(Spacer(1, 8))
        elements.append(self._make_line())
        elements.append(Spacer(1, 16))

        self.story.extend(elements)
        return self

    def add_heading(self, text: str, level: int = 1) -> "TrainingReportWriter":
        """Add a heading. Use add_section_* methods for better flow control."""
        style = self.styles.h1 if level == 1 else self.styles.h2
        self.story.append(Paragraph(text, style))
        return self

    def add_text(self, text: str) -> "TrainingReportWriter":
        """Add body text with markdown conversion."""
        converted = self._markdown_to_reportlab(text)
        self.story.append(Paragraph(converted, self.styles.body))
        return self

    def add_metric(self, name: str, value: Any, unit: str = "") -> "TrainingReportWriter":
        text = f"<b>{name}:</b> {value}{' ' + unit if unit else ''}"
        self.story.append(Paragraph(text, self.styles.body))
        return self

    def add_metrics_inline(self, metrics: dict[str, Any]) -> "TrainingReportWriter":
        parts = [f"<b>{k}:</b> {v}" for k, v in metrics.items()]
        self.story.append(Paragraph(" &nbsp;|&nbsp; ".join(parts), self.styles.body))
        return self

    # ==================== SMART SECTION METHODS ====================

    def add_section_with_table(
        self,
        heading: str,
        data: list[list[Any]],
        caption: Optional[str] = None,
        col_widths: Optional[list[float]] = None,
        header: bool = True,
        level: int = 1,
    ) -> "TrainingReportWriter":
        """Add heading + table, keeping them together on same page."""
        style = self.styles.h1 if level == 1 else self.styles.h2
        heading_elem = Paragraph(heading, style)

        table_elements = self._build_table_elements(data, caption, col_widths, header)
        all_elements = [heading_elem, Spacer(1, 4)] + table_elements

        # Use CondPageBreak to ensure we have space, then KeepTogether
        total_height = self._get_elements_height(all_elements)
        self.story.append(CondPageBreak(min(total_height + 0.5 * inch, 4 * inch)))
        self.story.append(KeepTogether(all_elements))
        return self

    def add_section_with_image(
        self,
        heading: str,
        data: str,
        caption: Optional[str] = None,
        width: Optional[float] = None,
        max_width: float = 5.5,
        level: int = 1,
    ) -> "TrainingReportWriter":
        """Add heading + image, keeping them together on same page."""
        style = self.styles.h1 if level == 1 else self.styles.h2
        heading_elem = Paragraph(heading, style)

        image_elements = self._build_image_elements(data, caption, width, max_width)
        all_elements = [heading_elem, Spacer(1, 4)] + image_elements

        total_height = self._get_elements_height(all_elements)
        self.story.append(CondPageBreak(min(total_height + 0.5 * inch, 6 * inch)))
        self.story.append(KeepTogether(all_elements))
        return self

    def add_section_with_content(
        self,
        heading: str,
        content_elements: List[Flowable],
        level: int = 1,
        min_together: int = 2,
    ) -> "TrainingReportWriter":
        """Add heading + content, keeping heading with at least some content."""
        style = self.styles.h1 if level == 1 else self.styles.h2
        heading_elem = Paragraph(heading, style)

        # Keep heading with first few elements
        keep_count = min(min_together, len(content_elements))
        keep_elements = [heading_elem, Spacer(1, 4)] + content_elements[:keep_count]

        min_height = self._get_elements_height(keep_elements)
        self.story.append(CondPageBreak(min(min_height + 0.5 * inch, 3 * inch)))
        self.story.append(KeepTogether(keep_elements))

        # Add remaining elements normally
        for elem in content_elements[keep_count:]:
            self.story.append(elem)

        return self

    # ==================== IMAGE METHODS ====================

    def _build_image_elements(
        self,
        data: str,
        caption: Optional[str] = None,
        width: Optional[float] = None,
        max_width: float = 5.5,
    ) -> List[Flowable]:
        """Build image elements without adding to story."""
        if "," in data:
            data = data.split(",", 1)[1]

        img_bytes = base64.b64decode(data)
        img = Image(io.BytesIO(img_bytes))

        if width:
            scale = (width * inch) / img.drawWidth
        else:
            max_w = min(max_width * inch, self._page_width)
            scale = min(1.0, max_w / img.drawWidth)

        img.drawWidth *= scale
        img.drawHeight *= scale

        elements = [Spacer(1, 6), img]

        if caption:
            self.figure_num += 1
            elements.append(Spacer(1, 4))
            elements.append(Paragraph(
                f"<b>Figure {self.figure_num}:</b> {caption}",
                self.styles.caption
            ))

        elements.append(Spacer(1, 8))
        return elements

    def add_image(
        self,
        data: str,
        caption: Optional[str] = None,
        width: Optional[float] = None,
        max_width: float = 5.5,
    ) -> "TrainingReportWriter":
        """Add a standalone image with smart page break."""
        elements = self._build_image_elements(data, caption, width, max_width)
        total_height = self._get_elements_height(elements)

        self.story.append(CondPageBreak(min(total_height + 0.3 * inch, 5 * inch)))
        self.story.append(KeepTogether(elements))
        return self

    # ==================== TABLE METHODS ====================

    def _build_table_elements(
        self,
        data: list[list[Any]],
        caption: Optional[str] = None,
        col_widths: Optional[list[float]] = None,
        header: bool = True,
    ) -> List[Flowable]:
        """Build table elements without adding to story."""
        if not data:
            return []

        str_data = [[str(cell) for cell in row] for row in data]

        if col_widths:
            widths = [w * inch for w in col_widths]
        else:
            n_cols = len(str_data[0])
            widths = [self._page_width / n_cols] * n_cols

        table = Table(str_data, colWidths=widths)

        style_cmds = [
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, Colors.BORDER),
        ]

        if header:
            style_cmds.extend([
                ("BACKGROUND", (0, 0), (-1, 0), Colors.TABLE_HEADER),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 11),
            ])
            for i in range(1, len(str_data)):
                if i % 2 == 0:
                    style_cmds.append(
                        ("BACKGROUND", (0, i), (-1, i), Colors.TABLE_ROW_ALT)
                    )

        table.setStyle(TableStyle(style_cmds))

        elements = [Spacer(1, 6), table]

        if caption:
            self.table_num += 1
            elements.append(Spacer(1, 4))
            elements.append(Paragraph(
                f"<b>Table {self.table_num}:</b> {caption}",
                self.styles.caption
            ))

        elements.append(Spacer(1, 8))
        return elements

    def add_table(
        self,
        data: list[list[Any]],
        caption: Optional[str] = None,
        col_widths: Optional[list[float]] = None,
        header: bool = True,
    ) -> "TrainingReportWriter":
        """Add a standalone table with smart page break."""
        elements = self._build_table_elements(data, caption, col_widths, header)
        if not elements:
            return self

        total_height = self._get_elements_height(elements)
        self.story.append(CondPageBreak(min(total_height + 0.3 * inch, 4 * inch)))
        self.story.append(KeepTogether(elements))
        return self

    def add_key_value_table(
        self,
        data: dict[str, Any],
        caption: Optional[str] = None,
        headers: Tuple[str, str] = None,
    ) -> "TrainingReportWriter":
        """Add a key-value table with context-aware headers."""
        if headers is None:
            if caption:
                caption_lower = caption.lower()
                if "distribution" in caption_lower or "class" in caption_lower:
                    headers = ("Class", "Sample Count")
                elif "hyperparameter" in caption_lower:
                    headers = ("Hyperparameter", "Setting")
                elif "result" in caption_lower or "metric" in caption_lower:
                    headers = ("Metric", "Value")
                elif "configuration" in caption_lower or "config" in caption_lower:
                    headers = ("Setting", "Value")
                else:
                    headers = ("Property", "Value")
            else:
                headers = ("Property", "Value")

        rows = [list(headers)] + [[k, str(v)] for k, v in data.items()]
        return self.add_table(rows, caption=caption, col_widths=[2.5, 4.0])

    def add_hyperparameters(self, params: dict[str, Any]) -> "TrainingReportWriter":
        """Add hyperparameters table."""
        return self.add_key_value_table(
            params,
            caption="Training Configuration",
            headers=("Hyperparameter", "Setting")
        )

    def add_training_history(
        self,
        history: dict[str, list[float]],
        epochs: Optional[list[int]] = None,
        max_rows: int = 20,
    ) -> "TrainingReportWriter":
        if not history:
            return self

        metrics = list(history.keys())
        n_epochs = len(next(iter(history.values())))

        if epochs is None:
            epochs = list(range(1, n_epochs + 1))

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
            row = [epochs[i]] + [
                f"{history[m][i]:.4f}" if isinstance(history[m][i], float) else history[m][i]
                for m in metrics
            ]
            rows.append(row)

        return self.add_table(
            rows,
            caption="Training History (sampled)" if n_epochs > max_rows else "Training History"
        )

    # ==================== UTILITY METHODS ====================

    def add_spacer(self, height: float = 0.25) -> "TrainingReportWriter":
        self.story.append(Spacer(1, height * inch))
        return self

    def add_page_break(self) -> "TrainingReportWriter":
        self.story.append(PageBreak())
        return self

    def add_conditional_page_break(self, min_space: float = 3.0) -> "TrainingReportWriter":
        """Add page break only if less than min_space inches remain."""
        self.story.append(CondPageBreak(min_space * inch))
        return self

    def add_separator(self) -> "TrainingReportWriter":
        self.story.append(Spacer(1, 8))
        self.story.append(self._make_line())
        self.story.append(Spacer(1, 8))
        return self

    # ==================== COMPOUND SECTION METHODS ====================

    def add_model_summary(
        self,
        name: str,
        params: int,
        layers: Optional[list[dict]] = None,
        extra: Optional[dict] = None,
    ) -> "TrainingReportWriter":
        """Add model summary section."""
        content = [
            Paragraph(f"<b>Architecture:</b> {name}", self.styles.body),
            Paragraph(f"<b>Total Parameters:</b> {params:,}", self.styles.body),
        ]

        if extra:
            for k, v in extra.items():
                content.append(Paragraph(f"<b>{k}:</b> {v}", self.styles.body))

        self.add_section_with_content("Model Summary", content, level=1)

        if layers:
            rows = [["Layer", "Output Shape", "Parameters"]]
            for layer in layers:
                rows.append([
                    layer.get("name", ""),
                    layer.get("output_shape", ""),
                    f"{layer.get('params', 0):,}",
                ])
            self.add_spacer(0.1)
            self.add_table(rows, caption="Layer Details")

        return self

    def add_results_summary(
        self,
        metrics: dict[str, float],
        title: str = "Final Results",
    ) -> "TrainingReportWriter":
        """Add results summary section with bold numbers."""
        # Build heading
        style = self.styles.h1
        heading_elem = Paragraph(title, style)

        # Build metrics as bold key-value pairs
        content_elements = []
        for k, v in metrics.items():
            if isinstance(v, float):
                # Format as percentage for accuracy, decimal for loss
                if "accuracy" in k.lower():
                    formatted = f"<b>{v:.2%}</b>"
                else:
                    formatted = f"<b>{v:.4f}</b>"
            else:
                formatted = f"<b>{v}</b>"
            content_elements.append(
                Paragraph(f"{k}: {formatted}", self.styles.metric)
            )

        all_elements = [heading_elem, Spacer(1, 6)] + content_elements + [Spacer(1, 8)]

        min_height = self._get_elements_height(all_elements)
        self.story.append(CondPageBreak(min(min_height + 0.5 * inch, 3 * inch)))
        self.story.append(KeepTogether(all_elements))
        return self

    def add_analysis_section(
        self,
        title: str,
        content: str,
    ) -> "TrainingReportWriter":
        """Add AI-generated analysis section with markdown support."""
        paragraphs = content.strip().split('\n\n')
        content_elements = []

        for para in paragraphs:
            if para.strip():
                converted = self._markdown_to_reportlab(para.strip())
                content_elements.append(Paragraph(converted, self.styles.body))

        if content_elements:
            self.add_section_with_content(title, content_elements, level=1, min_together=1)

        return self

    def _make_line(self) -> Table:
        line = Table([[""]], colWidths=[self._page_width])
        line.setStyle(TableStyle([
            ("LINEABOVE", (0, 0), (-1, -1), 1.5, Colors.PRIMARY_LIGHT),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        return line

    def add_dual_images(
        self,
        heading: str,
        image1_data: str,
        image2_data: str,
        caption1: Optional[str] = None,
        caption2: Optional[str] = None,
        max_width: float = 5.0,
        level: int = 1,
    ) -> "TrainingReportWriter":
        """Add two images stacked vertically with a shared heading, kept together on one page."""
        style = self.styles.h1 if level == 1 else self.styles.h2
        heading_elem = Paragraph(heading, style)

        # Build first image
        img1_elements = self._build_image_elements(image1_data, caption1, max_width=max_width)
        # Build second image
        img2_elements = self._build_image_elements(image2_data, caption2, max_width=max_width)

        # Combine all elements
        all_elements = [heading_elem, Spacer(1, 4)] + img1_elements + img2_elements

        # Calculate height and ensure it fits
        total_height = self._get_elements_height(all_elements)
        self.story.append(CondPageBreak(min(total_height + 0.5 * inch, 9 * inch)))
        self.story.append(KeepTogether(all_elements))
        return self

    def generate(self) -> str:
        self.doc.build(self.story)
        return self.output_path
