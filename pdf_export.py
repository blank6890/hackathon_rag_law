"""
ComplianceMind — PDF certificate export.

Generates a downloadable PDF compliance certificate that matches the
"Government Gazette" visual language of the web UI: ivory paper background,
navy headings in serif, seal-red accents, gold rule lines.

Uses ReportLab with built-in fonts (Times, Helvetica, Courier) so the PDF
renders identically on any system without requiring font registration.
Currency is written as "Rs." (not the rupee symbol) for the same reason.

Layout:
  1. Letterhead strip — Ref. No. + "Issued electronically" + gold rule
  2. Emblem (text-based scale glyph) + "ComplianceMind" title
  3. "NOTICE OF FINDINGS" masthead
  4. Score gauge — drawn as a colored ring with score + grade inside
  5. Score summary line
  6. Business description (truncated to 500 chars)
  7. Findings table — Section | Act | Status | Severity | Penalty | Reasoning
  8. Footer — "Issued by ComplianceMind" + date + "not legal advice"
"""

import io
import html
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, black, white
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY

# ── Design tokens (must match styles.py exactly) ───────────────────────────
PAPER = HexColor("#F7F5F0")
INK = HexColor("#1A1A1A")
NAVY = HexColor("#1B2A4A")
SEAL_RED = HexColor("#8C1D1D")
GOLD = HexColor("#B08D57")
GREEN = HexColor("#4C6B3F")
MAJOR_ORANGE = HexColor("#C97A1D")
RULE_GREY = HexColor("#1A1A1A0F")  # very light grey for hairlines

# Status → color mapping (matches styles.py)
_STATUS_COLORS = {
    "compliant": GREEN,
    "gap": SEAL_RED,
    "unclear": GOLD,
}
_STATUS_LABELS = {
    "compliant": "COMPLIANT",
    "gap": "GAP FOUND",
    "unclear": "UNCLEAR",
}
_SEVERITY_COLORS = {
    "critical": SEAL_RED,
    "major": MAJOR_ORANGE,
    "minor": GOLD,
}
_SEVERITY_LABELS = {
    "critical": "CRITICAL",
    "major": "MAJOR",
    "minor": "MINOR",
}


def _truncate(text: str, max_chars: int) -> str:
    """Truncate text to max_chars, adding an ellipsis if cut."""
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "\u2026"


def _draw_gauge(c: canvas.Canvas, x: float, y: float, diameter: float,
                score: int, grade: str, grade_color) -> None:
    """Draw a circular score gauge at (x, y) with given diameter.

    The outer ring is a thick arc colored by grade_color, proportional to
    the score (0-100). The inner disc is white with the score number and
    grade letter centered inside.
    """
    radius = diameter / 2
    cx = x + radius
    cy = y + radius

    # Background ring (light grey, full circle)
    c.setFillColor(HexColor("#1B2A4A1A"))  # 10% navy
    c.circle(cx, cy, radius, fill=1, stroke=0)

    # Filled arc — proportional to score
    # ReportLab's wedge(x1, y1, x2, y2, startAng, extent) draws a pie slice
    # from startAng degrees, counterclockwise by extent degrees. We want a
    # clockwise fill from 12 o'clock (90°), so start at 90 and use a
    # negative extent proportional to the score.
    if score > 0:
        c.setFillColor(grade_color)
        c.wedge(
            x, y, x + diameter, y + diameter,
            90,                              # startAng (12 o'clock)
            -(score * 3.6),                  # extent (clockwise)
            fill=1,
            stroke=0,
        )

    # Inner white disc — covers the center, leaving just the ring
    inner_radius = radius * 0.72
    c.setFillColor(white)
    c.setStrokeColor(HexColor("#1B2A4A14"))
    c.setLineWidth(0.5)
    c.circle(cx, cy, inner_radius, fill=1, stroke=1)

    # Score number — large, serif, navy, centered
    c.setFillColor(NAVY)
    c.setFont("Times-Bold", diameter * 0.32)
    score_str = str(score)
    score_w = c.stringWidth(score_str, "Times-Bold", diameter * 0.32)
    c.drawString(cx - score_w / 2, cy + 2, score_str)

    # Grade letter — small, mono, colored, below the number
    c.setFillColor(grade_color)
    c.setFont("Courier-Bold", diameter * 0.14)
    grade_w = c.stringWidth(grade, "Courier-Bold", diameter * 0.14)
    c.drawString(cx - grade_w / 2, cy - diameter * 0.18, grade)

    # Label below the gauge
    c.setFillColor(HexColor("#1A1A1A99"))  # 60% ink
    c.setFont("Courier", 6.5)
    label = "COMPLIANCE SCORE"
    label_w = c.stringWidth(label, "Courier", 6.5)
    c.drawString(cx - label_w / 2, y - 12, label)


