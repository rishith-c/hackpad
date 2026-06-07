"""Hackpad firmware - 4-key macropad + rotary encoder + OLED.

Runs on KMK (CircuitPython) on a Seeed XIAO RP2040.
Flash CircuitPython for XIAO RP2040, copy the kmk/ library to the drive,
then drop this file as `code.py` (or `main.py`).

Pin map:
  D0  GP26 = COL0      D6  GP0  = ROW0
  D1  GP27 = COL1      D7  GP1  = ROW1
  D2  GP28 = ENC_A     D8  GP2  = ENC_PUSH
  D3  GP29 = ENC_B     D10 GP3  = RGB_DIN (optional)
  D4  GP6  = I2C SDA   D5  GP7  = I2C SCL  (OLED on I2C1)
"""

import board

from kmk.kmk_keyboard import KMKKeyboard
from kmk.keys import KC
from kmk.matrix import DiodeOrientation
from kmk.modules.layers import Layers
from kmk.modules.encoder import EncoderHandler
from kmk.extensions.display import Display, TextEntry
from kmk.extensions.display.ssd1306 import SSD1306

keyboard = KMKKeyboard()
keyboard.modules.append(Layers())

# ---- 2x2 matrix --------------------------------------------------------
keyboard.col_pins = (board.D0, board.D1)              # COL0, COL1
keyboard.row_pins = (board.D6, board.D7)              # ROW0, ROW1
keyboard.diode_orientation = DiodeOrientation.COL2ROW

# Keymap: 2 rows x 2 cols = 4 keys per layer, plus an encoder column.
# Layer 0 = shortcuts, Layer 1 = media (hold encoder push to switch?).
keyboard.keymap = [
    [
        # Layer 0: app shortcuts
        KC.A,  KC.B,
        KC.C,  KC.MO(1),     # bottom-right key = layer hold
    ],
    [
        # Layer 1: media
        KC.MUTE, KC.MPLY,
        KC.MPRV, KC.TRNS,
    ],
]

# ---- Rotary encoder ----------------------------------------------------
encoder_handler = EncoderHandler()
keyboard.modules.append(encoder_handler)
# (pin_a, pin_b, button_pin, is_inverted)
encoder_handler.pins = (
    (board.D2, board.D3, board.D8, False),
)
# Per-layer encoder map: (clockwise, counter-clockwise, push)
encoder_handler.map = [
    ((KC.VOLU, KC.VOLD, KC.MUTE),),   # layer 0
    ((KC.MNXT, KC.MPRV, KC.MPLY),),   # layer 1
]

# ---- OLED display (optional, comment out if no display) ----------------
try:
    import busio
    i2c_bus = busio.I2C(board.D5, board.D4)   # SCL=D5, SDA=D4
    display = Display(
        display=SSD1306(i2c_bus, device_address=0x3C),
        entries=[
            TextEntry(text="Hackpad", x=0, y=0),
            TextEntry(text="L0", x=0, y=16, layer=0),
            TextEntry(text="L1", x=0, y=16, layer=1),
        ],
        brightness=0.5,
    )
    keyboard.extensions.append(display)
except Exception as e:   # noqa: BLE001
    # No display attached — keep running.
    pass


if __name__ == "__main__":
    keyboard.go()
