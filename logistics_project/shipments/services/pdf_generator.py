"""
shipments/services/pdf_generator.py
=====================================
Professional invoice PDF generator for CJ Darcl Logistics.
Uses ReportLab to produce an A4-sized invoice.

Usage:
    from shipments.services.pdf_generator import generate_invoice
    pdf_bytes = generate_invoice(shipment_id=123)
"""

import io
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, HRFlowable,
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT


# ─── Brand palette ────────────────────────────────────────────────────────────
BRAND_TEAL   = colors.HexColor("#0D9488")   # CJ Darcl primary
BRAND_DARK   = colors.HexColor("#0F172A")   # Near-black
BRAND_LIGHT  = colors.HexColor("#F0FDFA")   # Light teal background
BRAND_GRAY   = colors.HexColor("#64748B")   # Muted label
BRAND_LINE   = colors.HexColor("#CBD5E1")   # Table border
WHITE        = colors.white


def _styles():
    """Return a dict of named paragraph styles."""
    base = getSampleStyleSheet()
    return {
        "company": ParagraphStyle(
            "company",
            fontName="Helvetica-Bold",
            fontSize=18,
            textColor=WHITE,
            leading=22,
            alignment=TA_LEFT,
        ),
        "tagline": ParagraphStyle(
            "tagline",
            fontName="Helvetica",
            fontSize=9,
            textColor=colors.HexColor("#99F6E4"),
            leading=12,
            alignment=TA_LEFT,
        ),
        "invoice_label": ParagraphStyle(
            "invoice_label",
            fontName="Helvetica-Bold",
            fontSize=20,
            textColor=WHITE,
            alignment=TA_RIGHT,
        ),
        "invoice_sub": ParagraphStyle(
            "invoice_sub",
            fontName="Helvetica",
            fontSize=9,
            textColor=colors.HexColor("#99F6E4"),
            alignment=TA_RIGHT,
        ),
        "section_head": ParagraphStyle(
            "section_head",
            fontName="Helvetica-Bold",
            fontSize=9,
            textColor=BRAND_TEAL,
            spaceAfter=2,
        ),
        "label": ParagraphStyle(
            "label",
            fontName="Helvetica",
            fontSize=8.5,
            textColor=BRAND_GRAY,
            leading=12,
        ),
        "value": ParagraphStyle(
            "value",
            fontName="Helvetica-Bold",
            fontSize=9,
            textColor=BRAND_DARK,
            leading=13,
        ),
        "table_head": ParagraphStyle(
            "table_head",
            fontName="Helvetica-Bold",
            fontSize=8.5,
            textColor=WHITE,
            alignment=TA_CENTER,
        ),
        "cell": ParagraphStyle(
            "cell",
            fontName="Helvetica",
            fontSize=8.5,
            textColor=BRAND_DARK,
            alignment=TA_CENTER,
        ),
        "total_label": ParagraphStyle(
            "total_label",
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=BRAND_DARK,
            alignment=TA_RIGHT,
        ),
        "total_value": ParagraphStyle(
            "total_value",
            fontName="Helvetica-Bold",
            fontSize=11,
            textColor=BRAND_TEAL,
            alignment=TA_RIGHT,
        ),
        "footer": ParagraphStyle(
            "footer",
            fontName="Helvetica",
            fontSize=7.5,
            textColor=BRAND_GRAY,
            alignment=TA_CENTER,
        ),
    }


