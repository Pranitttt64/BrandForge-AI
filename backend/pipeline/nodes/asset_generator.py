"""
Asset Generator — BrandForge AI
Renders all brand assets from the fully validated pipeline state.

Outputs:
  flyer.pdf       — A4 brand flyer (WeasyPrint primary, ReportLab fallback)
  social_card.png — 1080x1080 social card (Pillow, layout-aware)
  email_*.html    — 3 email campaigns (template-based, 6 fields each)
  ad_copy.pdf     — Multi-format ad copy PDF
"""

from __future__ import annotations

import os
from html import escape
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from job_manager import job_manager


# ---------------------------------------------------------------------------
# State reading helpers
# ---------------------------------------------------------------------------

def _color_dict(raw) -> dict:
    if isinstance(raw, dict):
        return dict(raw)
    if hasattr(raw, "__dict__"):
        return dict(raw.__dict__)
    return {}


def get_colors(state: dict) -> dict:
    """Extract brand colors from state with safe fallbacks."""
    bc = (
        state.get("brand_colors")
        or state.get("brand_profile", {}).get("brand_colors")
        or state.get("brand_profile", {}).get("colors")
        or {}
    )
    if isinstance(bc, list) and bc:
        keys = ["primary", "secondary", "accent", "background", "text"]
        bc = {keys[i]: c for i, c in enumerate(bc) if i < len(keys)}
    else:
        bc = _color_dict(bc)

    return {
        "primary":    bc.get("primary")    or "#1a1a2e",
        "secondary":  bc.get("secondary")  or "#16213e",
        "accent":     bc.get("accent")     or "#e94560",
        "background": bc.get("background") or "#0f3460",
        "text":       bc.get("text")       or "#ffffff",
    }


def get_copy(state: dict) -> dict:
    """
    Extract copy_output from state. Handles both the old and new
    COPYWRITER_PROMPT schema. The new schema adds:
      hero_text, subheadlines, usp_titles, usp_descriptions
    """
    co = state.get("copy_output") or {}

    # Normalise flat / legacy formats to nested tone-keyed format
    if "headlines" not in co:
        co = {
            "headlines": {
                "bold":         co.get("bold_headlines", co.get("headlines", [])),
                "friendly":     co.get("friendly_headlines", []),
                "professional": co.get("professional_headlines", []),
            },
            "value_props": {
                "bold":         co.get("bold_value_props", co.get("value_props", [])),
                "friendly":     co.get("friendly_value_props", []),
                "professional": co.get("professional_value_props", []),
            },
            "call_to_actions": {
                "bold":         co.get("bold_ctas", co.get("call_to_actions", [])),
                "friendly":     co.get("friendly_ctas", []),
                "professional": co.get("professional_ctas", []),
            },
            "tagline":        co.get("tagline", ""),
            "elevator_pitch": co.get("elevator_pitch", ""),
            "hero_text":      co.get("hero_text", {}),
            "subheadlines":   co.get("subheadlines", {}),
            "usp_titles":     co.get("usp_titles", []),
            "usp_descriptions": co.get("usp_descriptions", []),
        }

    # Patch missing new fields
    if "hero_text" not in co:
        co["hero_text"] = {}
    if "subheadlines" not in co:
        co["subheadlines"] = {}
    if "usp_titles" not in co:
        co["usp_titles"] = []
    if "usp_descriptions" not in co:
        co["usp_descriptions"] = []
    if "call_to_actions" not in co and "ctas" in co:
        co["call_to_actions"] = {
            "bold": co["ctas"], "friendly": co["ctas"], "professional": co["ctas"]
        }
    if "value_props" not in co:
        co["value_props"] = {"bold": [], "friendly": [], "professional": []}

    return co


def get_layout(state: dict) -> dict:
    """Extract layout decisions with safe defaults."""
    lo = state.get("layout_output") or {}
    if not isinstance(lo, dict):
        lo = {}
    return {
        "template":           lo.get("template", "hero_left"),
        "content_density":    lo.get("content_density", "medium"),
        "layout_emphasis":    lo.get("layout_emphasis", "headline"),
        "color_application":  lo.get("color_application", "full-bleed"),
        "typography_mood":    lo.get("typography_mood", "geometric"),
        "social_card_layout": lo.get("social_card_layout", "left-aligned"),
        "email_header_style": lo.get("email_header_style", "bold-color"),
        "brand_category_tag": lo.get("brand_category_tag", "Other"),
    }


def get_emails(state: dict) -> list[dict]:
    """
    Return emails in a normalized list from the new keyed email format.
    email_output keys: email_welcome, email_promo, email_reengagement
    """
    eo = state.get("email_output") or {}
    brand_name = _brand_name(state)

    type_map = [
        ("email_welcome",       "welcome"),
        ("email_promo",         "promo"),
        ("email_reengagement",  "reengagement"),
    ]

    result: list[dict] = []
    for key, email_type in type_map:
        email = eo.get(key, {}) if isinstance(eo, dict) else {}
        if not isinstance(email, dict):
            email = {}
        result.append({
            "key":          key,
            "type":         email_type,
            "subject":      email.get("subject",      f"{brand_name} — {email_type}"),
            "preview_text": email.get("preview_text", f"See what {brand_name} has for you"),
            "headline":     email.get("headline",     f"Welcome to {brand_name}"),
            "body":         email.get("body",         f"{brand_name} is built for you."),
            "cta_text":     email.get("cta_text",     f"Explore {brand_name}"),
            "ps_line":      email.get("ps_line",      ""),
        })
    return result


def _brand_name(state: dict) -> str:
    return (
        state.get("brand_name")
        or (state.get("brand_profile") or {}).get("brand_name")
        or "Brand"
    )


def _usps(state: dict) -> list[str]:
    return (
        state.get("usps")
        or (state.get("brand_profile") or {}).get("usps")
        or []
    )


def _pick_tone(state: dict) -> str:
    """Map brand_tone to the best copy variant to use in assets."""
    brand_tone = (state.get("brand_tone") or "professional").lower()
    return {
        "bold":         "bold",
        "playful":      "bold",
        "friendly":     "friendly",
        "professional": "professional",
        "luxury":       "professional",
        "technical":    "professional",
    }.get(brand_tone, "professional")


# ---------------------------------------------------------------------------
# Copy safe-getters
# ---------------------------------------------------------------------------

def safe_get(mapping: dict, *keys: str, fallback: str = "") -> str:
    """Walk a nested dict by keys, return fallback if anything is missing."""
    val = mapping
    for k in keys:
        if not isinstance(val, dict):
            return fallback
        val = val.get(k)
        if val is None:
            return fallback
    if isinstance(val, list):
        return str(val[0]) if val else fallback
    return str(val) if val else fallback


def safe_get_list(mapping: dict, *keys: str, index: int = 0, fallback: str = "") -> str:
    val = mapping
    for k in keys:
        if not isinstance(val, dict):
            return fallback
        val = val.get(k)
    if isinstance(val, list):
        return str(val[index]) if index < len(val) else fallback
    return fallback


