"""
styles.py — PDF styling configuration.

Blue theme with larger fonts for professional ML reports.
"""

from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors


# Blue theme color palette
class Colors:
    """Blue-themed color palette."""
    PRIMARY = colors.HexColor("#1e40af")       # Deep blue
    PRIMARY_DARK = colors.HexColor("#1e3a8a")  # Darker blue
    PRIMARY_LIGHT = colors.HexColor("#3b82f6") # Bright blue
    ACCENT = colors.HexColor("#0ea5e9")        # Sky blue

    TEXT_DARK = colors.HexColor("#1e3a5f")     # Dark blue-gray
    TEXT_MEDIUM = colors.HexColor("#475569")   # Medium gray-blue
    TEXT_LIGHT = colors.HexColor("#64748b")    # Light gray-blue

    BG_LIGHT = colors.HexColor("#eff6ff")      # Very light blue
    BG_SUBTLE = colors.HexColor("#f8fafc")     # Almost white with blue tint

    BORDER = colors.HexColor("#bfdbfe")        # Light blue border
    TABLE_HEADER = colors.HexColor("#1e40af")  # Deep blue for headers
    TABLE_ROW_ALT = colors.HexColor("#eff6ff") # Light blue alternating rows


class StyleSheet:
    """Centralized styles for PDF reports with blue theme."""

    def __init__(self):
        self.title = ParagraphStyle(
            "Title",
            fontSize=22,
            fontName="Helvetica-Bold",
            alignment=TA_CENTER,
            spaceBefore=8,
            spaceAfter=10,
            leading=28,
            textColor=Colors.PRIMARY_DARK,
        )

        self.subtitle = ParagraphStyle(
            "Subtitle",
            fontSize=13,
            fontName="Helvetica",
            alignment=TA_CENTER,
            textColor=Colors.TEXT_LIGHT,
        )

        self.h1 = ParagraphStyle(
            "H1",
            fontSize=16,
            fontName="Helvetica-Bold",
            spaceBefore=18,
            spaceAfter=10,
            textColor=Colors.PRIMARY,
        )

        self.h2 = ParagraphStyle(
            "H2",
            fontSize=14,
            fontName="Helvetica-Bold",
            spaceBefore=14,
            spaceAfter=8,
            textColor=Colors.PRIMARY_LIGHT,
        )

        self.body = ParagraphStyle(
            "Body",
            fontSize=11,
            fontName="Helvetica",
            leading=16,
            spaceBefore=4,
            spaceAfter=6,
            textColor=Colors.TEXT_DARK,
        )

        self.body_bold = ParagraphStyle(
            "BodyBold",
            fontSize=11,
            fontName="Helvetica-Bold",
            leading=16,
            spaceBefore=4,
            spaceAfter=6,
            textColor=Colors.TEXT_DARK,
        )

        self.metric = ParagraphStyle(
            "Metric",
            fontSize=12,
            fontName="Helvetica",
            leading=18,
            spaceBefore=4,
            spaceAfter=4,
            textColor=Colors.TEXT_DARK,
        )

        self.caption = ParagraphStyle(
            "Caption",
            fontSize=10,
            fontName="Helvetica-Oblique",
            alignment=TA_CENTER,
            spaceBefore=6,
            spaceAfter=6,
            textColor=Colors.TEXT_MEDIUM,
        )

        self.code = ParagraphStyle(
            "Code",
            fontSize=9,
            fontName="Courier",
            leading=12,
            spaceBefore=4,
            spaceAfter=4,
            textColor=Colors.TEXT_DARK,
            backColor=Colors.BG_LIGHT,
        )

        self.number = ParagraphStyle(
            "Number",
            fontSize=12,
            fontName="Helvetica-Bold",
            textColor=Colors.PRIMARY,
        )
