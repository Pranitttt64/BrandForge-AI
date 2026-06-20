"""
Asset renderer using Playwright for HTML → PDF and HTML → PNG.
Production-grade rendering engine for BrandForge AI assets.
All visual design is in HTML/CSS templates — not Python drawing code.
"""

import asyncio
import re
from pathlib import Path
from typing import Optional

from utils.colors import (
    hex_to_rgb, get_luminance, pick_panel_color, pick_cta_color,
    is_near_neutral, ensure_contrast,
)


# ── Template selection ────────────────────────────────────────────────────────

FLYER_TEMPLATES = {
    "saas_dark":    "saas_dark.html",
    "saas_light":   "saas_light.html",
    "agency_bold":  "agency_bold.html",
    "enterprise":   "enterprise.html",
}

SOCIAL_TEMPLATES = {
    "editorial_dark":  "social_editorial_dark.html",
    "editorial_light": "social_editorial_light.html",
    "bold_accent":     "social_bold_accent.html",
    "minimal":         "social_minimal.html",
}

CATEGORY_TO_FLYER = {
    "SaaS":       "saas_dark",
    "Fintech":    "enterprise",
    "E-commerce": "agency_bold",
    "Health":     "saas_light",
    "Education":  "saas_light",
    "Agency":     "agency_bold",
    "Retail":     "agency_bold",
    "NGO":        "saas_light",
    "Food":       "agency_bold",
    "Other":      "saas_dark",
}

CATEGORY_TO_SOCIAL = {
    "SaaS":       "editorial_dark",
    "Fintech":    "editorial_dark",
    "E-commerce": "bold_accent",
    "Health":     "editorial_light",
    "Education":  "editorial_light",
    "Agency":     "bold_accent",
    "Retail":     "bold_accent",
    "NGO":        "editorial_light",
    "Food":       "bold_accent",
    "Other":      "editorial_dark",
}


def select_flyer_template(state: dict) -> str:
    layout  = state.get("layout_output") or {}
    cat     = layout.get("brand_category_tag") or state.get("brand_category") or "Other"
    style   = layout.get("visual_style") or ""
    colors  = state.get("brand_colors") or {}
    bg_lum  = get_luminance(colors.get("background", "#ffffff"))

    # Override: light brands on saas_dark look wrong — use saas_light
    template_key = CATEGORY_TO_FLYER.get(cat, "saas_dark")
    if template_key == "saas_dark" and bg_lum > 0.8:
        template_key = "saas_light"

    return FLYER_TEMPLATES[template_key]


def select_social_template(state: dict) -> str:
    layout  = state.get("layout_output") or {}
    cat     = layout.get("brand_category_tag") or state.get("brand_category") or "Other"
    colors  = state.get("brand_colors") or {}
    bg_lum  = get_luminance(colors.get("background", "#ffffff"))

    template_key = CATEGORY_TO_SOCIAL.get(cat, "editorial_dark")
    if template_key == "editorial_dark" and bg_lum > 0.8:
        template_key = "editorial_light"

    return SOCIAL_TEMPLATES[template_key]


# ── Data extraction helpers ───────────────────────────────────────────────────

def _brand_name(state: dict) -> str:
    return (
        state.get("brand_name")
        or state.get("brand_profile", {}).get("brand_name")
        or "Brand"
    )

def _usps(state: dict) -> list:
    return (
        state.get("usps")
        or state.get("brand_profile", {}).get("usps")
        or []
    )

def _get_copy_text(state: dict, field: str, tone: str = "bold",
                   fallback: str = "") -> str:
    co = state.get("copy_output") or {}
    data = co.get(field, {})
    if isinstance(data, str):
        return data or fallback
    if isinstance(data, dict):
        for t in [tone, "bold", "professional", "friendly"]:
            val = data.get(t)
            if val:
                if isinstance(val, list):
                    return val[0] if val else fallback
                if isinstance(val, str):
                    return val
    if isinstance(data, list):
        return data[0] if data else fallback
    return fallback

def _get_colors(state: dict) -> dict:
    colors = (
        state.get("brand_colors")
        or state.get("brand_profile", {}).get("brand_colors")
        or {}
    )
    result = {
        "primary":    colors.get("primary",    "#191919"),
        "secondary":  colors.get("secondary",  "#444444"),
        "accent":     colors.get("accent",     "#2383e2"),
        "background": colors.get("background", "#ffffff"),
        "text":       colors.get("text",       "#191919"),
    }
    if is_near_neutral(result["primary"]):
        result["primary"] = result["text"]
    if is_near_neutral(result["accent"]):
        result["accent"] = result["primary"]
    return result

def _hex_rgba(hex_color: str, alpha: float) -> str:
    try:
        r, g, b = hex_to_rgb(hex_color)
        return f"rgba({r},{g},{b},{alpha})"
    except Exception:
        return f"rgba(0,0,0,{alpha})"

