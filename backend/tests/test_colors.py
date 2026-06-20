import sys
from pipeline.nodes.brand_extractor import extract_colors_from_html

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def test_extract_colors():
    html_snippet = """
    <html>
    <head>
        <style>
            body { background-color: #f59e0b; color: #111111; border: 1px solid #FFF; }
            .accent { color: #f59e0b; }
            .secondary { background: #2a2a2a; }
            .dark { color: #000; background: #ffffff; }
        </style>
    </head>
    <body>
        <div style="background-color: #f59e0b; color: #111; border-color: #2a2a2a;">Test</div>
    </body>
    </html>
    """
    colors = extract_colors_from_html(html_snippet)
    print("Extracted Colors:", colors)
    assert "#f59e0b" in colors
    assert "#111111" in colors
    assert "#2a2a2a" in colors
    assert "#ffffff" not in colors
    assert "#000000" not in colors
    print("✅ Color extraction test passed!")

if __name__ == "__main__":
    test_extract_colors()
