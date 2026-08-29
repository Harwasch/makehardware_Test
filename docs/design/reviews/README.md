# Stage reviews

One record per workflow gate. Written by [`hw-review`](../../../.claude/skills/hw-review/SKILL.md).

A record answers: what was reviewed, where the artifact is, what was asked, what
was decided, and what changed as a result. **A gate is not passed until its
record exists**, and a record with unanswered questions means the gate is still
open.

The point is that a later session can see what was actually agreed, rather than
inferring agreement from the fact that work continued. On this project the first
four stages ran with no review at all — that is what these records exist to stop
happening again.

| Gate | Stage | Status |
|---|---|---|
| 1 | Vision | **open** — awaiting decisions |
