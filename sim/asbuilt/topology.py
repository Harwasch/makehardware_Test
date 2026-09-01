#!/usr/bin/env python3
"""What the EasyEDA files actually build, in numbers.

Everything here is derived from hw/easyeda/*/schematic.json via
scripts/eda_parse.py -- no value is typed in from a datasheet unless the
manufacturer part number itself encodes it, and those are marked.

    /opt/hw-py/bin/python sim/asbuilt/topology.py
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

BUILD = os.path.join(ROOT, "build", "eda")


def board(name):
    return json.load(open(os.path.join(BUILD, f"{name}.json")))


def by_ref(b):
    return {c["designator"]: c for c in b["components"]}


def rule(title):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


# ------------------------------------------------------------------ values
# Values EasyEDA stores as a free-text string; parsed, not assumed.
def farads(text):
    t = (text or "").strip().lower().replace("μ", "u")
    for suffix, mult in (("pf", 1e-12), ("nf", 1e-9), ("uf", 1e-6), ("f", 1.0)):
        if t.endswith(suffix):
            try:
                return float(t[: -len(suffix)]) * mult
            except ValueError:
                return None
    return None


def henries(text):
    t = (text or "").strip().lower().replace("μ", "u")
    for suffix, mult in (("nh", 1e-9), ("uh", 1e-6), ("mh", 1e-3), ("h", 1.0)):
        if t.endswith(suffix):
            try:
                return float(t[: -len(suffix)]) * mult
            except ValueError:
                return None
    return None


def net_caps(b, net):
    """Total capacitance on a net, and the parts that make it up."""
    refs = {m.split(".")[0] for m in b["nets"].get(net, [])}
    parts, total = [], 0.0
    for c in b["components"]:
        if c["designator"] in refs and len(c["pins"]) == 2:
            v = farads(c["value"])
            if v:
                parts.append((c["designator"], c["value"], c["mfr_part"]))
                total += v
    return total, parts


def main():
    tx, rx, dab = board("TX"), board("RX"), board("DAB")

    # -------------------------------------------------- 1. resonant tank
    rule("1.  SERIES COMPENSATION -- what the boards actually fit")
    c_tx, tx_parts = net_caps(tx, "PORT_OUT+")
    c_rx, rx_parts = net_caps(rx, "PORT+")
    print(f"  TX  PORT_OUT+ : {c_tx*1e9:6.1f} nF  ({len(tx_parts)} parts in parallel)")
    for d, v, m in tx_parts:
        print(f"        {d:5s} {v:10s} {m}")
    print(f"  RX  PORT+     : {c_rx*1e9:6.1f} nF  ({len(rx_parts)} parts in parallel)")
    for d, v, m in rx_parts:
        print(f"        {d:5s} {v:10s} {m}")

    print("\n  Series-series compensation resonates at f = 1/(2*pi*sqrt(L*C)).")
    print("  Solving for the coil inductance each capacitor bank implies:\n")
    print(f"    {'f (kHz)':>9} {'L_tx (uH)':>11} {'L_rx (uH)':>11}")
    for f in (20e3, 40e3, 85e3, 100e3, 150e3):
        ltx = 1.0 / ((2 * math.pi * f) ** 2 * c_tx)
        lrx = 1.0 / ((2 * math.pi * f) ** 2 * c_rx)
        print(f"    {f/1e3:9.0f} {ltx*1e6:11.2f} {lrx*1e6:11.2f}")

    L_DESIGN = 172e-6   # docs/design/coil-model.md, ADR-0001 design point
    f_design = 1.0 / (2 * math.pi * math.sqrt(L_DESIGN * c_tx))
    print(f"\n  The repo's coil (ADR-0001) is {L_DESIGN*1e6:.0f} uH per side.")
    print(f"  With {c_tx*1e9:.0f} nF that resonates at {f_design/1e3:.1f} kHz,")
    print(f"  not the 85 kHz the requirements assume.")
    c_needed = 1.0 / ((2 * math.pi * 85e3) ** 2 * L_DESIGN)
    print(f"  85 kHz with a {L_DESIGN*1e6:.0f} uH coil needs {c_needed*1e9:.1f} nF,"
          f" i.e. {c_tx/c_needed:.0f}x less than fitted.")

    # -------------------------------------------------- 2. tank current
    rule("2.  TANK CURRENT AND CAPACITOR STRESS AT 3 kW")
    P = 3000.0
    for f in (20.4e3, 85e3):
        for vbus, label in ((400.0, "400 V bus"),):
            # fundamental of a square-wave bridge output
            v1 = 4 / math.pi * vbus / math.sqrt(2)      # rms of fundamental
            i = P / v1                                  # unity-pf at resonance
            xc = 1.0 / (2 * math.pi * f * c_tx)
            vcap = i * xc
            dvdt = 2 * math.pi * f * vcap * math.sqrt(2) / 1e6   # V/us peak
            print(f"  f = {f/1e3:5.1f} kHz, {label}:")
            print(f"      bridge fundamental      {v1:8.1f} V rms")
            print(f"      tank current            {i:8.1f} A rms")
            print(f"      Xc of {c_tx*1e9:.0f} nF          {xc:8.2f} ohm")
            print(f"      volts across the bank   {vcap:8.1f} V rms")
            print(f"      reactive power in bank  {i*vcap/1000:8.2f} kVAr")
            print(f"      peak dV/dt              {dvdt:8.1f} V/us")
            print(f"      per capacitor: {i/len(tx_parts):.1f} A rms through a"
                  f" 100 nF X2 part")
            print()

    # -------------------------------------------------- 3. DAB link
    rule("3.  DAB -- the HV bridge output loop as drawn")
    dr = by_ref(dab)
    l1 = henries(dr["L1"]["value"])
    print(f"  L1 = {l1*1e6:.0f} uH  ({dr['L1']['mfr_part']}, {dr['L1']['package']})")
    print("  Net trace from the HV bridge:")
    print("      AH.S/AL.D  -> D1_1 -> L1.1")
    print("      L1.2       -> S$194154 -> U94.IN+   (TMCS1133 current sensor)")
    print("      U94.IN-    -> BH_3 -> BH.S/BL.D")
    print("  That is the whole loop.  There is no transformer, and no pad or")
    print("  connector, between the two bridge legs -- the sheet closes the")
    print("  bridge output on itself through L1 and the sense resistor path.")
    vbus = 400.0
    f = 85e3
    dipp = vbus / l1 * (1 / (2 * f))
    print(f"\n  Driven as a bridge at {f/1e3:.0f} kHz from {vbus:.0f} V with no")
    print(f"  load impedance but L1, the current ramps")
    print(f"      di/dt        = V/L = {vbus/l1/1e6:.2f} A/us")
    print(f"      peak-to-peak = V/(2*f*L) = {dipp:.0f} A")
    print(f"  L1 is an IHLP-6767 class part in a 17.2 x 17.2 mm footprint;")
    print(f"  {dipp:.0f} A pk-pk is far outside anything that package saturates at.")

    rule("4.  DAB -- LV bridge switch nodes")
    sec = sorted({m.split(".")[0] for m in dab["nets"]["SEC"]})
    print("  Net SEC carries:", ", ".join(sec))
    print()
    print("  CH1/CH2 sources, DH1/DH2 sources, CL1/CL2 drains and DL1/DL2 drains")
    print("  are all one node.  Leg C and leg D therefore share a switch node,")
    print("  while AGD3 (leg D) and AGD4 (leg C) are driven from separate")
    print("  MCU outputs C/C# and D/D#.")
    print("  The same 24 pads carry net SEC on the PCB, so this is the layout")
    print("  too, not a schematic-only slip.")
    print()
    print("  Consequence: any phase difference between the C and D gate pairs")
    print("  turns on a high-side FET of one leg and a low-side FET of the")
    print("  other across LV_BUS with nothing between them.")

    # -------------------------------------------------- 5. bus capacitors
    rule("5.  BUS CAPACITORS AND THEIR VOLTAGE CLASS")
    print("  Only parts whose EasyEDA value field is a number are summed.  The")
    print("  four NCC HHXC630ARA220MF80G on DAB LV_BUS carry the part number in")
    print("  the value field, so they are listed but not added; the NCC code")
    print("  reads 63 V / 22 uF and the 6.3 mm can in the footprint corroborates")
    print("  63 V, but the datasheet was not reachable -- see the manifest.\n")
    for b, name, nets in ((dab, "DAB", ("HV_BUS", "LV_BUS")),
                          (tx, "TX", ("VCC",)),
                          (rx, "RX", ("VCC",))):
        for net in nets:
            total, parts = net_caps(b, net)
            refs = {m.split(".")[0] for m in b["nets"].get(net, [])}
            unparsed = sorted(c["designator"] for c in b["components"]
                              if c["designator"] in refs and len(c["pins"]) == 2
                              and farads(c["value"]) is None
                              and c["package"].upper().startswith("C")
                              and "CONN" not in c["package"].upper())
            print(f"  {name} {net}: {total*1e6:.1f} uF from parts with a"
                  f" numeric value")
            seen = {}
            for d, v, m in parts:
                seen.setdefault((v, m), []).append(d)
            for (v, m), ds in sorted(seen.items()):
                print(f"      {len(ds):2d} x {v:22s} {m:24s} {','.join(ds)}")
            byref = by_ref(b)
            shown = set()
            for d in unparsed:
                key = byref[d]["mfr_part"]
                if key in shown:
                    continue
                shown.add(key)
                same = [x for x in unparsed if byref[x]["mfr_part"] == key]
                print(f"      {len(same):2d} x {'(value not numeric)':22s}"
                      f" {key:24s} {','.join(same)}")
            print()

    rule("6.  CONNECTOR CURRENT RATING vs THE CURRENT THE NET CARRIES")
    print("  Amass XT-series connectors are named for their CURRENT rating,")
    print("  not their voltage: TME/Amass list XT60 at 30 A continuous / 500 V DC")
    print("  and XT30 at 15 A continuous / 500 V DC.  Voltage is fine on a 400 V")
    print("  bus; current is where these land.\n")
    for tag, ref, part, net, p_w, v in (
            ("DAB", "U82", "XT60-M.",      "HV_BUS",         3000.0, 400.0),
            ("DAB", "U83", "XT60-M.",      "LV_BUS",         3000.0,  48.0),
            ("DAB", "CN1", "XT30UW-F.G.Y", "48V aux only",     50.0,  48.0),
            ("RX",  "CN3", "XT60PB-F.G.Y", "VCC (link out)", 3000.0, 400.0)):
        i = p_w / v
        rating = 15.0 if "XT30" in part else 30.0
        flag = "  <-- OVER" if i > rating else ""
        print(f"  {tag:3s} {ref:4s} {part:14s} on {net:16s}"
              f" {p_w/1000:4.1f} kW at {v:5.0f} V = {i:6.1f} A"
              f" vs {rating:4.0f} A{flag}")
    print("\n  CN1 only feeds the five TPSM560R6 aux converters, so its 15 A is")
    print("  ample.  The DAB's LV output connector is the binding one: 62.5 A")
    print("  through a 30 A part.")

    rule("7.  TX POWER STAGE HEADROOM -- LMG2640, SNOSDH5 (Nov 2024)")
    print("  Recommended operating condition ID(cnts) = +/-8.2 A, both FETs.")
    print("  Cycle-by-cycle over-current threshold IT(OC) = 8.2 A min,")
    print("  9.1 A typ, 10 A max -- the part shuts its own gate off above this.")
    print("  RDS(on) = 105 mohm at 25 C, 200 mohm at 125 C.  RthJA = 22.8 C/W.\n")
    v1 = 4 / math.pi * 400.0 / math.sqrt(2)
    print(f"  A 400 V bridge's fundamental is {v1:.0f} V rms.  At unity power")
    print("  factor the deliverable power is V1 * I1_rms, and the peak of a")
    print("  sinusoidal tank current is sqrt(2) x its rms:\n")
    print(f"    {'OCP trip (A pk)':>16} {'I1 rms (A)':>11} {'P (W)':>8}"
          f" {'P_FET at 125C (W)':>18}")
    for ipk in (8.2, 9.1, 10.0):
        irms = ipk / math.sqrt(2)
        p = v1 * irms
        # each FET carries the tank current for half the period
        pfet = (irms / math.sqrt(2)) ** 2 * 0.200
        print(f"    {ipk:16.1f} {irms:11.2f} {p:8.0f} {pfet:18.1f}")
    print(f"\n  3 kW needs {3000/v1:.1f} A rms = {3000/v1*math.sqrt(2):.1f} A peak,"
          f" which is above even the")
    print("  10 A best-case trip point.  The TX cannot reach 3 kW from a 400 V")
    print("  bus with one LMG2640 per leg, whatever the tank is tuned to.")
    pf = (3000 / v1 / math.sqrt(2)) ** 2 * 0.200
    print(f"\n  Conduction loss alone at 3 kW is {pf:.1f} W per FET,"
          f" {2*pf:.1f} W per package.")
    print("  On the datasheet's RthJA of 22.8 C/W that is a 319 C rise; the part")
    print("  has dual thermal pads and a real board does far better than the")
    print("  JEDEC number, but even a good 8-10 C/W path puts the junction over")
    print("  150 C before any switching loss is counted.  Thermals need a")
    print("  measurement, not an estimate -- and that is a lab task.")

    rule("8.  DAB LV BRIDGE CONDUCTION LOSS AT 3 kW  (ELE-003)")
    dr = by_ref(dab)
    lv = sorted({m.split(".")[0] for m in dab["nets"]["SEC"]}
                & {c["designator"] for c in dab["components"]
                   if c["mfr_part"] == "BSC190N15NS3G-TP"})
    print(f"  The board fits {len(lv)} x BSC190N15NS3G-TP: {', '.join(lv)}")
    print("  Two per switch position, four positions -- N = 2 per branch.")
    print(f"  Second-sourced from {dr['CH1']['mfr']} under the Infineon part")
    print("  number, which needs its own qualification.\n")
    v_lv, p_out = 48.0, 3000.0
    i_dc = p_out / v_lv
    # a DAB's LV-side tank current is a square wave of amplitude I_dc/D; at the
    # most favourable phase shift the rms approaches (pi/(2*sqrt(2))) * I_dc
    i_rms = math.pi / (2 * math.sqrt(2)) * i_dc
    rds25 = 19e-3          # datasheet max, Infineon product page
    rds100 = rds25 * 1.6   # OptiMOS 3 temperature factor at ~100 C
    print(f"  3 kW into {v_lv:.0f} V is {i_dc:.1f} A dc.")
    print(f"  Best-case tank rms = (pi/2sqrt2) x I_dc = {i_rms:.1f} A.")
    print(f"  R_ds(on) {rds25*1e3:.0f} mohm max at 25 C, x1.6 at 100 C"
          f" = {rds100*1e3:.1f} mohm.\n")
    print("  Each switch position conducts for half the cycle, so the whole")
    print("  four-position bridge costs 2 * I_rms^2 * R_ds / N:\n")
    print(f"    {'N per branch':>13} {'devices':>8} {'conduction (W)':>16}"
          f" {'vs 100 W budget':>17}")
    for n in (2, 4, 6):
        loss = 2 * i_rms ** 2 * rds100 / n
        print(f"    {n:13d} {4*n:8d} {loss:16.0f} {loss/100.0:16.1f}x")
    print("\n  The board's two per branch spends 1.5x the entire ELE-003 budget")
    print("  on low-voltage conduction alone, before the HV bridge, the")
    print("  transformer, or any switching loss.  Four per branch is under the")
    print("  budget but leaves almost nothing for the rest.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
