"""Excel export using openpyxl."""

from __future__ import annotations
try:
    import openpyxl
    from openpyxl.styles import (
        Font, Alignment, PatternFill, Border, Side, numbers
    )
    from openpyxl.utils import get_column_letter
    OPENPYXL_OK = True
except ImportError:
    OPENPYXL_OK = False

from database.db_manager import get_full_results, ms_to_str


def _border(style="thin"):
    s = Side(style=style)
    return Border(left=s, right=s, top=s, bottom=s)


def export_competition_excel(competition_id: int, filepath: str) -> str:
    """
    Export all results for *competition_id* to an Excel file at *filepath*.
    Returns the filepath on success.
    """
    if not OPENPYXL_OK:
        raise ImportError("openpyxl is not installed. Run: pip install openpyxl")

    rows = get_full_results(competition_id)
    if not rows:
        raise ValueError("No results found for this competition.")

    comp = rows[0]
    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # remove default sheet

    # Group rows by (acara_number, heat_number)
    from collections import defaultdict
    groups: dict[tuple, list] = defaultdict(list)
    for r in rows:
        groups[(r["acara_number"], r["heat_number"])].append(r)

    # One sheet per event
    event_sheets: dict[int, openpyxl.worksheet.worksheet.Worksheet] = {}
    for (acara_num, heat_num), heat_rows in sorted(groups.items()):
        sheet_name = f"Acara {acara_num}"
        if sheet_name not in event_sheets:
            ws = wb.create_sheet(title=sheet_name)
            event_sheets[sheet_name] = ws
            _write_event_header(ws, comp, heat_rows[0])
            ws._current_row = 8  # start data below headers
        else:
            ws = event_sheets[sheet_name]

        _write_heat(ws, heat_num, heat_rows)

    # Summary sheet
    _write_summary(wb, rows, comp)

    wb.save(filepath)
    return filepath


def _header_font(bold=True, size=11):
    return Font(name="Arial", bold=bold, size=size)


def _write_event_header(ws, comp: dict, first_row: dict):
    # Title rows
    ws.merge_cells("A1:H1")
    ws["A1"] = "BUKU ACARA"
    ws["A1"].font = Font(name="Arial", bold=True, size=14)
    ws["A1"].alignment = Alignment(horizontal="center")

    ws.merge_cells("A2:H2")
    ws["A2"] = f"{comp['comp_title']} {comp['comp_year']}"
    ws["A2"].font = Font(name="Arial", bold=True, size=12)
    ws["A2"].alignment = Alignment(horizontal="center")

    ws.merge_cells("A3:H3")
    ws["A3"] = comp["comp_date"]
    ws["A3"].font = Font(name="Arial", size=11)
    ws["A3"].alignment = Alignment(horizontal="center")

    ws.merge_cells("A4:H4")
    ws["A4"] = ""  # spacer

    # Event descriptor row
    ws.merge_cells("C5:H5")
    ws["A5"] = f"ACARA {first_row['acara_number']}"
    ws["A5"].font = _header_font()
    event_label = (
        f"{first_row['distance_m']} METER {first_row['stroke']} {first_row['gender']}"
    )
    ws["C5"] = event_label
    ws["C5"].font = _header_font()
    ws["C5"].alignment = Alignment(horizontal="right")

    # Seri row
    ws["A6"] = f"SERI {first_row['seri']}" if first_row.get("seri") else ""
    ws["A6"].font = _header_font()

    # Column headers
    header_fill = PatternFill("solid", fgColor="1F4E79")
    header_font = Font(name="Arial", bold=True, color="FFFFFF", size=10)
    headers = ["SERI", "LINTASAN", "NAMA ATLET", "SEKOLAH", "WAKTU", "KETERANGAN", "PERINGKAT", "HEAT"]
    for col, h in enumerate(headers, start=1):
        cell = ws.cell(row=7, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = _border()

    ws.column_dimensions["A"].width = 12
    ws.column_dimensions["B"].width = 10
    ws.column_dimensions["C"].width = 28
    ws.column_dimensions["D"].width = 28
    ws.column_dimensions["E"].width = 14
    ws.column_dimensions["F"].width = 18
    ws.column_dimensions["G"].width = 12
    ws.column_dimensions["H"].width = 8
    ws.row_dimensions[7].height = 20


def _write_heat(ws, heat_num: int, heat_rows: list):
    row_num = getattr(ws, "_current_row", 8)
    alt_fill = PatternFill("solid", fgColor="DCE6F1")
    for i, r in enumerate(heat_rows):
        fill = alt_fill if i % 2 == 0 else PatternFill()
        values = [
            r.get("seri", ""),
            r["lane"],
            r["athlete_name"],
            r["school"],
            ms_to_str(r["time_ms"]),
            r["notes"],
            r["rank"] if r["rank"] else "",
            heat_num,
        ]
        for col, val in enumerate(values, start=1):
            cell = ws.cell(row=row_num, column=col, value=val)
            cell.font = Font(name="Arial", size=10)
            cell.border = _border()
            cell.fill = fill
            if col == 2:
                cell.alignment = Alignment(horizontal="center")
            if col == 5:
                cell.alignment = Alignment(horizontal="center")
            if col in (7, 8):
                cell.alignment = Alignment(horizontal="center")
        row_num += 1
    ws._current_row = row_num + 1  # blank spacer between heats


def _write_summary(wb, rows: list, comp: dict):
    ws = wb.create_sheet(title="Rekapitulasi")
    ws.merge_cells("A1:G1")
    ws["A1"] = f"REKAPITULASI HASIL – {comp['comp_title']} {comp['comp_year']}"
    ws["A1"].font = Font(name="Arial", bold=True, size=13)
    ws["A1"].alignment = Alignment(horizontal="center")

    headers = ["ACARA", "SERI", "HEAT", "LINTASAN", "NAMA ATLET", "SEKOLAH", "WAKTU", "PERINGKAT"]
    fill = PatternFill("solid", fgColor="1F4E79")
    for col, h in enumerate(headers, start=1):
        cell = ws.cell(row=3, column=col, value=h)
        cell.font = Font(name="Arial", bold=True, color="FFFFFF", size=10)
        cell.fill = fill
        cell.alignment = Alignment(horizontal="center")
        cell.border = _border()

    for i, r in enumerate(rows, start=4):
        alt = PatternFill("solid", fgColor="EBF1DE") if i % 2 == 0 else PatternFill()
        values = [
            r["acara_number"], r.get("seri", ""), r["heat_number"],
            r["lane"], r["athlete_name"], r["school"],
            ms_to_str(r["time_ms"]), r["rank"] if r["rank"] else "",
        ]
        for col, val in enumerate(values, start=1):
            cell = ws.cell(row=i, column=col, value=val)
            cell.font = Font(name="Arial", size=10)
            cell.border = _border()
            cell.fill = alt

    col_widths = [8, 12, 8, 10, 28, 28, 14, 12]
    for col, w in enumerate(col_widths, start=1):
        ws.column_dimensions[get_column_letter(col)].width = w
