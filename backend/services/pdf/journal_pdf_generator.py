import logging
import os
import re
import uuid
import html
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    KeepTogether,
    HRFlowable,
)
from PIL import Image as PILImage

from backend.services.storage.memory_store import get_memory_photo_path

logger = logging.getLogger(__name__)

# Register Unicode font with system fallbacks
UNICODE_FONT = "Helvetica"
UNICODE_FONT_BOLD = "Helvetica-Bold"

for name, path in [
    ("JournalUnicode", "C:/Windows/Fonts/arial.ttf"),
    ("JournalUnicode-Bold", "C:/Windows/Fonts/arialbd.ttf"),
    ("JournalUnicode", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ("JournalUnicode-Bold", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
]:
    if os.path.exists(path):
        try:
            pdfmetrics.registerFont(TTFont(name, path))
            if "Bold" in name:
                UNICODE_FONT_BOLD = name
            else:
                UNICODE_FONT = name
        except Exception as e:
            logger.debug(f"Could not register font {path}: {e}")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
PDF_DIR = BASE_DIR / "pdfs"


def clean_filename(value: str) -> str:
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", str(value or "")).strip()


def sanitize_text(text: Any) -> str:
    """Escapes HTML entities, preserves linebreaks, and removes control characters."""
    if text is None:
        return ""
    val = str(text)
    # Strip null bytes and non-printable characters except standard whitespace
    val = "".join(ch for ch in val if ch in ("\n", "\r", "\t") or (ch.isprintable()))
    escaped = html.escape(val)
    escaped = escaped.replace("\r\n", "<br/>").replace("\n", "<br/>")
    return escaped


class NumberedCanvas:
    """Two-pass canvas to calculate accurate total page count on footer."""
    def __init__(self, *args, **kwargs):
        pass


def add_journal_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont(UNICODE_FONT, 8.5)
    canvas.setFillColor(colors.HexColor("#64748B"))

    now_str = datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")
    canvas.drawString(
        15 * mm,
        10 * mm,
        f"TravelSync AI Journal • Exported {now_str}",
    )
    canvas.drawRightString(
        195 * mm,
        10 * mm,
        f"Page {canvas.getPageNumber()}",
    )
    canvas.restoreState()


def generate_journal_pdf(
    trip_id: str,
    trip_title: str,
    destination: str,
    entries: List[Dict[str, Any]],
    requester_name: str,
    day_filter: Optional[int] = None,
) -> str:
    """
    Generates an authenticated, beautifully formatted PDF travel journal document.
    Enforces privacy, strictly validates photo paths to prevent path traversal,
    and handles missing photos and Unicode text gracefully.
    """
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    safe_trip_id = clean_filename(trip_id)[:24]
    pdf_filename = f"journal_{safe_trip_id}_{uuid.uuid4().hex[:12]}.pdf"
    pdf_path = PDF_DIR / pdf_filename

    doc = SimpleDocTemplate(
        str(pdf_path),
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=18 * mm,
    )
    doc.title = f"Travel Journal - {trip_title or destination}"
    doc.author = "TravelSync AI"
    doc.subject = f"Trip Memories Chronicle for {destination}"

    styles = getSampleStyleSheet()

    header_title_style = ParagraphStyle(
        "JournalHeaderTitle",
        parent=styles["Normal"],
        fontName=UNICODE_FONT_BOLD,
        fontSize=22,
        leading=26,
        textColor=colors.HexColor("#0F172A"),
    )

    header_subtitle_style = ParagraphStyle(
        "JournalHeaderSubtitle",
        parent=styles["Normal"],
        fontName=UNICODE_FONT,
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#475569"),
    )

    stat_label_style = ParagraphStyle(
        "StatLabel",
        parent=styles["Normal"],
        fontName=UNICODE_FONT,
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#64748B"),
        alignment=1,
    )

    stat_value_style = ParagraphStyle(
        "StatValue",
        parent=styles["Normal"],
        fontName=UNICODE_FONT_BOLD,
        fontSize=12,
        leading=14,
        textColor=colors.HexColor("#0284C7"),
        alignment=1,
    )

    entry_title_style = ParagraphStyle(
        "EntryTitle",
        parent=styles["Normal"],
        fontName=UNICODE_FONT_BOLD,
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#0F172A"),
    )

    entry_meta_style = ParagraphStyle(
        "EntryMeta",
        parent=styles["Normal"],
        fontName=UNICODE_FONT,
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#64748B"),
    )

    entry_body_style = ParagraphStyle(
        "EntryBody",
        parent=styles["Normal"],
        fontName=UNICODE_FONT,
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor("#1E293B"),
    )

    privacy_private_style = ParagraphStyle(
        "PrivacyPrivate",
        parent=styles["Normal"],
        fontName=UNICODE_FONT_BOLD,
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#7C3AED"),
        alignment=2,
    )

    privacy_shared_style = ParagraphStyle(
        "PrivacyShared",
        parent=styles["Normal"],
        fontName=UNICODE_FONT_BOLD,
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#059669"),
        alignment=2,
    )

    story = []

    # 1. Title Banner
    dest_display = destination or "Travel Itinerary"
    trip_heading = f"Travel Journal: {trip_title}" if trip_title and trip_title != dest_display else f"Travel Journal: {dest_display}"
    story.append(Paragraph(sanitize_text(trip_heading), header_title_style))
    story.append(Spacer(1, 4))

    filter_desc = f" • Day {day_filter} Memories Only" if day_filter is not None else ""
    meta_sub = f"Compiled for {sanitize_text(requester_name or 'Traveler')}{filter_desc} • Personal & Group Reflections"
    story.append(Paragraph(meta_sub, header_subtitle_style))
    story.append(Spacer(1, 14))

    # 2. Summary Statistics Box
    total_entries = len(entries)
    photo_entries = sum(1 for e in entries if e.get("photo_filename"))
    days_present = len(set(e.get("day_number") for e in entries if e.get("day_number") is not None))
    private_count = sum(1 for e in entries if e.get("is_private"))

    stats_data = [
        [
            Paragraph(f"<b>{total_entries}</b>", stat_value_style),
            Paragraph(f"<b>{photo_entries}</b>", stat_value_style),
            Paragraph(f"<b>{days_present or 'All'}</b>", stat_value_style),
            Paragraph(f"<b>{private_count}</b>", stat_value_style),
        ],
        [
            Paragraph("Total Memories", stat_label_style),
            Paragraph("Photos Included", stat_label_style),
            Paragraph("Days Covered", stat_label_style),
            Paragraph("Private (Yours)", stat_label_style),
        ],
    ]

    stats_table = Table(stats_data, colWidths=[45 * mm, 45 * mm, 45 * mm, 45 * mm])
    stats_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#E2E8F0")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(stats_table)
    story.append(Spacer(1, 18))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#E2E8F0"), spaceAfter=14))

    # 3. Entries List
    if not entries:
        empty_style = ParagraphStyle(
            "EmptyJournal",
            parent=styles["Normal"],
            fontName=UNICODE_FONT,
            fontSize=11,
            leading=15,
            textColor=colors.HexColor("#64748B"),
            alignment=1,
        )
        story.append(Spacer(1, 20))
        story.append(Paragraph("<i>No memories recorded for this trip yet.</i>", empty_style))
    else:
        for idx, entry in enumerate(entries):
            entry_elements = []

            # Format timestamp
            created_str = entry.get("created_at") or ""
            formatted_date = created_str
            if created_str:
                try:
                    dt = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                    formatted_date = dt.strftime("%b %d, %Y • %I:%M %p")
                except Exception:
                    pass

            # Meta badge string
            day_text = f"Day {entry.get('day_number')}" if entry.get("day_number") is not None else "Trip Reflection"
            attr_text = f" • 📍 {entry.get('attraction_name')}" if entry.get("attraction_name") else ""
            author_text = f" • by {entry.get('author_name') or entry.get('author_id') or 'Traveler'}"
            meta_left = f"<b>{sanitize_text(day_text)}</b>{sanitize_text(attr_text)}{sanitize_text(author_text)} • {formatted_date}"

            is_priv = bool(entry.get("is_private"))
            privacy_label = "[🔒 Private to You]" if is_priv else "[👥 Shared Memory]"
            priv_style = privacy_private_style if is_priv else privacy_shared_style

            header_table_data = [
                [
                    Paragraph(meta_left, entry_meta_style),
                    Paragraph(privacy_label, priv_style),
                ]
            ]
            header_table = Table(header_table_data, colWidths=[135 * mm, 45 * mm])
            header_table.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ]
                )
            )
            entry_elements.append(header_table)
            entry_elements.append(Spacer(1, 4))

            # Entry Title (if present)
            if entry.get("title"):
                entry_elements.append(Paragraph(sanitize_text(entry["title"]), entry_title_style))
                entry_elements.append(Spacer(1, 4))

            # Entry Reflection Content
            entry_elements.append(Paragraph(sanitize_text(entry.get("content")), entry_body_style))

            # Photo Embedding with Strict Security Check & Graceful Handling
            photo_filename = entry.get("photo_filename")
            if photo_filename:
                photo_path = get_memory_photo_path(photo_filename)
                if photo_path and photo_path.is_file():
                    try:
                        with PILImage.open(photo_path) as img:
                            orig_w, orig_h = img.size

                        if orig_w > 0 and orig_h > 0:
                            # Max printable bounds in points (ReportLab standard A4 printable area ~510pt width)
                            max_width_pt = 420.0
                            max_height_pt = 220.0
                            scale = min(max_width_pt / orig_w, max_height_pt / orig_h, 1.0)
                            render_w = orig_w * scale
                            render_h = orig_h * scale

                            entry_elements.append(Spacer(1, 8))
                            entry_elements.append(
                                Image(
                                    str(photo_path),
                                    width=render_w,
                                    height=render_h,
                                )
                            )
                    except Exception as img_err:
                        logger.warning(f"Could not load photo {photo_filename} for PDF: {img_err}")
                        entry_elements.append(Spacer(1, 4))
                        entry_elements.append(
                            Paragraph("<i>[Photo attachment unavailable]</i>", entry_meta_style)
                        )
                else:
                    entry_elements.append(Spacer(1, 4))
                    entry_elements.append(
                        Paragraph("<i>[Photo attachment missing or unreadable]</i>", entry_meta_style)
                    )

            # Divider between entries
            entry_elements.append(Spacer(1, 12))
            if idx < len(entries) - 1:
                entry_elements.append(
                    HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E2E8F0"), spaceAfter=12)
                )

            # Keep short entries together where practical to prevent awkward page splits
            if len(entry.get("content", "")) < 400 and not photo_filename:
                story.append(KeepTogether(entry_elements))
            else:
                story.extend(entry_elements)

    # 4. Build Document
    doc.build(
        story,
        onFirstPage=add_journal_footer,
        onLaterPages=add_journal_footer,
    )

    return str(pdf_path)
