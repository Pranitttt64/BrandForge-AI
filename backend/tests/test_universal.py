"""
Universal asset generation test.
Run from backend/ with: python tests/test_universal.py
Tests color extraction against 5 brand archetypes.
"""
import sys
sys.path.insert(0, '.')

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from utils.colors import (
    extract_brand_colors, pick_panel_color, pick_cta_color,
    get_luminance, ensure_contrast, is_near_neutral
)


def test_color_extraction():
    print("\n═══ TEST: Color Extraction ═══")

    brands = {
        "Notion (monochrome)": {
            "html": "<style>body{background:#ffffff;color:#191919;} .border{border:1px solid #e9e9e7;} .gray{color:#787774;}</style>",
            "expect_bg_light": True,
            "expect_text_dark": True,
            "expect_no_gray_primary": True,
        },
        "Stripe (dark primary)": {
            "html": "<style>body{background:#ffffff;} .btn{background:#635bff;} .dark{background:#0a2540;} .text{color:#425466;}</style>",
            "expect_bg_light": True,
            "expect_primary_dark": True,
        },
        "Colorful brand": {
            "html": "<style>body{background:#fff3e0;color:#212121;} .primary{background:#ff6d00;} .secondary{background:#00897b;}</style>",
            "expect_mid_colors": True,
        },
        "Image-heavy (minimal CSS)": {
            "html": "<style>body{margin:0;padding:0;}</style>",
            "expect_fallback": True,
        },
        "Light pastel brand": {
            "html": "<style>body{background:#fdf6ff;color:#2d0044;} .btn{background:#7c3aed;} .light{color:#c4b5fd;}</style>",
            "expect_dark_text": True,
        },
    }

    all_passed = True
    for brand_name, config in brands.items():
        colors = extract_brand_colors(config["html"])
        print(f"\n  {brand_name}:")
        print(f"    bg={colors['background']} text={colors['text']}")
        print(f"    primary={colors['primary']} accent={colors['accent']}")

        # Check no near-neutral colors as primary
        if is_near_neutral(colors["primary"]):
            print(f"    ✗ FAIL: primary {colors['primary']} is near-neutral (gray)")
            all_passed = False
        else:
            print(f"    ✓ primary is not gray")

        # Check panel always has contrast
        panel_bg, panel_text = pick_panel_color(colors)
        contrast = abs(get_luminance(panel_bg) - get_luminance(panel_text))
        if contrast < 0.3:
            print(f"    ✗ FAIL: panel {panel_bg}/{panel_text} has low contrast ({contrast:.2f})")
            all_passed = False
        else:
            print(f"    ✓ panel contrast OK: {panel_bg}/{panel_text} ({contrast:.2f})")

        # Check CTA has contrast
        cta_bg, cta_text = pick_cta_color(colors, panel_bg)
        cta_contrast = abs(get_luminance(cta_bg) - get_luminance(cta_text))
        if cta_contrast < 0.3:
            print(f"    ✗ FAIL: CTA {cta_bg}/{cta_text} has low contrast ({cta_contrast:.2f})")
            all_passed = False
        else:
            print(f"    ✓ CTA contrast OK: {cta_bg}/{cta_text} ({cta_contrast:.2f})")

    print(f"\n{'✓ ALL COLOR TESTS PASSED' if all_passed else '✗ SOME TESTS FAILED'}\n")
    return all_passed


def test_no_gray_in_output():
    print("═══ TEST: No #cccccc in any output ═══")
    GRAY = "#cccccc"
    brands_html = {
        "notion": "<style>body{background:#ffffff;color:#191919;}</style>",
        "stripe": "<style>body{background:#fff;} .btn{background:#635bff;} .dark{background:#0a2540;}</style>",
    }
    for name, html in brands_html.items():
        colors = extract_brand_colors(html)
        panel_bg, panel_text = pick_panel_color(colors)
        cta_bg, cta_text = pick_cta_color(colors, panel_bg)
        all_colors = list(colors.values()) + [panel_bg, panel_text, cta_bg, cta_text]
        if GRAY in all_colors:
            print(f"  ✗ FAIL: {name} still has {GRAY} in output colors")
        else:
            print(f"  ✓ {name}: no gray in output")


if __name__ == "__main__":
    ok1 = test_color_extraction()
    test_no_gray_in_output()
    print("\nAll tests complete.")
    sys.exit(0 if ok1 else 1)
