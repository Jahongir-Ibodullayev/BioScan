"""Yillik PDF kitob — foydalanuvchining barcha skanlarini terib chiqaradi.

Generates a beautiful "Tabiat Kundaligim" PDF with cover, stats, and
chronological pages of every observation (photo / species / date / GPS).
"""
from __future__ import annotations

import io
from collections import Counter
from datetime import datetime
from typing import Iterable

import requests
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# Brand
ACCENT = colors.HexColor("#D4FA2C")
INK = colors.HexColor("#0C1220")
INK2 = colors.HexColor("#444E63")
INK3 = colors.HexColor("#9CA3AF")
DANGER = colors.HexColor("#EF4444")
LINE = colors.HexColor("#E5E7EB")


def _styles():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle(name="H1Big",
                          parent=s["Heading1"],
                          fontSize=42, leading=46, textColor=INK,
                          alignment=0))
    s.add(ParagraphStyle(name="H2",
                          parent=s["Heading2"],
                          fontSize=22, leading=26, textColor=INK))
    s.add(ParagraphStyle(name="H3",
                          parent=s["Heading3"],
                          fontSize=15, leading=18, textColor=INK))
    s.add(ParagraphStyle(name="LabelLime",
                          parent=s["BodyText"],
                          fontSize=9, leading=12,
                          textColor=colors.HexColor("#7BAF00"),
                          spaceAfter=4))
    s.add(ParagraphStyle(name="Latin",
                          parent=s["BodyText"],
                          fontSize=11, leading=14,
                          textColor=INK3,
                          fontName="Helvetica-Oblique"))
    s.add(ParagraphStyle(name="Body",
                          parent=s["BodyText"],
                          fontSize=10, leading=14,
                          textColor=INK2))
    s.add(ParagraphStyle(name="Meta",
                          parent=s["BodyText"],
                          fontSize=9, leading=12,
                          textColor=INK3))
    return s


def _draw_cover(c: canvas.Canvas, user, year: int, total: int):
    w, h = A4
    # Bg
    c.setFillColor(INK)
    c.rect(0, 0, w, h, fill=1, stroke=0)
    # Lime stripe
    c.setFillColor(ACCENT)
    c.rect(0, h - 230, w, 90, fill=1, stroke=0)
    # Title
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 36)
    c.drawString(40, h - 190, "TABIAT")
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 36)
    c.drawString(40, h - 222, "KUNDALIGIM")
    # Year
    c.setFillColor(ACCENT)
    c.setFont("Helvetica-Bold", 110)
    c.drawString(40, 280, str(year))
    # Subtitle
    c.setFillColor(colors.white)
    c.setFont("Helvetica", 14)
    full_name = (getattr(user, "full_name", "") or "").strip() or \
        getattr(user, "phone", "") or ""
    c.drawString(40, 240, full_name)
    c.setFont("Helvetica", 11)
    c.setFillColor(colors.HexColor("#94A3B8"))
    c.drawString(40, 220, f"{total} ta tur aniqlandi")
    # Footer
    c.setFillColor(ACCENT)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(40, 50, "BioScan")
    c.setFillColor(colors.HexColor("#94A3B8"))
    c.setFont("Helvetica", 9)
    c.drawString(40, 36, "Tabiat AI yordamchisi · togai.uz")


def _safe_image(url: str, max_kb: int = 800) -> bytes | None:
    if not url:
        return None
    try:
        r = requests.get(url, timeout=8, stream=True)
        r.raise_for_status()
        data = r.content
        if len(data) > max_kb * 1024 * 4:  # > 3.2 MB skip
            return None
        return data
    except Exception:
        return None


def _format_date(s: str) -> str:
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt.strftime("%d.%m.%Y · %H:%M")
    except Exception:
        return s or ""


