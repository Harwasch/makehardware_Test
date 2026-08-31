#!/opt/hw-py/bin/python
"""Flatten raw HTML out of generated markdown, and check that none is left.

`vision-board` and `review-gate` both wrap sections in `<details><summary>`.
GitHub renders that.  `review-artifact` escapes it, so the published review page
showed the customer literal `<details><summary>Dimensioned isometric line
drawing</summary>` where a drawing should have been.

Markdown that renders in only one of the two places a document is read is not
usable, and both generators overwrite their output, so hand-editing the files
does not survive.  This runs after them instead.

    md-flatten docs/review/*.md      # flatten in place
    md-flatten --check docs/**/*.md  # exit 1 if raw HTML remains
"""
from __future__ import annotations

import argparse
import re
import sys

# <details><summary>CAP</summary> ... </details>  ->  **CAP** + the body
_BLOCK = re.compile(
    r'^<details>\s*<summary>(?P<cap>.*?)</summary>\s*$\n'
    r'(?P<body>.*?)'
    r'^</details>\s*$\n?',
    re.M | re.S)

# A body that is nothing but one image becomes a link rather than a heading.
_ONLY_IMG = re.compile(r'^\s*!\[(?P<alt>[^\]]*)\]\((?P<src>[^)]+)\)\s*$', re.S)

# Tags we accept: <sub>/<sup> render as text everywhere that matters.
_OK = ('sub', 'sup', 'br')


def flatten(text: str) -> str:
    def sub(m: re.Match) -> str:
        cap, body = m.group("cap").strip(), m.group("body")
        img = _ONLY_IMG.match(body)
        if img:
            return f'[{cap} →]({img.group("src")})\n'
        return f'**{cap}**\n\n{body.lstrip(chr(10))}'
    prev = None
    while prev != text:                      # nested blocks
        prev, text = text, _BLOCK.sub(sub, text)
    return text


def strip_code(text: str) -> str:
    """Drop fenced blocks and inline code — angle brackets there are literal."""
    text = re.sub(r'^```.*?^```', '', text, flags=re.M | re.S)
    return re.sub(r'`[^`\n]*`', '', text)


def raw_html(text: str) -> list[str]:
    tags = re.findall(r'</?([a-zA-Z][a-zA-Z0-9]*)[^>\n]*>', strip_code(text))
    return sorted({t for t in tags if t.lower() not in _OK})


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--check", action="store_true",
                    help="report only; change nothing")
    args = ap.parse_args()

    bad = 0
    for path in args.files:
        try:
            with open(path) as fh:
                text = fh.read()
        except OSError as exc:
            sys.stderr.write(f"{path}: {exc}\n")
            bad += 1
            continue
        new = text if args.check else flatten(text)
        if new != text:
            with open(path, "w") as fh:
                fh.write(new)
            print(f"flattened {path}")
        left = raw_html(new)
        if left:
            bad += 1
            sys.stderr.write(f"{path}: raw HTML remains: "
                             + ", ".join(f"<{t}>" for t in left) + "\n")
    if not bad:
        print(f"{len(args.files)} file(s): no raw HTML")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
