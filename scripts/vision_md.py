#!/opt/hw-py/bin/python
"""Render the concept gallery, in markdown that every viewer can actually read.

Two problems this solves, both of which have already cost us a review cycle.

`vision-board` writes its gallery over `docs/design/vision.md`, which is the
hand-written narrative — it has clobbered it twice.  So the tool is pointed at
`docs/design/vision-gallery.md`, which it owns outright, and the narrative
includes it by reference.

The generated gallery wraps each line drawing in a raw `<details>` block.
GitHub renders that; `review-artifact` escapes it, so the published review page
showed literal `<details><summary>` tags to the customer.  Markdown that only
renders in one of the two places it is read is not markdown we can use, so the
block is flattened to a plain link here.

    vision-md                # render and flatten
    vision-md --check        # verify the gallery carries no raw HTML
"""
from __future__ import annotations

import argparse
import glob
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from md_flatten import flatten, raw_html  # noqa: E402

GALLERY = "docs/design/vision-gallery.md"
OUT = "docs/design/vision"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    if not args.check:
        concepts = sorted(glob.glob("concepts/*.py"))
        concepts = [c for c in concepts if not c.endswith("_common.py")]
        if not concepts:
            sys.stderr.write("no concepts in concepts/\n")
            return 1
        r = subprocess.run(["vision-board", *concepts, "--out", OUT,
                            "--doc", GALLERY],
                           capture_output=True, text=True)
        sys.stdout.write(r.stdout)
        if r.returncode:
            sys.stderr.write(r.stderr)
            return r.returncode
        with open(GALLERY) as fh:
            text = fh.read()
        with open(GALLERY, "w") as fh:
            fh.write(flatten(text))
        print(f"flattened raw HTML in {GALLERY}")

    with open(GALLERY) as fh:
        left = raw_html(fh.read())
    if left:
        sys.stderr.write(f"{GALLERY} still carries raw HTML: "
                         + ", ".join(sorted(set(left))[:8]) + "\n")
        return 1
    print(f"{GALLERY}: no raw HTML")
    return 0


if __name__ == "__main__":
    sys.exit(main())
