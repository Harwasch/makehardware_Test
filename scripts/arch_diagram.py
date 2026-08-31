#!/opt/hw-py/bin/python
"""Render the architecture sheets: modular, left to right, no wire over a block.

`block-diagram` lays every block out on a three-column grid with a heuristic
that put eight of the dock sheet's ten blocks in column one, routed buses
straight through boxes, and drew the dual active bridge twice because the master
spec contains it twice.  None of that is fixable from the spec side, so the
views are drawn here instead.

The content still comes from `hw/block-diagram.yaml` — parts, kinds, rails — and
that file is still what `block-diagram --check` gates and what the power budget
is computed from.  `hw/architecture.yaml` adds only layout: which sheet, which
stage of the power path, which row, and which pairs of blocks are two instances
of one design.

Layout is a stage grid: stages are columns running left to right in the
direction power flows, rows within a stage are free.  Every wire leaves the
right edge of its source, turns in the gutter between two stages, and enters the
left edge of its target, so a wire is never over a box.  Links that span more
than one stage drop to a highway band under the blocks rather than cutting
across the stages between.

    arch-diagram            # write docs/design/arch-*.svg
    arch-diagram --check    # verify only; non-zero if a sheet is malformed
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict

import yaml

PLUGIN = os.path.expanduser(
    "~/.claude/plugins/cache/makehardware/makehardware/0.2.0/scripts")
sys.path.insert(0, PLUGIN)
import block_diagram as bd  # noqa: E402

MASTER = "hw/block-diagram.yaml"
VIEWS = "hw/architecture.yaml"
OUT = "docs/design"

# ---- the house visual language, matched to block_diagram.py ---------------
BOX_W, BOX_H = 190, 62
GUTTER = 106                    # between stage columns — wires and labels live here
ROW_PITCH = 84
PAD = 24
HEAD = 98
LANE = 15                       # spacing between parallel wires in a gutter
PORT = 13                       # spacing between ports on a box edge

INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
RULE, RULE_SOFT = "#c3c2b7", "#e4e2dc"
GROUND, PANEL, SUNK = "#fcfcfb", "#ffffff", "#f4f3f0"

KIND_COLOUR = {
    "swd": "#2a78d6", "analog": "#d03b3b", "uart": "#e08a1e",
    "power": "#0b0b0b", "other": "#52514e",
}
RAIL_COLOUR = {
    "V48_LEV": "#d03b3b", "V48_MAKO": "#e08a1e", "HV400": "#e08a1e",
    "HVDC": "#d03b3b", "TX12": "#0ca30c", "VEH12": "#0ca30c",
    "DOCK12": "#8b5cf6", "TX3V3": "#2a78d6", "VEH3V3": "#0f9b8e",
    "DOCK3V3": "#0f9b8e",
}


def esc(s) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def clip(s: str, n: int) -> str:
    s = str(s)
    return s if len(s) <= n else s[:n - 1].rstrip() + "…"


# ---------------------------------------------------------------------------
# Build the node list for a sheet
# ---------------------------------------------------------------------------
def build(sheet: dict, master: dict, views: dict) -> tuple[list[dict], list[dict]]:
    blocks = {b["id"]: b for b in master["blocks"]}
    nodes: list[dict] = []
    links: list[dict] = []

    if sheet.get("from_module"):
        mod = views["modules"][sheet["from_module"]]
        for r in mod["roles"]:
            a, b = r["pair"]
            ba, bb = blocks[a], blocks[b]
            nodes.append({
                "id": r["role"],
                "tag": f"{a} / {b}",
                "name": generic(ba["name"], bb["name"]),
                "part": ba.get("part", ""),
                "kind": ba.get("kind", "other"),
                "rails": rails_of(ba),
                "stage": r["stage"], "row": r["row"],
            })
        for u in mod.get("unpaired") or []:
            bu = blocks[u["id"]]
            nodes.append({
                "id": u["id"], "tag": u["id"], "name": bu["name"],
                "part": bu.get("part", ""), "kind": bu.get("kind", "other"),
                "rails": rails_of(bu), "stage": u["stage"], "row": u["row"],
                "foot": u.get("note", ""),
            })
        links = [dict(lk) for lk in mod.get("links") or []]
        return nodes, links

    for n in sheet.get("nodes") or []:
        ref = n.get("ref")
        if ref in ("module", "group", "gap"):
            nodes.append({
                "id": n["id"], "tag": n["id"], "name": n["name"],
                "part": n.get("part", ""), "kind": n.get("kind", "other"),
                "rails": [], "stage": n["stage"], "row": n["row"],
                "big": True, "gap": ref == "gap",
            })
        else:
            b = blocks[n["id"]]
            nodes.append({
                "id": n["id"], "tag": n["id"], "name": b["name"],
                "part": b.get("part", ""), "kind": b.get("kind", "other"),
                "rails": rails_of(b), "stage": n["stage"], "row": n["row"],
            })
    for p in sheet.get("edge_ports") or []:
        nodes.append({
            "id": p["id"], "tag": "", "name": p["name"], "part": p.get("part", ""),
            "kind": "other", "rails": [], "stage": p["stage"], "row": p["row"],
            "port": True,
        })
    links = list(sheet.get("links") or [])
    return nodes, links


def rails_of(b: dict) -> list[str]:
    return [ld["rail"] for ld in (b.get("powered_by") or [])]


def strip_inst(bus_id: str) -> str:
    for p in ("PWR_DOCK_", "PWR_DAB_", "DOCK_", "HVLV_"):
        if bus_id.startswith(p):
            return bus_id[len(p):]
    return bus_id


def generic(a: str, b: str) -> str:
    """The role name both instances share, e.g. 'Dock DAB LV bridge 16x' +
    'HVLV LV bridge 16x' -> 'LV bridge 16x'."""
    aw, bw = a.split(), b.split()
    while aw and bw and aw[0] != bw[0]:
        if len(aw) > len(bw):
            aw.pop(0)
        else:
            bw.pop(0)
    tail = []
    for x, y in zip(aw, bw):
        if x != y:
            break
        tail.append(x)
    return " ".join(tail) or a


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------
def place(nodes: list[dict]) -> None:
    for n in nodes:
        n["w"] = BOX_W
        n["h"] = BOX_H if not n.get("port") else 40
        n["x"] = PAD + n["stage"] * (BOX_W + GUTTER)
        n["y"] = HEAD + n["row"] * ROW_PITCH


def route(nodes: list[dict], links: list[dict]) -> tuple[list[dict], float]:
    """Orthogonal routes that never cross a box.

    Every vertical run happens in a gutter between two stage columns, which is
    empty by construction, or directly between two boxes stacked in the same
    column with nothing between them.  Only links spanning more than one stage
    drop to a highway band under the diagram.
    """
    by_id = {n["id"]: n for n in nodes}
    occupied = {(n["stage"], n["row"]) for n in nodes}
    bottom = max(n["y"] + n["h"] for n in nodes)
    highway0 = bottom + 30

    out_n: dict[str, int] = defaultdict(int)
    in_n: dict[str, int] = defaultdict(int)
    for lk in links:
        out_n[lk["from"]] += 1
        in_n[lk["to"]] += 1
    out_i: dict[str, int] = defaultdict(int)
    in_i: dict[str, int] = defaultdict(int)

    gut_lane: dict[int, int] = defaultdict(int)
    hi_lane = 0
    routes = []
    for lk in links:
        a, b = by_id[lk["from"]], by_id[lk["to"]]
        ia, ib = out_i[a["id"]], in_i[b["id"]]
        out_i[a["id"]] += 1
        in_i[b["id"]] += 1
        ya = edge_y(a, ia, out_n[a["id"]])
        yb = edge_y(b, ib, in_n[b["id"]])
        span = b["stage"] - a["stage"]
        arrow = "left"

        if span == 1:                                  # forward one stage
            mx = gutter_x(a["stage"], gut_lane)
            pts = [(a["x"] + a["w"], ya), (mx, ya), (mx, yb), (b["x"], yb)]
            anchor = ((a["x"] + a["w"] + b["x"]) / 2, min(ya, yb) - 7, "mid")

        elif span == -1:                               # feedback one stage
            mx = gutter_x(b["stage"], gut_lane)
            pts = [(a["x"], ya), (mx, ya), (mx, yb), (b["x"] + b["w"], yb)]
            arrow = "right"
            anchor = ((a["x"] + b["x"] + b["w"]) / 2, min(ya, yb) - 7, "mid")

        elif span == 0:
            step = 1 if b["row"] > a["row"] else -1
            between = [(a["stage"], r) for r in
                       range(a["row"] + step, b["row"], step)]
            cx = a["x"] + a["w"] / 2
            if not any(c in occupied for c in between):
                # nothing in the way: straight down (or up) the column
                if step > 0:
                    pts = [(cx, a["y"] + a["h"]), (cx, b["y"])]
                    arrow = "down"
                    anchor = (cx + 6, (a["y"] + a["h"] + b["y"]) / 2 + 3, "start")
                else:
                    pts = [(cx, a["y"]), (cx, b["y"] + b["h"])]
                    arrow = "up"
                    anchor = (cx + 6, (a["y"] + b["y"] + b["h"]) / 2 + 3, "start")
            else:
                mx = gutter_x(a["stage"], gut_lane)
                pts = [(a["x"] + a["w"], ya), (mx, ya), (mx, yb),
                       (b["x"] + b["w"], yb)]
                arrow = "right"
                anchor = (mx + 6, (ya + yb) / 2 + 3, "start")

        else:                                          # long haul
            hy = highway0 + hi_lane * LANE
            hi_lane += 1
            ax = a["x"] + a["w"] if span > 0 else a["x"]
            gx = gutter_x(a["stage"] if span > 0 else a["stage"] - 1, gut_lane)
            bx = b["x"] if span > 0 else b["x"] + b["w"]
            hx = gutter_x(b["stage"] - 1 if span > 0 else b["stage"], gut_lane)
            pts = [(ax, ya), (gx, ya), (gx, hy), (hx, hy), (hx, yb), (bx, yb)]
            arrow = "left" if span > 0 else "right"
            anchor = ((gx + hx) / 2, hy - 6, "mid")

        routes.append({"pts": pts, "label": lk.get("label"),
                       "anchor": anchor,
                       "colour": KIND_COLOUR.get(lk.get("kind", "other"),
                                                 KIND_COLOUR["other"]),
                       "arrow": arrow})
    height = (highway0 + hi_lane * LANE + 38) if hi_lane else (bottom + 34)
    return routes, height


def crossings(nodes: list[dict], routes: list[dict]) -> list[tuple[str, str]]:
    """Wire segments that pass through a box. Should always be empty.

    This is the check `block-diagram --check` never had: it validated the spec
    and let a drawing through with buses routed straight over blocks. A segment
    touching a box edge is how a wire connects, so the box is inset by 4 px
    before testing.
    """
    bad = []
    for i, r in enumerate(routes):
        for p, q in zip(r["pts"], r["pts"][1:]):
            lo_x, hi_x = min(p[0], q[0]), max(p[0], q[0])
            lo_y, hi_y = min(p[1], q[1]), max(p[1], q[1])
            for n in nodes:
                bx, by = n["x"] + 4, n["y"] + 4
                bw, bh = n["w"] - 8, n["h"] - 8
                if lo_x < bx + bw and bx < hi_x and lo_y < by + bh and by < hi_y:
                    bad.append((r.get("label") or f"link {i}", n["id"]))
    return bad


def gutter_x(stage: int, lanes: dict[int, int]) -> float:
    """A free vertical lane in the gutter to the right of `stage`."""
    k = lanes[stage]
    lanes[stage] += 1
    return PAD + stage * (BOX_W + GUTTER) + BOX_W + 20 + k * LANE


def edge_y(n: dict, i: int, total: int) -> float:
    mid = n["y"] + n["h"] / 2
    if total <= 1:
        return mid
    off = (i - (total - 1) / 2) * min(PORT, (n["h"] - 16) / max(total - 1, 1))
    return mid + off


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------
def render(sheet: dict, nodes: list[dict], links: list[dict],
           views: dict, out: dict | None = None) -> str:
    place(nodes)
    routes, height = route(nodes, links)
    if out is not None:
        out["routes"] = routes
    width = PAD * 2 + max(n["x"] + n["w"] for n in nodes) - PAD
    stages = sheet.get("stages") or []
    width = max(width, PAD * 2 + len(stages) * (BOX_W + GUTTER))

    o: list[str] = []
    a = o.append
    a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" '
      f'height="{height:.0f}" viewBox="0 0 {width:.0f} {height:.0f}" '
      f'font-family="ui-sans-serif,system-ui,-apple-system,\'Segoe UI\','
      f'Roboto,\'Helvetica Neue\',Arial,sans-serif" role="img" '
      f'aria-label="{esc(sheet["title"])}">')
    a(f'<style>.s{{fill:{GROUND}}} .bx{{fill:{PANEL};stroke:{RULE}}} '
      f'.ink{{fill:{INK}}} .ink2{{fill:{INK2}}} .mut{{fill:{MUTED}}} '
      f'.gt{{fill:{SUNK};stroke:{RULE_SOFT}}} '
      f'@media (prefers-color-scheme:dark){{.s{{fill:#1a1a19}} '
      f'.bx{{fill:#242422;stroke:#383835}} .ink{{fill:#fff}} '
      f'.ink2{{fill:#c3c2b7}} .gt{{fill:#1f1f1e;stroke:#2c2c2a}}}} '
      f'.t{{font-size:12px}} .tb{{font-size:12.5px;font-weight:600}} '
      f'.ts{{font-size:10px}} .h{{font-size:15px;font-weight:600}} '
      f'.hh{{font-size:10px;font-weight:600;letter-spacing:0.07em}}</style>')
    a(f'<rect width="{width:.0f}" height="{height:.0f}" class="s" rx="6"/>')
    a(f'<text x="{PAD}" y="27" class="h ink">{esc(sheet["title"])}</text>')
    a(f'<text x="{PAD}" y="46" class="t ink2">{esc(sheet.get("subtitle",""))}</text>')
    a(f'<text x="{PAD}" y="61" class="ts mut">generated from '
      f'hw/block-diagram.yaml + hw/architecture.yaml — edit those, not this file'
      f'</text>')

    # stage headers
    for i, s in enumerate(stages):
        x = PAD + i * (BOX_W + GUTTER)
        a(f'<text x="{x}" y="{HEAD - 12}" class="hh mut">{esc(s.upper())}</text>')

    # wires first, so boxes sit on top of any label
    for r in routes:
        d = " ".join(("M" if i == 0 else "L") + f"{px:.0f} {py:.0f}"
                     for i, (px, py) in enumerate(r["pts"]))
        a(f'<path d="{d}" fill="none" stroke="{r["colour"]}" stroke-width="1.4" '
          f'stroke-linejoin="round"/>')
        ex, ey = r["pts"][-1]
        dx, dy = {"left": (-6, 0), "right": (6, 0),
                  "down": (0, -6), "up": (0, 6)}[r["arrow"]]
        px, py = (3.5, 0) if dy else (0, 3.5)
        a(f'<path d="M{ex + dx - px:.0f} {ey + dy - py:.0f} '
          f'L{ex:.0f} {ey:.0f} '
          f'L{ex + dx + px:.0f} {ey + dy + py:.0f}" fill="{r["colour"]}"/>')

    # wire labels, anchored where the router knows there is clear space
    for r in routes:
        if not r["label"]:
            continue
        lx, ly, how = r["anchor"]
        txt = r["label"]
        wl = len(txt) * 5.3 + 6
        rx = lx - wl / 2 if how == "mid" else lx - 2
        a(f'<rect x="{rx:.0f}" y="{ly - 10:.0f}" width="{wl:.0f}" '
          f'height="13" class="s" rx="2"/>')
        a(f'<text x="{lx:.0f}" y="{ly:.0f}" class="ts mut"'
          + (' text-anchor="middle"' if how == "mid" else "")
          + f'>{esc(txt)}</text>')

    # boxes
    for n in nodes:
        x, y, w, h = n["x"], n["y"], n["w"], n["h"]
        cls = "gt" if n.get("gap") or n.get("port") else "bx"
        dash = ' stroke-dasharray="4 3"' if n.get("gap") or n.get("port") else ""
        a(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" class="{cls}" '
          f'rx="4"{dash}/>')
        head = f'{n["tag"]} · {n["name"]}' if n["tag"] else n["name"]
        a(f'<text x="{x + 10}" y="{y + 20}" class="tb ink">'
          f'{esc(clip(head, 30))}</text>')
        if n.get("part"):
            a(f'<text x="{x + 10}" y="{y + 35}" class="t ink2">'
              f'{esc(clip(n["part"], 32))}</text>')
        if n.get("foot"):
            a(f'<text x="{x + 10}" y="{y + 50}" class="ts mut">'
              f'{esc(clip(n["foot"], 34))}</text>')
        cx = x + 10
        for rail in n["rails"]:
            wc = 8 + len(rail) * 5.6
            a(f'<rect x="{cx:.0f}" y="{y + h - 19}" width="{wc:.0f}" height="14" '
              f'rx="7" fill="{RAIL_COLOUR.get(rail, MUTED)}"/>')
            a(f'<text x="{cx + wc / 2:.0f}" y="{y + h - 8}" class="ts" '
              f'fill="#fff" text-anchor="middle">{esc(rail)}</text>')
            cx += wc + 5

    a("</svg>")
    return "\n".join(o)


# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    master = bd.load(MASTER)
    with open(VIEWS) as fh:
        views = yaml.safe_load(fh)
    blocks = {b["id"] for b in master["blocks"]}

    bad = 0
    # The master's own generated sheet still carries the power budget, so it is
    # still rendered by `block-diagram` — check it does not collide, which
    # `block-diagram --check` does not do.
    import itertools
    mnodes = list(bd.layout(master, {})["nodes"].values())
    mov = [(x["id"], y["id"]) for x, y in itertools.combinations(mnodes, 2)
           if x["x"] < y["x"] + y["w"] and y["x"] < x["x"] + x["w"]
           and x["y"] < y["y"] + y["h"] and y["y"] < x["y"] + x["h"]]
    if mov:
        bad += 1
        sys.stderr.write(f"block-diagram.svg: {len(mov)} overlapping block "
                         f"pairs: " + ", ".join(f"{x}/{y}" for x, y in mov[:6])
                         + "\n")
    else:
        print(f"master   {len(mnodes)} blocks, no overlaps "
              f"(power budget sheet)")

    covered: set[str] = set()
    for sheet in views["sheets"]:
        nodes, links = build(sheet, master, views)
        ids = {n["id"] for n in nodes}
        for lk in links:
            for end in (lk["from"], lk["to"]):
                if end not in ids:
                    sys.stderr.write(f"{sheet['id']}: link end {end!r} is not "
                                     f"on the sheet\n")
                    bad += 1
        if sheet.get("from_module"):
            mod = views["modules"][sheet["from_module"]]
            for r in mod["roles"]:
                covered |= set(r["pair"])
            covered |= {u["id"] for u in mod.get("unpaired") or []}
        for n in sheet.get("nodes") or []:
            if n.get("ref") == "group":
                covered |= set(n["members"])
            elif not n.get("ref"):
                covered.add(n["id"])

        # no two boxes may share a cell
        cells: dict[tuple[int, int], str] = {}
        for n in nodes:
            key = (n["stage"], n["row"])
            if key in cells:
                sys.stderr.write(f"{sheet['id']}: {n['id']} and {cells[key]} "
                                 f"are both at stage {key[0]} row {key[1]}\n")
                bad += 1
            cells[key] = n["id"]

        laid: dict = {}
        svg = render(sheet, nodes, links, views, laid)
        import re as _re
        w, h = _re.search(r'width="(\d+)" height="(\d+)"', svg).groups()
        over = crossings(nodes, laid["routes"])
        if over:
            bad += 1
            sys.stderr.write(f"{sheet['id']}: {len(over)} wire(s) cross a box: "
                             + ", ".join(f"{a} over {b}" for a, b in over[:6])
                             + "\n")
        print(f"{sheet['id']:8} {len(nodes):2} boxes, {len(links):2} links, "
              f"{w}x{h}, {len(over)} wire/box crossings")
        if not args.check:
            path = f"{OUT}/arch-{sheet['id']}.svg"
            with open(path, "w") as fh:
                fh.write(svg)
            print(f"  wrote {path}")

    missing = blocks - covered
    if missing:
        sys.stderr.write("blocks on no sheet: " + ", ".join(sorted(missing)) + "\n")
        bad += 1
    unknown = covered - blocks
    if unknown:
        sys.stderr.write("sheets name blocks the master does not define: "
                         + ", ".join(sorted(unknown)) + "\n")
        bad += 1
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