def safe_headline(copy: dict, tone: str = "bold", index: int = 0,
                  fallback: str = "Your Brand, Elevated") -> str:
    return safe_get_list(copy, "headlines", tone, index=index, fallback=fallback)


def safe_cta(copy: dict, tone: str = "bold", index: int = 0,
             fallback: str = "Get Started") -> str:
    return safe_get_list(copy, "call_to_actions", tone, index=index, fallback=fallback)


def safe_value_prop(copy: dict, tone: str = "bold", index: int = 0,
                    fallback: str = "Quality you can trust") -> str:
    return safe_get_list(copy, "value_props", tone, index=index, fallback=fallback)


def safe_hero_text(copy: dict, tone: str = "bold", fallback: str = "") -> str:
    ht = copy.get("hero_text", {})
    if isinstance(ht, dict):
        return ht.get(tone) or ht.get("professional") or fallback
    return str(ht) if ht else fallback


def safe_usp_title(copy: dict, state: dict, index: int = 0) -> str:
    titles = copy.get("usp_titles", [])
    if titles and index < len(titles) and titles[index]:
        return str(titles[index])
    # Fallback: truncate the raw USP to 5 words
    usps = _usps(state)
    if index < len(usps):
        words = str(usps[index]).split()
        return " ".join(words[:6])
    return f"Key Advantage {index + 1}"


def safe_usp_desc(copy: dict, state: dict, tone: str, index: int = 0) -> str:
    descs = copy.get("usp_descriptions", [])
    if descs and index < len(descs) and descs[index]:
        return str(descs[index])
    # Fallback: value prop or raw USP
    vp = safe_value_prop(copy, tone, index)
    if vp and vp != "Quality you can trust":
        return vp
    usps = _usps(state)
    return usps[index] if index < len(usps) else ""


# ---------------------------------------------------------------------------
# Token replacement
# ---------------------------------------------------------------------------

def _replace_tokens(template: str, replacements: dict[str, str]) -> str:
    html = template
    for token, value in replacements.items():
        html = html.replace(token, escape(str(value or "")))
    return html


# ---------------------------------------------------------------------------
# Image helpers
# ---------------------------------------------------------------------------

def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    value = (hex_color or "#000000").lstrip("#")
    if len(value) == 3:
        value = "".join(c * 2 for c in value)
    try:
        return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))
    except Exception:
        return (0, 0, 0)


def _hex_to_rgba(hex_color: str, alpha: int = 255) -> tuple[int, int, int, int]:
    return _hex_to_rgb(hex_color) + (alpha,)


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    base = Path(__file__).resolve().parents[2] / "assets" / "fonts"
    candidates = [
        base / ("Inter-Bold.ttf" if bold else "Inter-Regular.ttf"),
        base / "JetBrainsMono-Regular.ttf",
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
             else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for path in candidates:
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size)
            except Exception:
                pass
    return ImageFont.load_default()


def fit_text(draw: ImageDraw.Draw, text: str, font: ImageFont.FreeTypeFont,
             max_width: int, max_lines: int = 3) -> list[str]:
    """Wrap text to fit within max_width pixels. Caps at max_lines."""
    words = str(text or "").split()
    lines: list[str] = []
    current = ""
    for word in words:
        test = (current + " " + word).strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
        if len(lines) >= max_lines:
            break
    if current and len(lines) < max_lines:
        lines.append(current)
    # Truncate last line with ellipsis if overflow
    if len(lines) == max_lines and current and current not in lines:
        last = lines[-1]
        lines[-1] = last[: max(0, len(last) - 3)] + "..."
    return lines


def _draw_text_block(draw: ImageDraw.Draw, text: str, xy: tuple[int, int],
                     font: ImageFont.FreeTypeFont, fill: tuple,
                     max_width: int, line_height: int,
                     max_lines: int = 4) -> int:
    """Draw wrapped text, return the Y position after the last line."""
    x, y = xy
    for line in fit_text(draw, text, font, max_width, max_lines):
        draw.text((x, y), line, font=font, fill=fill)
        y += line_height
    return y


