"""Yillik PDF — Django observations/yearbook.py async portasi.

reportlab sinxron → executor'da chaqiramiz. Observation kelishi async query'dan,
keyin sync render qilamiz.
"""
from __future__ import annotations

import asyncio
import io
from collections import Counter
from datetime import datetime

import httpx
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

ACCENT = colors.HexColor("#D4FA2C")
INK = colors.HexColor("#0C1220")
INK2 = colors.HexColor("#444E63")
INK3 = colors.HexColor("#9CA3AF")
LINE = colors.HexColor("#E5E7EB")


def _styles():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle(name="H1Big", parent=s["Heading1"], fontSize=42, leading=46, textColor=INK))
    s.add(ParagraphStyle(name="H2", parent=s["Heading2"], fontSize=22, leading=26, textColor=INK))
    s.add(ParagraphStyle(name="H3", parent=s["Heading3"], fontSize=15, leading=18, textColor=INK))
    s.add(ParagraphStyle(name="LabelLime", parent=s["BodyText"], fontSize=9, leading=12,
                          textColor=colors.HexColor("#7BAF00"), spaceAfter=4))
    s.add(ParagraphStyle(name="Latin", parent=s["BodyText"], fontSize=11, leading=14,
                          textColor=INK3, fontName="Helvetica-Oblique"))
    s.add(ParagraphStyle(name="Body", parent=s["BodyText"], fontSize=10, leading=14, textColor=INK2))
    s.add(ParagraphStyle(name="Meta", parent=s["BodyText"], fontSize=9, leading=12, textColor=INK3))
    return s


def _draw_cover(c: canvas.Canvas, user_full_name: str, year: int, total: int):
    w, h = A4
    c.setFillColor(INK)
    c.rect(0, 0, w, h, fill=1, stroke=0)
    c.setFillColor(ACCENT)
    c.rect(0, h - 230, w, 90, fill=1, stroke=0)
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 36)
    c.drawString(40, h - 190, "TABIAT")
    c.drawString(40, h - 222, "KUNDALIGIM")
    c.setFillColor(ACCENT)
    c.setFont("Helvetica-Bold", 110)
    c.drawString(40, 280, str(year))
    c.setFillColor(colors.white)
    c.setFont("Helvetica", 14)
    c.drawString(40, 240, user_full_name or "BioScan foydalanuvchisi")
    c.setFont("Helvetica", 11)
    c.setFillColor(colors.HexColor("#94A3B8"))
    c.drawString(40, 220, f"{total} ta tur aniqlandi")
    c.setFillColor(ACCENT)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(40, 50, "BioScan")
    c.setFillColor(colors.HexColor("#94A3B8"))
    c.setFont("Helvetica", 9)
    c.drawString(40, 36, "Tabiat AI yordamchisi · bioscan.uz")


def _safe_fetch_image(url: str, max_kb: int = 800) -> bytes | None:
    if not url:
        return None
    try:
        with httpx.Client(timeout=8.0) as c:
            r = c.get(url)
            r.raise_for_status()
            data = r.content
        if len(data) > max_kb * 1024 * 4:
            return None
        return data
    except Exception:
        return None


def _render_pdf(user_full_name: str, year: int, observations: list[dict]) -> bytes:
    """observations = list[{species_name, species_latin, species_category, species_redbook,
                            species_picture, ai_confidence, note, latitude, longitude,
                            place_name, created_at}]."""
    obs = observations
    total = len(obs)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
        title=f"Tabiat Kundaligim {year}",
        author=user_full_name or "BioScan",
    )
    styles = _styles()
    story = [Spacer(1, 1), PageBreak()]

    story.append(Paragraph("YIL STATISTIKASI", styles["LabelLime"]))
    story.append(Paragraph(f"{year} yil yakunlari", styles["H2"]))
    story.append(Spacer(1, 16))

    by_cat: Counter = Counter(o.get("species_category") or "—" for o in obs)
    redbook = sum(1 for o in obs if o.get("species_redbook"))
    species_ids = {o.get("species_id") for o in obs if o.get("species_id")}

    stats = [
        ["Jami skanlar", str(total)],
        ["Aniqlangan turlar", str(len(species_ids))],
        ["Qizil kitob turlari", str(redbook)],
        ["GPS koordinatasi bilan", str(sum(1 for o in obs if o.get("latitude") and o.get("longitude")))],
    ]
    t = Table(stats, colWidths=[80 * mm, 40 * mm])
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

    # Categories
    if by_cat:
        story.append(Paragraph("KATEGORIYALAR", styles["LabelLime"]))
        cat_uz = {
            "giyoh": "Giyoh", "daraxt": "Daraxt", "gul": "Gul",
            "jonivor": "Jonivor", "qush": "Qush",
            "hasharot": "Hasharot", "qoziqorin": "Qo'ziqorin",
            "—": "Aniqlanmagan",
        }
        max_n = max(by_cat.values())
        rows = [
            [cat_uz.get(c, c), str(n), "█" * min(20, max(1, int(n / max_n * 20)))]
            for c, n in sorted(by_cat.items(), key=lambda x: -x[1])
        ]
        t2 = Table(rows, colWidths=[60 * mm, 20 * mm, 80 * mm])
        t2.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("TEXTCOLOR", (0, 0), (0, -1), INK2),
            ("TEXTCOLOR", (2, 0), (2, -1), ACCENT),
            ("FONTNAME", (2, 0), (2, -1), "Courier"),
        ]))
        story.append(t2)

    # Observation pages
    for o in obs:
        story.append(PageBreak())
        story.append(Paragraph((o.get("species_category") or "TUR").upper(), styles["LabelLime"]))
        story.append(Paragraph(o.get("species_name") or "Aniqlanmagan", styles["H2"]))
        latin = o.get("species_latin") or ""
        if latin:
            story.append(Paragraph(latin, styles["Latin"]))
        # Photo
        img_url = o.get("species_picture") or o.get("photo")
        img_bytes = _safe_fetch_image(img_url) if img_url and img_url.startswith("http") else None
        if img_bytes:
            try:
                story.append(Spacer(1, 8))
                story.append(Image(io.BytesIO(img_bytes), width=150 * mm, height=100 * mm, kind="proportional"))
            except Exception:
                pass
        story.append(Spacer(1, 10))
        meta = []
        if o.get("created_at"):
            try:
                dt = datetime.fromisoformat(str(o["created_at"]).replace("Z", "+00:00"))
                meta.append(dt.strftime("%d.%m.%Y · %H:%M"))
            except Exception:
                pass
        if o.get("latitude") and o.get("longitude"):
            meta.append(f"GPS: {o['latitude']:.4f}, {o['longitude']:.4f}")
        if meta:
            story.append(Paragraph(" · ".join(meta), styles["Meta"]))
        if o.get("note"):
            story.append(Spacer(1, 6))
            story.append(Paragraph(o["note"][:500], styles["Body"]))

    def first_page(c, _doc):
        _draw_cover(c, user_full_name, year, total)

    doc.build(story, onFirstPage=first_page)
    return buf.getvalue()


async def render_yearbook(user_full_name: str, year: int,
                           observations: list[dict]) -> bytes:
    """Async wrapper — executor'da render qiladi."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, _render_pdf, user_full_name, year, observations
    )
