#!/usr/bin/env python3
"""Generate ngspice decks for the link and the DAB exactly as the boards draw them.

Component values come from the EasyEDA export (build/eda/*.json via
scripts/eda_parse.py) and from datasheets recorded in
docs/reference/manifest.yaml.  Coil L / R / k come from sim/coil/coil_rect.py
at the ADR-0001 geometry.  Nothing is invented here.

    /opt/hw-py/bin/python sim/asbuilt/make_decks.py
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "sim", "coil"))
import coil_rect as cr                                        # noqa: E402

# --- ADR-0001 coil geometry, unchanged -------------------------------------
GEOM = dict(a_out=0.102, b_out=0.203, w=0.25e-3, t=4 * 34.8e-6,
            clearance=0.20e-3, layers=16, gap=10e-3, transposition=1.0)

# --- values read out of the EasyEDA files ----------------------------------
C_TANK = 300e-9      # TX PORT_OUT+ and RX PORT+ : 3 x B32921C3104M000
L1_DAB = 47e-6       # DAB L1, IHLP6767GZER470M11
L1_DCR = 42.7e-3     # datasheet, DigiKey/TME parametric (Vishay PDF blocked)
VBUS = 400.0         # TX VCC / DAB HV_BUS class implied by the 500 V parts
C_OUT_RX = 7.5e-6    # RX VCC : 5 x B32672P5155K000
RDSON_GAN = 0.200    # LMG2640 RDS(on) at TJ = 125 C, SNOSDH5 Table 5.5
RDSON_HV = 0.120     # IPB60R120P7, 120 mOhm class from the part number
VF_DIODE = 1.5       # MURSD860A -- BLOCKED, see manifest; MUR860 family value


def r_ac_at(c, f):
    """coil_rect.analyse() reports R_ac at its own F_NOM (85 kHz).  Skin and
    proximity loss are strong functions of frequency, so re-evaluate the
    Kuhn-Ibrahim factor at the frequency the deck actually runs at -- using
    it at 85 kHz for a 20 kHz case would overstate the loss by ~3x."""
    fr, _ = cr.kuhn_ibrahim(c["w"], GEOM["clearance"], c["t"], f=f, t_c=100.0)
    r_dc1 = c["r_dc1"]
    r_prox1 = r_dc1 * (fr - 1.0)
    return (r_dc1 / c["layers"]
            + c["layers"] * r_prox1 * (1.0 - c["transposition"] * 0.75))


def link_deck(n_turns, f_sw, c_tank=C_TANK, p_target=3000.0, path=None):
    c = cr.analyse(n=n_turns, **GEOM)
    if c is None:
        raise SystemExit(f"coil model: {n_turns} turns closes on itself")
    L, k = c["L"], c["k"]
    r = r_ac_at(c, f_sw)
    f0 = 1.0 / (2 * math.pi * math.sqrt(L * c_tank))
    # DC load that draws p_target from the rectified output at VBUS
    rload = VBUS ** 2 / p_target
    t_end = 400.0 / f_sw
    t_meas = 360.0 / f_sw
    step = 1.0 / f_sw / 400.0
    deck = f"""* Ulysses link as built -- TX bridge, {c_tank*1e9:.0f} nF, coil, {c_tank*1e9:.0f} nF, RX bridge
* coil: {n_turns} turns, L = {L*1e6:.2f} uH, k = {k:.3f}, R_ac = {r*1e3:.1f} mOhm
* series-resonant at {f0/1e3:.1f} kHz, driven at {f_sw/1e3:.1f} kHz
.param FSW={f_sw}
.param TP={{1/FSW}}

VBUS bus 0 DC {VBUS}

* --- TX full bridge, two LMG2640 half bridges (RDS(on) at 125 C)
SAH bus sw   ga 0 SWMOD
SAL sw  0    gb 0 SWMOD
SBH bus sw2  gb 0 SWMOD
SBL sw2 0    ga 0 SWMOD
* Body diodes / reverse conduction.  Without them the 1 ns gap between the
* two gate signals leaves the tank current with nowhere to go, ROFF = 1e9
* develops a numerically explosive voltage, and the deck pumps energy in.
DAH sw  bus BODY
DAL 0   sw  BODY
DBH sw2 bus BODY
DBL 0   sw2 BODY
.model BODY D(IS=1e-12 RS=0.05 N=1.2 CJO=100p TT=1n BV=800)
VGA ga 0 PULSE(0 5 0 1n 1n {{TP/2-4n}} {{TP}})
VGB gb 0 PULSE(0 5 {{TP/2}} 1n 1n {{TP/2-4n}} {{TP}})
.model SWMOD SW(RON={RDSON_GAN} ROFF=1e9 VT=2.5 VH=0.5)

* --- TX tank: 3 x 100 nF in the leg-A output, coil, then RX tank
CTX  sw  txa {c_tank}
LTX  txa txb {L}
RTX  txb 0   {r}
LRX  rxa rxb {L}
RRX  rxb rxn {r}
K1 LTX LRX {k}
CRX  rxa prt {c_tank}

