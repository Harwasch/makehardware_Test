# Friction log

Three lines per entry, written as it happens. One of them names the
MakeHardware file that should change. See the `hw-retro` skill.

---

**The power budget adds child-rail current to its parent without referring it
through the voltage ratio.** `block_diagram.py` has a 400 V rail feeding a 48 V
rail through an isolated DAB; the roll-up added 67 A of 48 V load straight onto
the 400 V rail and declared it 8x over budget, which stopped the gate being
usable until the tree was restructured.
The docstring in `budget()` says loads are "referred through their regulators",
but the code does `rows[parent]["max"] += rows[rid]["max"]` with no voltage
term, so the promise and the behaviour disagree.
**Fix `scripts/block_diagram.py`, `budget()`:** multiply by
`child_voltage / parent_voltage` when rolling up, or drop the claim from the
docstring and say plainly that the check is conservative. As written, any
project with a large step-down gets an answer that is wrong by the step ratio —
here 8.3x — and the natural workaround (declaring rails independent) only
happens to be correct because both converters are galvanically isolated.

---

**A single package timing out took the entire Python toolchain down, silently.**
`phase_python()` in `env/setup.sh` installs eleven packages in one `uv pip
install`; `pandas` metadata timed out, the whole phase returned 1, and the venv
was left empty. `hw-doctor` then reported strictdoc, pyyaml, build123d,
build123d-mcp and ltspice-mcp all FAIL — five separate-looking failures from one
network hiccup, with nothing to indicate they shared a cause.
Reinstalling in four smaller groups worked first time on the same network.
**Fix `env/setup.sh`, `phase_python()`:** split the install into an essential
group (strictdoc, pyyaml — the requirements and planning gates) and optional
groups, so a transient failure on a plotting dependency cannot take out the
requirements toolchain. `pandas` in particular is not imported by any script in
`scripts/`.

---

**`build123d-mcp` and `ltspice-mcp` cannot coexist in one venv.** `build123d-mcp
0.3.83` requires `mcp>=2,<3`; `ltspice-mcp` pins `mcp[cli]<2.0,>=1.27.0`.
Whichever resolves last wins and the other dies at import, so `hw-doctor` shows
one of the two MCP servers failing no matter what — which reads as a broken
install rather than a dependency conflict.
Resolved here by giving `build123d-mcp` its own venv at `/opt/hw-py-b123d` and
symlinking the console script back into `/opt/hw-py/bin`.
**Fix `env/setup.sh`, `phase_python()`:** install each MCP server into its own
venv and symlink the entry points, since they are separate processes and share
nothing but the interpreter. Also worth a line in `hw-doctor.sh` output when an
MCP server fails on an import error rather than a missing binary — the two look
identical in the current report and have completely different fixes.
