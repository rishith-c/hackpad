#!/usr/bin/env python3
"""Build a clean schematic diagram of the Hackpad v2 using schemdraw.

Produces assets/schematic.{svg,png} — XIAO RP2040 with every pin labeled,
4x3 switch+diode matrix, EC11 rotary encoder, and 0.91" OLED with their
electrical connections.
"""

import os

import schemdraw
import schemdraw.elements as elm

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ASSETS = os.path.join(ROOT, "assets")
os.makedirs(ASSETS, exist_ok=True)

schemdraw.config(font='sans-serif', fontsize=11)


def build():
    d = schemdraw.Drawing(canvas='svg')

    # ======= XIAO RP2040 IC block =======
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

    # Power flags
    d.add(elm.Vdd().at(xiao.V5).label('+5V', loc='right'))
    d.add(elm.Vdd().at(xiao.V3).label('+3V3', loc='right'))
    d.add(elm.Ground().at(xiao.GND))

    # XIAO signal labels
    for pin, signal, side in [
        ('D0', 'COL0',    'left'),  ('D1',  'COL1',    'left'),
        ('D2', 'COL2',    'left'),  ('D3',  'COL3',    'left'),
        ('D4', 'I2C_SDA', 'left'),  ('D5',  'I2C_SCL', 'left'),
        ('D6', 'ROW0',    'left'),
        ('D7', 'ROW1',    'right'), ('D8',  'ROW2',    'right'),
        ('D9', 'ENC_A',   'right'), ('D10', 'ENC_B',   'right'),
    ]:
        anchor = getattr(xiao, pin)
        line = elm.Line().left().length(0.8) if side == 'left' else elm.Line().right().length(0.8)
        d.add(line.at(anchor).label(signal, loc=side))

    # ======= 4x3 matrix (12 switches + 12 diodes) =======
    grid_origin_x = 8.5
    grid_origin_y = 2.5
    col_pitch = 3.5
    row_pitch = 2.5

    cathode_pts = {}
    switch_a_pts = {}

    for row in range(3):
        for col in range(4):
            idx = row * 4 + col + 1
            sx = grid_origin_x + col * col_pitch
            sy = grid_origin_y - row * row_pitch
            sw = d.add(elm.Switch().right().at((sx, sy)).label(f'SW{idx}', loc='top'))
            di = d.add(elm.Diode().right().at(sw.end).label(f'D{idx}', loc='top'))
            switch_a_pts[(row, col)] = sw.start
            cathode_pts[(row, col)] = di.end

    # COL buses (vertical, left of leftmost switch)
    col_x_bus = [grid_origin_x - 0.5 + c * col_pitch for c in range(4)]
    for col in range(4):
        ytop = grid_origin_y + 1.0
        ybot = grid_origin_y - 2 * row_pitch - 0.5
        d.add(elm.Line().at((col_x_bus[col], ytop)).to((col_x_bus[col], ybot)))
        d.add(elm.Label().at((col_x_bus[col], ytop + 0.3)).label(f'COL{col}'))
        for row in range(3):
            a = switch_a_pts[(row, col)]
            d.add(elm.Line().at(a).to((col_x_bus[col], a.y)))
            d.add(elm.Dot().at((col_x_bus[col], a.y)))

    # ROW buses (horizontal, right of rightmost cathode in row)
    for row in range(3):
        xs = [cathode_pts[(row, c)].x for c in range(4)]
        bus_y = grid_origin_y - row * row_pitch + 1.4
        xleft = min(xs) - 0.4
        xright = max(xs) + 0.8
        d.add(elm.Line().at((xleft, bus_y)).to((xright, bus_y)))
        d.add(elm.Label().at((xright + 0.6, bus_y)).label(f'ROW{row}'))
        for col in range(4):
            c = cathode_pts[(row, col)]
            d.add(elm.Line().at(c).to((c.x, bus_y)))
            d.add(elm.Dot().at((c.x, bus_y)))

    # ======= EC11 encoder =======
    enc_x, enc_y = 11.0, -7.5
    d.add(elm.RBox(w=3.2, h=2.0).at((enc_x, enc_y)).label('EC11\nENC1', loc='center'))
    for off, name, lab in [(0.5, 'A', 'ENC_A'), (0.0, 'C', 'GND'), (-0.5, 'B', 'ENC_B')]:
        x0 = enc_x - 1.6
        y0 = enc_y + off
        d.add(elm.Line().at((x0, y0)).to((x0 - 0.8, y0)))
        d.add(elm.Label().at((x0 - 0.8, y0)).label(lab, loc='left'))
        d.add(elm.Label().at((x0 + 0.15, y0)).label(name, loc='right'))

    # ======= OLED display =======
    oled_x, oled_y = 16.5, -7.5
    d.add(elm.RBox(w=3.2, h=2.6).at((oled_x, oled_y)).label('0.91"\nSSD1306\n128x32\nJ3', loc='center'))
    for off, name, lab in [(1.0, 'GND', 'GND'),
                            (0.35, 'VCC', '+5V'),
                            (-0.35, 'SCL', 'I2C_SCL'),
                            (-1.0, 'SDA', 'I2C_SDA')]:
        x0 = oled_x - 1.6
        y0 = oled_y + off
        d.add(elm.Line().at((x0, y0)).to((x0 - 0.8, y0)))
        d.add(elm.Label().at((x0 - 0.8, y0)).label(lab, loc='left'))
        d.add(elm.Label().at((x0 + 0.15, y0)).label(name, loc='right'))

    # ======= Title =======
    d.add(elm.Label().at((10, 6.0)).label('Hackpad v2 — 12-key + Encoder + OLED Macropad', halign='center'))
    d.add(elm.Label().at((10, 5.4)).label('Schematic (XIAO RP2040, KMK firmware)', halign='center'))

    svg_path = os.path.join(ASSETS, 'schematic.svg')
    png_path = os.path.join(ASSETS, 'schematic.png')
    d.save(svg_path)
    print(f'Wrote {svg_path}')
    try:
        import cairosvg
        cairosvg.svg2png(url=svg_path, write_to=png_path, output_width=2000)
        print(f'Wrote {png_path}')
    except Exception as e:
        print(f'PNG export skipped: {e}')


if __name__ == '__main__':
    build()
