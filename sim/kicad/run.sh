#!/usr/bin/env bash
# Run the DAB simulation without opening KiCad.
#
# The GUI is the nicer way to explore (Inspect > Simulator, then click a wire to
# probe it). This is the reproducible path: same schematic, same ngspice, same
# numbers, no clicking. Use it in CI, or to check a change did what you meant.
#
#   ./run.sh            measure and plot
#   ./run.sh --no-plot  measure only (no matplotlib needed)
set -euo pipefail
cd "$(dirname "$0")"

SCH=dab-sim.kicad_sch
NET=build/dab-sim.cir
RUN=build/run.cir
mkdir -p build

command -v kicad-cli >/dev/null || { echo "kicad-cli not found - install KiCad 8 or newer"; exit 1; }
command -v ngspice   >/dev/null || { echo "ngspice not found - install ngspice"; exit 1; }

echo "==> exporting the netlist from the schematic"
kicad-cli sch export netlist --format spice -o "$NET" "$SCH" >/dev/null
# Nothing to copy: the transformer's coupling reaches ngspice through
# Sim.Library on T1, which KiCad resolves into an absolute .include itself.

# The .tran on the sheet drives the GUI. Here it is replaced by a .control block
# so the run also prints measurements; the circuit itself is untouched.
python3 - "$NET" "$RUN" <<'PY'
import sys
src, dst = sys.argv[1], sys.argv[2]
s = open(src).read()
if ".tran" not in s:
    sys.exit("no .tran directive found - is the SPICE directive text still on the sheet?")
import re
s = re.sub(r"^\.tran .*$", """.control
  tran 5n 500u 400u
  meas tran iv1_avg AVG i(V1) FROM=460u TO=500u
  meas tran iv2_avg AVG i(V2) FROM=460u TO=500u
  meas tran il_rms  RMS i(L3) FROM=460u TO=500u
  meas tran il_pk   MAX i(L3) FROM=460u TO=500u
  wrdata build/wf.txt v(/LA)-v(/LB) v(/HA)-v(/HB) i(L3) i(L1)
  print iv1_avg iv2_avg il_rms il_pk
.endc""", s, count=1, flags=re.M)
open(dst, "w").write(s)
PY

echo "==> running ngspice"
OUT=$(ngspice -b "$RUN" 2>&1)
echo "$OUT" | grep -iE "singular|convergence|error" && echo "   ^^ read these before believing the numbers" || true

V1=$(echo "$OUT" | sed -n 's/^iv1_avg = *//p' | tail -1)
V2=$(echo "$OUT" | sed -n 's/^iv2_avg = *//p' | tail -1)
IR=$(echo "$OUT" | sed -n 's/^il_rms = *//p'  | tail -1)
IP=$(echo "$OUT" | sed -n 's/^il_pk = *//p'   | tail -1)

python3 - "$V1" "$V2" "$IR" "$IP" <<'PY'
import sys
v1, v2, ir, ip = (float(x) for x in sys.argv[1:5])
pin, pout = abs(v1) * 48.0, abs(v2) * 400.0
print()
print(f"  input from the 48 V pack   {pin:8.1f} W   ({abs(v1):.2f} A)")
print(f"  output into the 400 V link {pout:8.1f} W   ({abs(v2):.3f} A)")
print(f"  efficiency                 {100*pout/pin:8.1f} %")
print(f"  tank current, HV side      {ir:8.2f} A rms   {ip:.2f} A peak")
print()
print(f"  closed form for these values: 3001 W."
      f"  Deviation {100*abs(pin-3001)/3001:.1f}%.")
PY

[ "${1:-}" = "--no-plot" ] && exit 0

# Plotting is optional. Set PYTHON= to point at an interpreter that has
# matplotlib if the default one does not.
PY_PLOT="${PYTHON:-}"
if [ -z "$PY_PLOT" ]; then
  for c in python3 /opt/hw-py/bin/python; do
    command -v "$c" >/dev/null 2>&1 || [ -x "$c" ] || continue
    "$c" -c "import matplotlib" >/dev/null 2>&1 && { PY_PLOT="$c"; break; }
  done
fi
if [ -z "$PY_PLOT" ]; then
  echo "  (no matplotlib - waveform data is in build/wf.txt; plot it however you like)"
  exit 0
fi
"$PY_PLOT" - <<'PY'
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, numpy as np
d = np.loadtxt("build/wf.txt"); t = d[:, 0] * 1e6
m = t > t.max() - 40
fig, ax = plt.subplots(3, 1, figsize=(10, 7.5), sharex=True)
ax[0].plot(t[m], d[m, 1], lw=1.2, color="#0f9b8e"); ax[0].set_ylabel("v(LA)-v(LB)  [V]")
ax[0].set_title("dab-sim - 48 V to 400 V, 56 uH, 100 kHz")
ax[1].plot(t[m], d[m, 3], lw=1.2, color="#d03b3b"); ax[1].set_ylabel("v(HA)-v(HB)  [V]")
ax[2].plot(t[m], d[m, 5], lw=1.3, color="#2a78d6", label="i(L3)  56 uH")
ax[2].plot(t[m], d[m, 7] / 8.333, lw=1.0, ls="--", color="#898781", label="i(L1)/n")
ax[2].set_ylabel("current [A]"); ax[2].set_xlabel("time [us]")
ax[2].legend(loc="upper right", fontsize=8)
for a in ax: a.grid(alpha=.3); a.axhline(0, color="k", lw=.5)
plt.tight_layout(); plt.savefig("dab-waveforms.png", dpi=110)
print("  wrote dab-waveforms.png")
PY
