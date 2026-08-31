#!/opt/hw-py/bin/python
"""Derive per-subsystem block-diagram sheets from the one master spec.

`hw/block-diagram.yaml` stays the single source of truth: it carries the whole
power tree, so it is what `block-diagram --check` gates and what the power
budget is computed from.  Thirty-six blocks and twenty-three buses do not fit
one readable sheet, though, so this script slices that master into four
subsystem views for people to actually read.

Every block carries a `sheet:` tag.  For each sheet we emit a spec holding the
blocks tagged with it, plus a stub connector for every bus endpoint that lives
on another sheet, so a signal leaving the sheet is still visible and says where
it goes.  Rails are carried through when something on the sheet draws from them.

Also checks what `block-diagram --check` does not: that no two block boxes
overlap in the rendered layout.  Rev C shipped eight overlapping pairs and the
gate passed, because the generator honours stale hand positions out of the
.drawio without testing them for collisions.

    block-sheets            # write the sheet specs and SVGs
    block-sheets --check    # verify only; non-zero if a sheet is unreadable
"""
from __future__ import annotations

import argparse
import itertools
import os
import sys

import yaml

PLUGIN = os.path.expanduser(
    "~/.claude/plugins/cache/makehardware/makehardware/0.2.0/scripts")
sys.path.insert(0, PLUGIN)
import block_diagram as bd  # noqa: E402

MASTER = "hw/block-diagram.yaml"
SPEC_DIR = "hw/sheets"
OUT_DIR = "docs/design"

TITLES = {
    "dock": "Dock converter — 48 V Leviathan pack to the 400 V link",
    "tx":   "Transmitter — 400 V link to the coil, and the TX control island",
    "rx":   "Receiver — coil to the 400 V vehicle link, and in-band comms",
    "veh":  "Vehicle converter — 400 V link to the 48 V Mako pack",
}
ORDER = ["dock", "tx", "rx", "veh"]


def overlapping(model: dict) -> list[tuple[str, str]]:
    """Pairs of block boxes whose rectangles intersect."""
    ns = list(model["nodes"].values())
    return [(a["id"], b["id"]) for a, b in itertools.combinations(ns, 2)
            if a["x"] < b["x"] + b["w"] and b["x"] < a["x"] + a["w"]
            and a["y"] < b["y"] + b["h"] and b["y"] < a["y"] + a["h"]]


