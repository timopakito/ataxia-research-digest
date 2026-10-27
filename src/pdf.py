from datetime import date
from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"

_styles = getSampleStyleSheet()
TITLE_STYLE = ParagraphStyle("DigestTitle", parent=_styles["Title"])
INTRO_STYLE = ParagraphStyle("DigestIntro", parent=_styles["BodyText"], spaceAfter=14)
HEADING_STYLE = ParagraphStyle(

    "DigestHeading", parent=_styles["Heading2"], spaceBefore=18, spaceAfter=8
)
ITEM_TITLE_STYLE = ParagraphStyle(
    "DigestItemTitle",
    parent=_styles["BodyText"],
    textColor=colors.HexColor("#1a4b8c"),
    spaceAfter=2,
)
ITEM_SUMMARY_STYLE = ParagraphStyle(
    "DigestItemSummary", parent=_styles["BodyText"], spaceAfter=12
)


def render_pdf(digest, title, output_path=None):
    output_path = output_path or OUTPUT_DIR / f"digest-{date.today().isoformat()}.pdf"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
    )

    story = [
        Paragraph(escape(title), TITLE_STYLE),
        Spacer(1, 12),
        Paragraph(escape(digest["intro"]), INTRO_STYLE),
    ]

    for section in digest["sections"]:
        items = [
            item
            for item in section["items"]
            if item["url"].startswith(("http://", "https://"))
        ]
        if not items:
            continue
        story.append(Paragraph(escape(section["heading"]), HEADING_STYLE))
        for item in items:
            safe_url = escape(item["url"], quote=True)
            title_text = escape(item["title"])
            story.append(
                Paragraph(f'<a href="{safe_url}">{title_text}</a>', ITEM_TITLE_STYLE)
            )
            story.append(Paragraph(escape(item["summary"]), ITEM_SUMMARY_STYLE))

    doc.build(story)
    return output_path
