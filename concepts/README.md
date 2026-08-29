# concepts/

build123d models for the vision stage. Every dimension here is one the model
actually holds — these are geometry renders, not artistic impressions, so a
concept cannot show something unbuildable.

```bash
vision-board concepts/dock_belly.py concepts/dock_flank.py concepts/dock_saddle.py \
    --out build/vision
```

| File | Concept |
|---|---|
| `_common.py` | shared geometry — coil pad, hull, enclosure, struts |
| `dock_belly.py` | A — vehicle settles onto a cradle, pads horizontal |
| `dock_flank.py` | B — vehicle alongside a vertical face, pads vertical |
| `dock_saddle.py` | C — hull nests into a vee, two pads at ±45° |

**The Mako hull is a placeholder.** Its real form factor is an open question at
gate 1; it is drawn as a 1.4 m capsule so the coil pad has something believable
to sit on. The coil pad itself is real — 102 × 203 mm at a 16 mm stack, from
`sim/coil/coil_rect.py`.

No image backend is configured in this environment (`imagegen --list` reports no
keys), so styled or contextual imagery is not available. If the vision board
should look like a product rather than shaded CAD, that needs `FAL_KEY`,
`BFL_API_KEY` or `OPENAI_API_KEY` set in the environment.
