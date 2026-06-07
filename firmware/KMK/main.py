"""Hackpad firmware - 12-key macropad (4x3 matrix) + EC11 encoder + OLED.

Runs on KMK (CircuitPython) on a Seeed XIAO RP2040.
Flash CircuitPython for XIAO RP2040, copy the kmk/ library to the drive,
then drop this file as `code.py` (or `main.py`).

Pin map (all 11 GPIO used):
  D0  GP26 = COL0      D6  GP0  = ROW0
  D1  GP27 = COL1      D7  GP1  = ROW1
  D2  GP28 = COL2      D8  GP2  = ROW2
  D3  GP29 = COL3      D9  GP4  = ENC_A
  D4  GP6  = I2C SDA   D10 GP3  = ENC_B
  D5  GP7  = I2C SCL

Matrix is 4 columns × 3 rows = 12 keys, COL2ROW (1N4148 diodes,
cathode-stripe toward the row trace).
"""

import board

from kmk.kmk_keyboard import KMKKeyboard
from kmk.keys import KC
from kmk.matrix import DiodeOrientation
from kmk.modules.layers import Layers
from kmk.modules.encoder import EncoderHandler

keyboard = KMKKeyboard()
keyboard.modules.append(Layers())

# ---- 4×3 matrix --------------------------------------------------------
keyboard.col_pins = (board.D0, board.D1, board.D2, board.D3)   # COL0..COL3
keyboard.row_pins = (board.D6, board.D7, board.D8)             # ROW0..ROW2
keyboard.diode_orientation = DiodeOrientation.COL2ROW

# Keymap layout: 3 rows × 4 cols = 12 keys per layer.
keyboard.keymap = [
    [
        # Layer 0 — app shortcuts
        KC.A,   KC.B,   KC.C,   KC.D,
        KC.E,   KC.F,   KC.G,   KC.H,
        KC.I,   KC.J,   KC.K,   KC.MO(1),    # bottom-right = hold layer 1
    ],
    [
        # Layer 1 — media controls
        KC.MUTE,  KC.MPLY,  KC.MNXT,  KC.MPRV,
        KC.VOLU,  KC.VOLD,  KC.NO,    KC.NO,
        KC.NO,    KC.NO,    KC.MO(2), KC.TRNS,
    ],
    [
        # Layer 2 — numpad (tap-tap from layer 0 → layer 1 → layer 2)
        KC.N7, KC.N8, KC.N9, KC.PLUS,
        KC.N4, KC.N5, KC.N6, KC.MINS,
        KC.N1, KC.N2, KC.N3, KC.TRNS,
    ],
]

# ---- Rotary encoder ----------------------------------------------------
encoder_handler = EncoderHandler()
keyboard.modules.append(encoder_handler)
# (pin_a, pin_b, button_pin_or_None, is_inverted)
encoder_handler.pins = (
    (board.D9, board.D10, None, False),
)
# Per-layer encoder map: (clockwise, counter-clockwise)
encoder_handler.map = [
    ((KC.VOLU, KC.VOLD),),       # layer 0 — volume
    ((KC.MNXT, KC.MPRV),),       # layer 1 — track skip
    ((KC.PPLS, KC.PMNS),),       # layer 2 — numpad + / -
]

# ---- OLED display (optional; skipped if not connected) ----------------
try:
    import busio
    from kmk.extensions.display import Display, TextEntry
    from kmk.extensions.display.ssd1306 import SSD1306
    i2c_bus = busio.I2C(board.D5, board.D4)   # SCL=D5, SDA=D4
    display = Display(
        display=SSD1306(i2c_bus, device_address=0x3C),
        entries=[
            TextEntry(text="Hackpad", x=0, y=0),
            TextEntry(text="L0 default",   x=0, y=16, layer=0),
            TextEntry(text="L1 media",     x=0, y=16, layer=1),
            TextEntry(text="L2 numpad",    x=0, y=16, layer=2),
        ],
        brightness=0.5,
    )
    keyboard.extensions.append(display)
except Exception:   # noqa: BLE001
    # No display attached — keep running.
    pass


if __name__ == "__main__":
    keyboard.go()
