#!/usr/bin/env python3
"""Check local documentation/media targets and the generated guide contract."""
from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]


class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.values = []
    def handle_starttag(self, tag, attrs):
        self.values.extend(value for key, value in attrs if key in {"href", "src"} and value)


def check():
    missing = []
    for path in [*ROOT.glob("*.md"), *ROOT.glob("docs/*.md"), *ROOT.glob("examples/**/*.md")]:
        for target in re.findall(r"\]\(([^)\s]+)\)", path.read_text()):
            target = target.split("#", 1)[0]
            if target and "://" not in target and not (path.parent / unquote(target)).exists():
                missing.append((str(path.relative_to(ROOT)), target))
    guide = ROOT / "START-HERE.html"
    parser = Links(); parser.feed(guide.read_text())
    for target in parser.values:
        if target and "://" not in target and not target.startswith("#") and not (ROOT / unquote(target)).exists():
            missing.append((guide.name, target))
    assert not missing, missing
    assert "@@DATA@@" not in guide.read_text()
    print("Local documentation, gallery and download-pack links verified.")


if __name__ == "__main__": check()
