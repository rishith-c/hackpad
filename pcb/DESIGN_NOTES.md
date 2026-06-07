# Design notes

## Why a 4-key + encoder build (and not 16 keys)?

The Hack Club Hackpad submission requires **less than 16 inputs** and a
PCB ≤ 100 × 100 mm. A 16-key (4×4) build would max out the input count
and need a bigger board. The 4-key + 1-encoder layout is the smallest
"complete" macropad that uses every kind of input the kit ships:
keyboard switch, rotary encoder, OLED display.

It also tracks the [Orpheuspad reference design](https://github.com/hackclub/hackpad/tree/main/hackpads/orpheuspad)
so reviewers see something familiar.

## Pin budget

The XIAO RP2040 exposes 11 usable GPIO. This build uses 10 of them:

| Peripheral | Pins |
|---|---|
| 2×2 matrix | 4 (2 rows + 2 cols) |
| EC11 encoder + push | 3 (A, B, S1) |
| OLED (I²C SDA / SCL) | 2 |
| RGB data (optional, off-PCB) | 1 |
| **Total** | **10 / 11** |

D9 (GP4) is left as a SPARE — wire up a second encoder, an external LED, or
a 5th switch in firmware later if you want.

## Alternate builds (without rebuilding the PCB)

You can re-purpose the firmware to act as any of these by re-flashing — the
pin map carries over because every input is broken out on the XIAO socket.

### Build A — current default

4 keys + 1 encoder + OLED. KMK with 2 layers. See `firmware/main.py`.

### Build B — 5 keys (no encoder)

Wire a 5th switch between XIAO D9 (GP4) and GND. Update `firmware/main.py`:

```python
# replace encoder pins with a 5th direct-wired key on GP4
from kmk.modules.keys import KC
# matrix stays 2x2; add a direct key by reading board.D9 in a custom loop,
# or extend the matrix to 3 rows.
```

### Build C — twin-encoder DJ pad

Wire a second encoder using `board.D9` (GP4) and one of the matrix pins
(reduce matrix to 1 row × 2 cols, 2 keys total). Update the encoder block in
`firmware/main.py`:

```python
encoder_handler.pins = (
    (board.D2, board.D3, board.D8, False),   # encoder 1 (current)
    (board.D9, board.D0, None, False),       # encoder 2 (steals COL0)
)
```

## RGB reality check

The kit ships 20 SK6812 MINI-E LEDs. These are reverse-mount SMD and are
"the single hardest solder in the kit". This board intentionally **does not
place** the SK6812 footprints — instead, D10 (GP3) is broken out on the XIAO
socket so you can solder thin wires to a separately-mounted SK6812 strip on
the underside of the case. Populate as few or as many as you like (KMK is
configured for 0 by default; `extensions.peg_rgb_matrix.PegRGB(num_leds=N)`
to enable N LEDs).

## OLED pin order

The Hack Club kit OLED uses the **GND - VCC - SCL - SDA** order. This board's
4-pin OLED header matches that order (J3 pads 1–4). Double-check the pin
labels on your specific module before soldering — some 0.91" OLEDs flip
SCL/SDA and you'll have to bend the header pins or use a 4-wire harness.

## ROW trunk offset trick

To keep the B.Cu row trunk from shorting through the diode anode pads (which
sit at the same Y as the cathode pads), the trunk is offset **1.5 mm above**
the pad row, with a short 1.5 mm vertical tab from each cathode pad up to
the trunk. Anode pads (different net, same Y as cathodes) end up 1.5 mm away
from the trunk centerline — comfortably outside the 0.2 mm clearance limit.
