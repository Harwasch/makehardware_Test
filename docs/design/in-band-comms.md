# In-band communication over the resonant coils

Requested during the vision interview: a handshake and control packets carried
over the same coils as the power, rather than over a separate radio or optical
path. Captured as `VIS-011`, decomposed through `SYS-012` and `SYS-013`.

Reproduce every number here with:

```bash
/opt/hw-py/bin/python sim/link-budget/comms_budget.py
```

## The constraint is bandwidth, not signal-to-noise

The intuition for a coupled-coil data link is that it is a short, quiet channel
with a large signal, so the limit will be noise. It is not. The limit is that
**the resonant tank is a bandpass filter, and its bandwidth is set by its loaded
Q — which the load itself changes by a factor of fifty.**

With the matched coil that the power budget requires (162 µH, unloaded Q ≈ 98):

| Condition | Reflected R | Loaded Q | Tank bandwidth | Usable symbol rate |
|---|---|---|---|---|
| Full power, 3 kW | 43.2 Ω | 2.0 | 43.3 kHz | ~21 700 Bd |
| 1 kW | 14.4 Ω | 5.7 | 15.0 kHz | ~7 500 Bd |
| 300 W trickle | 4.3 Ω | 16.6 | 5.1 kHz | ~2 550 Bd |
| 30 W standby ping | 0.43 Ω | 65.8 | 1.3 kHz | ~650 Bd |
| **No load (handshake)** | 0 | **98** | **867 Hz** | **~434 Bd** |

The awkward part is the shape of that table: **the link is fastest exactly when
you need it least, and slowest exactly when you need it first.** Handshake
happens before any power flows, which is the one condition where the tank is at
its full unloaded Q and the bandwidth has collapsed to under a kilohertz.

This is a direct consequence of `MEC-001`. The efficiency requirement demands a
high unloaded Q — that is the whole point of moving away from a PCB coil — and a
high unloaded Q is a narrow filter. **The two requirements pull in opposite
directions, and the resolution has to be explicit.**

## Two ways out, and why both are in the requirements

**1. Accept the low rate for the handshake.** 434 Bd carries a 16-byte frame in
about 370 ms. That is perfectly adequate for an identification exchange, and it
costs nothing. `SYS-012` therefore asks for only 200 bit/s with no power flowing
— comfortably inside what the undamped tank allows, with margin for the
demodulator to be imperfect.

**2. Damp the tank deliberately during handshake.** A shunt resistor across the
tank lowers the loaded Q on demand:

| Shunt | Loaded Q | Bandwidth | At 40 V drive | At 20 V | At 10 V |
|---|---|---|---|---|---|
| 100 Ω | 0.9 | 99 kHz | 16 W | 4.0 W | 1.0 W |
| 47 Ω | 1.8 | 47 kHz | 34 W | 8.5 W | 2.1 W |
| **22 Ω** | **3.8** | **22.5 kHz** | 73 W | **18 W** | 4.5 W |

A 22 Ω shunt at a 20 V fundamental drive gives 22.5 kHz of bandwidth for 18 W —
a 26× improvement over the undamped no-load tank, for a power that is trivial
next to 3 kW. That is `ELE-016`.

The prohibition in `ELE-016` on engaging the network above handshake drive is
not a nicety: the same 22 Ω across the tank at the full 360 V fundamental would
dissipate 5.9 kW. It has to be interlocked in hardware, not only in firmware.

## The handshake level doubles as a safety probe

Driving the tank at 20 V instead of 360 V to talk also means the dock is only
putting tens of watts into whatever is in front of it. `ELE-017` bounds that at
50 W into a short or an absent receiver.

That turns the communication requirement into a safety mechanism, which is what
`SYS-013` makes explicit: **no power above handshake level until a receiver has
been identified and has answered.** Without it the dock energises 3 kW into
whatever is present — a foreign object, a flooded receiver, or nothing. With it,
foreign-object and absent-receiver protection come for free from a mechanism
that had to exist anyway.

## The link and the resonance tracker will fight

This is the interaction most likely to be discovered late on a bench, so it is
written down as `FW-009`.

Load-shift keying works by modulating the receiver's load, which changes the
reflected impedance seen by the transmitter. The resonance tracker of `FW-001`
hill-climbs on exactly that quantity. An unblanked tracker will therefore
**follow the data stream instead of following resonance** — and because the
modulation is periodic and the tracker is a gradient follower, it will do so
confidently and wrongly.

The reverse direction fails too: the tracker perturbs the drive frequency by
design, which a frequency-shift-keyed demodulator reads as symbols.

The resolution is to make the two mutually exclusive in time: no frequency
perturbation while a frame is in flight, and tracking samples taken during a
frame are discarded. This is affordable because `SYS-009` allows 2 s to
re-acquire resonance and a frame at 2 kbit/s occupies a small fraction of that.

## Starting assumption for the modulation

Conventional for this class of link, and the assumption `ELE-015` is written
against:

* **Receiver → transmitter: load-shift keying.** The receiver switches a small
  reactive or resistive load; the transmitter sees it as an amplitude change on
  the tank current it is already measuring for `ELE-010`. Costs one switch and
  one component on the receiver, and no new sensing on the transmitter.
* **Transmitter → receiver: frequency-shift keying.** The transmitter already
  has fine control of drive frequency for resonance tracking; the receiver sees
  it as a phase or amplitude change across its own tank.

Neither needs a separate carrier, an antenna or a second transducer, which is
what `VIS-011` asked for. The real design difficulty is not the modulation but
the 50× swing in tank bandwidth and received amplitude that the demodulator has
to work across — which is why `ELE-015` is written as a bit-error-rate
requirement across the full range rather than as a modulation scheme.

## Open

* Whether the receiver can wake and answer on harvested energy alone at the
  `ELE-017` drive level, or needs its own standby supply from the pack. The
  second is simpler and the vehicle has a battery; the first is what allows a
  fully discharged pack to be recovered. This needs a decision.
* Whether the link should carry a rolling code or any authentication. Nothing in
  the brief asks for it, but a dock that will deliver 3 kW to anything that
  answers correctly is worth a deliberate decision rather than a default.
