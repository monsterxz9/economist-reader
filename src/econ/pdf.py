import datetime
import os
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ECONOMIST_RED = colors.HexColor("#E3120B")
ECONOMIST_BLACK = colors.HexColor("#1F1F1F")
TEXT_GRAY = colors.HexColor("#333333")

REPO_FONT_DIR = Path(__file__).resolve().parents[2] / "fonts"

CJK_FONT_CANDIDATES = [
    REPO_FONT_DIR / "NotoSansSC-Regular.ttf",
    Path("/System/Library/Fonts/STHeiti Light.ttc"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
]
CJK_BOLD_CANDIDATES = [
    REPO_FONT_DIR / "NotoSansSC-Bold.ttf",
    Path("/System/Library/Fonts/STHeiti Medium.ttc"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"),
    Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc"),
]


def _first_existing(candidates: list[Path]) -> Path:
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(f"No CJK font found. Tried: {[str(p) for p in candidates]}")


def _header_footer(canvas, doc):
    canvas.saveState()

    canvas.setFillColor(ECONOMIST_RED)
    canvas.rect(0, A4[1] - 15 * mm, A4[0], 15 * mm, fill=1, stroke=0)

    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 12)
    canvas.drawString(15 * mm, A4[1] - 10 * mm, "The Economist | Daily Study Guide")

    today = datetime.date.today().strftime("%B %d, %Y")
    canvas.drawRightString(A4[0] - 15 * mm, A4[1] - 10 * mm, today)

    canvas.setFillColor(colors.gray)
    canvas.setFont("Helvetica", 9)
    canvas.drawRightString(A4[0] - 15 * mm, 10 * mm, f"Page {canvas.getPageNumber()}")

    canvas.setStrokeColor(ECONOMIST_RED)
    canvas.setLineWidth(0.5)
    canvas.line(15 * mm, 15 * mm, A4[0] - 15 * mm, 15 * mm)

    canvas.restoreState()


def _register_fonts():
    regular = _first_existing(CJK_FONT_CANDIDATES)
    bold = _first_existing(CJK_BOLD_CANDIDATES)
    print(f"[pdf] CJK font: {regular} / {bold}", file=sys.stderr)
    pdfmetrics.registerFont(TTFont("CJK", str(regular)))
    pdfmetrics.registerFont(TTFont("CJK-Bold", str(bold)))
    registerFontFamily("CJK", normal="CJK", bold="CJK-Bold", italic="CJK", boldItalic="CJK-Bold")


def _styles():
    base = getSampleStyleSheet()
    return {
        "title_en": ParagraphStyle(
            "TitleEn", parent=base["Heading1"], fontName="Helvetica-Bold",
            fontSize=24, leading=28, textColor=ECONOMIST_BLACK, spaceAfter=4,
        ),
        "title_cn": ParagraphStyle(
            "TitleCn", parent=base["Heading1"], fontName="CJK-Bold",
            fontSize=16, leading=22, textColor=TEXT_GRAY, spaceAfter=15,
        ),
        "meta": ParagraphStyle(
            "Meta", parent=base["Normal"], fontName="CJK",
            fontSize=10, textColor=ECONOMIST_RED, spaceAfter=20,
        ),
        "h2_en": ParagraphStyle(
            "H2En", parent=base["Heading2"], fontName="Helvetica-Bold",
            fontSize=11, textColor=ECONOMIST_RED, spaceBefore=15, spaceAfter=3,
        ),
        "h2_cn": ParagraphStyle(
            "H2Cn", parent=base["Heading2"], fontName="CJK-Bold",
            fontSize=11, textColor=ECONOMIST_BLACK, spaceAfter=8,
        ),
        "body_en": ParagraphStyle(
            "BodyEn", parent=base["Normal"], fontName="Times-Roman",
            fontSize=11, leading=15, spaceAfter=8, alignment=4,
        ),
        "body_cn": ParagraphStyle(
            "BodyCn", parent=base["Normal"], fontName="CJK",
            fontSize=10, leading=14, textColor=TEXT_GRAY, spaceAfter=15,
        ),
        "vocab_header": ParagraphStyle(
            "VocabHeader", parent=base["Heading1"], fontName="Helvetica-Bold",
            fontSize=18, textColor=ECONOMIST_RED, spaceBefore=10, spaceAfter=15,
        ),
    }


def generate(data: dict, output_path: str | os.PathLike) -> Path:
    _register_fonts()
    styles = _styles()

    doc = SimpleDocTemplate(
        str(output_path), pagesize=A4,
        rightMargin=20 * mm, leftMargin=20 * mm,
        topMargin=25 * mm, bottomMargin=25 * mm,
    )

    elements: list = [Spacer(1, 5)]
    elements.append(Paragraph(data.get("title_en", ""), styles["title_en"]))
    elements.append(Paragraph(data.get("title_cn", ""), styles["title_cn"]))
    elements.append(Paragraph(f"<b>SUMMARY:</b> {data.get('summary', '')}", styles["meta"]))

    for section in data.get("sections", []):
        if section.get("subtitle_en"):
            elements.append(Paragraph(section["subtitle_en"].upper(), styles["h2_en"]))
        if section.get("subtitle_cn"):
            elements.append(Paragraph(section["subtitle_cn"], styles["h2_cn"]))
        for p in section.get("paragraphs", []):
            if p.get("en"):
                elements.append(Paragraph(p["en"], styles["body_en"]))
            if p.get("cn"):
                elements.append(Paragraph(p["cn"], styles["body_cn"]))

    if data.get("vocabulary"):
        elements.append(PageBreak())
        elements.append(Paragraph("Essential Vocabulary", styles["vocab_header"]))

        table_data = [[
            Paragraph("<b>WORD / PHRASE</b>", styles["h2_en"]),
            Paragraph("<b>MEANING</b>", styles["h2_cn"]),
            Paragraph("<b>CONTEXT</b>", styles["h2_en"]),
        ]]
        for item in data["vocabulary"]:
            table_data.append([
                Paragraph(f"<b>{item.get('word', '')}</b>", styles["body_en"]),
                Paragraph(item.get("mean", ""), styles["body_cn"]),
                Paragraph(f"<i>{item.get('context', '')}</i>", styles["body_en"]),
            ])

        t = Table(table_data, colWidths=[45 * mm, 40 * mm, 85 * mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.95, 0.95, 0.95)),
            ("LINEBELOW", (0, 0), (-1, 0), 2, ECONOMIST_RED),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("PADDING", (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.Color(0.98, 0.98, 0.98)]),
            ("LINEBELOW", (0, 1), (-1, -1), 0.5, colors.lightgrey),
        ]))
        elements.append(t)

    doc.build(elements, onFirstPage=_header_footer, onLaterPages=_header_footer)
    return Path(output_path)
