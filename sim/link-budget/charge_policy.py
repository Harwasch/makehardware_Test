#!/usr/bin/env python
"""Charge-rate policy for the Ulysses LARS charger.

The charger's power rating and the pack's charge acceptance are separate
constraints, and today they disagree by a factor of two. This works out what
each implies, so the requirements carry the right numbers.

Run:  /opt/hw-py/bin/python sim/link-budget/charge_policy.py

Inputs from the vision interview, 2026-08-28:
  * pack 48 V nominal, 33 Ah today, growing in capacity but never in voltage
  * normal charge 0.3-0.5C, ceiling 1.0C
  * charger design point 3 kW
"""

V_NOM = 48.0
AH_TODAY = 33.0
P_DESIGN = 3000.0
C_NORM_LO, C_NORM_HI, C_MAX = 0.30, 0.50, 1.00

# SYS-003 pack window. The bottom of it sets the worst-case current.
V_MIN, V_MAX = 40.0, 60.0


def energy_kwh(ah, v=V_NOM):
    return v * ah / 1000.0


def pack_for(power_w, c_rate, v=V_NOM):
    """Pack energy, and capacity, at which `power_w` is exactly `c_rate`."""
    e_kwh = power_w / 1000.0 / c_rate
    return e_kwh, e_kwh * 1000.0 / v


def main():
    e_today = energy_kwh(AH_TODAY)
    print(f"Pack today: {V_NOM:.0f} V x {AH_TODAY:.0f} Ah = {e_today:.3f} kWh\n")

    print("What today's pack will actually accept:")
    print(f"  {'C-rate':>10}{'power':>10}{'current':>10}{'full charge':>14}")
    for c, label in ((C_NORM_LO, ''), (C_NORM_HI, ''), (C_MAX, '  <- ceiling')):
        p = c * e_today * 1000.0
        print(f"  {c:9.2f}C{p:9.0f} W{p/V_NOM:9.1f} A{60/c:12.0f} min{label}")
    print(f"\n  So the usable ceiling today is {C_MAX*e_today*1000:.0f} W, which is "
          f"{C_MAX*e_today*1000/P_DESIGN*100:.0f}% of the {P_DESIGN/1000:.0f} kW design point.")

    print(f"\nWhat a {P_DESIGN/1000:.0f} kW design point implies about the future pack:")
    print(f"  {'C-rate':>10}{'pack':>10}{'capacity':>12}{'':>4}")
    for c, note in ((C_NORM_LO, 'bottom of the normal band'),
                    (C_NORM_HI, 'top of the normal band'),
                    (C_MAX, 'absolute ceiling - not a design target')):
        e, ah = pack_for(P_DESIGN, c)
        print(f"  {c:9.2f}C{e:9.1f} kWh{ah:11.0f} Ah   {note}")

    e8 = 8.0
    c8 = P_DESIGN / 1000.0 / e8
    print(f"\n  The white paper's 8 kWh pack ({8000/V_NOM:.0f} Ah at 48 V) takes "
          f"{P_DESIGN/1000:.0f} kW at {c8:.3f}C over {e8/(P_DESIGN/1000):.1f} h,")
    print(f"  which sits inside the {C_NORM_LO}-{C_NORM_HI}C normal band. The design point "
          f"and the paper agree.")

    print(f"\nDESIGN CONCLUSION")
    lo_e, lo_ah = pack_for(P_DESIGN, C_NORM_HI)
    hi_e, hi_ah = pack_for(P_DESIGN, C_NORM_LO)
    print(f"  3 kW is the NORMAL charge rate for a pack between {lo_e:.0f} and {hi_e:.0f} kWh")
    print(f"  ({lo_ah:.0f} to {hi_ah:.0f} Ah at 48 V). Below {pack_for(P_DESIGN, C_MAX)[0]:.0f} kWh "
          f"the charger can never reach its rating without exceeding 1C.")

    print(f"\nWORST-CASE CURRENT the hardware must carry")
    print(f"  {'condition':<34}{'V':>7}{'A':>9}")
    print(f"  {'3 kW at nominal 48 V':<34}{V_NOM:6.0f} V{P_DESIGN/V_NOM:8.1f} A")
    print(f"  {'3 kW at bottom of window':<34}{V_MIN:6.0f} V{P_DESIGN/V_MIN:8.1f} A  <- sizes the LV bridge")
    print(f"  {'3 kW at top of window':<34}{V_MAX:6.0f} V{P_DESIGN/V_MAX:8.1f} A")

    print(f"\nFIRMWARE CLAMP (FW-006)")
    print(f"  The clamp must be a C-rate applied to a CONFIGURED pack capacity,")
    print(f"  not a fixed current, or it stops protecting the pack the moment the")
    print(f"  pack changes. For the present {AH_TODAY:.0f} Ah pack:")
    for c in (C_NORM_LO, C_NORM_HI, C_MAX):
        print(f"    {c:.2f}C -> {c*AH_TODAY:5.1f} A -> {c*e_today*1000:6.0f} W")


if __name__ == "__main__":
    main()
