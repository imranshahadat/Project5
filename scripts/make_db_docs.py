"""Render src/docs/DATABASE_ARCHITECTURE.md -> DATABASE_ARCHITECTURE.html.

Self-contained HTML (CSS embedded, no external assets/CDN).
Run from Project4/:
    python scripts/make_db_docs.py

Needs:  pip install markdown pygments
"""

from datetime import datetime
from pathlib import Path

import markdown

BASE_DIR = Path(__file__).resolve().parents[1]
SRC = BASE_DIR / "src" / "docs" / "DATABASE_ARCHITECTURE.md"
OUT = BASE_DIR / "src" / "docs" / "DATABASE_ARCHITECTURE.html"

EXTENSIONS = ["fenced_code", "tables", "toc", "codehilite", "sane_lists"]
EXT_CONFIG = {"codehilite": {"guess_lang": False}}


def pygments_css() -> str:
    try:
        from pygments.formatters import HtmlFormatter

        return HtmlFormatter(style="default").get_style_defs(".codehilite")
    except ImportError:
        return ""


CSS = """
:root { --fg:#1f2328; --muted:#59636e; --bg:#fff; --code-bg:#f6f8fa;
        --border:#d1d9e0; --accent:#0969da; }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--fg);
  font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif; }
main { max-width: 920px; margin:0 auto; padding:48px 28px 24px; }
h1,h2,h3,h4 { line-height:1.25; margin:1.6em 0 .6em; font-weight:600; }
h1 { font-size:2em; margin-top:0; padding-bottom:.3em;
     border-bottom:1px solid var(--border); }
h2 { font-size:1.5em; padding-bottom:.3em; border-bottom:1px solid var(--border); }
h3 { font-size:1.2em; }
a { color:var(--accent); text-decoration:none; }
a:hover { text-decoration:underline; }
blockquote { margin:0 0 1em; padding:.4em 1em; color:var(--muted);
             border-left:.25em solid var(--border); }
code { font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
       font-size:.875em; background:var(--code-bg);
       padding:.2em .35em; border-radius:4px; }
pre { background:var(--code-bg); padding:14px 16px; border-radius:8px;
      overflow-x:auto; line-height:1.5; }
pre code { background:none; padding:0; font-size:.82em; }
table { border-collapse:collapse; margin:1em 0; width:100%; font-size:.92em;
        display:block; overflow-x:auto; }
th,td { border:1px solid var(--border); padding:6px 10px;
        text-align:left; vertical-align:top; }
th { background:var(--code-bg); font-weight:600; }
tr:nth-child(even) td { background:#fafbfc; }
footer { max-width:920px; margin:0 auto; padding:16px 28px 40px;
         color:var(--muted); font-size:.85em; }
"""

TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
__CSS__
</style>
</head>
<body>
<main>
__BODY__
</main>
<footer>Generated __STAMP__ from __SRCFILE__ — Project4 database layer</footer>
</body>
</html>
"""


def main() -> None:
    if not SRC.exists():
        raise SystemExit(f"not found: {SRC}")

    md_text = SRC.read_text(encoding="utf-8")
    body = markdown.markdown(
        md_text, extensions=EXTENSIONS, extension_configs=EXT_CONFIG
    )

    html = (
        TEMPLATE.replace("__TITLE__", "Project4 — Database Architecture")
        .replace("__CSS__", CSS + "\n" + pygments_css())
        .replace("__BODY__", body)
        .replace("__STAMP__", datetime.now().strftime("%Y-%m-%d %H:%M"))
        .replace("__SRCFILE__", SRC.name)
    )

    OUT.write_text(html, encoding="utf-8")
    print(f"✔ wrote {OUT} ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
