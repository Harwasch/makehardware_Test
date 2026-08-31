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

---

**Both of the tooling defects logged above are FIXED upstream, and the review
gap is now a first-class stage.** MakeHardware v0.2.0 (commit `93ed502`) lands
`skills/hw-review/`, `bin/review-gate`, `bin/review-artifact`, a
`docs/review/` template and a `review:` field in `plan.yaml` that
`plan-render --check` enforces — so a chunk cannot be called done without a
committed sign-off. It also fixes `block_diagram.py`'s budget roll-up: child
rails are now referred through the voltage ratio, and where a voltage is
missing it rolls up 1:1 and *says so* rather than inventing a ratio.
This session was running v0.1.0 the whole time, from a branch that had since
been deleted upstream, and never checked for an update.
**Fix `skills/hw-doctor` or `hooks/session-start.sh`:** report the installed
plugin commit against the marketplace's current head at session start. A
toolbox whose whole value is current practice should notice when it is running
a version that no longer exists on the remote. The project-local
`.claude/skills/hw-review/` drafted in this session is deleted; the upstream
skill supersedes it and is better.

---

**The block diagram shipped with eight overlapping blocks, and the gate passed
it.** `block_diagram.py` reads hand positions back out of the existing `.drawio`
and pins the layout to them with no collision test. Rev C added seven blocks;
the pre-existing twenty-nine stayed at their rev-B coordinates and eight pairs
landed on top of each other. `block-diagram --check` exited 0, so nothing caught
it and the broken SVG went into a published review packet — the customer found
it. A fresh layout (`--relayout`) has zero overlaps.
**Fix `scripts/block_diagram.py`:** `layout()` should drop or re-flow a kept
position that collides, and `--check` should test the rendered boxes for overlap
rather than validating the spec alone. A gate that passes a diagram nobody can
read is worse than no gate.

---

**Block names are truncated mid-word with no ellipsis.** `render_svg` cuts names
at 24 characters and part numbers at 26. Fourteen of thirty-six blocks were cut,
and "Tank current sense ampli" reads as a typo rather than as an elision — which
is worse than a shortened name, because it makes the whole drawing look
unreviewed.
**Fix `scripts/block_diagram.py`, `render_svg()`:** ellipsize, or wrap onto the
second line the box already has room for, and warn at generation time listing
what was cut so the spec can be shortened deliberately.

---

**One sheet is the only option, and thirty-six blocks do not fit on one.**
Nothing in the generator divides a diagram. At 36 blocks and 23 buses the sheet
is 1376 x 3438 px, the column heuristic interleaves subsystems, and bus labels
print over boxes. Worked around with `scripts/block_sheets.py`, which slices the
master spec by a `sheet:` tag into four subsystem views with stub connectors for
off-sheet endpoints — the master stays the single source of truth so the power
budget still closes across the whole system.
**Fix `scripts/block_diagram.py`:** support a `sheet:` tag natively. Every
project past about twenty blocks needs it, and the master spec has to stay one
file or the budget cannot roll up.

---

**Two generators emit raw HTML that the review renderer escapes.**
`vision_board.py:293` and `review_gate.py:378` both wrap sections in
`<details><summary>`. GitHub renders it; `review_artifact.py` HTML-escapes
everything, so the published review page showed the customer literal
`<details><summary>Dimensioned isometric line drawing</summary>` where a drawing
should have been — in the vision document and in all four review packets.
Worked around with `scripts/md_flatten.py`, which runs after both.
**Fix `scripts/vision_board.py` and `scripts/review_gate.py`:** emit plain
markdown, or give `review_artifact.py` a small tag allowlist. Markdown that only
renders in one of the two places a document is read is the actual defect, and it
is invisible until a human opens the published page.

---

**`vision-board` overwrites the hand-written vision document. Third
occurrence.** `--doc` defaults to `docs/design/vision.md`, which is also where
the narrative lives, so every re-render destroys it; twice it was recovered by
hand and once the loss was only caught by `git diff --stat`. Now pointed at
`docs/design/vision-gallery.md` via `scripts/vision_md.py`.
**Fix `scripts/vision_board.py`:** default the generated gallery to its own
filename, or refuse to overwrite a file it did not itself write.

---

**`MATERIAL` sets the render colour but not the mass.** `vision-board` quotes
mass as `volume x 1.4 g/cm3` whatever the material, and `--material` accepts only
{cobalt, graphite, sand, steel}, so `MATERIAL = "aluminum"` silently fell back to
cobalt. The label does say "at 1.4 g/cm3" so it is not a false statement, but for
an aluminium test rig it reads 23 kg against a real 44 kg — the difference
between a one-person and a two-person lift.
**Fix `scripts/vision_board.py`:** carry a density per material and quote the
mass at it, or omit the mass when the material is not one it knows.

---

**The three-column layout is not fixable from the spec side, so the
architecture views are now drawn outside the plugin.** The customer rejected
`block-diagram`'s output twice. Fixing the stale-position collisions and
splitting into four subsystem sheets was not enough, because the layout engine
itself is the problem: it assigns columns by a heuristic that put eight of the
dock sheet's ten blocks in column one, it routes buses vertically straight
through boxes, and it has no notion of a module, so the dual active bridge was
drawn twice because the master spec instantiates it twice.
`scripts/arch_diagram.py` replaces the views with a stage grid — stages run left
to right in the direction power flows, every vertical run happens in a gutter
that is empty by construction, and a `modules:` section in
`hw/architecture.yaml` draws one design once however many times it is built. The
master spec still owns all content and still feeds the power budget.
**Fix `scripts/block_diagram.py`:** the useful primitives are a stage/flow
direction per block, gutter routing rather than free vertical runs, and module
instancing. Without those, any power-electronics diagram past a handful of
blocks comes out unreadable, and the gate cannot tell — `--check` passed every
version the customer rejected. A geometric assertion that no wire crosses a box
is four lines and would have caught all of it.

---

**The review page's architecture tab shows one hardcoded figure and ignores the
review's artefact list.** `phase_architecture` in `review_artifact.py` calls
`figure(root, "docs/design/block-diagram.svg", ...)` and nothing else, so four
artefacts sent for review arrived as one diagram on the published page. The
customer, whose only access is that page, reported seeing a single drawing.
`review-gate open --artifact` and `review-artifact`'s figures are two unrelated
mechanisms, and nothing says so.
Worked around with `docs/review/artifact.yaml`, which has a second cost: `hide`
suppresses a configured phase of the same id as well as the standard one, and a
review binds to a phase BY ID, so replacing the architecture tab forces the
review id to change from `architecture` to `arch` to keep the questions on the
same tab as the drawings.
**Fix `scripts/review_artifact.py`:** every standard phase should show the
artefacts its review actually lists, falling back to the hardcoded path only
when the review has none. Failing that, `hide` should not suppress a configured
phase that is replacing a standard one of the same id.

---

**A sheet wider than the review column is scaled down bodily, with no warning
and no horizontal scroll.** `.sheet svg{width:100%}` means a 2120 px diagram
arrives in a ~1150 px column at 54%, turning 12 px labels into 6 px. Nothing in
`--check` mentions it — the page reports "clear" — and it is invisible until a
human opens the page and cannot read it. Every architecture sheet is now laid
out to land under 1160 px and `arch_diagram.py --check` fails if one does not.
**Fix `scripts/review_artifact.py`:** either put an oversized figure in an
`overflow-x:auto` container, as the tables already are, or warn at generation
time with the effective scale, the way an oversized raster is already reported.
A diagram nobody can read is the same defect as a diagram that did not embed.