def generate_invoice(shipment_id, hide_financials=False) -> bytes:
    """
    Generate a professional A4 invoice PDF for the given shipment.

    Args:
        shipment_id: The Shipment DB primary key (int) or shipment_id string.
        hide_financials: If True, sensitive monetary fields (rate, amount, deductions) are omitted.

    Returns:
        Raw PDF bytes ready to stream in an HTTP response.

    Raises:
        Shipment.DoesNotExist: If shipment not found.
    """
    from shipments.models import Shipment  # local import to avoid circular

    # Support both PK and shipment_id string lookup
    try:
        if isinstance(shipment_id, int):
            s = Shipment.objects.select_related("route").get(pk=shipment_id)
        else:
            s = Shipment.objects.select_related("route").get(shipment_id=shipment_id)
    except Shipment.DoesNotExist:
        raise

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=10 * mm,
        bottomMargin=15 * mm,
    )

    S = _styles()
    W = A4[0] - 30 * mm   # usable width
    story = []

    # ── HEADER BANNER ─────────────────────────────────────────────────────────
    header_data = [[
        Paragraph("CJ DARCL LOGISTICS", S["company"]),
        Paragraph("INVOICE", S["invoice_label"]),
    ]]
    header_table = Table(header_data, colWidths=[W * 0.6, W * 0.4])
    header_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), BRAND_DARK),
        ("ROWBACKGROUNDS",(0, 0), (-1, -1), [BRAND_DARK]),
        ("TOPPADDING",    (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (0, -1), 14),
        ("RIGHTPADDING",  (-1, 0), (-1, -1), 14),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(header_table)

    # Sub-header: branch info + invoice number
    sub_data = [[
        Paragraph("Jamshedpur Branch | NH-33, Adityapur Industrial Area, Jharkhand 831013", S["tagline"]),
        Paragraph(f"Invoice # {s.shipment_id} | {date.today().strftime('%d %b %Y')}", S["invoice_sub"]),
    ]]
    sub_table = Table(sub_data, colWidths=[W * 0.6, W * 0.4])
    sub_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), BRAND_TEAL),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (0, -1), 14),
        ("RIGHTPADDING",  (-1, 0), (-1, -1), 14),
    ]))
    story.append(sub_table)
    story.append(Spacer(1, 6 * mm))

    # ── SHIPMENT + CUSTOMER INFO ──────────────────────────────────────────────
    def _lv(label, value):
        """Label–Value pair as two Paragraphs."""
        return [Paragraph(label, S["label"]), Paragraph(str(value or "—"), S["value"])]

    dispatch_str = s.dispatch_date.strftime("%d %b %Y") if s.dispatch_date else "—"
    delivery_str = s.delivery_date.strftime("%d %b %Y") if s.delivery_date else "Pending"

    info_data = [
        [Paragraph("SHIPMENT DETAILS", S["section_head"]), "", Paragraph("BILLING PARTY", S["section_head"]), ""],
        _lv("Shipment ID (C/N No.)", s.shipment_id) + _lv("Customer / Consignee", s.consignee_name or s.customer_name),
        _lv("Origin", s.route.origin) + _lv("Consignor", s.consignor_name),
        _lv("Destination", s.route.destination) + _lv("Booking Region", s.booking_region),
        _lv("Dispatch Date", dispatch_str) + _lv("Contract ID", s.contract_id),
        _lv("Delivery Date", delivery_str) + _lv("Billing Status", s.billing_status or "Pending"),
    ]
    col_w = W / 4
    info_table = Table(info_data, colWidths=[col_w * 0.55, col_w * 1.45, col_w * 0.55, col_w * 1.45])
    info_table.setStyle(TableStyle([
        ("SPAN",         (0, 0), (1, 0)),
        ("SPAN",         (2, 0), (3, 0)),
        ("BACKGROUND",   (0, 0), (1, 0), BRAND_LIGHT),
        ("BACKGROUND",   (2, 0), (3, 0), BRAND_LIGHT),
        ("TOPPADDING",   (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 3),
        ("LEFTPADDING",  (0, 0), (-1, -1), 6),
        ("LINEBELOW",    (0, -1), (-1, -1), 0.5, BRAND_LINE),
        ("VALIGN",       (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 5 * mm))

    # ── VEHICLE / DRIVER INFO ─────────────────────────────────────────────────
    story.append(Paragraph("TRANSPORT DETAILS", S["section_head"]))
    story.append(Spacer(1, 1 * mm))
    transport_data = [
        ["Vehicle No.", "Vehicle Type", "Transporter", "Material Type", "Total Distance"],
        [
            s.vehicle_no or "—",
            s.vehicle_type or "—",
            s.transporter_name or "—",
            s.material_type or "—",
            f"{s.total_distance:.0f} km" if s.total_distance else "—",
        ],
    ]
    transport_table = Table(transport_data, colWidths=[W / 5] * 5)
    transport_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), BRAND_DARK),
        ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 8),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("FONTSIZE",      (0, 1), (-1, -1), 8.5),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, BRAND_LIGHT]),
        ("GRID",          (0, 0), (-1, -1), 0.4, BRAND_LINE),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(transport_table)
    story.append(Spacer(1, 5 * mm))

    # ── CARGO + FREIGHT TABLE ─────────────────────────────────────────────────
    if hide_financials:
        # Non-financial version: only cargo description and weights
        story.append(Paragraph("CARGO / CONSIGNMENT DETAILS", S["section_head"]))
        story.append(Spacer(1, 1 * mm))
        cargo_data = [
            ["#", "Description", "Gross Wt (MT)", "Net Wt (MT)", "Chargeable Wt (MT)"],
            [
                "1",
                s.material_type or "General Cargo",
                f"{float(s.gross_weight):.3f}",
                f"{float(s.net_weight):.3f}",
                f"{float(s.charge_weight):.3f}",
            ],
        ]
        col_widths = [W * 0.05, W * 0.45, W * 0.16, W * 0.16, W * 0.18]
    else:
        # Full financial version
        story.append(Paragraph("CARGO & FREIGHT CHARGES", S["section_head"]))
        story.append(Spacer(1, 1 * mm))
        cargo_data = [
            ["#", "Description", "Gross Wt (MT)", "Net Wt (MT)", "Chargeable Wt (MT)", "Rate / MT (₹)", "Amount (₹)"],
            [
                "1",
                s.material_type or "General Cargo",
                f"{float(s.gross_weight):.3f}",
                f"{float(s.net_weight):.3f}",
                f"{float(s.charge_weight):.3f}",
                f"₹{float(s.rate_per_mt):,.2f}",
                f"₹{float(s.total_amount):,.2f}",
            ],
        ]
        col_widths = [W * 0.05, W * 0.25, W * 0.12, W * 0.12, W * 0.14, W * 0.14, W * 0.18]

    cargo_table = Table(cargo_data, colWidths=col_widths)
    cargo_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), BRAND_TEAL),
        ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 8),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("ALIGN",         (1, 0), (1, -1), "LEFT"),
        ("FONTSIZE",      (0, 1), (-1, -1), 8.5),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, BRAND_LIGHT]),
        ("GRID",          (0, 0), (-1, -1), 0.4, BRAND_LINE),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (1, 0), (1, -1), 6),
    ]))
    story.append(cargo_table)
    story.append(Spacer(1, 4 * mm))

    # ── FINANCIAL SUMMARY ─────────────────────────────────────────────────────
    if not hide_financials:
        finance_data = [
            ["Gross Freight Amount",        f"₹{float(s.total_amount):,.2f}"],
            ["Freight Deduction",           f"(₹{float(s.freight_deduction):,.2f})"],
            ["Shortage Penalty",            f"(₹{float(s.penalty):,.2f})"],
            ["GST @ 18% (indicative)",      f"₹{float(s.total_amount) * 0.18:,.2f}"],
        ]
        net_receivable = float(s.amount_receivable)

        finance_table = Table(
            finance_data,
            colWidths=[W * 0.75, W * 0.25],
        )
        finance_table.setStyle(TableStyle([
            ("ALIGN",         (0, 0), (-1, -1), "RIGHT"),
            ("FONTNAME",      (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE",      (0, 0), (-1, -1), 8.5),
            ("TEXTCOLOR",     (0, 0), (-1, -1), BRAND_DARK),
            ("TOPPADDING",    (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LINEABOVE",     (0, 0), (-1, 0), 0.5, BRAND_LINE),
        ]))
        story.append(finance_table)

        # Total row
        total_data = [["NET AMOUNT RECEIVABLE", f"₹{net_receivable:,.2f}"]]
        total_table = Table(total_data, colWidths=[W * 0.75, W * 0.25])
        total_table.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), BRAND_DARK),
            ("TEXTCOLOR",     (0, 0), (-1, -1), WHITE),
            ("FONTNAME",      (0, 0), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, -1), 10),
            ("ALIGN",         (0, 0), (-1, -1), "RIGHT"),
            ("TOPPADDING",    (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING",  (-1, 0), (-1, -1), 8),
            ("LEFTPADDING",   (0, 0), (0, -1), 8),
        ]))
        story.append(total_table)
        story.append(Spacer(1, 8 * mm))

    # ── POD STATUS + TRANSIT ──────────────────────────────────────────────────
    status_data = [
        ["POD Status", "Delivery Status", "Transit SLA (days)", "Actual Transit (days)", "Delay"],
        [
            "Delivered ✓" if s.pod_status == "Uploaded" else (s.pod_status or "Pending"),
            "Delivered ✓" if s.pod_status == "Uploaded" else ("On Time ✓" if s.is_on_time else f"Delayed {s.delay_days}d ✗"),
            str(s.transit_permissible),
            str(s.transit_taken),
            f"{s.delay_days}d" if s.delay_days > 0 else "—",
        ],
    ]
    status_table = Table(status_data, colWidths=[W / 5] * 5)
    delay_color = colors.HexColor("#EF4444") if not s.is_on_time else colors.HexColor("#10B981")
    status_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), BRAND_GRAY),
        ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 7.5),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("FONTSIZE",      (0, 1), (-1, -1), 8.5),
        ("TEXTCOLOR",     (1, 1), (1, 1), delay_color),
        ("FONTNAME",      (1, 1), (1, 1), "Helvetica-Bold"),
        ("GRID",          (0, 0), (-1, -1), 0.4, BRAND_LINE),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(status_table)
    story.append(Spacer(1, 10 * mm))

    # ── SIGNATURE LINE ────────────────────────────────────────────────────────
    sig_data = [
        ["Authorised Signatory", "", "Customer Acknowledgement"],
        ["\n\n\n" + "_" * 28, "", "_" * 28],
        ["Branch Manager, CJ Darcl Logistics", "", s.consignee_name or "Customer Name"],
        ["Jamshedpur Branch", "", "Date: _______________"],
    ]
    sig_table = Table(sig_data, colWidths=[W * 0.38, W * 0.24, W * 0.38])
    sig_table.setStyle(TableStyle([
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("TEXTCOLOR",     (0, 0), (-1, 0), BRAND_GRAY),
        ("ALIGN",         (0, 0), (0, -1), "LEFT"),
        ("ALIGN",         (2, 0), (2, -1), "RIGHT"),
        ("TOPPADDING",    (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(sig_table)
    story.append(HRFlowable(width=W, thickness=0.5, color=BRAND_LINE))
    story.append(Spacer(1, 3 * mm))

    # ── FOOTER ────────────────────────────────────────────────────────────────
    footer_text = (
        "CJ Darcl Logistics Ltd. | Jamshedpur Branch | NH-33, Adityapur Industrial Area, Jharkhand 831013 | "
        "This is a computer-generated invoice. | GST No. (add your GSTIN here)"
    )
    story.append(Paragraph(footer_text, S["footer"]))

    doc.build(story)
    return buffer.getvalue()