def slice_sheet(spec: dict, sheet: str) -> dict:
    blocks = [b for b in spec["blocks"] if b.get("sheet") == sheet]
    on = {b["id"] for b in blocks}
    sheet_of = {b["id"]: b.get("sheet") for b in spec["blocks"]}

    # Buses: keep any that touch this sheet; an endpoint elsewhere becomes a
    # stub so the reader can see the signal leaves and where it lands.
    buses, stubs = [], {}
    for bus in spec.get("buses") or []:
        nodes = bd.bus_nodes(bus)
        if not (on & set(nodes)):
            continue
        mapped = []
        for n in nodes:
            if n in on:
                mapped.append(n)
                continue
            other = sheet_of.get(n)
            sid = f"X_{other}"
            stubs.setdefault(sid, {
                "id": sid,
                "name": f"to {other} sheet",
                "kind": "connector",
                "part": f"see block-diagram-{other}.svg",
                "notes": "",
            })
            names = stubs[sid]["notes"].split(", ") if stubs[sid]["notes"] else []
            if n not in names:
                names.append(n)
            stubs[sid]["notes"] = ", ".join(names)
            mapped.append(sid)
        seen, uniq = set(), []
        for n in mapped:
            if n not in seen:
                seen.add(n)
                uniq.append(n)
        if len(uniq) < 2:
            continue
        nb = {k: v for k, v in bus.items()
              if k not in ("between", "controller", "members")}
        if bus.get("controller") and bus["controller"] in on:
            nb["controller"] = bus["controller"]
            nb["members"] = [n for n in uniq if n != bus["controller"]]
        else:
            nb["between"] = uniq
        buses.append(nb)

    for s in stubs.values():
        s["notes"] = "off-sheet endpoint of: " + s["notes"]

    allb = blocks + list(stubs.values())
    bids = {b["id"] for b in allb}

    # Rails: those anything on the sheet draws from, and their ancestors so the
    # tree still reads.  A rail sourced off-sheet keeps its voltage and budget
    # but loses `source`, which would otherwise name a block that is not here.
    want = {ld["rail"] for b in allb for ld in (b.get("powered_by") or [])}
    by_id = {r["id"]: r for r in spec.get("rails") or []}
    grown = True
    while grown:
        grown = False
        for rid in list(want):
            parent = (by_id.get(rid) or {}).get("from")
            if parent and parent not in want:
                want.add(parent)
                grown = True
    rails = []
    for r in spec.get("rails") or []:
        if r["id"] not in want:
            continue
        nr = dict(r)
        if nr.get("source") and nr["source"] not in bids:
            nr["notes"] = ((nr.get("notes", "") + " ") if nr.get("notes") else "") \
                + f"(sourced by {nr['source']} on the {sheet_of.get(nr['source'])} sheet)"
            nr.pop("source")
        rails.append(nr)

    return {
        "project": f"{spec['project']} — {TITLES[sheet]}",
        "revision": spec.get("revision", ""),
        "rails": rails,
        "blocks": allb,
        "buses": buses,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="verify only; write nothing")
    args = ap.parse_args()

    master = bd.load(MASTER)
    untagged = [b["id"] for b in master["blocks"] if not b.get("sheet")]
    if untagged:
        sys.stderr.write("blocks with no sheet: " + ", ".join(untagged) + "\n")
        return 1

    bad = 0
    mm = bd.layout(master, {})
    ov = overlapping(mm)
    if ov:
        bad += 1
        sys.stderr.write(f"master: {len(ov)} overlapping block pairs: "
                         + ", ".join(f"{a}/{b}" for a, b in ov[:8]) + "\n")
    else:
        print(f"master: {len(master['blocks'])} blocks, no overlaps "
              f"({mm['width']}x{mm['height']})")

    if not args.check:
        os.makedirs(SPEC_DIR, exist_ok=True)

    for sheet in ORDER:
        spec = slice_sheet(master, sheet)
        errors, _ = bd.validate(spec)
        if errors:
            bad += 1
            sys.stderr.write(f"{sheet}: invalid\n")
            for e in errors:
                sys.stderr.write(f"  - {e}\n")
            continue

        model = bd.layout(spec, {})
        ov = overlapping(model)
        n_real = sum(1 for b in spec["blocks"] if not b["id"].startswith("X_"))
        if ov:
            bad += 1
            sys.stderr.write(f"{sheet}: {len(ov)} overlapping block pairs: "
                             + ", ".join(f"{a}/{b}" for a, b in ov) + "\n")
        else:
            print(f"{sheet}: {n_real} blocks + "
                  f"{len(spec['blocks']) - n_real} off-sheet stubs, "
                  f"{len(spec['buses'])} buses, no overlaps "
                  f"({model['width']}x{model['height']})")

        if args.check:
            continue

        with open(f"{SPEC_DIR}/block-diagram-{sheet}.yaml", "w") as fh:
            fh.write("# GENERATED from hw/block-diagram.yaml by scripts/"
                     "block_sheets.py — edit the master, not this file.\n")
            yaml.safe_dump(spec, fh, sort_keys=False, width=88,
                           default_flow_style=False, allow_unicode=True)
        with open(f"{OUT_DIR}/block-diagram-{sheet}.svg", "w") as fh:
            fh.write(bd.render_svg(model, bd.budget(spec)))
        print(f"  wrote {OUT_DIR}/block-diagram-{sheet}.svg")

    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
