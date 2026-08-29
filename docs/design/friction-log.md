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

---

**Seven parallel research subagents exhausted the account's five-hour rate
limit.** A workflow fanned out seven agents, each fetching and parsing multi-
megabyte datasheet PDFs. One returned before the quota was spent; the other six
and all seven verification agents died on "You've hit your session limit".
The work was not wrong, only sized wrong: datasheet research is unusually
token-heavy because every PDF arrives as a large blob.
**Fix `skills/hw-sourcing/SKILL.md`:** say plainly that datasheet fan-out should
be serialised or capped at two or three concurrent agents, and that PDFs should
be fetched and extracted locally with pypdf rather than pulled through an agent's
context. There is a working recipe for this already in this repo's history —
the LMG2610 datasheet was extracted successfully that way in the same session
the agents failed.

---

**`WebFetch` cannot read most datasheet PDFs, and the fallback is not
installed.** Agents repeatedly got back "the actual technical specifications are
embedded within the compressed PDF content stream and are not directly
readable", then tried `pdftoppm` and found poppler-utils absent; `apt-get
install poppler-utils` fails because the package is not in the image's sources.
Meanwhile `pypdf` in a clean venv extracts the same documents without trouble.
**Fix `env/setup.sh`:** add `poppler-utils` to the apt phase and `pypdf` to the
Python phase. A hardware toolbox whose central rule is "never take a number from
memory when a datasheet exists" cannot ship without a working PDF text
extractor.

---

**Four workflow stages ran with no human review, because the workflow has exit
conditions but no mechanism.** `docs/02-workflow.md` states an exit condition
for every stage — "the human points at one concept and its numbers without
qualifying", "the human has looked at the image and agreed to it" — and nothing
anywhere causes that to happen. So it did not, four times running: the vision
concepts were rendered and never shown, the StrictDoc HTML export was generated
on every validation run and never mentioned, and the concepts themselves were
built at the wrong scope (two bare coil pads where the human wanted to see a
product) with nobody in a position to catch it.
The cost was not the wasted renders. It was that the vision stage was reported
as complete, and the plan, requirements and architecture were all built on top
of an agreement that had never been made.
**Fix `docs/02-workflow.md` and add `skills/hw-review/`:** make the review an
artefact-producing step with a committed sign-off record, and make "stage is
`done`" conditional on that record existing — the same discipline `req-trace
--gate` applies to evidence, applied to agreement. A draft of the skill is in
this repo at `.claude/skills/hw-review/` and works today; it should move
upstream. The single rule that matters: **an artefact the human has not seen is
not a deliverable.**

---

**A wrong conclusion survived because one configuration was generalised to a
whole technology.** The coil analysis tested a single-layer etched spiral,
found it 70 W short, and wrote up "PCB coils cannot reach the efficiency the
thermal path requires". Parallel layers — the obvious lever — were never
modelled. Six layers turn a 190 W failure into a 73 W pass, so the headline
finding of the project was wrong for two days.
`MEC-001` was unaffected, because it was written against k·Q and dissipation
rather than naming a conductor. That is the requirements discipline doing
exactly its job, and it is why the correction cost an analysis rather than a
requirements rewrite.
**Fix `skills/hw-simulation/SKILL.md`:** add a rule alongside "cross-check
against closed form" — **before concluding that an approach cannot work, list
the design levers you did not vary and say why.** A negative result from one
configuration is a result about that configuration. The existing corner-sweeping
rule covers tolerance, temperature and supply; it does not cover the geometry
and topology choices that are usually the real levers.
