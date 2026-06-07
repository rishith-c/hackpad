# Design notes

## Why a 12-key + encoder + OLED build

The Hack Club Hackpad submission allows **less than 16 inputs** and a
**≤ 100 × 100 mm** PCB. The XIAO RP2040 exposes **11 usable GPIO**. This
build hits the most loaded point in that 3-way constraint:

- **12 MX keys** (4 cols × 3 rows matrix, 7 pins)
- **1 EC11 rotary encoder** (A/B only, no push — 2 pins)
- **1 0.91" OLED** display (I²C, 2 pins)
- **= 13 inputs · 11 / 11 GPIO · 95 × 95 mm**

That's every kind of input the kit ships in the densest configuration the
rules allow. (The 16-key full numpad designs are at the edge of the input
limit and have no room for an encoder; the orpheuspad-style 4-key builds
have lots of free GPIO but few keys.)

## Pin budget

| Peripheral | Pins | Which GPIOs |
|---|---|---|
| 4×3 matrix | 7 | D0–D3 (COL0..3) + D6–D8 (ROW0..2) |
| EC11 encoder (A, B) | 2 | D9, D10 |
| OLED I²C (SDA, SCL) | 2 | D4, D5 |
| **Total** | **11 / 11** | every usable GPIO consumed |

D9 (GP4) was the spare in v1; v2 spends it on the encoder.

## Alternate firmware tweaks (no PCB change needed)

The pin map is broken out on the XIAO socket, so you can repurpose without
re-fabbing the board — just flash a different `firmware/KMK/main.py`:

### 14 inputs (drop OLED, add encoder push + RGB)

Wire the SK6812 chain off **D10** (currently ENC_B) and the encoder push
button off **D4** (currently SDA). Rebuild firmware to drop the OLED and
add `EncoderHandler` with a button pin. You give up the layer-name
display, gain a click+rotate + RGB underglow.

### 9 keys + 2 encoders + OLED

Shrink the matrix to a 3×3 (uses D0–D2 + D6–D8 = 6 pins), wire encoder 2
across **D3** and **D9**, keep OLED. 10 inputs but two knobs.

## ROW trunk offset trick (carried over from v1)

To keep the B.Cu row trunk from shorting through other columns' diode
anode pads, the trunk is offset **1.5 mm above** the pad row, with a
short 1.5 mm vertical tab from each cathode pad up to the trunk. The
anode pads end up 1.5 mm away from the trunk centerline — comfortably
outside the 0.2 mm clearance limit. See [build_pcb.py](../build_scripts/build_pcb.py)
`_route_matrix()`.

## OLED pin order

The Hack Club kit OLED uses **GND – VCC – SCL – SDA**. This board's
J3 header (rotated 90°) matches that order on pads 1–4.

## RGB

No SK6812 on the PCB — every GPIO is taken. Hand-wire a few LEDs off
the unused side of the encoder pad if you want underglow; firmware does
not enable RGB by default.
