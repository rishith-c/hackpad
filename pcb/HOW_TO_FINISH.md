# HOW TO FINISH: ~11 trace pulls in KiCad

The `.kicad_pro`, `.kicad_sch`, and `.kicad_pcb` are all included, the matrix
is fully routed in copper, and `production/gerbers.zip` was exported directly
from this `.kicad_pcb` — DRC passes at error level. **The board will fab
as-is, but the connections below need to be pulled in KiCad before the board
will actually do anything past the matrix.**

If you'd rather regenerate everything: re-run [`build_scripts/build_pcb.py`](../build_scripts/build_pcb.py)
with KiCad 9's bundled Python.

## What's already routed (don't touch)

- 4 MX switches + 4 1N4148 diodes placed in a 2×2 grid (19.05 mm pitch).
- COL0..COL1 trunks on F.Cu (vertical, one per column).
- ROW0..ROW1 trunks on B.Cu (horizontal, 1.5 mm above the diode pad row)
  with cathode-to-trunk tabs.
- Switch pad B → diode anode bridges on F.Cu (short L behind each switch).
- Edge cuts: 90 × 70 mm rounded rectangle, 3 mm corner radius.
- GND pour on B.Cu with thermal reliefs (GND auto-connects every pad on the
  GND net through the pour).
- M3 mounting holes at (±40, ±30).
- XIAO socket: two `PinHeader_1x07_P2.54mm_Vertical` at X = ±7.62, top of
  board, USB-C facing the top edge.
- OLED socket: `PinHeader_1x04_P2.54mm_Vertical` rotated 90°, centered on
  (24, −25). Pad order from −X to +X: GND, VCC, SCL, SDA.
- EC11 encoder at (22, 14).

## What you finish in KiCad (~11 traces, ~5 min)

Open [`pcb/hackpad.kicad_pcb`](hackpad.kicad_pcb). Switch to **Route > Single
Track** (`X`). Default trace width is 0.25 mm for signals, 0.5 mm for power.

| # | Net | From (XIAO pin) | To (target) | Notes |
|---|---|---|---|---|
| 1 | COL0 | J1 pad 1 — (−7.62, −32.62) | Top of COL0 trunk — (−31.525, −6.525) | F.Cu, lane Y = −20 |
| 2 | COL1 | J1 pad 2 — (−7.62, −30.08) | Top of COL1 trunk — (−12.475, −6.525) | F.Cu, lane Y = −18.5 |
| 3 | ROW0 | J1 pad 7 — (−7.62, −17.38) | Leftmost cathode area — (−29.525, −10.025) | B.Cu via at pin; lane via left of XIAO |
| 4 | ROW1 | J2 pad 4 — (7.62, −22.96) | Rightmost cathode — (−6.665, 8.95) | B.Cu via at pin; cross between matrix and encoder |
| 5 | ENC_A | J1 pad 3 — (−7.62, −27.54) | Encoder pad A — (22, 14) | F.Cu, route around top of matrix |
| 6 | ENC_B | J1 pad 4 — (−7.62, −25.0) | Encoder pad B — (22, 19) | F.Cu, parallel to ENC_A |
| 7 | ENC_PUSH | J2 pad 3 — (7.62, −27.54) | Encoder pad S1 — (36.5, 19) | F.Cu, straight right |
| 8 | I2C_SDA | J1 pad 5 — (−7.62, −22.46) | OLED pad 4 — (27.81, −25) | F.Cu, lane Y = −19 |
| 9 | I2C_SCL | J1 pad 6 — (−7.62, −19.92) | OLED pad 3 — (25.27, −25) | F.Cu, lane Y = −20.5 |
| 10 | VCC_5V | J2 pad 7 — (7.62, −17.38) | OLED pad 2 — (22.73, −25) | F.Cu, **0.5 mm** wide, lane Y = −18 |
| 11 | RGB_DIN | J2 pad 1 — (7.62, −32.62) | (off-board / hand-wired) | optional — see "Optional RGB" |

**GND** (XIAO J2 pad 5 → OLED J3 pad 1 → encoder C, S2) is **already connected**
through the B.Cu GND pour's thermal reliefs — no manual route needed.

### Tips

- The XIAO header pads are THT, so you can start a B.Cu trace right at the
  pad without a via — the pad already exists on both layers.
- The COL fanout (rows 1–2) and SDA/SCL lanes are all in the empty space
  between the XIAO header (bottom of XIAO body at Y = −17.38) and the matrix
  top (COL trunk top at Y = −6.525). That's ~10 mm of clear F.Cu space.
- For ENC_A and ENC_B, route them parallel on F.Cu — they only carry quadrature
  pulses, no signal-integrity concerns.

### Optional RGB

XIAO D10 (right pin 1, RGB_DIN net) is left unconnected on the PCB. If you
want underglow, solder thin wires from that pad to SK6812 MINI-E LEDs on the
underside of the case. Per-LED wiring:

```
XIAO D10 ──► DIN of LED1
              VDD (LED1) → 5V
              GND (LED1) → GND
              DOUT (LED1) ──► DIN (LED2)
              ...
```

The KMK firmware (`firmware/main.py`) does not enable RGB by default — uncomment
the `kmk.extensions.peg_rgb_matrix` import + setup if you wire them.

## After routing

```bash
# In KiCad GUI:
#   Inspect > Design Rules Checker > Run DRC (should be 0 errors, 0 unconnected)
#   File > Fabrication Outputs > Gerbers... → output to a fresh folder
#   File > Fabrication Outputs > Drill Files... → same folder
#   zip the .gbr + .drl files as gerbers.zip → drop in production/

# OR from the CLI (replace the bundled gerbers):
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
