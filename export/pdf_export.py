"""PDF export using reportlab."""

from __future__ import annotations

try:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph,
        Spacer, PageBreak, KeepTogether,
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    REPORTLAB_OK = True
except ImportError:
    REPORTLAB_OK = False

from database.db_manager import get_full_results, ms_to_str
from collections import defaultdict


def export_competition_pdf(competition_id: int, filepath: str) -> str:
    if not REPORTLAB_OK:
        raise ImportError("reportlab is not installed. Run: pip install reportlab")

    rows = get_full_results(competition_id)
    if not rows:
        raise ValueError("No results found for this competition.")

    comp = rows[0]
    doc = SimpleDocTemplate(
        filepath,
        pagesize=landscape(A4),
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        title=f"Buku Acara – {comp['comp_title']} {comp['comp_year']}",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title2", parent=styles["Title"], fontSize=14, spaceAfter=2
    )
    sub_style = ParagraphStyle(
        "Sub", parent=styles["Normal"], fontSize=11, alignment=TA_CENTER, spaceAfter=2
    )
    section_style = ParagraphStyle(
        "Section", parent=styles["Normal"], fontSize=10, textColor=colors.HexColor("#1F4E79"),
        spaceAfter=2,
    )

    story = []

    # Cover header
    story.append(Paragraph("BUKU ACARA", title_style))
    story.append(Paragraph(f"{comp['comp_title']} {comp['comp_year']}", sub_style))
    story.append(Paragraph(comp["comp_date"], sub_style))
    if comp.get("comp_venue"):
        story.append(Paragraph(comp["comp_venue"], sub_style))
    story.append(Spacer(1, 0.5 * cm))

    # Group by acara then heat
    groups: dict[int, dict] = defaultdict(lambda: defaultdict(list))
    event_meta: dict[int, dict] = {}
    for r in rows:
        acara = r["acara_number"]
        heat = r["heat_number"]
        groups[acara][heat].append(r)
        if acara not in event_meta:
            event_meta[acara] = r

    header_color = colors.HexColor("#1F4E79")
    alt_color = colors.HexColor("#DCE6F1")
    white = colors.white

    for acara_num in sorted(groups.keys()):
        meta = event_meta[acara_num]
        event_label = (
            f"ACARA {acara_num} – {meta['distance_m']} METER "
            f"{meta['stroke']} {meta['gender']}"
        )
        if meta.get("seri"):
            event_label += f"  |  SERI {meta['seri']}"
        story.append(Paragraph(event_label, section_style))

        for heat_num in sorted(groups[acara_num].keys()):
            heat_rows = groups[acara_num][heat_num]
            story.append(Paragraph(f"Heat {heat_num}", styles["Normal"]))

            table_data = [["LINTASAN", "NAMA ATLET", "SEKOLAH", "WAKTU", "PERINGKAT", "KETERANGAN"]]
            for r in heat_rows:
                table_data.append([
                    str(r["lane"]),
                    r["athlete_name"] or "-",
                    r["school"] or "-",
                    ms_to_str(r["time_ms"]) or "-",
                    str(r["rank"]) if r["rank"] else "-",
                    r["notes"] or "",
                ])

            col_widths = [2 * cm, 6 * cm, 6 * cm, 3 * cm, 2.5 * cm, 5 * cm]
            tbl = Table(table_data, colWidths=col_widths)
            style_cmds = [
                ("BACKGROUND", (0, 0), (-1, 0), header_color),
                ("TEXTCOLOR", (0, 0), (-1, 0), white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("ALIGN", (0, 1), (0, -1), "CENTER"),
                ("ALIGN", (3, 1), (4, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, alt_color]),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
            tbl.setStyle(TableStyle(style_cmds))
            story.append(KeepTogether([tbl, Spacer(1, 0.3 * cm)]))

        story.append(Spacer(1, 0.4 * cm))

    # Summary table
    story.append(PageBreak())
    story.append(Paragraph("REKAPITULASI HASIL", title_style))
    story.append(Spacer(1, 0.3 * cm))

    summary_data = [["ACARA", "SERI", "HEAT", "LANE", "NAMA ATLET", "SEKOLAH", "WAKTU", "RANK"]]
    for r in rows:
        summary_data.append([
            str(r["acara_number"]),
            r.get("seri", ""),
            str(r["heat_number"]),
            str(r["lane"]),
            r["athlete_name"] or "-",
            r["school"] or "-",
            ms_to_str(r["time_ms"]) or "-",
            str(r["rank"]) if r["rank"] else "-",
        ])

    s_widths = [1.8 * cm, 2.5 * cm, 1.8 * cm, 1.8 * cm, 6 * cm, 6 * cm, 3 * cm, 2 * cm]
    s_tbl = Table(summary_data, colWidths=s_widths)
    s_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), header_color),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, alt_color]),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(s_tbl)

    doc.build(story)
    return filepath
