# Firmware

This hackpad runs on **KMK** (CircuitPython). The sources live in [`KMK/`](KMK/):

- [`KMK/main.py`](KMK/main.py) — keyboard + encoder + OLED setup, 2 keymap layers
- [`KMK/code.py`](KMK/code.py) — CircuitPython entry point (imports `main`)
- [`KMK/boot.py`](KMK/boot.py) — disables CIRCUITPY auto-reload while plugged in

## Flashing

1. Download **CircuitPython for Seeed XIAO RP2040** from
   <https://circuitpython.org/board/seeeduino_xiao_rp2040/> (the `.uf2`).
2. Double-tap the XIAO BOOT button to enter bootloader mode (a `RPI-RP2`
   drive will mount). Drag the `.uf2` onto it. The XIAO will reboot into
   CircuitPython and a `CIRCUITPY` drive will appear.
3. Download the latest [KMK firmware](https://github.com/KMKfw/kmk_firmware)
   release zip. Copy the `kmk/` folder from the zip onto `CIRCUITPY`.
4. Copy `main.py`, `code.py`, and `boot.py` from this folder onto
   `CIRCUITPY` (overwrite anything that's there).
5. Done. The macropad will start working immediately. Unplug to disable
   auto-reload before editing `main.py` to avoid mid-keystroke resets.

## Default keymap

| Layer | Top-L | Top-R | Bot-L | Bot-R | Encoder turn | Encoder push |
|---|---|---|---|---|---|---|
| 0 (default) | A | B | C | hold for layer 1 | volume +/− | mute |
| 1 (media) | mute | play/pause | prev track | (hold) | next/prev track | play/pause |

Edit `keyboard.keymap` and `encoder_handler.map` in `KMK/main.py` to change.