def _get_usp_titles(state: dict, usps: list) -> list:
    co = state.get("copy_output") or {}
    titles = co.get("usp_titles") or state.get("brand_profile", {}).get("usp_titles") or []
    result = []
    for i, usp in enumerate(usps[:4]):
        if i < len(titles) and titles[i]:
            result.append(titles[i])
        else:
            words = usp.split()
            result.append(" ".join(words[:4]))
    return result

def _get_usp_descs(state: dict, usps: list) -> list:
    co = state.get("copy_output") or {}
    descs = co.get("usp_descriptions") or []
    result = []
    for i, usp in enumerate(usps[:4]):
        if i < len(descs) and descs[i]:
            result.append(descs[i][:160])
        else:
            words = usp.split()
            desc = " ".join(words[4:]) if len(words) > 4 else usp
            result.append(desc[:160])
    return result

def _build_token_map(state: dict) -> dict:
    """Build complete token replacement map for all templates."""
    colors     = _get_colors(state)
    brand_name = _brand_name(state)
    usps       = _usps(state)
    usp_titles = _get_usp_titles(state, usps)
    usp_descs  = _get_usp_descs(state, usps)

    panel_color, panel_text = pick_panel_color(colors)
    cta_bg,      cta_text   = pick_cta_color(colors, panel_color)

    bg_lum = get_luminance(colors["background"])
    is_dark_brand = bg_lum < 0.4

    headline  = _get_copy_text(state, "headlines", "bold",
                               f"{brand_name} — Built for What's Next")
    tagline   = _get_copy_text(state, "taglines", "professional",
                               state.get("brand_profile", {}).get("tagline", ""))
    if not tagline:
        tagline = (state.get("copy_output") or {}).get("tagline") or \
                  state.get("brand_profile", {}).get("tagline", "")
    cta       = _get_copy_text(state, "call_to_actions", "bold", "Get Started")
    elevator  = (state.get("copy_output") or {}).get("elevator_pitch") or \
                state.get("brand_profile", {}).get("elevator_pitch") or \
                state.get("brand_promise", "")

    url       = state.get("url", "")
    category  = state.get("brand_category") or \
                state.get("brand_profile", {}).get("brand_category", "")

    # Color variants for templates
    accent_10  = _hex_rgba(colors["accent"], 0.10)
    accent_15  = _hex_rgba(colors["accent"], 0.15)
    accent_20  = _hex_rgba(colors["accent"], 0.20)
    accent_06  = _hex_rgba(colors["accent"], 0.06)
    primary_08 = _hex_rgba(colors["primary"], 0.08)
    primary_04 = _hex_rgba(colors["primary"], 0.04)

    # Safe-escape for HTML
    def esc(s: str) -> str:
        return str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

    tokens = {
        # Brand
        "{{BRAND_NAME}}":       esc(brand_name),
        "{{BRAND_NAME_UPPER}}": esc(brand_name.upper()),
        "{{TAGLINE}}":          esc(tagline[:100] if tagline else ""),
        "{{HEADLINE}}":         esc(headline[:120] if headline else ""),
        "{{ELEVATOR_PITCH}}":   esc(elevator[:280] if elevator else ""),
        "{{CTA_TEXT}}":         esc(cta[:32] if cta else "Get Started"),
        "{{BRAND_URL}}":        esc(url),
        "{{BRAND_CATEGORY}}":   esc(category),
        # Colors
        "{{PRIMARY}}":          colors["primary"],
        "{{SECONDARY}}":        colors["secondary"],
        "{{ACCENT}}":           colors["accent"],
        "{{BG}}":               colors["background"],
        "{{TEXT}}":             colors["text"],
        "{{PANEL_BG}}":         panel_color,
        "{{PANEL_TEXT}}":       panel_text,
        "{{CTA_BG}}":           cta_bg,
        "{{CTA_TEXT_COLOR}}":   cta_text,
        "{{ACCENT_10}}":        accent_10,
        "{{ACCENT_15}}":        accent_15,
        "{{ACCENT_20}}":        accent_20,
        "{{ACCENT_06}}":        accent_06,
        "{{PRIMARY_08}}":       primary_08,
        "{{PRIMARY_04}}":       primary_04,
        # USPs
        "{{USP_1_TITLE}}": esc(usp_titles[0] if len(usp_titles) > 0 else ""),
        "{{USP_1_DESC}}":  esc(usp_descs[0]  if len(usp_descs)  > 0 else ""),
        "{{USP_2_TITLE}}": esc(usp_titles[1] if len(usp_titles) > 1 else ""),
        "{{USP_2_DESC}}":  esc(usp_descs[1]  if len(usp_descs)  > 1 else ""),
        "{{USP_3_TITLE}}": esc(usp_titles[2] if len(usp_titles) > 2 else ""),
        "{{USP_3_DESC}}":  esc(usp_descs[2]  if len(usp_descs)  > 2 else ""),
        "{{USP_4_TITLE}}": esc(usp_titles[3] if len(usp_titles) > 3 else ""),
        "{{USP_4_DESC}}":  esc(usp_descs[3]  if len(usp_descs)  > 3 else ""),
        # USP raw strings for lists
        "{{USP_1_RAW}}": esc(usps[0] if len(usps) > 0 else ""),
        "{{USP_2_RAW}}": esc(usps[1] if len(usps) > 1 else ""),
        "{{USP_3_RAW}}": esc(usps[2] if len(usps) > 2 else ""),
        "{{USP_4_RAW}}": esc(usps[3] if len(usps) > 3 else ""),
        # Meta
        "{{GENERATOR}}": "BrandForge AI",
    }
    return tokens


