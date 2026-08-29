---
name: hw-review
description: Put a stage's work in front of the human as a reviewable artifact and record their decision. Use at the end of any MakeHardware stage - vision, plan, requirements, architecture - before treating that stage as agreed, and whenever a finding changes something the human already signed off on.
---

# Stage review

The MakeHardware workflow defines an exit condition for every stage - "the human
points at one concept and its numbers without qualifying", "the human has agreed
the chunk list and the ordering", "the human has looked at the image and agreed
to it". It provides **no mechanism** for that to happen, so it silently does not,
and the agent proceeds on an agreement that was never made.

This skill is the mechanism.

## The failure it exists to stop

On this project, four stages ran without a single review. The vision-stage
concept renders were built, opened by the agent, judged by the agent, and never
shown to the human. The requirements HTML export was generated on every
validation run and never mentioned. The concepts themselves were built at the
wrong scope - two bare coil pads where the human wanted to see a product - and
nobody caught it, because nobody looked.

Each of those is individually small. Together they meant the vision stage's exit
condition was reported as met when it had not been attempted.

**An artefact the human has not seen is not a deliverable. It is work in
progress that looks like a deliverable.**

## When to run it

* At the end of every stage, before its status goes to `done` in `plan.yaml`.
* Whenever an analysis changes something the human already agreed to. A
  correction they have not seen is worse than the original error, because the
  design proceeds on their memory of the old answer.
* When a finding is blocking and the human's answer changes what happens next.

## What to produce

One HTML artifact per gate, published so it has a URL. It has to be built to be
**reviewed**, not to report work done. The difference is real:

| A report says | A review asks |
|---|---|
| what was built | which of these do you want |
| what the numbers are | here is the number, does it match what you expected |
| what the risks are | here is a risk, is it acceptable to you |
| that a decision was made | here is the decision, confirm or push back |

Include, in this order:

1. **What you need from them**, at the top, in one sentence. If you cannot state
   it, the gate is not ready to review.
2. **The options, shown not described.** Renders, diagrams, plots. At least two
   that differ in a nameable way - one option invites polite agreement, a pair
   forces a real preference and the reason given is worth more than the choice.
3. **Anything you got wrong since they last looked**, stated plainly and early.
   Not buried in a footnote.
4. **The numbers that decide it**, with the arithmetic reproducible.
5. **The open questions**, each one an answer that changes the design.
6. **A sign-off block** listing exactly what is being asked.

## Record the decision

Write `docs/design/reviews/gate-<n>-<stage>.md` with: what was reviewed, the
artifact URL, what was asked, what the human decided, and what changed as a
result. Date it. Commit it.

**The gate is not passed until that record exists**, and a stage whose record
shows open questions is still open. This is the same discipline `req-trace
--gate` applies to evidence, applied to agreement - and for the same reason. A
later session reading the repo can then see what was actually agreed rather than
inferring it from the fact that work continued.

## The rule that makes it work

**Never mark a stage `done` on the strength of having produced its artefacts.**
Produce them, show them, get an answer, record it. If the human has not
answered, the stage is `in_progress` and the plan should say so - an agreement
you assumed is a defect that surfaces three stages later, when it is expensive.
