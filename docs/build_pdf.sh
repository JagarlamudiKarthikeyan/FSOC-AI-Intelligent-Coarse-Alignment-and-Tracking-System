#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
source ../venv/bin/activate

pip install -q markdown

python3 - <<'PY'
import markdown
import pathlib

src = pathlib.Path("manual.md").read_text(encoding="utf-8")
body = markdown.markdown(
    src,
    extensions=["tables", "fenced_code", "sane_lists", "toc"],
    extension_configs={"toc": {"title": "Table of Contents", "toc_depth": "1-2"}},
    output_format="html5",
)
html = (
    "<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
    "<title>FSOC Coarse Tracker Manual</title>"
    "<link rel='stylesheet' href='style.css'></head><body>"
    + body +
    "</body></html>"
)
pathlib.Path("manual.html").write_text(html, encoding="utf-8")
print("rendered manual.html")
PY

weasyprint manual.html manual.pdf

rm -f manual.html
echo "built docs/manual.pdf"