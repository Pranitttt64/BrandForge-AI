"""
Universal color system for BrandForge AI.
Handles color extraction, semantic role assignment, and contrast guarantees
for all 5 brand archetypes: monochrome, dark-primary, colorful, pastel, multi-color.
"""

import re
from collections import Counter
from typing import Optional
from bs4 import BeautifulSoup


def hex_to_rgb(hex_color: str) -> tuple:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    try:
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    except Exception:
        return (0, 0, 0)


def rgb_to_hex(r: int, g: int, b: int) -> str:
    return "#{:02x}{:02x}{:02x}".format(r, g, b)


def get_luminance(hex_color: str) -> float:
    try:
        r, g, b = hex_to_rgb(hex_color)
        return (0.299 * r + 0.587 * g + 0.114 * b) / 255
    except Exception:
        return 0.5


def normalize_hex(raw: str) -> Optional[str]:
    raw = raw.lstrip("#").strip()
    if len(raw) == 3:
        raw = "".join(c * 2 for c in raw)
    if len(raw) != 6:
        return None
    try:
        int(raw, 16)
        return f"#{raw.lower()}"
    except ValueError:
        return None


def is_near_neutral(hex_color: str) -> bool:
    """True if color is close to gray (R≈G≈B) — unlikely to be a brand color."""
    try:
        r, g, b = hex_to_rgb(hex_color)
        avg = (r + g + b) / 3
        return max(abs(r - avg), abs(g - avg), abs(b - avg)) < 18
    except Exception:
        return True


def colors_are_similar(hex1: str, hex2: str, tolerance: int = 35) -> bool:
    try:
        r1, g1, b1 = hex_to_rgb(hex1)
        r2, g2, b2 = hex_to_rgb(hex2)
        return (abs(r1 - r2) + abs(g1 - g2) + abs(b1 - b2)) < tolerance
    except Exception:
        return False


def ensure_contrast(fg: str, bg: str) -> str:
    """Return fg if it contrasts with bg, otherwise return white or black."""
    try:
        diff = abs(get_luminance(fg) - get_luminance(bg))
        if diff > 0.3:
            return fg
        return "#ffffff" if get_luminance(bg) < 0.5 else "#191919"
    except Exception:
        return "#191919"


def pick_panel_color(colors: dict) -> tuple:
    """
    Returns (panel_bg_hex, panel_text_hex) guaranteed to contrast.
    Works for every brand archetype.
    Priority waterfall:
      1. primary is dark → use as panel, white text
      2. primary is mid-tone → check white text contrast
      3. primary is light → use text color as panel, white text
      4. accent is dark → use accent as panel
      5. force #191919 panel as absolute fallback
    """
    primary = colors.get("primary", "#191919")
    text    = colors.get("text",    "#191919")
    accent  = colors.get("accent",  "#2383e2")

    lum_primary = get_luminance(primary)

    if lum_primary < 0.4:
        return primary, "#ffffff"

    if lum_primary < 0.65:
        if abs(lum_primary - get_luminance("#ffffff")) > 0.25:
            return primary, "#ffffff"
        return primary, "#191919"

    lum_text = get_luminance(text)
    if lum_text < 0.45:
        return text, "#ffffff"

    lum_accent = get_luminance(accent)
    if lum_accent < 0.6:
        return accent, "#ffffff"

    return "#191919", "#ffffff"


def pick_cta_color(colors: dict, panel_color: str) -> tuple:
    """
    Returns (cta_bg_hex, cta_text_hex).
    CTA must be visually distinct from panel and readable.
    """
    accent  = colors.get("accent",  "#2383e2")
    primary = colors.get("primary", "#191919")
    bg      = colors.get("background", "#ffffff")

    for candidate in [accent, primary]:
        lum = get_luminance(candidate)
        if not colors_are_similar(candidate, panel_color, 60):
            if lum < 0.7:
                text_on_cta = "#ffffff" if lum < 0.45 else "#191919"
                return candidate, text_on_cta

    panel_lum = get_luminance(panel_color)
    if panel_lum < 0.5:
        fallback = bg if get_luminance(bg) > 0.5 else "#ffffff"
        return fallback, "#191919"
    return "#191919", "#ffffff"


def extract_brand_colors(html: str) -> dict:
    """Universal color extraction from HTML/CSS/SVG/Meta."""
    try:
        soup = BeautifulSoup(html, "html.parser")
        color_text = ""
        
        # 1. Meta theme-color
        for meta in soup.find_all("meta", attrs={"name": "theme-color"}):
            if meta.get("content"):
                color_text += meta["content"] + " "
                
        # 2. Inline styles
        for tag in soup.find_all(style=True):
            color_text += tag["style"] + " "
            
        # 3. SVG fills and strokes
        for svg in soup.find_all(["svg", "path", "rect", "circle", "polygon"]):
            for attr in ["fill", "stroke", "color"]:
                if svg.get(attr) and svg[attr] != "none":
                    color_text += svg[attr] + " "
                    
        # 4. Internal style blocks
        for style_tag in soup.find_all("style"):
            color_text += style_tag.get_text() + " "
            
        # Extract Hex
        hex_pattern = r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b"
        raw_hex = re.findall(hex_pattern, color_text)
        
        # Extract RGB/RGBA
        rgb_pattern = r"rgba?\(\s*(\d+)\s*(?:,|\s)\s*(\d+)\s*(?:,|\s)\s*(\d+)"
        raw_rgb = re.findall(rgb_pattern, color_text)

        normalized = []
        for c in raw_hex:
            n = normalize_hex(c)
            if n: normalized.append(n)
            
        for r, g, b in raw_rgb:
            try:
                normalized.append(rgb_to_hex(int(r), int(g), int(b)))
            except Exception:
                pass

        if not normalized:
            return {"background": "#ffffff", "text": "#191919", "primary": "#191919", "secondary": "#444444", "accent": "#2383e2"}

        counter = Counter(normalized)
        lights, darks, non_neutrals = [], [], []

        for color, freq in counter.most_common(100):
            lum = get_luminance(color)
            if lum > 0.8:
                lights.append(color)
            elif lum < 0.25:
                darks.append(color)
                
            if not is_near_neutral(color):
                non_neutrals.append(color)

        bg = lights[0] if lights else "#ffffff"
        text = darks[0] if darks else "#191919"

        unique_brand = []
        for c in non_neutrals:
            if not any(colors_are_similar(c, u, 35) for u in unique_brand) and not colors_are_similar(c, bg, 40):
                unique_brand.append(c)

        if len(unique_brand) >= 1:
            primary = unique_brand[0]
            secondary = unique_brand[1] if len(unique_brand) > 1 else primary
            accent = unique_brand[2] if len(unique_brand) > 2 else secondary
        else:
            # Monochrome fallback
            primary = darks[0] if darks else "#191919"
            secondary = darks[1] if len(darks) > 1 else primary
            accent = primary

        return {"background": bg, "text": text, "primary": primary, "secondary": secondary, "accent": accent}

    except Exception as e:
        print(f"[colors] extract_brand_colors failed: {e}")
        return {"background": "#ffffff", "text": "#191919", "primary": "#191919", "secondary": "#444444", "accent": "#2383e2"}