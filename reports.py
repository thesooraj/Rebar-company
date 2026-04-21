"""
reports.py — The Rebar Company
Generates weekly/fortnightly PDF timesheet reports.
"""

import os
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

import database as db

# ── Output folder ──────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR = os.path.join(BASE_DIR, "database", "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

# ── Brand colours ──────────────────────────────────────────
BLUE   = colors.HexColor("#1565C0")
ORANGE = colors.HexColor("#FF6F00")
DARK   = colors.HexColor("#0A0F1E")
LIGHT  = colors.HexColor("#F0F4FF")
GREY   = colors.HexColor("#8898AA")
WHITE  = colors.white


def get_period_dates(period_type: str, ref_date: datetime = None):
    """Return (start, end) date strings for weekly or fortnightly periods."""
    if ref_date is None:
        ref_date = datetime.utcnow()

    # Find most recent Monday
    days_since_monday = ref_date.weekday()
    monday = ref_date - timedelta(days=days_since_monday)
    monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)

    if period_type == "weekly":
        start = monday
        end   = monday + timedelta(days=6)
    else:  # fortnightly
        start = monday - timedelta(weeks=1)
        end   = monday + timedelta(days=6)

    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def generate_report(period_type: str, from_date: str, to_date: str,
                    generated_by: int = None) -> str:
    """
    Generate a PDF timesheet report.
    Returns the file path of the generated PDF.
    """
    conn    = db.get_connection()
    records = conn.execute(
        """SELECT cr.*, e.full_name, e.employee_code, e.department, e.role
           FROM clock_records cr
           JOIN employees e ON e.id = cr.employee_id
           WHERE DATE(cr.clock_in) BETWEEN DATE(?) AND DATE(?)
           ORDER BY e.full_name, cr.clock_in""",
        (from_date, to_date)
    ).fetchall()
    conn.close()

    # ── Group by employee ──────────────────────────────────
    employees = {}
    for r in records:
        eid = r["employee_code"]
        if eid not in employees:
            employees[eid] = {
                "name":       r["full_name"],
                "code":       r["employee_code"],
                "department": r["department"] or "—",
                "records":    [],
                "total_mins": 0,
            }
        employees[eid]["records"].append(r)
        employees[eid]["total_mins"] += r["total_minutes"] or 0

    # ── File path ──────────────────────────────────────────
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename  = f"report_{period_type}_{from_date}_to_{to_date}_{timestamp}.pdf"
    filepath  = os.path.join(REPORTS_DIR, filename)

    # ── Build PDF ──────────────────────────────────────────
    doc   = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=15*mm,  bottomMargin=15*mm,
    )
    story = []
    styles = getSampleStyleSheet()

    # Header title style
    title_style = ParagraphStyle(
        "title", fontName="Helvetica-Bold", fontSize=22,
        textColor=BLUE, spaceAfter=2
    )
    sub_style = ParagraphStyle(
        "sub", fontName="Helvetica", fontSize=10,
        textColor=GREY, spaceAfter=10
    )
    section_style = ParagraphStyle(
        "section", fontName="Helvetica-Bold", fontSize=11,
        textColor=WHITE, spaceAfter=4
    )
    normal_style = ParagraphStyle(
        "normal", fontName="Helvetica", fontSize=9,
        textColor=DARK
    )

    # ── Logo / Header ──────────────────────────────────────
    story.append(Paragraph("THE REBAR COMPANY", title_style))
    story.append(Paragraph(
        f"{period_type.capitalize()} Timesheet Report  ·  "
        f"{from_date}  to  {to_date}  ·  "
        f"Generated {datetime.utcnow().strftime('%d %b %Y %H:%M')} UTC",
        sub_style
    ))
    story.append(HRFlowable(width="100%", thickness=2, color=ORANGE, spaceAfter=14))

    # ── Summary table ──────────────────────────────────────
    total_all_mins = sum(e["total_mins"] for e in employees.values())
    total_shifts   = sum(len(e["records"]) for e in employees.values())

    summary_data = [
        ["Total Employees", "Total Shifts", "Total Hours"],
        [
            str(len(employees)),
            str(total_shifts),
            f"{total_all_mins // 60}h {total_all_mins % 60}m",
        ]
    ]
    summary_table = Table(summary_data, colWidths=[60*mm, 60*mm, 60*mm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0), BLUE),
        ("TEXTCOLOR",    (0, 0), (-1, 0), WHITE),
        ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0), 10),
        ("ALIGN",        (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME",     (0, 1), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 1), (-1, 1), 14),
        ("TEXTCOLOR",    (0, 1), (-1, 1), BLUE),
        ("BACKGROUND",   (0, 1), (-1, 1), colors.HexColor("#EEF4FF")),
        ("ROWBACKGROUNDS", (0, 1), (-1, 1), [colors.HexColor("#EEF4FF")]),
        ("BOX",          (0, 0), (-1, -1), 0.5, BLUE),
        ("GRID",         (0, 0), (-1, -1), 0.3, GREY),
        ("TOPPADDING",   (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 8),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 14))

    # ── Per-employee sections ──────────────────────────────
    for eid, emp in employees.items():
        # Employee header bar
        header_data = [[
            f"  {emp['name']}  ·  {emp['code']}  ·  {emp['department']}",
            f"Total: {emp['total_mins'] // 60}h {emp['total_mins'] % 60}m  "
        ]]
        header_table = Table(header_data, colWidths=[130*mm, 50*mm])
        header_table.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), BLUE),
            ("TEXTCOLOR",     (0, 0), (-1, -1), WHITE),
            ("FONTNAME",      (0, 0), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, -1), 10),
            ("ALIGN",         (0, 0), (0, 0),   "LEFT"),
            ("ALIGN",         (1, 0), (1, 0),   "RIGHT"),
            ("TOPPADDING",    (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ]))
        story.append(header_table)

        # Shifts table
        shift_data = [["Date", "Clock In", "Clock Out", "Duration", "Method", "Location"]]
        for r in emp["records"]:
            shift_data.append([
                r["clock_in"][:10],
                r["clock_in"][11:16],
                r["clock_out"][11:16] if r["clock_out"] else "—",
                f"{(r['total_minutes'] or 0) // 60}h {(r['total_minutes'] or 0) % 60}m"
                    if r["total_minutes"] else "Active",
                (r["method"] or "manual").capitalize(),
                r["location"] or "—",
            ])

        shift_table = Table(
            shift_data,
            colWidths=[28*mm, 22*mm, 22*mm, 22*mm, 22*mm, 64*mm]
        )
        shift_table.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0), colors.HexColor("#1976D2")),
            ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
            ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, -1), 8),
            ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1),
             [colors.HexColor("#F8FAFF"), WHITE]),
            ("GRID",          (0, 0), (-1, -1), 0.3, GREY),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(shift_table)
        story.append(Spacer(1, 12))

    # ── Footer ─────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=1, color=GREY, spaceAfter=6))
    story.append(Paragraph(
        f"Confidential — The Rebar Company  ·  Generated {datetime.utcnow().strftime('%d %b %Y')}",
        ParagraphStyle("footer", fontName="Helvetica", fontSize=8, textColor=GREY, alignment=TA_CENTER)
    ))

    doc.build(story)

    # ── Save to DB ─────────────────────────────────────────
    conn = db.get_connection()
    conn.execute(
        """INSERT INTO reports (report_type, period_start, period_end, generated_by, file_path)
           VALUES (?, ?, ?, ?, ?)""",
        (period_type, from_date, to_date, generated_by, filepath)
    )
    conn.commit()
    conn.close()

    return filepath