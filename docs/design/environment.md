# Environmental envelope

Chunk **R2**. The dock electronics sit in an enclosure on the **open deck** of a
surface vessel operating worldwide (vision interview, 2026-08-28).

## The maximum

IEC 60945 is the maritime navigation and radiocommunication equipment standard,
and it derives its exposed-equipment maximum this way:

| Term | Value |
|---|---|
| Maximum expected air temperature at sea | **+32 °C** |
| Maximum solar gain at sea | **+23 °C** |
| **Total design maximum** | **+55 °C** |

That derivation is what makes +55 °C the right number rather than an arbitrary
round figure: it is an air temperature plus a solar allowance, and the solar
allowance is the larger part of it. An open-deck enclosure gets both.

**Design maximum ambient: +55 °C.** This is the number `SYS-016` carries and
the boundary condition the thermal work in `M3` runs against.

## The minimum

IEC 60945 splits equipment into protected (Class A) and exposed (Class B), with
Class B carrying the lower cold limit. **−25 °C** is the figure generally cited
for the exposed class, and it is what this project designs to — but see the
caveat below.

## What could not be verified

**The IEC 60945 standard itself is paywalled** and the secondary sources that
describe it do not carry the per-class numbers consistently. The +32/+23/+55 °C
derivation above is well attested across independent sources; the −25 °C cold
limit and the exact clause references are not, at the level of confidence this
project's rules require.

Recorded as blocked in `docs/reference/manifest.yaml`. **A purchased copy is
needed before `SYS-016` can be cited as compliant with IEC 60945** rather than
merely consistent with it. The +55 °C maximum is safe to design against now; the
cold limit should be confirmed before anything is qualified against it.

Two further sources worth having, neither yet fetched: **IACS UR E10** (type
testing for shipboard equipment) and the classification-society rules from DNV
and Lloyd's Register, which set ambient temperatures per location class and may
be more stringent than IEC 60945 for equipment in an unconditioned space.

## Why the maximum bites harder than it looks

The thermal budget is not "55 °C ambient, dissipate 300 W". It is 55 °C
ambient, **conduction only**, no pumped coolant and no forced air — so the
temperature rise from the coil conductor through the ferrite, the interface and
the cold plate to the structure, and from the structure to the sea, all has to
fit in the margin between +55 °C and the conductor's 100 °C limit in `MEC-004`.

**That is a 45 °C budget for the whole chain.** It is the reason `MEC-001`'s
coil loss allowance is 120 W and not a looser number, and it is why the etched
spiral's predicted 190 W is disqualifying rather than merely disappointing.