def _inject_tokens(html: str, tokens: dict) -> str:
    for token, value in tokens.items():
        html = html.replace(token, str(value or ""))
    return html


# ── Playwright rendering ──────────────────────────────────────────────────────

async def render_html_to_pdf(html_content: str, output_path: Path) -> None:
    """Render HTML to A4 PDF using Playwright Chromium."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            args=["--no-sandbox", "--disable-setuid-sandbox",
                  "--disable-dev-shm-usage"]
        )
        page = await browser.new_page()

        await page.set_content(html_content, wait_until="networkidle")

        # Wait for Google Fonts to load
        try:
            await page.wait_for_function(
                "document.fonts.ready.then(() => true)",
                timeout=8000
            )
        except Exception:
            pass  # Proceed even if font wait times out

        # Additional wait for any CSS animations/transitions
        await asyncio.sleep(0.5)

        await page.pdf(
            path=str(output_path),
            format="A4",
            print_background=True,
            margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
        )
        await browser.close()


async def render_html_to_png(html_content: str, output_path: Path,
                              width: int = 1080, height: int = 1080) -> None:
    """Render HTML to PNG screenshot using Playwright Chromium."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            args=["--no-sandbox", "--disable-setuid-sandbox",
                  "--disable-dev-shm-usage"]
        )
        page = await browser.new_page(
            viewport={"width": width, "height": height},
        )

        await page.set_content(html_content, wait_until="networkidle")

        try:
            await page.wait_for_function(
                "document.fonts.ready.then(() => true)",
                timeout=8000
            )
        except Exception:
            pass

        await asyncio.sleep(0.5)

        await page.screenshot(
            path=str(output_path),
            full_page=False,
            type="png",
            clip={"x": 0, "y": 0, "width": width, "height": height},
        )
        await browser.close()


# ── Main render functions ─────────────────────────────────────────────────────

async def render_flyer(state: dict, output_dir: Path) -> str:
    """
    Render flyer PDF using HTML → Playwright PDF.
    Falls back to ReportLab if Playwright fails.
    """
    output_path = output_dir / "flyer.pdf"
    tokens      = _build_token_map(state)
    template    = select_flyer_template(state)
    tpl_path    = Path("assets/flyer_templates") / template

    if not tpl_path.exists():
        tpl_path = Path(__file__).resolve().parents[2] / "assets" / "flyer_templates" / template

    if not tpl_path.exists():
        print(f"[renderer] Template not found: {template}, using fallback")
        from pipeline.nodes.asset_generator import _render_flyer_reportlab, get_colors, get_copy
        colors = get_colors(state)
        copy   = get_copy(state)
        _render_flyer_reportlab(state, colors, copy, output_path)
        return str(output_path)

    html = tpl_path.read_text(encoding="utf-8")
    html = _inject_tokens(html, tokens)

    try:
        await render_html_to_pdf(html, output_path)
        print(f"[renderer] [OK] Flyer PDF: {output_path} ({template})")
    except Exception as e:
        print(f"[renderer] Playwright PDF failed: {e} — using ReportLab")
        from pipeline.nodes.asset_generator import _render_flyer_reportlab, get_colors, get_copy
        colors = get_colors(state)
        copy   = get_copy(state)
        _render_flyer_reportlab(state, colors, copy, output_path)

    return str(output_path)


async def render_social_card(state: dict, output_dir: Path) -> str:
    """
    Render social card PNG using HTML → Playwright screenshot.
    Falls back to Pillow if Playwright fails.
    """
    output_path = output_dir / "social_card.png"
    tokens      = _build_token_map(state)
    template    = select_social_template(state)
    tpl_path    = Path("assets/social_templates") / template

    if not tpl_path.exists():
        tpl_path = Path(__file__).resolve().parents[2] / "assets" / "social_templates" / template

    if not tpl_path.exists():
        print(f"[renderer] Social template not found: {template}, using Pillow")
        from pipeline.nodes.asset_generator import generate_social_card, get_colors, get_copy
        colors = get_colors(state)
        copy   = get_copy(state)
        return generate_social_card(state, colors, copy, output_dir)

    html = tpl_path.read_text(encoding="utf-8")
    html = _inject_tokens(html, tokens)

    try:
        await render_html_to_png(html, output_path, 1080, 1080)
        print(f"[renderer] [OK] Social card PNG: {output_path} ({template})")
    except Exception as e:
        print(f"[renderer] Playwright PNG failed: {e} — using Pillow")
        from pipeline.nodes.asset_generator import generate_social_card, get_colors, get_copy
        colors = get_colors(state)
        copy   = get_copy(state)
        return generate_social_card(state, colors, copy, output_dir)

    return str(output_path)