* --- RX bridge: 12 x MURSD860A, 3 in parallel per arm
DR1 prt vout DMOD
DR2 0d  prt DMOD
DR3 rxn vout DMOD
DR4 0d  rxn DMOD
VSENSE 0d 0 DC 0
.model DMOD D(IS=1e-8 RS={VF_DIODE/24.0:.4f} N=2 CJO=100p TT=25n BV=600)

COUT vout 0 {C_OUT_RX} IC=0
RLOAD vout 0 {rload:.2f}

.ic V(vout)=0

.control
tran {step:.4g} {t_end:.6g} 0 uic
let pin  = -v(bus)*i(vbus)
let pout = v(vout)*v(vout)/{rload:.2f}
let vctx = v(sw)-v(txa)
meas tran p_in   avg pin  from={t_meas:.6g} to={t_end:.6g}
meas tran p_out  avg pout from={t_meas:.6g} to={t_end:.6g}
meas tran i_tank rms i(ltx) from={t_meas:.6g} to={t_end:.6g}
meas tran i_pk   max i(ltx) from={t_meas:.6g} to={t_end:.6g}
meas tran v_out  avg v(vout) from={t_meas:.6g} to={t_end:.6g}
meas tran v_ctx  rms vctx from={t_meas:.6g} to={t_end:.6g}
print p_in p_out i_tank i_pk v_out v_ctx
.endc
.end
"""
    if path:
        open(path, "w").write(deck)
    q = 2 * math.pi * f_sw * L / r
    return deck, dict(L=L, k=k, r=r, f0=f0, rload=rload, coil=c, Q=q, kQ=k * q)


def dab_deck(f_sw=85e3, path=None):
    t_end = 5e-3            # >> L1/R = 1.1 ms, so the start-up
    t_meas = 4.5e-3         # DC offset has decayed before we measure
    step = 1.0 / f_sw / 400.0
    deck = f"""* Ulysses DAB HV bridge exactly as the schematic draws it.
* AH/AL and BH/BL across HV_BUS; the bridge output goes
*   A_SW -> L1 (47 uH) -> current sensor -> B_SW
* and nothing else.  No transformer, no external port.
.param FSW={f_sw}
.param TP={{1/FSW}}

VBUS bus 0 DC {VBUS}
SAH bus asw ga 0 SWMOD
SAL asw 0   gb 0 SWMOD
SBH bus bsw gb 0 SWMOD
SBL bsw 0   ga 0 SWMOD
* Body diodes -- see the note in link_deck().
DAH asw bus BODY
DAL 0   asw BODY
DBH bsw bus BODY
DBL 0   bsw BODY
.model BODY D(IS=1e-12 RS=0.05 N=1.2 CJO=100p TT=1n BV=800)
VGA ga 0 PULSE(0 5 0 1n 1n {{TP/2-4n}} {{TP}})
VGB gb 0 PULSE(0 5 {{TP/2}} 1n 1n {{TP/2-4n}} {{TP}})
.model SWMOD SW(RON={RDSON_HV} ROFF=1e9 VT=2.5 VH=0.5)

L1  asw mid {L1_DAB}
RL1 mid bsw {L1_DCR}

.control
tran {step:.4g} {t_end:.6g} 0 uic
meas tran i_pk   max i(l1)  from={t_meas:.6g} to={t_end:.6g}
meas tran i_min  min i(l1)  from={t_meas:.6g} to={t_end:.6g}
meas tran i_rms  rms i(l1)  from={t_meas:.6g} to={t_end:.6g}
meas tran i_bus  avg i(vbus) from={t_meas:.6g} to={t_end:.6g}
print i_pk i_min i_rms i_bus
.endc
.end
"""
    if path:
        open(path, "w").write(deck)
    return deck


if __name__ == "__main__":
    # 15.9 nF is what 85 kHz needs against the 24-turn coil; it is the
    # "as it should be" case, not something the boards fit.
    cases = [(24, 85e3, C_TANK, "link-24t-85k.cir"),
             (24, 19.6e3, C_TANK, "link-24t-res.cir"),
             (5, 85e3, C_TANK, "link-5t-85k.cir"),
             (24, 85e3, 15.9e-9, "link-24t-tuned.cir")]
    for n, f, ct, name in cases:
        _, info = link_deck(n, f, c_tank=ct, path=os.path.join(HERE, name))
        print(f"{name:22s} n={n:2d} f={f/1e3:5.1f}k C={ct*1e9:6.1f}nF "
              f"L={info['L']*1e6:6.1f}uH k={info['k']:.3f} "
              f"R={info['r']*1e3:6.1f}mR f0={info['f0']/1e3:5.1f}k "
              f"Q={info['Q']:5.1f} kQ={info['kQ']:5.1f} "
              f"Rload={info['rload']:.1f}")
    dab_deck(path=os.path.join(HERE, "dab-hv-loop.cir"))
    print("dab-hv-loop.cir: HV bridge closed through L1 only")
