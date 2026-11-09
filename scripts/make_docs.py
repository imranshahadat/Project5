"""Convert docs/ARCHITECTURE.md directly to PDF using WeasyPrint."""

import sys
from pathlib import Path
import markdown

try:
    from weasyprint import HTML
except ImportError:
    print("❌ Error: weasyprint is required for PDF generation.")
    print("👉 Please run: pip install weasyprint")
    sys.exit(1)

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "ARCHITECTURE.md"

STYLE = """
@page {
    size: A4;
    margin: 18mm;
    @bottom-right {
        content: counter(page);
        font-size: 10px;
        color: #888;
    }
}
body {
    font-family: 'Segoe UI', Roboto, sans-serif;
    max-width: 800px;
    margin: 40px auto;
    line-height: 1.6;
    color: #222;
    font-size: 14px;
}
h1 {
    border-bottom: 3px solid #2563eb;
    padding-bottom: 8px;
    color: #1e3a8a;
}
h2 {
    border-bottom: 1px solid #ddd;
    padding-bottom: 5px;
    margin-top: 36px;
    color: #1e3a8a;
}
pre {
    background: #f6f8fa;
    padding: 12px;
    border-radius: 6px;
    overflow-x: auto;
    font-size: 12px;
    page-break-inside: avoid;
    border: 1px solid #e5e7eb;
}
code {
    background: #f6f8fa;
    padding: 2px 4px;
    border-radius: 3px;
    font-size: 12px;
}
table {
    border-collapse: collapse;
    width: 100%;
    margin: 14px 0;
    page-break-inside: avoid;
}
th, td {
    border: 1px solid #d1d5db;
    padding: 6px 10px;
    text-align: left;
}
th {
    background: #eff6ff;
}
blockquote {
    color: #555;
    border-left: 4px solid #93c5fd;
    margin-left: 0;
    padding-left: 12px;
}
"""


def build_html() -> str:
    """Read the markdown file and wrap it with embedded CSS styling."""
    if not DOC.exists():
        print(f"❌ Error: Could not find documentation source file at: {DOC}")
        sys.exit(1)

    md_content = DOC.read_text(encoding="utf-8")
    body_content = markdown.markdown(md_content, extensions=["fenced_code", "tables"])

    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>{STYLE}</style>
</head>
<body>
    {body_content}
</body>
</html>"""


def main() -> None:
    html_content = build_html()
    out_pdf = DOC.with_suffix(".pdf")

    print("⏳ Generating PDF...")
    HTML(string=html_content, base_url=str(ROOT)).write_pdf(out_pdf)
    print(f"✅ Successfully wrote PDF to: {out_pdf}")


if __name__ == "__main__":
    main()