def _draw_centered_text(draw: ImageDraw.Draw, text: str, y: int,
                        font: ImageFont.FreeTypeFont, fill: tuple,
                        canvas_width: int, max_width: int,
                        line_height: int, max_lines: int = 2) -> int:
    """Draw centered text block, return Y after last line."""
    for line in fit_text(draw, text, font, max_width, max_lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        x = (canvas_width - (bbox[2] - bbox[0])) // 2
        draw.text((x, y), line, font=font, fill=fill)
        y += line_height
    return y


def _reportlab_color(hex_color: str):
    try:
        from reportlab.lib.colors import HexColor
        return HexColor(hex_color or "#000000")
    except Exception:
        from reportlab.lib.colors import black
        return black


# ---------------------------------------------------------------------------
# Flyer PDF
# ---------------------------------------------------------------------------

def render_flyer_pdf(state: dict, colors: dict, copy: dict,
                     layout: dict, output_dir: Path) -> str:
    """Render the brand flyer as a PDF using the HTML template."""
    tone = _pick_tone(state)
    template_name = layout.get("template", "hero_left")
    if template_name not in ("hero_left", "minimal_text"):
        template_name = "hero_left"

    base = Path(__file__).resolve().parents[2] / "assets" / "flyer_templates"
    template_path = base / f"{template_name}.html"
    if not template_path.exists():
        template_path = Path("assets/flyer_templates") / f"{template_name}.html"

    brand_name = _brand_name(state)
    usps = _usps(state)

    replacements = {
        # Colors
        "{{PRIMARY_COLOR}}":    colors["primary"],
        "{{SECONDARY_COLOR}}":  colors["secondary"],
        "{{ACCENT_COLOR}}":     colors["accent"],
        "{{BACKGROUND_COLOR}}": colors["background"],
        "{{TEXT_COLOR}}":       colors["text"],
        # Brand identity
        "{{BRAND_NAME}}":       brand_name,
        "{{BRAND_URL}}":        state.get("url", ""),
        "{{BRAND_CATEGORY}}":   state.get("brand_category", ""),
        # Copy — primary selections
        "{{HEADLINE}}":         safe_headline(copy, tone, 0,
                                    f"{brand_name} — {state.get('target_audience', 'Built for you')}"),
        "{{HERO_TEXT}}":        safe_hero_text(copy, tone,
                                    state.get("brand_promise", "")),
        "{{TAGLINE}}":          copy.get("tagline") or safe_headline(copy, "professional", 0, ""),
        "{{ELEVATOR_PITCH}}":   copy.get("elevator_pitch") or state.get("brand_promise", ""),
        "{{CTA_TEXT}}":         safe_cta(copy, tone, 0, f"Explore {brand_name}"),
        # USPs — from copywriter's usp_titles/usp_descriptions
        "{{USP_1_TITLE}}":      safe_usp_title(copy, state, 0),
        "{{USP_1_DESC}}":       safe_usp_desc(copy, state, tone, 0),
        "{{USP_2_TITLE}}":      safe_usp_title(copy, state, 1),
        "{{USP_2_DESC}}":       safe_usp_desc(copy, state, tone, 1),
        "{{USP_3_TITLE}}":      safe_usp_title(copy, state, 2),
        "{{USP_3_DESC}}":       safe_usp_desc(copy, state, tone, 2),
    }

    populated = _replace_tokens(template_path.read_text(encoding="utf-8"), replacements)
    output_path = output_dir / "flyer.pdf"

    _use_weasyprint = os.name != "nt" or os.getenv("BRANDFORGE_USE_WEASYPRINT") == "1"

    if _use_weasyprint:
        try:
            from weasyprint import HTML as WP
            WP(string=populated).write_pdf(str(output_path))
            print(f"[asset_generator] Flyer PDF written via WeasyPrint: {output_path}")
            return str(output_path)
        except Exception as e:
            print(f"[asset_generator] WeasyPrint flyer failed: {e} — falling back to ReportLab")

    _render_flyer_reportlab(state, colors, copy, output_path)
    return str(output_path)

def get_luminance(hex_color: str) -> float:
    r, g, b = _hex_to_rgb(hex_color)
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255.0

def pick_panel_color(colors: dict) -> tuple[str, str]:
    pri = colors.get("primary", "#191919")
    sec = colors.get("secondary", "#2a2a2a")
    if get_luminance(pri) < 0.5:
        return pri, "#ffffff"
    elif get_luminance(sec) < 0.5:
        return sec, "#ffffff"
    return "#191919", "#ffffff"

def pick_cta_color(colors: dict, panel_color: str) -> tuple[str, str]:
    acc = colors.get("accent", "#2383e2")
    if get_luminance(acc) > 0.5:
        return acc, "#000000"
    return acc, "#ffffff"

def _safe_rounded_rect(draw: ImageDraw.Draw, xy: list, radius: int, fill: tuple):
    try:
        draw.rounded_rectangle(xy, radius=radius, fill=fill)
    except AttributeError:
        draw.rectangle(xy, fill=fill)

def _render_flyer_reportlab(state: dict, colors: dict,
                             copy: dict, output_path: Path) -> None:
    """
    Production-quality A4 flyer using ReportLab.
    Two-column layout: dark left panel + white right panel.
    Text is properly wrapped and vertically distributed.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER
    from reportlab.platypus import Paragraph
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib import colors as rl_colors

    PAGE_W, PAGE_H = A4          # 595.27 x 841.89 pts
    LEFT_W  = PAGE_W * 0.40      # 40% left dark panel
    RIGHT_X = LEFT_W + 0         # right panel starts here
    RIGHT_W = PAGE_W - LEFT_W    # 60% right content panel

    brand_name  = _brand_name(state)
    usps        = _usps(state)
    headline    = safe_headline(copy, "bold", 0, f"{brand_name} — Built for What's Next")
    tagline     = copy.get("tagline") or state.get("brand_promise", "")
    cta         = safe_cta(copy, "bold", 0)
    url         = state.get("url", "")
    elevator    = copy.get("elevator_pitch") or state.get("brand_promise", "")

    panel_color, panel_text = pick_panel_color(colors)
    cta_color,   cta_text   = pick_cta_color(colors, panel_color)
    
    # We want a subtle accent color for the right panel grid
    acc_hex = colors.get("accent", "#2383e2")

    def rl_color(hex_c: str):
        try:
            return rl_colors.HexColor(hex_c)
        except Exception:
            return rl_colors.black

    c = rl_canvas.Canvas(str(output_path), pagesize=A4)

    # ── RIGHT PANEL BACKGROUND ───────────────────────────────────
    # Subtly patterned minimalist design to fill white space
    
    # Very light base fill
    c.setFillColor(rl_color("#fafafa"))
    c.rect(RIGHT_X, 0, RIGHT_W, PAGE_H, fill=1, stroke=0)
    
    # Minimalist Dot Grid in right panel
    c.setFillColor(rl_color(acc_hex))
    c.setFillAlpha(0.04)
    grid_spacing = 8 * mm
    for x in range(int(RIGHT_X) + int(6*mm), int(PAGE_W), int(grid_spacing)):
        for y in range(int(22*mm), int(PAGE_H), int(grid_spacing)):
            c.circle(x, y, 0.7, fill=1, stroke=0)
    
    # Large, subtle typographic watermark (first letter of brand)
    if brand_name:
        c.setFillColor(rl_color(acc_hex))
        c.setFillAlpha(0.02)
        c.setFont("Helvetica-Bold", 350)
        # Shift watermark so it's a structural background element
        c.drawString(RIGHT_X - 10*mm, 40*mm, brand_name[0].upper())
        c.setFillAlpha(1.0)

    # ── LEFT PANEL background ─────────────────────────────────────
    c.setFillColor(rl_color(panel_color))
    c.rect(0, 0, LEFT_W, PAGE_H, fill=1, stroke=0)

    # Accent bar — top of left panel
    c.setFillColor(rl_color(cta_color))
    c.rect(0, PAGE_H - 6, LEFT_W, 6, fill=1, stroke=0)

    # Decorative circle — bottom left of panel
    c.setFillColor(rl_color(panel_color))
    c.setStrokeColor(rl_color(cta_color))
    c.setLineWidth(1.5)
    c.circle(LEFT_W * 0.15, 60, 36, fill=0, stroke=1)

    # Brand name — top of left panel
    c.setFillColor(rl_color(panel_text))
    c.setFont("Helvetica-Bold", 11)
    c.setFillAlpha(0.55)
    brand_upper = brand_name.upper()
    # Letter-spaced brand name
    x_pos = 18 * mm
    for ch in brand_upper:
        c.drawString(x_pos, PAGE_H - 28 * mm, ch)
        x_pos += c.stringWidth(ch, "Helvetica-Bold", 11) + 2.5

    c.setFillAlpha(1.0)

    # Small accent rectangle under brand name
    c.setFillColor(rl_color(cta_color))
    c.rect(18 * mm, PAGE_H - 31 * mm, 32, 3, fill=1, stroke=0)

    # Headline — large, left panel center
    # Dynamically adjust font size for longer headlines
    head_len = len(headline)
    font_size = 32 if head_len < 30 else (28 if head_len < 50 else 24)
    line_h = font_size + 6
    
    c.setFillColor(rl_color(panel_text))
    headline_style = ParagraphStyle(
        "HeadlineLeft",
        fontName="Helvetica-Bold",
        fontSize=font_size,
        leading=line_h,
        textColor=rl_color(panel_text),
        alignment=TA_LEFT,
    )
    # Draw headline using Paragraph for proper wrapping
    p = Paragraph(headline.replace("&", "&amp;"), headline_style)
    avail_w = LEFT_W - 32 * mm  # slightly wider margins to reduce messy orphans
    w, h = p.wrapOn(c, avail_w, 200)
    p.drawOn(c, 16 * mm, PAGE_H - 80 * mm - h)

    # Tagline — below headline
    tagline_y = PAGE_H - 80 * mm - h - 16
    tag_style = ParagraphStyle(
        "TaglineLeft",
        fontName="Helvetica",
        fontSize=12,
        leading=17,
        textColor=rl_color(panel_text),
        alignment=TA_LEFT,
    )
    c.setFillAlpha(0.72)
    p2 = Paragraph((tagline[:120] if tagline else "").replace("&", "&amp;"), tag_style)
    w2, h2 = p2.wrapOn(c, avail_w, 100)
    p2.drawOn(c, 16 * mm, tagline_y - h2)
    c.setFillAlpha(1.0)

    # CTA button — left panel, lower third
    btn_y     = 60 * mm
    btn_w     = LEFT_W - 32 * mm
    btn_h     = 14 * mm
    btn_x     = 16 * mm
    c.setFillColor(rl_color(cta_color))
    c.roundRect(btn_x, btn_y, btn_w, btn_h, 3 * mm, fill=1, stroke=0)
    c.setFillColor(rl_color(cta_text))
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(btn_x + btn_w / 2, btn_y + 4 * mm, cta[:28])

    # Powered by — very bottom of left panel
    c.setFillColor(rl_color(panel_text))
    c.setFillAlpha(0.3)
    c.setFont("Helvetica", 7.5)
    c.drawString(16 * mm, 10 * mm, "Generated by BrandForge AI")
    c.setFillAlpha(1.0)

    # ── RIGHT PANEL CONTENT ────────────────────────────────────────

    # "WHY [BRAND]" eyebrow
    c.setFillColor(rl_color(colors.get("text", "#191919")))
    c.setFillAlpha(0.4)
    c.setFont("Helvetica-Bold", 8)
    eyebrow = f"WHY {brand_name.upper()}"
    x_pos = RIGHT_X + 16 * mm
    for ch in eyebrow:
        c.drawString(x_pos, PAGE_H - 22 * mm, ch)
        x_pos += c.stringWidth(ch, "Helvetica-Bold", 8) + 2
    c.setFillAlpha(1.0)

    # Elevator pitch / brand promise — top of right panel
    if elevator:
        pitch_style = ParagraphStyle(
            "Pitch",
            fontName="Helvetica",
            fontSize=11.5,
            leading=17,
            textColor=rl_color(colors.get("text", "#191919")),
            alignment=TA_LEFT,
        )
        p_pitch = Paragraph(
            (elevator[:280] if elevator else "").replace("&", "&amp;"),
            pitch_style
        )
        pitch_w = RIGHT_W - 32 * mm
        wp, hp = p_pitch.wrapOn(c, pitch_w, 120)
        c.setFillAlpha(0.65)
        p_pitch.drawOn(c, RIGHT_X + 16 * mm, PAGE_H - 42 * mm - hp)
        c.setFillAlpha(1.0)
        usp_start_y = PAGE_H - 42 * mm - hp - 20
    else:
        usp_start_y = PAGE_H - 52 * mm

    # Divider line
    c.setStrokeColor(rl_color(colors.get("text", "#191919")))
    c.setLineWidth(0.4)
    c.setStrokeAlpha(0.1)
    c.line(RIGHT_X + 16 * mm, usp_start_y, PAGE_W - 16 * mm, usp_start_y)
    c.setStrokeAlpha(1.0)

    # USP items — elegantly padded blocks
    usp_area_h  = usp_start_y - 36 * mm   # leave space for footer
    n_usps      = min(len(usps), 3)
    if n_usps == 0:
        usps = ["Feature 1", "Feature 2", "Feature 3"]
        n_usps = 3
    usp_slot_h  = usp_area_h / n_usps

    usp_title_style = ParagraphStyle(
        "USPTitle",
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=rl_color(colors.get("text", "#191919")),
    )
    usp_desc_style = ParagraphStyle(
        "USPDesc",
        fontName="Helvetica",
        fontSize=10,
        leading=14.5,
        textColor=rl_color(colors.get("text", "#444444")),
    )

    usp_titles = (
        copy.get("usp_titles")
        or state.get("brand_profile", {}).get("usp_titles")
        or []
    )
    usp_descs = (
        copy.get("usp_descriptions")
        or state.get("brand_profile", {}).get("usp_descriptions")
        or []
    )

    for i in range(n_usps):
        slot_top = usp_start_y - (i * usp_slot_h)
        
        # Subtle white card behind each USP to make it pop over the dot grid
        block_pad = 6 * mm
        c.setFillColor(rl_color("#ffffff"))
        c.setFillAlpha(0.7)
        c.roundRect(RIGHT_X + 10*mm, slot_top - usp_slot_h + block_pad, 
                    RIGHT_W - 20*mm, usp_slot_h - 2*block_pad, 2*mm, fill=1, stroke=0)
        c.setFillAlpha(1.0)

        dot_y = slot_top - 18

        # Accent dot
        c.setFillColor(rl_color(cta_color))
        c.circle(RIGHT_X + 16 * mm + 4, dot_y, 4, fill=1, stroke=0)

        # Number
        c.setFillColor(rl_color(cta_color))
        c.setFont("Helvetica-Bold", 9)
        c.drawString(RIGHT_X + 16 * mm + 12, dot_y - 3, f"0{i+1}")

        # USP title
        if i < len(usp_titles) and usp_titles[i]:
            title_text = usp_titles[i]
        else:
            words = usps[i].split()
            title_text = " ".join(words[:4]) if len(words) > 4 else usps[i]

        title_x = RIGHT_X + 34 * mm
        title_w = RIGHT_W - 52 * mm

        p_title = Paragraph(title_text.replace("&", "&amp;"), usp_title_style)
        wt, ht  = p_title.wrapOn(c, title_w, 40)
        p_title.drawOn(c, title_x, slot_top - 14 - ht)

        # USP description
        if i < len(usp_descs) and usp_descs[i]:
            desc_text = usp_descs[i]
        else:
            words = usps[i].split()
            desc_text = " ".join(words[4:]) if len(words) > 4 else ""

        if desc_text:
            p_desc = Paragraph(
                (desc_text[:200]).replace("&", "&amp;"),
                usp_desc_style
            )
            wd, hd = p_desc.wrapOn(c, title_w, 60)
            desc_y = slot_top - 18 - ht - hd
            if desc_y > slot_top - usp_slot_h + block_pad:
                p_desc.drawOn(c, title_x, desc_y)

    # Bottom footer bar
    c.setFillColor(rl_color(colors.get("primary", "#444444")))
    c.setFillAlpha(0.05)
    c.rect(RIGHT_X, 0, RIGHT_W, 22 * mm, fill=1, stroke=0)
    c.setFillAlpha(1.0)

    c.setFillColor(rl_color(colors.get("text", "#888888")))
    c.setFillAlpha(0.5)
    c.setFont("Helvetica-Bold", 8)
    if url:
        c.drawString(RIGHT_X + 16 * mm, 9 * mm, url[:50].replace("https://", "").replace("http://", ""))
    c.drawRightString(PAGE_W - 16 * mm, 9 * mm, (copy.get("tagline", "") or "")[:50])
    c.setFillAlpha(1.0)

    c.showPage()
    c.save()


# ---------------------------------------------------------------------------
# Social Card PNG
# ---------------------------------------------------------------------------

def generate_social_card(state: dict, colors: dict, copy: dict,
                          output_dir: Path) -> str:
    """
    Production social card 1080x1080px.
    Dark card for light brands (like Notion), light card for dark brands.
    Robust font loading with multiple fallbacks.
    Full content: brand name, headline, tagline, USPs, CTA.
    """
    import urllib.request

    brand_name = _brand_name(state)
    usps       = _usps(state)
    headline   = safe_headline(copy, "bold", 0, brand_name)
    tagline    = copy.get("tagline") or state.get("brand_promise", "")[:80]
    cta        = safe_cta(copy, "bold", 0, f"Explore {brand_name}")

    panel_color, panel_text = pick_panel_color(colors)
    cta_color,   cta_text   = pick_cta_color(colors, panel_color)

    # Card color decision
    # Light brand (Notion: white bg) → dark card using panel_color
    # Dark brand (Stripe: dark bg)   → use bg color as card base
    bg_lum = get_luminance(colors["background"])
    if bg_lum > 0.7:
        card_bg   = panel_color          # dark
        card_text = panel_text           # white
        card_acc  = cta_color
    else:
        card_bg   = colors["background"]
        card_text = colors["text"]
        card_acc  = cta_color

    bg_rgb   = _hex_to_rgb(card_bg)
    text_rgb = _hex_to_rgb(card_text)
    acc_rgb  = _hex_to_rgb(card_acc)
    cta_text_rgb = _hex_to_rgb(cta_text)

    # Muted text color (70% blend toward bg)
    muted_rgb = tuple(
        int(text_rgb[i] * 0.55 + bg_rgb[i] * 0.45)
        for i in range(3)
    )

    W, H = 1080, 1080
    img  = Image.new("RGB", (W, H), bg_rgb)
    draw = ImageDraw.Draw(img)

    # ── Background design elements ────────────────────────────────

    # Large circle — top right, slightly lighter/darker than bg
    shift = 22 if get_luminance(card_bg) < 0.5 else -14
    circ_color = tuple(min(255, max(0, c + shift)) for c in bg_rgb)
    draw.ellipse([700, -200, 1280, 580], fill=circ_color)

    # Small circle — bottom left
    shift2 = 16 if get_luminance(card_bg) < 0.5 else -10
    circ2 = tuple(min(255, max(0, c + shift2)) for c in bg_rgb)
    draw.ellipse([-120, 750, 280, 1150], fill=circ2)

    # ── Structural lines ──────────────────────────────────────────

    # Top accent bar — full width, 16px
    draw.rectangle([0, 0, W, 16], fill=acc_rgb)

    # Left accent strip — full height, 8px
    draw.rectangle([0, 0, 8, H], fill=acc_rgb)

    # ── Font loading ──────────────────────────────────────────────
    # Try downloading fonts if not present, then load with fallbacks

    fonts_dir = Path("assets/fonts")
    fonts_dir.mkdir(exist_ok=True)

    font_downloads = {
        "Syne-Bold.ttf": (
            "https://github.com/google/fonts/raw/main/ofl/syne/Syne-Bold.ttf"
        ),
        "Syne-Regular.ttf": (
            "https://github.com/google/fonts/raw/main/ofl/syne/Syne-Regular.ttf"
        ),
    }
    for fname, url_dl in font_downloads.items():
        fpath = fonts_dir / fname
        if not fpath.exists():
            try:
                urllib.request.urlretrieve(url_dl, fpath)
                print(f"[social] Downloaded font: {fname}")
            except Exception as fe:
                print(f"[social] Font download failed {fname}: {fe}")

    def load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
        candidates = [
            fonts_dir / ("Syne-Bold.ttf" if bold else "Syne-Regular.ttf"),
            fonts_dir / ("Inter-Bold.ttf" if bold else "Inter-Regular.ttf"),
            fonts_dir / "JetBrainsMono-Regular.ttf",
            Path("C:/Windows/Fonts/arialbd.ttf") if bold else Path("C:/Windows/Fonts/arial.ttf"),
            Path("C:/Windows/Fonts/arial.ttf"),
        ]
        for p in candidates:
            if p.exists():
                try:
                    return ImageFont.truetype(str(p), size)
                except Exception:
                    pass
        # PIL default — always works, renders small
        return ImageFont.load_default()

    font_brand    = load_font(64, bold=True)
    font_headline = load_font(72, bold=True)
    font_tagline  = load_font(36)
    font_usp      = load_font(28, bold=True)
    font_num      = load_font(20, bold=True)
    font_cta      = load_font(30, bold=True)
    font_small    = load_font(20)

    # ── Brand label — top left ────────────────────────────────────
    brand_upper = brand_name.upper()
    draw.text((48, 44), brand_upper, font=font_brand, fill=text_rgb)

    # Accent underline under brand name
    try:
        bbox = draw.textbbox((48, 44), brand_upper, font=font_brand)
        line_y = bbox[3] + 6
        line_w = bbox[2] - bbox[0]
    except Exception:
        line_y = 44 + 70
        line_w = len(brand_upper) * 38
    draw.rectangle([48, line_y, 48 + line_w, line_y + 4], fill=acc_rgb)

    # ── Headline ──────────────────────────────────────────────────
    y = line_y + 32

    # Word-wrap headline
    words = headline.split()
    lines_h, line_cur = [], []
    for word in words:
        test = " ".join(line_cur + [word])
        try:
            bbox = draw.textbbox((0, 0), test, font=font_headline)
            w_test = bbox[2] - bbox[0]
        except Exception:
            w_test = len(test) * 40
        if w_test > W - 100 and line_cur:
            lines_h.append(" ".join(line_cur))
            line_cur = [word]
        else:
            line_cur.append(word)
    if line_cur:
        lines_h.append(" ".join(line_cur))

    for line in lines_h[:3]:
        draw.text((48, y), line, font=font_headline, fill=text_rgb)
        try:
            bbox = draw.textbbox((48, y), line, font=font_headline)
            y = bbox[3] + 8
        except Exception:
            y += 86

    # ── Divider ───────────────────────────────────────────────────
    y += 20
    draw.rectangle([48, y, W - 48, y + 2], fill=acc_rgb)
    y += 24

    # ── Tagline ───────────────────────────────────────────────────
    if tagline:
        words_t  = tagline.split()
        lines_t, line_t = [], []
        for word in words_t:
            test = " ".join(line_t + [word])
            try:
                bbox = draw.textbbox((0, 0), test, font=font_tagline)
                wt   = bbox[2] - bbox[0]
            except Exception:
                wt = len(test) * 20
            if wt > W - 100 and line_t:
                lines_t.append(" ".join(line_t))
                line_t = [word]
            else:
                line_t.append(word)
        if line_t:
            lines_t.append(" ".join(line_t))

        for line in lines_t[:2]:
            draw.text((48, y), line, font=font_tagline, fill=muted_rgb)
            try:
                bbox = draw.textbbox((48, y), line, font=font_tagline)
                y = bbox[3] + 6
            except Exception:
                y += 44

    # ── USPs ──────────────────────────────────────────────────────
    y += 32

    for i, usp in enumerate(usps[:3]):
        # Number badge
        num_str = f"0{i+1}"
        draw.text((48, y), num_str, font=font_num, fill=acc_rgb)

        # USP text — clamp to single line
        usp_display = usp[:72] + ("…" if len(usp) > 72 else "")
        draw.text((96, y), usp_display, font=font_usp, fill=text_rgb)

        try:
            bbox = draw.textbbox((96, y), usp_display, font=font_usp)
            y = bbox[3] + 14
        except Exception:
            y += 48

        # Thin separator
        if i < min(len(usps), 3) - 1:
            draw.rectangle(
                [48, y + 4, W - 48, y + 5],
                fill=tuple(int(c * 0.15 + bg_rgb[i_] * 0.85)
                           for i_, c in enumerate(text_rgb))
            )
            y += 18

    # ── CTA button ────────────────────────────────────────────────
    cta_label = f"  {cta}  →"
    cta_y = H - 150

    try:
        bbox_cta = draw.textbbox((0, 0), cta_label, font=font_cta)
        btn_w = bbox_cta[2] - bbox_cta[0] + 56
    except Exception:
        btn_w = len(cta_label) * 18 + 56
    btn_h = 62

    _safe_rounded_rect(
        draw,
        [48, cta_y, 48 + btn_w, cta_y + btn_h],
        radius=10,
        fill=acc_rgb,
    )
    draw.text((48 + 28, cta_y + 15), cta_label, font=font_cta,
              fill=cta_text_rgb)

    # ── Bottom bar + watermark ────────────────────────────────────
    draw.rectangle([0, H - 10, W, H], fill=acc_rgb)

    watermark_color = tuple(
        int(text_rgb[i] * 0.25 + bg_rgb[i] * 0.75) for i in range(3)
    )
    draw.text(
        (W - 340, H - 46),
        "Generated by BrandForge AI",
        font=font_small,
        fill=watermark_color,
    )

    output_path = output_dir / "social_card.png"
    img.save(output_path, "PNG", quality=95)
    print(
        f"[social] [OK] card_bg={card_bg} text={card_text} "
        f"acc={card_acc} fonts_loaded=True"
    )
    return str(output_path)


# --- Drawing helpers for social card ---

def _make_gradient(W: int, H: int, color1: str, color2: str) -> Image.Image:
    img = Image.new("RGBA", (W, H))
    r1, g1, b1 = _hex_to_rgb(color1)
    r2, g2, b2 = _hex_to_rgb(color2)
    for y in range(H):
        t = y / H
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        for x in range(W):
            img.putpixel((x, y), (r, g, b, 255))
    return img


def _draw_pills(draw: ImageDraw.Draw, pills: list[str], x: int, y: int,
                font: ImageFont.FreeTypeFont, bg: tuple, fg: tuple,
                max_x: int) -> None:
    """Draw USP pills left-to-right."""
    cx = x
    PAD_H, PAD_V, RADIUS, GAP = 22, 12, 24, 14
    for pill in pills:
        bbox = draw.textbbox((0, 0), pill, font=font)
        pw = bbox[2] - bbox[0] + PAD_H * 2
        ph = bbox[3] - bbox[1] + PAD_V * 2
        if cx + pw > max_x:
            break
        draw.rounded_rectangle([cx, y, cx + pw, y + ph], radius=RADIUS, fill=bg)
        draw.text((cx + PAD_H, y + PAD_V - 2), pill, font=font, fill=fg)
        cx += pw + GAP


def _draw_pills_centered(draw: ImageDraw.Draw, pills: list[str], W: int, y: int,
                          font: ImageFont.FreeTypeFont, bg: tuple, fg: tuple) -> None:
    PAD_H, PAD_V, RADIUS, GAP = 22, 12, 24, 14
    widths = []
    for pill in pills:
        bbox = draw.textbbox((0, 0), pill, font=font)
        widths.append(bbox[2] - bbox[0] + PAD_H * 2)
    total_w = sum(widths) + GAP * (len(widths) - 1)
    cx = (W - total_w) // 2
    for pill, pw in zip(pills, widths):
        bbox = draw.textbbox((0, 0), pill, font=font)
        ph = bbox[3] - bbox[1] + PAD_V * 2
        draw.rounded_rectangle([cx, y, cx + pw, y + ph], radius=RADIUS, fill=bg)
        draw.text((cx + PAD_H, y + PAD_V - 2), pill, font=font, fill=fg)
        cx += pw + GAP


def _draw_cta_button(draw: ImageDraw.Draw, text: str, xy: tuple[int, int],
                      font: ImageFont.FreeTypeFont, bg: tuple, fg: tuple,
                      pad_h: int = 44, pad_v: int = 22, radius: int = 36) -> None:
    x, y = xy
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.rounded_rectangle([x, y, x + tw + pad_h * 2, y + th + pad_v * 2],
                            radius=radius, fill=bg)
    draw.text((x + pad_h, y + pad_v), text, font=font, fill=fg)


def _draw_cta_button_centered(draw: ImageDraw.Draw, text: str, W: int, y: int,
                                font: ImageFont.FreeTypeFont, bg: tuple, fg: tuple) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    ph, pv = 48, 24
    x = (W - tw - ph * 2) // 2
    draw.rounded_rectangle([x, y, x + tw + ph * 2, y + th + pv * 2],
                            radius=36, fill=bg)
    draw.text((x + ph, y + pv), text, font=font, fill=fg)


def _draw_url(draw: ImageDraw.Draw, url: str, x: int, y: int,
               font: ImageFont.FreeTypeFont, fill: tuple,
               align: str = "right") -> None:
    short = url.replace("https://", "").replace("http://", "").rstrip("/")[:45]
    bbox = draw.textbbox((0, 0), short, font=font)
    w = bbox[2] - bbox[0]
    if align == "right":
        draw.text((x - w, y), short, font=font, fill=fill)
    elif align == "center":
        draw.text((x - w // 2, y), short, font=font, fill=fill)
    else:
        draw.text((x, y), short, font=font, fill=fill)


# ---------------------------------------------------------------------------
# Email HTML
# ---------------------------------------------------------------------------

def render_email_html(state: dict, colors: dict, layout: dict,
                       output_dir: Path) -> list[str]:
    """Render all 3 email HTML files using keyed email_output."""
    base = Path(__file__).resolve().parents[2] / "assets" / "email_templates"
    if not base.exists():
        base = Path("assets/email_templates")

    brand_name = _brand_name(state)
    emails     = get_emails(state)
    paths: list[str] = []

    # Email header style affects header height and visual treatment
    header_style = layout.get("email_header_style", "bold-color")
    header_height = {"bold-color": "90px", "full-bleed": "140px",
                     "minimal-line": "60px", "subtle-gradient": "100px"}.get(
        header_style, "90px"
    )

    for email in emails:
        template_path = base / f"email_{email['type']}.html"
        if not template_path.exists():
            print(f"[asset_generator] Email template not found: {template_path}")
            continue

        html = template_path.read_text(encoding="utf-8")
        populated = _replace_tokens(html, {
            "{{HEADER_COLOR}}":    colors["primary"],
            "{{ACCENT_COLOR}}":    colors["accent"],
            "{{CTA_TEXT_COLOR}}":  "#ffffff",
            "{{BRAND_NAME}}":      brand_name,
            "{{SUBJECT}}":         email["subject"],
            "{{PREVIEW_TEXT}}":    email["preview_text"],
            "{{HEADLINE}}":        email["headline"],
            "{{BODY_CONTENT}}":    email["body"],
            "{{CTA_TEXT}}":        email["cta_text"],
            "{{PS_LINE}}":         email["ps_line"],
            "{{HEADER_HEIGHT}}":   header_height,
            "{{BRAND_URL}}":       state.get("url", ""),
        })

        output_path = output_dir / f"email_{email['type']}.html"
        output_path.write_text(populated, encoding="utf-8")
        paths.append(str(output_path))
        print(f"[asset_generator] Email written: {output_path.name} "
              f"| subject: {email['subject'][:40]}")

    return paths


# ---------------------------------------------------------------------------
# Ad Copy PDF
# ---------------------------------------------------------------------------

def _normalize_ads(state: dict) -> dict:
    """Normalize ad_output to the new AD_PROMPT schema."""
    ads = state.get("ad_output") or {}
    if not isinstance(ads, dict):
        ads = {}

    brand_name = _brand_name(state)

    # Handle old format (google_ads list + instagram list)
    if "headlines" not in ads and ("google_ads" in ads or "instagram" in ads):
        google = ads.get("google_ads") or []
        insta  = ads.get("instagram") or []
        linkedin = ads.get("linkedin") or {}
        headlines, descs = [], []
        for ad in google:
            if isinstance(ad, dict):
                headlines += [ad.get("headline_1"), ad.get("headline_2"), ad.get("headline_3")]
                descs     += [ad.get("description_1"), ad.get("description_2")]
        bodies = [item.get("caption", "") for item in insta if isinstance(item, dict)]
        if isinstance(linkedin, dict) and linkedin.get("post"):
            bodies.append(linkedin["post"])
        ads = {
            "headlines":      [h for h in headlines if h],
            "body_copies":    bodies,
            "ctas":           [linkedin.get("cta", f"Explore {brand_name}")
                               if isinstance(linkedin, dict) else f"Explore {brand_name}"],
            "google_rsa":     {"headlines": headlines[:5], "descriptions": descs[:2]},
            "meta_primary_text": bodies[0] if bodies else "",
            "linkedin_ad":    {},
            "hooks":          [],
        }

    return {
        "headlines":        ads.get("headlines", []),
        "body_copies":      ads.get("body_copies", []),
        "ctas":             ads.get("ctas", []),
        "google_rsa":       ads.get("google_rsa", {"headlines": [], "descriptions": []}),
        "meta_primary_text": ads.get("meta_primary_text", ""),
        "linkedin_ad":      ads.get("linkedin_ad", {}),
        "hooks":            ads.get("hooks", []),
    }


def render_ad_copy_pdf(state: dict, colors: dict, output_dir: Path) -> str:
    """Render ad copy as a rich multi-section branded PDF."""
    brand_name = _brand_name(state)
    ads        = _normalize_ads(state)

    # Build the HTML for WeasyPrint
    def items_html(lst: list, numbered: bool = False) -> str:
        if not lst:
            return "<p style='color:#888'>None generated.</p>"
        tag = "ol" if numbered else "ul"
        items = "".join(
            f"<li>{escape(str(item))}</li>"
            for item in lst if item
        )
        return f"<{tag}>{items}</{tag}>"

    def card(content: str) -> str:
        return (
            f"<div style='background:#f5f7fa;border:1px solid #e1e4e8;"
            f"border-radius:8px;padding:18px 20px;margin:10px 0;"
            f"line-height:1.65;font-size:14px;color:#2d3748'>"
            f"{escape(str(content))}</div>"
        )

    def chips(lst: list) -> str:
        return "".join(
            f"<span style='display:inline-block;background:{colors['accent']};"
            f"color:#fff;padding:10px 18px;border-radius:20px;margin:5px;"
            f"font-weight:700;font-size:14px'>{escape(str(item))}</span>"
            for item in lst if item
        )

    linkedin = ads.get("linkedin_ad") or {}
    hooks    = ads.get("hooks") or []

    html = f"""<!DOCTYPE html>
<html><head><meta charset='utf-8'><style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
body {{ font-family: Arial, sans-serif; padding: 48px; color: #1a202c; max-width: 800px; }}
h1 {{ color: {colors['primary']}; font-size: 34px; margin: 0 0 8px; }}
.subtitle {{ color: #666; font-size: 15px; margin: 0 0 36px; }}
h2 {{ color: {colors['secondary']}; font-size: 20px; margin: 36px 0 10px;
      border-bottom: 3px solid {colors['accent']}; padding-bottom: 8px; }}
h3 {{ color: #4a5568; font-size: 15px; margin: 18px 0 6px; text-transform: uppercase;
      letter-spacing: 0.06em; }}
ol, ul {{ margin: 0; padding-left: 22px; }}
li {{ margin-bottom: 10px; font-size: 14px; line-height: 1.55; }}
.char-note {{ font-size: 11px; color: #999; margin-bottom: 6px; }}
</style></head><body>

<h1>Ad Copy Kit</h1>
<p class="subtitle">{escape(brand_name)} &mdash; All Formats</p>

<h2>Attention Headlines</h2>
{items_html(ads['headlines'], numbered=True)}

<h2>Body Copy Variants</h2>
{"".join(card(b) for b in ads['body_copies'] if b)}

<h2>Call-to-Actions</h2>
{chips(ads['ctas'])}

<h2>Google Responsive Search Ads (RSA)</h2>
<h3>Headlines <span class="char-note">(30 char max each)</span></h3>
{items_html(ads['google_rsa'].get('headlines', []), numbered=True)}
<h3>Descriptions <span class="char-note">(90 char max each)</span></h3>
{items_html(ads['google_rsa'].get('descriptions', []))}

<h2>Meta / Facebook & Instagram</h2>
{card(ads.get('meta_primary_text', ''))}

{"<h2>LinkedIn Ad</h2>" +
  card((linkedin.get('intro','') + ' ' + linkedin.get('body','')).strip()) +
  chips([linkedin.get('cta','')]) if linkedin else ""}

{"<h2>Social Hooks</h2>" + items_html(hooks) if hooks else ""}

<p style='margin-top:60px;color:#bbb;font-size:12px;border-top:1px solid #eee;
   padding-top:16px'>Generated by BrandForge AI &mdash; {escape(state.get('url',''))}</p>
</body></html>"""

    output_path = output_dir / "ad_copy.pdf"
    _use_weasyprint = os.name != "nt" or os.getenv("BRANDFORGE_USE_WEASYPRINT") == "1"

    if _use_weasyprint:
        try:
            from weasyprint import HTML as WP
            WP(string=html).write_pdf(str(output_path))
            print(f"[asset_generator] Ad copy PDF written via WeasyPrint: {output_path}")
            return str(output_path)
        except Exception as e:
            print(f"[asset_generator] WeasyPrint ad failed: {e} — falling back")

    _render_ad_reportlab(brand_name, ads, colors, output_path)
    return str(output_path)


def _render_ad_reportlab(brand_name: str, ads: dict, colors: dict,
                          output_path: Path) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                     ListFlowable, ListItem, Table, TableStyle)
    from reportlab.lib import colors as rl_colors

    doc = SimpleDocTemplate(str(output_path), pagesize=A4,
                             rightMargin=18*mm, leftMargin=18*mm,
                             topMargin=18*mm, bottomMargin=18*mm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("BFTitle", parent=styles["Title"],
                               textColor=_reportlab_color(colors["primary"]),
                               fontSize=26, leading=32, spaceAfter=20))
    styles.add(ParagraphStyle("BFSection", parent=styles["Heading2"],
                               textColor=_reportlab_color(colors["secondary"]),
                               fontSize=16, leading=20, spaceBefore=16, spaceAfter=8))
    styles.add(ParagraphStyle("BFCard", parent=styles["BodyText"],
                               backColor=rl_colors.HexColor("#f5f7fa"),
                               borderColor=rl_colors.HexColor("#e1e4e8"),
                               borderWidth=0.5, borderPadding=10,
                               leading=16, spaceAfter=8))
    styles.add(ParagraphStyle("BFChip", parent=styles["BodyText"],
                               textColor=rl_colors.white,
                               backColor=_reportlab_color(colors["accent"]),
                               borderPadding=7, leading=14, spaceAfter=5))

    story = [Paragraph(f"Ad Copy Kit — {escape(brand_name)}", styles["BFTitle"])]

    sections = [
        ("Attention Headlines",    ads.get("headlines", []),     True),
        ("Body Copy Variants",     ads.get("body_copies", []),   False),
        ("Call-to-Actions",        ads.get("ctas", []),          False),
        ("Google RSA Headlines",   (ads.get("google_rsa") or {}).get("headlines", []), True),
        ("Google RSA Descriptions",(ads.get("google_rsa") or {}).get("descriptions",[]),False),
        ("Meta Primary Text",      [ads.get("meta_primary_text","")], False),
    ]

    for title, items, numbered in sections:
        story.append(Paragraph(title, styles["BFSection"]))
        if not items or not any(items):
            story.append(Paragraph("None generated.", styles["BodyText"]))
            continue
        if title == "Call-to-Actions":
            tbl = Table([[Paragraph(escape(str(i)), styles["BFChip"]) for i in items[:3]]])
            tbl.setStyle(TableStyle([("VALIGN", (0,0),(-1,-1),"TOP"),
                                      ("LEFTPADDING",(0,0),(-1,-1),3),
                                      ("RIGHTPADDING",(0,0),(-1,-1),3)]))
            story.append(tbl)
        elif numbered:
            story.append(ListFlowable(
                [ListItem(Paragraph(escape(str(i)), styles["BodyText"])) for i in items if i],
                bulletType="1",
            ))
        else:
            for item in items:
                if item:
                    story.append(Paragraph(escape(str(item)), styles["BFCard"]))
        story.append(Spacer(1, 4))

    linkedin = ads.get("linkedin_ad") or {}
    if linkedin:
        story.append(Paragraph("LinkedIn Ad", styles["BFSection"]))
        body = (linkedin.get("intro","") + " " + linkedin.get("body","")).strip()
        if body:
            story.append(Paragraph(escape(body), styles["BFCard"]))
        if linkedin.get("cta"):
            story.append(Paragraph(escape(linkedin["cta"]), styles["BFChip"]))

    hooks = ads.get("hooks") or []
    if hooks:
        story.append(Paragraph("Social Hooks", styles["BFSection"]))
        story.append(ListFlowable(
            [ListItem(Paragraph(escape(str(h)), styles["BodyText"])) for h in hooks if h],
            bulletType="bullet",
        ))

    doc.build(story)
    print(f"[asset_generator] Ad copy PDF written via ReportLab: {output_path}")


# ---------------------------------------------------------------------------
# Main node
# ---------------------------------------------------------------------------

async def asset_generator_node(state: dict) -> dict:
    job_id = state.get("job_id", "")
    job_manager.emit(job_id, {
        "type": "asset_generator", "stage": "asset_generator",
        "status": "running", "message": "Generating brand assets...",
    })

    output_dir = Path("outputs") / job_id / "assets"
    output_dir.mkdir(parents=True, exist_ok=True)

    colors = get_colors(state)
    copy   = get_copy(state)
    layout = get_layout(state)
    paths  = {}

    # ── Flyer PDF — HTML → Playwright ──────────────────────────
    try:
        from pipeline.nodes.asset_renderer import render_flyer
        flyer_path = await render_flyer(state, output_dir)
        paths["flyer_pdf_path"] = flyer_path
        job_manager.emit(job_id, {
            "type": "asset_generator", "stage": "asset_generator",
            "status": "progress", "message": "✓ Flyer PDF generated",
        })
    except Exception as e:
        print(f"[asset] Flyer error: {e}")
        job_manager.emit(job_id, {
            "type": "asset_generator", "stage": "asset_generator",
            "status": "warning", "message": f"⚠ Flyer failed: {e}",
        })

    # ── Social card PNG — HTML → Playwright ────────────────────
    try:
        from pipeline.nodes.asset_renderer import render_social_card
        social_path = await render_social_card(state, output_dir)
        paths["social_card_path"] = social_path
        job_manager.emit(job_id, {
            "type": "asset_generator", "stage": "asset_generator",
            "status": "progress", "message": "✓ Social card generated",
        })
    except Exception as e:
        print(f"[asset] Social card error: {e}")
        job_manager.emit(job_id, {
            "type": "asset_generator", "stage": "asset_generator",
            "status": "warning", "message": f"⚠ Social card failed: {e}",
        })

    # ── Emails ──────────────────────────────────────────────────
    try:
        email_paths = render_email_html(state, colors, layout, output_dir)
        paths["email_html_paths"] = email_paths
        paths["email_html_path"]  = email_paths[0] if email_paths else ""
        job_manager.emit(job_id, {
            "type": "asset_generator", "stage": "asset_generator",
            "status": "progress", "message": "✓ Email templates generated",
        })
    except Exception as e:
        print(f"[asset] Email error: {e}")

    # ── Ad copy PDF ─────────────────────────────────────────────
    try:
        ad_path = render_ad_copy_pdf(state, colors, output_dir)
        paths["ad_copy_pdf_path"] = ad_path
        job_manager.emit(job_id, {
            "type": "asset_generator", "stage": "asset_generator",
            "status": "progress", "message": "✓ Ad copy PDF generated",
        })
    except Exception as e:
        print(f"[asset] Ad copy error: {e}")

    job_manager.emit(job_id, {
        "type": "asset_generator", "stage": "asset_generator",
        "status": "done", "message": "All assets generated.",
    })

    return {
        "flyer_pdf_path":   paths.get("flyer_pdf_path",   ""),
        "social_card_path": paths.get("social_card_path", ""),
        "email_html_path":  paths.get("email_html_path",  ""),
        "email_html_paths": paths.get("email_html_paths", []),
        "ad_copy_pdf_path": paths.get("ad_copy_pdf_path", ""),
    }