def render_yearbook(user, year: int, observations) -> bytes:
    """Build PDF as bytes from queryset of observations."""
    obs = list(observations)
    total = len(obs)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
        title=f"Tabiat Kundaligim {year}",
        author=getattr(user, "full_name", "BioScan"),
    )
    styles = _styles()
    story = []

    # ---- Cover (drawn directly on first page) ----
    # We'll add a placeholder paragraph then override drawPage
    story.append(Spacer(1, 1))

    def cover_page(c, _doc):
        _draw_cover(c, user, year, total)

    # ---- Stats page ----
    story.append(PageBreak())
    story.append(Paragraph("YIL STATISTIKASI", styles["LabelLime"]))
    story.append(Paragraph(f"{year} yil yakunlari", styles["H2"]))
    story.append(Spacer(1, 16))

    by_cat: Counter = Counter(
        (o.species.category if o.species else "—") for o in obs
    )
    redbook_count = sum(
        1 for o in obs if o.species and getattr(o.species, "red_book", False)
    )

    stats_data = [
        ["Jami skanlar", str(total)],
        ["Aniqlangan turlar", str(len({o.species_id for o in obs if o.species_id}))],
        ["Qizil kitob turlari", str(redbook_count)],
        ["GPS koordinatasi bilan",
         str(sum(1 for o in obs if o.latitude and o.longitude))],
    ]
    t = Table(stats_data, colWidths=[80 * mm, 40 * mm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("TEXTCOLOR", (0, 0), (0, -1), INK2),
        ("TEXTCOLOR", (1, 0), (1, -1), INK),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (1, 0), (1, -1), 18),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, LINE),
    ]))
    story.append(t)
    story.append(Spacer(1, 24))

    if by_cat:
        story.append(Paragraph("KATEGORIYALAR", styles["LabelLime"]))
        cat_uz = {
            "giyoh": "Giyoh", "daraxt": "Daraxt", "gul": "Gul",
            "jonivor": "Jonivor", "qush": "Qush",
            "hasharot": "Hasharot", "qoziqorin": "Qo'ziqorin",
            "ilon": "Sudralib yuruvchi", "—": "Aniqlanmagan",
        }
        rows = [
            [cat_uz.get(c, c), str(n),
             "█" * min(20, max(1, int(n / max(by_cat.values()) * 20)))]
            for c, n in sorted(by_cat.items(), key=lambda x: -x[1])
        ]
        ct = Table(rows, colWidths=[60 * mm, 20 * mm, 80 * mm])
        ct.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("TEXTCOLOR", (0, 0), (0, -1), INK),
            ("TEXTCOLOR", (1, 0), (1, -1), INK2),
            ("TEXTCOLOR", (2, 0), (2, -1), colors.HexColor("#7BAF00")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(ct)

    # ---- Observations pages ----
    story.append(PageBreak())
    story.append(Paragraph("KUZATUVLAR XRONOLOGIYASI", styles["LabelLime"]))
    story.append(Paragraph(f"{total} ta yozuv", styles["H2"]))
    story.append(Spacer(1, 12))

    for i, o in enumerate(obs, start=1):
        sp = o.species
        title_uz = sp.name if sp else "Aniqlanmagan tur"
        latin = sp.latin if sp else ""
        date = _format_date(str(o.created_at)) if o.created_at else ""
        place = o.place_name or ""
        gps = ""
        if o.latitude is not None and o.longitude is not None:
            gps = f"{o.latitude:.4f}, {o.longitude:.4f}"
        conf = f"AI {int((o.ai_confidence or 0) * 100)}%"
        red = "QIZIL KITOB" if (sp and getattr(sp, "red_book", False)) else None

        # photo
        photo_cell = ""
        try:
            url = None
            if o.photo and hasattr(o.photo, "url"):
                url = o.photo.url
                if url.startswith("/"):
                    # local file path → can also use storage path
                    pass
            if url and url.startswith("/"):
                # try direct file open
                with open(o.photo.path, "rb") as f:
                    img_bytes = f.read()
                photo_cell = Image(io.BytesIO(img_bytes),
                                   width=45 * mm, height=45 * mm)
            elif url:
                data = _safe_image(url)
                if data:
                    photo_cell = Image(io.BytesIO(data),
                                       width=45 * mm, height=45 * mm)
        except Exception:
            photo_cell = ""

        right = [
            Paragraph(f"<font color='#9CA3AF' size='8'>#{i:03d} · {date}</font>",
                      styles["Meta"]),
            Spacer(1, 4),
            Paragraph(f"<b>{title_uz}</b>", styles["H3"]),
        ]
        if latin:
            right.append(Paragraph(f"<i>{latin}</i>", styles["Latin"]))
        meta_bits = [conf]
        if place:
            meta_bits.append(place)
        if gps:
            meta_bits.append(gps)
        if red:
            meta_bits.append(f"<font color='#EF4444'><b>{red}</b></font>")
        right.append(Spacer(1, 4))
        right.append(Paragraph(" · ".join(meta_bits), styles["Meta"]))
        if sp and sp.summary:
            right.append(Spacer(1, 6))
            right.append(Paragraph(sp.summary[:200], styles["Body"]))

        row = [photo_cell, right]
        rt = Table([row], colWidths=[50 * mm, 110 * mm])
        rt.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
            ("LINEBELOW", (0, 0), (-1, 0), 0.5, LINE),
        ]))
        story.append(rt)
        story.append(Spacer(1, 8))

    if not obs:
        story.append(Paragraph(
            "Bu yilda hozircha skanlar yo'q. Skaner orqali tabiatni "
            "rasmga oling — keyingi yillik kitobingizda paydo bo'ladi.",
            styles["Body"],
        ))

    # ---- Build with cover overlay ----
    def first_page(c, d):
        cover_page(c, d)
        c.showPage()  # ensure cover is its own page

    def later_pages(c, _d):
        # Footer
        c.setFillColor(INK3)
        c.setFont("Helvetica", 8)
        c.drawRightString(A4[0] - 18 * mm, 12 * mm,
                           f"BioScan · Tabiat Kundaligim {year}")
        c.drawString(18 * mm, 12 * mm, str(_d.page))

    doc.build(story, onFirstPage=first_page, onLaterPages=later_pages)
    return buf.getvalue()
