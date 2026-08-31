# Human review

An artefact the human has not seen is not a deliverable.

This directory is where agreement is recorded. Each review is a page the
human can open in a browser on github.com — because the agent works in a
cloud VM and that is the only surface the human actually has — plus a line in
`reviews.yaml` saying what they decided and what the artefacts looked like
when they decided it.

```
reviews.yaml       the sign-off ledger, with a digest per agreed artefact
<id>.md            one review packet per milestone or design stage
```

## The four milestones, at a minimum

| id | The artefact that renders on GitHub |
|---|---|
| `vision` | `docs/design/vision.md` and the renders beside it |
| `plan` | `docs/plan.md` (scope) and `docs/plan.svg` (dependency Gantt) |
| `requirements` | `docs/design/requirements-map.svg` |
| `arch` | `docs/design/arch-system.svg`, `arch-link.svg`, `arch-dab.svg`, `block-diagram.svg` |

Then one per large design stage — schematic, layout, enclosure, each
simulation campaign.

## The loop

```bash
review-gate open vision --title "..." --summary "..." \
    --artifact docs/design/vision.md --artifact docs/design/vision/ \
    --reference concepts/ \
    --question "Which concept, and why?"

#  ... ask the human directly with the printed github.com link, and wait ...

review-gate sign vision --approve --by <name> --note "<what they said>"
review-gate list                 # where every review stands
review-gate check --gate         # exit 1 while any milestone is open or stale
```

`--artifact` is what they are agreeing to: change one after sign-off and the
review goes **stale**, which fails the gate. `--reference` is a link to a
source file that legitimately churns — `plan.yaml`, a live `.kicad_sch` —
so the review does not break on every ordinary edit.

A chunk in `plan.yaml` that names a `review:` cannot be marked `done` until
that review is signed off. `plan-render --check` refuses it.

Full detail: the `hw-review` skill, and `hw-review/references/exports.md` for
how to turn a schematic, a board or a CAD model into something a browser can
open.

## Why the architecture milestone is `arch`, not `architecture`

`review-artifact`'s standard architecture phase is hardcoded to one figure,
`docs/design/block-diagram.svg`, and does not read the review's artefact list —
so a reviewer whose only access is the published page saw one diagram where
four were sent. It is replaced by a configured phase in
[`artifact.yaml`](artifact.yaml), which must use a different id because `hide`
suppresses a configured phase of the same id as well as the standard one. The
review binds to a phase by id, so the review is `arch` too, which keeps the
questions on the same tab as the drawings they are about.

`review-gate list` reports `architecture` as "never requested" for that reason.
That is expected, not a gap.