def generate_certificate(
    business_desc: str,
    findings: list[dict],
    sources: list[dict],
    score: int = 0,
    grade: str = "—",
    grade_color=None,
    score_summary: str = "",
) -> bytes:
    """Generate a PDF compliance certificate as bytes.

    Args:
        business_desc: The user's original business description text.
        findings: List of finding dicts from the pipeline (each with act,
            section, status, severity, penalty_range, reasoning).
        sources: List of source statute sections (each with act, section,
            title, text).
        score: 0-100 compliance score.
        grade: Letter grade (A/B/C/D/F).
        grade_color: HexColor for the grade.
        score_summary: One-line human-readable summary.

    Returns:
        PDF file contents as bytes.
    """
    if grade_color is None:
        grade_color = NAVY

    buf = io.BytesIO()

    # A4 page with ivory background — we'll draw the background manually
    # on each page via a page template function.
    page_w, page_h = A4
    margin = 20 * mm

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin,
        bottomMargin=margin,
    )

    # ── Styles ───────────────────────────────────────────────────────────
    styles = getSampleStyleSheet()

    style_eyebrow = ParagraphStyle(
        "Eyebrow", parent=styles["Normal"],
        fontName="Courier-Bold", fontSize=7, textColor=SEAL_RED,
        alignment=TA_LEFT, spaceAfter=4, leading=9,
    )
    style_title = ParagraphStyle(
        "Title", parent=styles["Heading1"],
        fontName="Times-Bold", fontSize=22, textColor=NAVY,
        alignment=TA_LEFT, spaceAfter=4, leading=26,
    )
    style_subtitle = ParagraphStyle(
        "Subtitle", parent=styles["Normal"],
        fontName="Helvetica", fontSize=9, textColor=INK,
        alignment=TA_LEFT, spaceAfter=10, leading=13,
    )
    style_section = ParagraphStyle(
        "Section", parent=styles["Heading2"],
        fontName="Times-Bold", fontSize=13, textColor=NAVY,
        alignment=TA_LEFT, spaceBefore=12, spaceAfter=6, leading=16,
    )
    style_body = ParagraphStyle(
        "Body", parent=styles["Normal"],
        fontName="Helvetica", fontSize=9, textColor=INK,
        alignment=TA_LEFT, leading=13, spaceAfter=4,
    )
    style_body_just = ParagraphStyle(
        "BodyJust", parent=style_body,
        alignment=TA_LEFT,  # left, not justify — per project rule
    )
    style_mono = ParagraphStyle(
        "Mono", parent=styles["Normal"],
        fontName="Courier", fontSize=8, textColor=NAVY,
        alignment=TA_LEFT, leading=11,
    )
    style_summary = ParagraphStyle(
        "Summary", parent=styles["Normal"],
        fontName="Courier", fontSize=8.5, textColor=NAVY,
        alignment=TA_LEFT, leading=12,
        backColor=HexColor("#1B2A4A0D"),
        borderPadding=6,
        leftIndent=0,
        spaceAfter=8,
    )
    style_footer = ParagraphStyle(
        "Footer", parent=styles["Normal"],
        fontName="Courier", fontSize=7, textColor=HexColor("#1A1A1A99"),
        alignment=TA_LEFT, leading=10,
    )
    style_footer_right = ParagraphStyle(
        "FooterR", parent=style_footer,
        alignment=TA_RIGHT,
    )
    style_cell = ParagraphStyle(
        "Cell", parent=styles["Normal"],
        fontName="Helvetica", fontSize=7.5, textColor=INK,
        alignment=TA_LEFT, leading=10,
    )
    style_cell_mono = ParagraphStyle(
        "CellMono", parent=style_cell,
        fontName="Courier", fontSize=7,
    )

    # ── Build content flowables ──────────────────────────────────────────
    story = []

    # Letterhead strip
    ref_suffix = "%04X" % (abs(hash(business_desc)) % 0xFFFF)
    ref_no = f"Ref. No. CM/{datetime.now().strftime('%Y')}/{ref_suffix}"
    letterhead = Table(
        [[
            Paragraph(f'<font name="Courier" size="7" color="#1B2A4A99">{ref_no}</font>', style_mono),
            Paragraph('<font name="Courier" size="7" color="#1B2A4A99">Issued electronically</font>',
                      ParagraphStyle("lr", parent=style_mono, alignment=TA_RIGHT)),
        ]],
        colWidths=[doc.width / 2, doc.width / 2],
    )
    letterhead.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, GOLD),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("TOPPADDING", (0, 0), (-1, 0), 0),
    ]))
    story.append(letterhead)
    story.append(Spacer(1, 14))

    # Emblem + title block
    # Use a 2-column table: emblem glyph on the left, title text on the right
    emblem_cell = Paragraph(
        '<font name="Times-Bold" size="32" color="#B08D57">\u2696</font>',
        ParagraphStyle("em", parent=style_body, alignment=TA_CENTER, leading=36),
    )
    title_cell = [
        Paragraph(
            '<font name="Times-Bold" size="22" color="#1B2A4A">ComplianceMind</font>',
            style_title,
        ),
        Paragraph(
            '<font name="Helvetica" size="8" color="#1A1A1AB3">'
            'A cited compliance check, not a guess. Each finding below is '
            'grounded in a specific provision of Indian statute law.'
            '</font>',
            style_subtitle,
        ),
    ]
    header_table = Table(
        [[emblem_cell, title_cell]],
        colWidths=[36 * mm, doc.width - 36 * mm],
    )
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 18))

    # "NOTICE OF FINDINGS" masthead with score gauge
    # We'll draw the gauge on the canvas via a custom flowable
    story.append(Paragraph(
        '<font name="Courier-Bold" size="7" color="#8C1D1D">OFFICIAL COMMUNICATION</font>',
        style_eyebrow,
    ))
    story.append(Paragraph(
        '<font name="Times-Bold" size="16" color="#1B2A4A">Notice of Findings</font>',
        style_section,
    ))
    story.append(Paragraph(
        '<font name="Helvetica" size="9" color="#1A1A1AB3">'
        'The following compliance assessment has been prepared from the '
        'business description you submitted. Each finding is grounded in a '
        'specific provision of Indian statute law.'
        '</font>',
        style_body,
    ))
    story.append(Spacer(1, 8))

    # Score summary
    if score_summary:
        story.append(Paragraph(
            html.escape(score_summary),
            style_summary,
        ))
        story.append(Spacer(1, 6))

    # Business description
    story.append(Paragraph(
        '<font name="Times-Bold" size="11" color="#1B2A4A">Business Description</font>',
        style_section,
    ))
    story.append(Paragraph(
        html.escape(_truncate(business_desc, 600)),
        style_body_just,
    ))
    story.append(Spacer(1, 12))

    # Findings table
    story.append(Paragraph(
        '<font name="Times-Bold" size="11" color="#1B2A4A">Findings</font>',
        style_section,
    ))

    # Build table data
    header_row = [
        Paragraph('<font name="Courier-Bold" size="7" color="#F7F5F0">SECTION</font>', style_cell_mono),
        Paragraph('<font name="Courier-Bold" size="7" color="#F7F5F0">ACT</font>', style_cell_mono),
        Paragraph('<font name="Courier-Bold" size="7" color="#F7F5F0">STATUS</font>', style_cell_mono),
        Paragraph('<font name="Courier-Bold" size="7" color="#F7F5F0">SEVERITY</font>', style_cell_mono),
        Paragraph('<font name="Courier-Bold" size="7" color="#F7F5F0">PENALTY EXPOSURE</font>', style_cell_mono),
        Paragraph('<font name="Courier-Bold" size="7" color="#F7F5F0">ASSESSMENT</font>', style_cell_mono),
    ]
    data = [header_row]

    for f in findings:
        status = (f.get("status") or "").lower()
        severity = (f.get("severity") or "minor").lower()
        status_label = _STATUS_LABELS.get(status, status.title())
        sev_label = _SEVERITY_LABELS.get(severity, severity.title())
        status_color_hex = _STATUS_COLORS.get(status, GOLD).hexval()[2:]  # strip 0x
        sev_color_hex = _SEVERITY_COLORS.get(severity, GOLD).hexval()[2:]

        penalty = f.get("penalty_range") or "Not specified"
        if penalty == "Not specified in section":
            penalty = "Not specified"

        row = [
            Paragraph(f'<font name="Courier" size="7" color="#1B2A4A">{html.escape(f.get("section", ""))}</font>', style_cell_mono),
            Paragraph(html.escape(_truncate(f.get("act", ""), 40)), style_cell),
            Paragraph(f'<font name="Courier-Bold" size="6.5" color="#{status_color_hex}">{status_label}</font>', style_cell_mono),
            Paragraph(f'<font name="Courier-Bold" size="6.5" color="#{sev_color_hex}">{sev_label}</font>', style_cell_mono),
            Paragraph(html.escape(_truncate(penalty, 35)), style_cell),
            Paragraph(html.escape(_truncate(f.get("reasoning", ""), 100)), style_cell),
        ]
        data.append(row)

    # Column widths — total must equal doc.width (~170mm on A4 with 20mm margins)
    col_widths = [22 * mm, 32 * mm, 20 * mm, 18 * mm, 32 * mm, 46 * mm]

    findings_table = Table(data, colWidths=col_widths, repeatRows=1)
    findings_table.setStyle(TableStyle([
        # Header row
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), PAPER),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        # Body rows
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
        ("TOPPADDING", (0, 1), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        # Alternating row backgrounds
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, HexColor("#F7F5F0")]),
        # Grid
        ("LINEBELOW", (0, 0), (-1, 0), 1, GOLD),
        ("LINEBELOW", (0, 1), (-1, -2), 0.25, HexColor("#1B2A4A20")),
        ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#1B2A4A30")),
    ]))
    story.append(findings_table)
    story.append(Spacer(1, 16))

    # Sources note
    if sources:
        story.append(Paragraph(
            '<font name="Times-Bold" size="11" color="#1B2A4A">Cited Statute Sections</font>',
            style_section,
        ))
        src_lines = []
        for s in sources:
            src_lines.append(
                f'<font name="Courier" size="7.5" color="#1B2A4A">'
                f'{html.escape(s.get("section", ""))}</font> '
                f'<font name="Helvetica" size="8.5">'
                f'{html.escape(s.get("act", ""))} \u2014 {html.escape(s.get("title", ""))}'
                f'</font>'
            )
        story.append(Paragraph("<br/>".join(src_lines), style_body))
        story.append(Spacer(1, 16))

    # Footer
    today = datetime.now().strftime("%d %B %Y")
    footer_table = Table(
        [[
            Paragraph(
                f'<font name="Times-Bold" size="10" color="#1B2A4A">\u2696</font> '
                f'<font name="Helvetica-Bold" size="8" color="#1B2A4A">Issued by ComplianceMind</font><br/>'
                f'<font name="Courier" size="6" color="#1A1A1A99">CITED COMPLIANCE CHECK \u00B7 NOT LEGAL ADVICE</font>',
                style_footer,
            ),
            Paragraph(
                f'<font name="Courier" size="6.5" color="#1A1A1A99">'
                f'Generated on {today}<br/>'
                f'Statutes reviewed: DPDP \u00B7 IT Act \u00B7 CPA \u00B7 GST'
                f'</font>',
                style_footer_right,
            ),
        ]],
        colWidths=[doc.width / 2, doc.width / 2],
    )
    footer_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEABOVE", (0, 0), (-1, 0), 0.5, HexColor("#1A1A1A1A")),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
    ]))
    story.append(Spacer(1, 20))
    story.append(footer_table)

    # ── Build with page background ───────────────────────────────────────
    def _on_page(c: canvas.Canvas, doc):
        # Ivory paper background — full page
        c.saveState()
        c.setFillColor(PAPER)
        c.rect(0, 0, page_w, page_h, fill=1, stroke=0)
        c.restoreState()

        # Top accent stripe (navy → gold gradient simulated with 2 stripes)
        c.saveState()
        c.setFillColor(NAVY)
        c.rect(0, page_h - 3, page_w * 0.7, 3, fill=1, stroke=0)
        c.setFillColor(GOLD)
        c.rect(page_w * 0.7, page_h - 3, page_w * 0.3, 3, fill=1, stroke=0)
        c.restoreState()

        # Draw the score gauge in the top-right of the first page
        if doc.page == 1:
            gauge_diameter = 24 * mm
            gauge_x = page_w - margin - gauge_diameter
            gauge_y = page_h - margin - gauge_diameter - 4
            _draw_gauge(
                c, gauge_x, gauge_y, gauge_diameter,
                score, grade, grade_color,
            )

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)

    return buf.getvalue()
