#!/usr/bin/env python3
"""Build a clean schematic diagram of the Hackpad using schemdraw.

Produces assets/schematic.png (and .svg) showing the XIAO RP2040, the 2x2
key matrix with diodes, the EC11 rotary encoder with push-switch, and the
0.91" OLED display with their actual electrical connections.
"""

import os

import schemdraw
import schemdraw.elements as elm

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ASSETS = os.path.join(ROOT, "assets")
os.makedirs(ASSETS, exist_ok=True)

schemdraw.config(font='sans-serif', fontsize=11)


def label_at(d, xy, text, halign='left'):
    d.add(elm.Label().at(xy).label(text, halign=halign))


def build():
    d = schemdraw.Drawing(canvas='svg')

    # ====================== XIAO RP2040 IC block ======================
    xiao = elm.Ic(
        pins=[
            elm.IcPin(name='D0/GP26',  side='left',  pin='1',  anchorname='D0'),
            elm.IcPin(name='D1/GP27',  side='left',  pin='2',  anchorname='D1'),
            elm.IcPin(name='D2/GP28',  side='left',  pin='3',  anchorname='D2'),
            elm.IcPin(name='D3/GP29',  side='left',  pin='4',  anchorname='D3'),
            elm.IcPin(name='D4/GP6',   side='left',  pin='5',  anchorname='D4'),
            elm.IcPin(name='D5/GP7',   side='left',  pin='6',  anchorname='D5'),
            elm.IcPin(name='D6/GP0',   side='left',  pin='7',  anchorname='D6'),
            elm.IcPin(name='5V',       side='right', pin='14', anchorname='V5'),
            elm.IcPin(name='3V3',      side='right', pin='13', anchorname='V3'),
            elm.IcPin(name='GND',      side='right', pin='12', anchorname='GND'),
            elm.IcPin(name='D7/GP1',   side='right', pin='11', anchorname='D7'),
            elm.IcPin(name='D8/GP2',   side='right', pin='10', anchorname='D8'),
            elm.IcPin(name='D9/GP4',   side='right', pin='9',  anchorname='D9'),
            elm.IcPin(name='D10/GP3',  side='right', pin='8',  anchorname='D10'),
        ],
        edgepadH=0.4, edgepadW=0.7, pinspacing=0.7, leadlen=0.5,
        label='XIAO\nRP2040\nU1',
    )
    d.add(xiao.at((0, 0)))

    # Power flags on XIAO
    d.add(elm.Vdd().at(xiao.V5).label('+5V', loc='right'))
    d.add(elm.Vdd().at(xiao.V3).label('+3V3', loc='right'))
    d.add(elm.Ground().at(xiao.GND))

    # XIAO signal labels (stub + label, NO redundant logical wire)
    for pin, signal, side in [
        ('D0', 'COL0',     'left'),  ('D1',  'COL1',     'left'),
        ('D2', 'ENC_A',    'left'),  ('D3',  'ENC_B',    'left'),
        ('D4', 'I2C_SDA',  'left'),  ('D5',  'I2C_SCL',  'left'),
        ('D6', 'ROW0',     'left'),
        ('D7', 'ROW1',     'right'), ('D8',  'ENC_PUSH', 'right'),
        ('D10','RGB_DIN',  'right'),
    ]:
        anchor = getattr(xiao, pin)
        line = elm.Line().left().length(0.8) if side == 'left' else elm.Line().right().length(0.8)
        d.add(line.at(anchor).label(signal, loc=side))

    # ====================== Switch matrix (2x2) + diodes ======================
    # Lay out 4 switch+diode pairs on a 2x2 grid to the right of the XIAO.
    grid_origin_x = 8.5
    grid_origin_y = 1.5
    col_pitch = 3.5
    row_pitch = 2.6

    cathode_pts = {}   # diode cathode position per (row, col)
    switch_a_pts = {}  # switch pad A position per (row, col)

    for row in range(2):
        for col in range(2):
            idx = row * 2 + col + 1
            sx = grid_origin_x + col * col_pitch
            sy = grid_origin_y - row * row_pitch
            sw = d.add(elm.Switch().right().at((sx, sy)).label(f'SW{idx}', loc='top'))
            di = d.add(elm.Diode().right().at(sw.end).label(f'D{idx}', loc='top'))
            switch_a_pts[(row, col)] = sw.start
            cathode_pts[(row, col)] = di.end

    # COL buses: vertical line at the LEFT of each column connects pad A's.
    col_x_bus = [grid_origin_x - 0.5, grid_origin_x + col_pitch - 0.5]
    for col in range(2):
        # Bus line spans both rows + a bit above/below
        ytop = grid_origin_y + 1.0
        ybot = grid_origin_y - row_pitch - 0.5
        d.add(elm.Line().at((col_x_bus[col], ytop)).to((col_x_bus[col], ybot)))
        d.add(elm.Label().at((col_x_bus[col], ytop + 0.3)).label(f'COL{col}'))
        for row in range(2):
            a = switch_a_pts[(row, col)]
            d.add(elm.Line().at(a).to((col_x_bus[col], a.y)))
            d.add(elm.Dot().at((col_x_bus[col], a.y)))

    # ROW buses: horizontal line at the RIGHT of each row connects cathodes.
    row_y_bus = [grid_origin_y + 1.4, grid_origin_y - row_pitch + 1.4]
    for row in range(2):
        xs = [cathode_pts[(row, c)].x for c in range(2)]
        xleft = min(xs) - 0.4
        xright = max(xs) + 0.8
        d.add(elm.Line().at((xleft, row_y_bus[row])).to((xright, row_y_bus[row])))
        d.add(elm.Label().at((xright + 0.5, row_y_bus[row])).label(f'ROW{row}'))
        for col in range(2):
            c = cathode_pts[(row, col)]
            d.add(elm.Line().at(c).to((c.x, row_y_bus[row])))
            d.add(elm.Dot().at((c.x, row_y_bus[row])))

    # ====================== EC11 rotary encoder + push-switch ======================
    enc_x, enc_y = 9.0, -4.5
    enc = elm.RBox(w=3.2, h=2.4)
    d.add(enc.at((enc_x, enc_y)).label('EC11\nENC1', loc='center'))
    # Left side: A, C(GND), B
    for off, name, lab in [(0.7, 'A', 'ENC_A'), (0.0, 'C', 'GND'), (-0.7, 'B', 'ENC_B')]:
        x0 = enc_x - 1.6  # left edge of box
        y0 = enc_y + off
        d.add(elm.Line().at((x0, y0)).to((x0 - 0.8, y0)))
        d.add(elm.Label().at((x0 - 0.8, y0)).label(lab, loc='left'))
        d.add(elm.Label().at((x0 + 0.15, y0)).label(name, loc='right'))
    # Right side: S1, S2 (push-switch)
    for off, name, lab in [(0.5, 'S1', 'ENC_PUSH'), (-0.5, 'S2', 'GND')]:
        x0 = enc_x + 1.6
        y0 = enc_y + off
        d.add(elm.Line().at((x0, y0)).to((x0 + 0.8, y0)))
        d.add(elm.Label().at((x0 + 0.8, y0)).label(lab, loc='right'))
        d.add(elm.Label().at((x0 - 0.15, y0)).label(name, loc='left'))

    # ====================== OLED display (4-pin header) ======================
    oled_x, oled_y = 9.0, -8.5
    oled = elm.RBox(w=3.2, h=2.4)
    d.add(oled.at((oled_x, oled_y)).label('0.91"\nSSD1306\n128x32\nJ3', loc='center'))
    for off, name, lab in [(0.9, 'GND', 'GND'),
                            (0.3, 'VCC', '+5V'),
                            (-0.3, 'SCL', 'I2C_SCL'),
                            (-0.9, 'SDA', 'I2C_SDA')]:
        x0 = oled_x - 1.6
        y0 = oled_y + off
        d.add(elm.Line().at((x0, y0)).to((x0 - 0.8, y0)))
        d.add(elm.Label().at((x0 - 0.8, y0)).label(lab, loc='left'))
        d.add(elm.Label().at((x0 + 0.15, y0)).label(name, loc='right'))

    # ====================== Title ======================
    d.add(elm.Label().at((6, 5.0)).label('Hackpad — 4-key + Encoder + OLED Macropad', halign='center'))
    d.add(elm.Label().at((6, 4.5)).label('Schematic v1.0 (XIAO RP2040, KMK firmware)', halign='center'))

    svg_path = os.path.join(ASSETS, 'schematic.svg')
    png_path = os.path.join(ASSETS, 'schematic.png')
    d.save(svg_path)
    print(f'Wrote {svg_path}')
    try:
        import cairosvg
        cairosvg.svg2png(url=svg_path, write_to=png_path, output_width=1800)
        print(f'Wrote {png_path}')
    except Exception as e:
        print(f'PNG export skipped (cairosvg not installed): {e}')


if __name__ == '__main__':
    build()
