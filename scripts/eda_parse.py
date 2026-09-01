#!/usr/bin/env python3
"""Parse EasyEDA Standard (v6) schematic JSON into components and a netlist.

EasyEDA stores a sheet as ``schematics[0].dataStr.shape`` -- a list of
``~``-delimited strings, one per graphical object.  The shapes that carry
electrical meaning are:

  LIB  component instance; ``#@$``-separated sub-shapes hold its pins and text
  W    wire polyline, ``W~x1 y1 x2 y2 ...``
  N    net label placed on a wire
  F    net flag / power port (GND, +15V, ...)
  J    junction dot
  O    no-connect marker

Connectivity is geometric: nothing in the file names a net.  This module
rebuilds it by unioning wire vertices, then attaching pins, labels and flags
to any wire segment that passes through their coordinate.

Usage:
    eda_parse.py <schematic.json> [--bom out.csv] [--netlist out.txt] [--json out.json]
"""
import argparse
import json
import sys
from collections import defaultdict

TOL = 0.02  # EasyEDA grid is 5 or 10 units; coordinates are exact to ~1e-6


# ---------------------------------------------------------------- loading

def load(path):
    """Return the list of sheet dataStr dicts in an EasyEDA export."""
    d = json.load(open(path, encoding="utf-8"))
    docs = d.get("schematics") or d.get("boards") or [d]
    out = []
    for s in docs:
        ds = s.get("dataStr", s)
        if isinstance(ds, str):
            ds = json.loads(ds)
        out.append(ds)
    return out


def kv(seg):
    """EasyEDA packs attributes as key`value`key`value`..."""
    parts = seg.split("`")
    return {parts[i]: parts[i + 1] for i in range(0, len(parts) - 1, 2)}


def _f(x):
    return round(float(x), 2)


def _pt(x, y):
    return (_f(x), _f(y))


# ---------------------------------------------------------------- shapes

def components(ds):
    """Component instances with designator, value, package and supplier data."""
    comps = []
    for sh in ds.get("shape", []):
        if not isinstance(sh, str) or not sh.startswith("LIB~"):
            continue
        blocks = sh.split("#@$")
        head = blocks[0].split("~")
        attrs = kv(head[3]) if len(head) > 3 else {}
        des = val = None
        pins = []
        for b in blocks[1:]:
            f = b.split("~")
            if b.startswith("T~") and len(f) > 12:
                if f[1] == "P":
                    des = f[12]
                elif f[1] == "N":
                    val = f[12]
            elif b.startswith("P~"):
                segs = b.split("^^")
                f = segs[0].split("~")
                num = f[3]
                x, y = _pt(f[4], f[5])
                name = ""
                if len(segs) > 3:
                    nf = segs[3].split("~")
                    if len(nf) > 4:
                        name = nf[4]
                pins.append({"num": num, "name": name, "x": x, "y": y})
        comps.append({
            "designator": des,
            "value": val,
            "package": attrs.get("package", ""),
            "mfr": attrs.get("Manufacturer", ""),
            "mfr_part": attrs.get("Manufacturer Part", ""),
            "lcsc": attrs.get("Supplier Part", ""),
            "pins": pins,
            "x": _f(head[1]) if len(head) > 2 else 0.0,
            "y": _f(head[2]) if len(head) > 2 else 0.0,
        })
    return comps


def wires(ds):
    """Wire polylines as lists of (x, y) vertices."""
    out = []
    for sh in ds.get("shape", []):
        if not isinstance(sh, str) or not sh.startswith("W~"):
            continue
        nums = sh.split("~")[1].split()
        pts = [_pt(nums[i], nums[i + 1]) for i in range(0, len(nums) - 1, 2)]
        if len(pts) >= 2:
            out.append(pts)
    return out


def labels(ds):
    """Net labels: (name, (x, y))."""
    out = []
    for sh in ds.get("shape", []):
        if not isinstance(sh, str) or not sh.startswith("N~"):
            continue
        f = sh.split("~")
        if len(f) > 5 and f[5]:
            out.append((f[5], _pt(f[1], f[2])))
    return out


def flags(ds):
    """Net flags / power ports: (name, (x, y))."""
    out = []
    for sh in ds.get("shape", []):
        if not isinstance(sh, str) or not sh.startswith("F~"):
            continue
        segs = sh.split("^^")
        head = segs[0].split("~")
        anchor = _pt(head[2], head[3])
        name = ""
        if len(segs) > 1:
            ap = segs[1].split("~")
            if len(ap) >= 2:
                anchor = _pt(ap[0], ap[1])
        if len(segs) > 2:
            name = segs[2].split("~")[0]
        if not name:
            name = head[1].replace("part_netLabel_", "")
        out.append((name, anchor))
    return out


def junctions(ds):
    return [_pt(sh.split("~")[1], sh.split("~")[2])
            for sh in ds.get("shape", [])
            if isinstance(sh, str) and sh.startswith("J~")]


def noconnects(ds):
    return [_pt(sh.split("~")[1], sh.split("~")[2])
            for sh in ds.get("shape", [])
            if isinstance(sh, str) and sh.startswith("O~")]


# ---------------------------------------------------------------- netlist

class DSU:
    def __init__(self):
        self.p = {}

    def find(self, a):
        self.p.setdefault(a, a)
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]
            a = self.p[a]
        return a

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[ra] = rb


