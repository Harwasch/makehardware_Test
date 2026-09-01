#!/usr/bin/env python3
"""Compare a KiCad netlist against the EasyEDA source it was converted from.

The conversion is only worth anything if it carries the same connectivity, so
this diffs the two node sets net by net.  Net *names* are allowed to differ
(KiCad renames unnamed nets); what must match is the partition of pins into
nets.

Usage:  kicad_net_check.py <board.net> <board.json>
"""
import json
import re
import sys


def kicad_nets(path):
    """Parse the (nets ...) section of a kicad-cli netlist export."""
    nets, name, ref = {}, None, None
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        m = re.match(r'\(name "([^"]*)"\)$', line)
        if m and name is None:
            name = m.group(1).lstrip("/")
            nets.setdefault(name, set())
            continue
        m = re.match(r'\(ref "([^"]+)"\)$', line)
        if m:
            ref = m.group(1)
            continue
        m = re.match(r'\(pin "([^"]+)"\)$', line)
        if m and ref and name is not None:
            nets[name].add(f"{ref}.{m.group(1)}")
            ref = None
            continue
        if line == "(net":
            name = None
    return {k: v for k, v in nets.items() if v}


def eda_nets(path):
    d = json.load(open(path))
    return {n: {m.split("(")[0] for m in members}
            for n, members in d["nets"].items()}


def partition(nets):
    """node -> frozenset of the net it belongs to, for name-independent diff."""
    return {node: frozenset(members) for members in nets.values() for node in members}


def main(argv):
    knet, ejson = argv[1], argv[2]
    k, e = kicad_nets(knet), eda_nets(ejson)
    # KiCad gives every unconnected pin a net of its own; those are not
    # connectivity, they are the absence of it.
    auto = re.compile(r"^(unconnected-|Net-)")
    floating = sorted(next(iter(v)) for n, v in k.items()
                      if len(v) == 1 and auto.match(n))
    k = {n: v for n, v in k.items() if len(v) > 1 or not auto.match(n)}
    kp, ep = partition(k), partition(e)

    only_e = sorted(set(ep) - set(kp))
    only_k = sorted(set(kp) - set(ep))
    differing = sorted(n for n in set(kp) & set(ep) if kp[n] != ep[n])

    print(f"KiCad : {len(k)} nets, {len(kp)} connected pins, "
          f"{len(floating)} single-pin (unconnected) nets")
    print(f"EasyEDA: {len(e)} nets, {len(ep)} connected pins")
    ok = True
    if only_e:
        ok = False
        print(f"\nIn EasyEDA but not connected in KiCad ({len(only_e)}):")
        for n in only_e[:40]:
            print("   ", n)
    if only_k:
        ok = False
        print(f"\nConnected in KiCad but not in EasyEDA ({len(only_k)}):")
        for n in only_k[:40]:
            print("   ", n)
    if differing:
        ok = False
        print(f"\nPins whose net membership differs ({len(differing)}):")
        seen = set()
        for n in differing:
            key = (kp[n], ep[n])
            if key in seen:
                continue
            seen.add(key)
            print(f"    {n}\n      KiCad  : {sorted(kp[n])}\n      EasyEDA: {sorted(ep[n])}")
    print("\nMATCH" if ok else "\nMISMATCH")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
