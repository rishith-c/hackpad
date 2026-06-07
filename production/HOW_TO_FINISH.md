# HOW TO FINISH: 11 trace pulls in KiCad

The `.kicad_pro`, `.kicad_sch`, and `.kicad_pcb` are all included, the
12-key matrix is fully routed in copper, and `production/gerbers.zip` was
exported directly from this `.kicad_pcb` — DRC passes at error level. **The
board will fab as-is, but the connections below need to be pulled in KiCad
before the board will actually do anything past the matrix.**

If you'd rather regenerate everything: re-run
[`build_scripts/build_pcb.py`](../build_scripts/build_pcb.py) with KiCad 9's
bundled Python.

## What's already routed (don't touch)

- 12 MX switches + 12 1N4148 diodes placed in a 4×3 grid (19.05 mm pitch).
- COL0..COL3 trunks on **F.Cu** (vertical, one per column, from Y = −9 down
  through every switch in the column).
- ROW0..ROW2 trunks on **B.Cu** (horizontal, 1.5 mm above the diode pad row)
  with short cathode-to-trunk tabs.
- Switch pad B → diode anode bridges on **F.Cu** (short L behind each switch).
- Edge cuts: 95 × 95 mm rounded rectangle, 3 mm corner radius.
- GND pour on **B.Cu** with thermal reliefs — auto-connects every GND pad.
- M3 mounting holes at (±42, ±42).
- XIAO socket: two `PinHeader_1x07_P2.54mm_Vertical` at X = ±7.62, top-center,
  USB-C facing the top edge.
- OLED socket: `PinHeader_1x04_P2.54mm_Vertical` rotated 90°, GND end at
  (−29.81, −36). Pad order from −X to +X: GND, VCC, SCL, SDA.
- EC11 rotary encoder at (30, −28). Pads A, C(GND), B sit at X = 30,
  Y = −28 / −25.5 / −23. C (common) is already on the GND pour.
- Silkscreen branding ("HACKPAD" v2.0 on the front, repo URL on the back).

## What you finish in KiCad (11 traces, ~5 min)

Open [`pcb/hackpad.kicad_pcb`](hackpad.kicad_pcb). Switch to
**Route > Single Track** (`X`). Default trace width is 0.25 mm for
signals, 0.5 mm for power.

| # | Net | From (XIAO pin) | To | Notes |
|---|---|---|---|---|
| 1 | COL0 | J1 pad 1 — (−7.62, −45.62) | Top of COL0 trunk — (−28.575, −9) | F.Cu, longest fanout |
| 2 | COL1 | J1 pad 2 — (−7.62, −43.08) | Top of COL1 trunk — (−9.525, −9) | F.Cu |
| 3 | COL2 | J1 pad 3 — (−7.62, −40.54) | Top of COL2 trunk — (9.525, −9) | F.Cu, must dodge XIAO right pins |
| 4 | COL3 | J1 pad 4 — (−7.62, −38.00) | Top of COL3 trunk — (28.575, −9) | F.Cu, must dodge XIAO right pins + encoder |
| 5 | I2C_SDA | J1 pad 5 — (−7.62, −35.46) | OLED pad 4 — (−22.19, −36) | F.Cu, short hop left |
| 6 | I2C_SCL | J1 pad 6 — (−7.62, −32.92) | OLED pad 3 — (−24.73, −36) | F.Cu, parallel to SDA |
| 7 | ROW0 | J1 pad 7 — (−7.62, −30.38) | Left end of ROW0 trunk — (−26.765, −13.5) | B.Cu via at pin; cleanest on B.Cu under everything |
| 8 | ROW1 | J2 pad 4 — (7.62, −38.00) | Right end of ROW1 trunk — (34.385, 5.55) | B.Cu via at pin; route through right gutter |
| 9 | ROW2 | J2 pad 3 — (7.62, −40.54) | Right end of ROW2 trunk — (34.385, 24.6) | B.Cu, right gutter, different lane than ROW1 |
| 10 | ENC_A | J2 pad 2 — (7.62, −43.08) | Encoder pad A — (30, −28) | F.Cu, short hop right |
| 11 | ENC_B | J2 pad 1 — (7.62, −45.62) | Encoder pad B — (30, −23) | F.Cu, parallel to ENC_A |
| 12 | VCC_5V | J2 pad 7 — (7.62, −30.38) | OLED pad 2 — (−27.27, −36) | **F.Cu, 0.5 mm wide**, runs across the top |

**GND** (XIAO J2 pad 5 → OLED J3 pad 1 → encoder C) connects automatically
through the B.Cu GND pour's thermal reliefs.

### Tips

- The XIAO header pads are THT, so you can start a B.Cu trace right at the
  pad without a via — the pad already exists on both layers.
- All COL fanout traces (1–4) live in the F.Cu space between the XIAO bottom
  (Y ≈ −30) and the COL trunk tops (Y = −9). That's ~20 mm of clear lane;
  pick a separate Y lane per column to keep them parallel.
- ROW1 and ROW2 should use the right gutter (around X = 40–42, between the
  matrix's right edge at X ≈ 35 and the right mounting hole at X = 42).
- Place ENC_A and ENC_B on F.Cu before routing the VCC_5V trace — VCC_5V
  is fatter (0.5 mm) and will block them otherwise.

## After routing

```bash
# In KiCad GUI:
#   Inspect > Design Rules Checker > Run DRC (0 errors, 0 unconnected)
#   File > Fabrication Outputs > Gerbers... → output to a fresh folder
#   File > Fabrication Outputs > Drill Files... → same folder
#   zip the .gbr + .drl files as gerbers.zip → drop in production/

# OR from the CLI (replaces production/gerbers.zip):
mkdir -p /tmp/gerbers && \
  /Applications/KiCad.app/Contents/MacOS/kicad-cli pcb export gerbers \
    --output /tmp/gerbers/ \
    --layers "F.Cu,B.Cu,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts" \
    pcb/hackpad.kicad_pcb && \
  /Applications/KiCad.app/Contents/MacOS/kicad-cli pcb export drill \
    --output /tmp/gerbers/ --excellon-separate-th pcb/hackpad.kicad_pcb && \
  ( cd /tmp/gerbers && zip /path/to/production/gerbers.zip *.gtl *.gbl *.gto *.gbo *.gts *.gbs *.gm1 *.drl )
```

## JLCPCB order (covered by the Hackpad $15 grant)

2 layers · 1.6 mm · qty 5 · HASL · green (cheapest). Upload `gerbers.zip`,
preview, order. **Get the design approved by Hack Club first** so the grant applies.