def _on_segment(p, a, b):
    """True if p lies on segment a-b (inclusive) within TOL."""
    (px, py), (ax, ay), (bx, by) = p, a, b
    if not (min(ax, bx) - TOL <= px <= max(ax, bx) + TOL):
        return False
    if not (min(ay, by) - TOL <= py <= max(ay, by) + TOL):
        return False
    cross = (bx - ax) * (py - ay) - (by - ay) * (px - ax)
    length = max(((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5, 1e-9)
    return abs(cross) / length <= TOL


def build_netlist(ds):
    """Return (nets, unconnected) where nets maps name -> sorted node list.

    Connectivity is rebuilt geometrically.  The atoms are coordinates, so two
    objects that share a coordinate -- a pin under a power flag, two abutted
    pins, two wire endpoints -- are the same net without needing a wire
    between them.  Wires crossing mid-segment are only joined where the sheet
    carries a junction dot, which is what EasyEDA itself renders.

    A node is "REFDES.pin".  Pins carrying an explicit no-connect marker are
    left out of *unconnected* -- the designer said they are meant to float.
    """
    dsu = DSU()
    ws = wires(ds)

    # 1. all vertices of one wire are one net
    for pts in ws:
        for q in pts[1:]:
            dsu.union(pts[0], q)

    def touching(p):
        """Wire indices whose polyline passes through p (vertex or segment)."""
        hit = []
        for i, pts in enumerate(ws):
            for a, b in zip(pts, pts[1:]):
                if _on_segment(p, a, b):
                    hit.append(i)
                    break
        return hit

    # 2. a junction ties together every wire passing through it
    for jp in junctions(ds):
        ids = touching(jp)
        if ids:
            dsu.union(jp, ws[ids[0]][0])
            for j in ids[1:]:
                dsu.union(ws[ids[0]][0], ws[j][0])

    # 3. pins, labels and flags join any wire they sit on; coincident
    #    coordinates merge on their own because the atom is the coordinate
    comps = components(ds)
    nc = set(noconnects(ds))
    pin_nodes = {}
    for c in comps:
        for pin in c["pins"]:
            p = (pin["x"], pin["y"])
            ids = touching(p)
            if ids:
                dsu.union(p, ws[ids[0]][0])
            pin_nodes.setdefault(p, []).append(
                (c["designator"], pin["num"], pin["name"]))

    # 4. labels and flags name a net -- and, as in KiCad, every occurrence of
    #    the same name is the same net wherever it appears on the sheet
    placed = []
    for name, p in labels(ds) + flags(ds):
        ids = touching(p)
        if ids:
            dsu.union(p, ws[ids[0]][0])
        placed.append((name, p))

    by_name = defaultdict(list)
    for name, p in placed:
        by_name[name].append(p)
    for name, pts in by_name.items():
        for q in pts[1:]:
            dsu.union(pts[0], q)

    named = defaultdict(set)
    for name, p in placed:
        named[dsu.find(p)].add(name)

    # 5. collect
    groups = defaultdict(list)
    for p, members in pin_nodes.items():
        root = dsu.find(p)
        for des, num, pname in members:
            groups[root].append(f"{des}.{num}" + (f"({pname})" if pname else ""))

    nets, unconnected = {}, []
    anon = 0
    for root, members in groups.items():
        names = sorted(named.get(root, []))
        members = sorted(set(members))
        if names:
            name = names[0]
            if len(names) > 1:
                name = names[0] + "  [aliases: " + ", ".join(names[1:]) + "]"
        elif len(members) < 2:
            continue          # a lone pin on no wire is not a net
        else:
            anon += 1
            name = f"N${anon:03d}"
        nets[name] = members

    for c in comps:
        for pin in c["pins"]:
            p = (pin["x"], pin["y"])
            if p in nc:
                continue
            root = dsu.find(p)
            if len(set(groups.get(root, []))) < 2 and not named.get(root):
                unconnected.append(f'{c["designator"]}.{pin["num"]}'
                                   f' ({pin["name"]}) @ {p}')
    return nets, unconnected


# ---------------------------------------------------------------- CLI

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("schematic")
    ap.add_argument("--bom")
    ap.add_argument("--netlist")
    ap.add_argument("--json")
    args = ap.parse_args(argv)

    sheets = load(args.schematic)
    comps, nets, unconn = [], {}, []
    for ds in sheets:
        comps += components(ds)
        n, u = build_netlist(ds)
        nets.update(n)
        unconn += u

    print(f"{args.schematic}: {len(comps)} components, {len(nets)} nets, "
          f"{len(unconn)} unconnected pins")

    if args.bom:
        import csv
        with open(args.bom, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["designator", "value", "package", "manufacturer",
                        "mfr_part", "lcsc", "pins"])
            for c in sorted(comps, key=lambda c: (c["designator"] or "")):
                w.writerow([c["designator"], c["value"], c["package"],
                            c["mfr"], c["mfr_part"], c["lcsc"],
                            len(c["pins"])])
        print(f"  wrote {args.bom}")

    if args.netlist:
        with open(args.netlist, "w", encoding="utf-8") as fh:
            for name in sorted(nets):
                fh.write(f"{name}\n")
                for m in nets[name]:
                    fh.write(f"    {m}\n")
            if unconn:
                fh.write("\nUNCONNECTED PINS\n")
                for u in unconn:
                    fh.write(f"    {u}\n")
        print(f"  wrote {args.netlist}")

    if args.json:
        json.dump({"components": comps, "nets": nets,
                   "unconnected": unconn}, open(args.json, "w"), indent=1)
        print(f"  wrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
