#!/usr/bin/env python3
"""Build the Hackpad KiCad PCB programmatically with pcbnew.

Design: 4-key macropad (2x2 matrix) + EC11 rotary encoder + 0.91" OLED on a
Seeed XIAO RP2040 - matches Hack Club Hackpad submission rules:
  - PCB <= 100mm x 100mm (this is 90 x 70 mm)
  - < 16 inputs (4 keys + 1 encoder w/ push = 5 inputs)
  - 2 layers, through-hole XIAO RP2040
  - OLED pin order: GND - VCC - SCL - SDA (kit standard)

Layout:
  - XIAO at top-center (0, -25), USB-C faces top edge of board
  - OLED 4-pin header at top-right (28, -25)
  - 2x2 switches at bottom-left (centered on (-22, +5))
  - EC11 encoder at bottom-right (+22, +12)
  - 4 M3 mounting holes at (+/-40, +/-30)
  - 2 SK6812 LEDs (one underglow, one accent) optional

Pin map (XIAO RP2040):
   D0 (GP26) = COL0     D6 (GP0)  = ROW0
   D1 (GP27) = COL1     D7 (GP1)  = ROW1
   D2 (GP28) = ENC_A    D8 (GP2)  = ENC_PUSH
   D3 (GP29) = ENC_B    D9 (GP4)  = (spare)
   D4 (GP6)  = I2C_SDA  D10 (GP3) = RGB_DIN
   D5 (GP7)  = I2C_SCL
"""

import os
import sys

import pcbnew
from pcbnew import (
    BOARD, NETINFO_ITEM, PCB_SHAPE, PCB_TRACK, PCB_VIA, VECTOR2I, ZONE,
)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PCB_DIR = os.path.join(ROOT, "pcb")
KICAD_FP_ROOT = "/Applications/KiCad.app/Contents/SharedSupport/footprints"

PROJECT_NAME = "hackpad"
PCB_PATH = os.path.join(PCB_DIR, f"{PROJECT_NAME}.kicad_pcb")

# ---- design constants ----
BOARD_W_MM = 90.0
BOARD_H_MM = 70.0
BOARD_CORNER_R_MM = 3.0
TRACK_SIG_MM = 0.25
TRACK_PWR_MM = 0.5
VIA_DRILL_MM = 0.4
VIA_DIA_MM = 0.8
CLEARANCE_MM = 0.2

# Switch grid (KiCad mm). Origin = board center. KiCad Y positive = downward.
SW_PITCH = 19.05
SW_CENTER_X = -22.0       # centered between the two columns
SW_CENTER_Y = 5.0         # centered between the two rows
SW_X = [SW_CENTER_X - SW_PITCH / 2, SW_CENTER_X + SW_PITCH / 2]   # cols 0,1
SW_Y = [SW_CENTER_Y - SW_PITCH / 2, SW_CENTER_Y + SW_PITCH / 2]   # rows 0,1
DIODE_DY = -5.0           # diode origin Y offset from switch (above)

OLED_XY = (24.0, -25.0)
XIAO_XY = (0.0, -25.0)
ENC_XY  = (22.0, 14.0)
MOUNT_HOLES = [(-40.0, -30.0), (40.0, -30.0), (40.0, 30.0), (-40.0, 30.0)]
# SK6812 LEDs are optional and hand-wired off XIAO D10 if desired (the kit
# ships 20 MINI-E LEDs but they are reverse-mount and difficult to solder).
# Footprints are NOT placed on the PCB to keep routing clean.
LED_POSITIONS = []

_IO = pcbnew.PCB_IO_KICAD_SEXPR()


def mm(x):
    return pcbnew.FromMM(x)


def vp(x_mm, y_mm):
    return VECTOR2I(mm(x_mm), mm(y_mm))


def load_footprint(lib, name):
    fp = _IO.FootprintLoad(os.path.join(KICAD_FP_ROOT, f"{lib}.pretty"), name)
    if fp is None:
        raise RuntimeError(f"Footprint not found: {lib}:{name}")
    return fp


def add_footprint(board, lib, name, ref, value, x_mm, y_mm, rot_deg=0.0):
    fp = load_footprint(lib, name)
    fp.SetReference(ref)
    fp.SetValue(value)
    fp.SetPosition(vp(x_mm, y_mm))
    if rot_deg:
        fp.SetOrientationDegrees(rot_deg)
    board.Add(fp)
    return fp


def ensure_net(board, name):
    existing = board.FindNet(name)
    if existing is not None and existing.GetNetCode() > 0:
        return existing
    n = NETINFO_ITEM(board, name)
    board.Add(n)
    return n


def pad_by_name(fp, pad_name):
    for p in fp.Pads():
        if p.GetName() == pad_name:
            return p
    raise RuntimeError(f"{fp.GetReference()} has no pad {pad_name}")


def pad_xy(fp, name):
    p = pad_by_name(fp, name).GetPosition()
    return (pcbnew.ToMM(p.x), pcbnew.ToMM(p.y))


def connect_pad(fp, pad_name, net):
    pad_by_name(fp, pad_name).SetNet(net)


def add_track(board, p1, p2, net, layer=pcbnew.F_Cu, width=TRACK_SIG_MM):
    if p1 == p2:
        return None
    t = PCB_TRACK(board)
    t.SetStart(vp(*p1))
    t.SetEnd(vp(*p2))
    t.SetLayer(layer)
    t.SetWidth(mm(width))
    t.SetNet(net)
    board.Add(t)
    return t


def add_path(board, pts, net, layer=pcbnew.F_Cu, width=TRACK_SIG_MM):
    for a, b in zip(pts, pts[1:]):
        add_track(board, a, b, net, layer, width)


def add_via(board, p_mm, net):
    v = PCB_VIA(board)
    v.SetPosition(vp(*p_mm))
    v.SetWidth(mm(VIA_DIA_MM))
    v.SetDrill(mm(VIA_DRILL_MM))
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetNet(net)
    board.Add(v)
    return v


def add_rounded_rect_outline(board, w, h, r):
    hw, hh = w / 2.0, h / 2.0
    for a, b in [
        ((-hw + r, -hh), (hw - r, -hh)),
        ((-hw + r, hh), (hw - r, hh)),
        ((-hw, -hh + r), (-hw, hh - r)),
        ((hw, -hh + r), (hw, hh - r)),
    ]:
        s = PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(vp(*a))
        s.SetEnd(vp(*b))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(mm(0.1))
        board.Add(s)
    for center, start, end in [
        ((-hw + r, -hh + r), (-hw, -hh + r), (-hw + r, -hh)),
        ((hw - r, -hh + r),  (hw - r, -hh),  (hw, -hh + r)),
        ((hw - r, hh - r),   (hw, hh - r),   (hw - r, hh)),
        ((-hw + r, hh - r),  (-hw + r, hh),  (-hw, hh - r)),
    ]:
        a = PCB_SHAPE(board)
        a.SetShape(pcbnew.SHAPE_T_ARC)
        a.SetCenter(vp(*center))
        a.SetStart(vp(*start))
        a.SetEnd(vp(*end))
        a.SetLayer(pcbnew.Edge_Cuts)
        a.SetWidth(mm(0.1))
        board.Add(a)


def add_gnd_zone(board, gnd_net, layer, w, h):
    z = ZONE(board)
    z.SetLayer(layer)
    z.SetNet(gnd_net)
    z.SetIsRuleArea(False)
    z.SetAssignedPriority(0)
    z.SetLocalClearance(mm(CLEARANCE_MM))
    z.SetMinThickness(mm(0.2))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetThermalReliefGap(mm(0.4))
    z.SetThermalReliefSpokeWidth(mm(0.5))
    pts = pcbnew.SHAPE_LINE_CHAIN()
    hw, hh = w / 2.0, h / 2.0
    m = 0.5
    pts.Append(mm(-hw + m), mm(-hh + m))
    pts.Append(mm(hw - m),  mm(-hh + m))
    pts.Append(mm(hw - m),  mm(hh - m))
    pts.Append(mm(-hw + m), mm(hh - m))
    pts.SetClosed(True)
    z.AddPolygon(pts)
    board.Add(z)
    return z


def add_silk_text(board, text, x, y, size=2.0, layer=pcbnew.F_SilkS, mirror=False):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(text)
    t.SetPosition(vp(x, y))
    t.SetLayer(layer)
    t.SetTextThickness(mm(0.2))
    t.SetTextWidth(mm(size))
    t.SetTextHeight(mm(size))
    t.SetMirrored(mirror)
    board.Add(t)
    return t


def _dbg(msg):
    print(msg, flush=True)


def build():
    _dbg("[1] Creating board")
    board = BOARD()
    board.SetCopperLayerCount(2)
    tb = board.GetTitleBlock()
    tb.SetTitle("Hackpad - 4-Key + Encoder Macropad")
    tb.SetCompany("Hackpad")
    tb.SetRevision("1.0")
    board.SetTitleBlock(tb)
    dsn = board.GetDesignSettings()
    dsn.m_CopperEdgeClearance = mm(0.3)
    dsn.m_MinClearance = mm(CLEARANCE_MM)

    # ---- nets ----
    names = ["VCC_5V", "GND", "+3V3",
             "I2C_SDA", "I2C_SCL",
             "RGB_DIN",
             "ENC_A", "ENC_B", "ENC_PUSH",
             "COL0", "COL1", "ROW0", "ROW1"]
    names += [f"SW{i+1}_K" for i in range(4)]
    names += [f"LED_LINK_{i+1}" for i in range(1)]
    nets = {n: ensure_net(board, n) for n in names}
    gnd, vcc = nets["GND"], nets["VCC_5V"]

    # ---- matrix: 4 switches + 4 diodes ----
    # Same construction as before: diode horizontal under switch, anode at
    # (sx - 3.81, sy - 5), cathode at (sx + 3.81, sy - 5). ROW trunk on B.Cu
    # offset 1.5mm above pad row to clear all anodes. Switch->anode bridge L
    # on F.Cu at (sx - 6.35) and (sy - 5).
    _dbg("[2] Switches + diodes")
    sw_fps, d_fps = {}, {}
    for row in range(2):
        for col in range(2):
            idx = row * 2 + col + 1
            sx, sy = SW_X[col], SW_Y[row]
            sw = add_footprint(board, "Button_Switch_Keyboard",
                               "SW_Cherry_MX_1.00u_PCB",
                               f"SW{idx}", "MX", sx, sy)
            d = add_footprint(board, "Diode_THT",
                              "D_DO-35_SOD27_P7.62mm_Horizontal",
                              f"D{idx}", "1N4148",
                              sx - 3.81, sy + DIODE_DY)
            sw_fps[idx], d_fps[idx] = sw, d
            connect_pad(sw, "1", nets[f"COL{col}"])
            connect_pad(sw, "2", nets[f"SW{idx}_K"])
            connect_pad(d, "1", nets[f"SW{idx}_K"])
            connect_pad(d, "2", nets[f"ROW{row}"])

    # ---- XIAO RP2040: two 1x7 pin headers, 15.24mm apart ----
    _dbg("[3] XIAO headers")
    xiao_x, xiao_y = XIAO_XY
    left_origin_x = xiao_x - 7.62
    right_origin_x = xiao_x + 7.62
    pin1_y = xiao_y - 7.62
    xiao_left = add_footprint(board, "Connector_PinHeader_2.54mm",
                              "PinHeader_1x07_P2.54mm_Vertical",
                              "J1", "XIAO_L",
                              left_origin_x, pin1_y)
    xiao_right = add_footprint(board, "Connector_PinHeader_2.54mm",
                               "PinHeader_1x07_P2.54mm_Vertical",
                               "J2", "XIAO_R",
                               right_origin_x, pin1_y)
    # XIAO pin map (USB-C end = top, less Y):
    #  Left  1..7: D0(COL0)  D1(COL1)  D2(ENC_A) D3(ENC_B) D4(SDA)   D5(SCL)   D6(ROW0)
    #  Right 1..7: D10(RGB)  D9(spare) D8(PUSH)  D7(ROW1)  GND       3V3       5V
    left_nets = [nets["COL0"], nets["COL1"], nets["ENC_A"], nets["ENC_B"],
                 nets["I2C_SDA"], nets["I2C_SCL"], nets["ROW0"]]
    right_nets = [nets["RGB_DIN"], ensure_net(board, "SPARE"),
                  nets["ENC_PUSH"], nets["ROW1"],
                  nets["GND"], nets["+3V3"], nets["VCC_5V"]]
    for i, n in enumerate(left_nets, 1):
        connect_pad(xiao_left, str(i), n)
    for i, n in enumerate(right_nets, 1):
        connect_pad(xiao_right, str(i), n)

    # ---- OLED 4-pin header (pad order: GND, VCC, SCL, SDA -- kit standard) ----
    _dbg("[4] OLED header")
    ox, oy = OLED_XY
    oled = add_footprint(board, "Connector_PinHeader_2.54mm",
                         "PinHeader_1x04_P2.54mm_Vertical",
                         "J3", "OLED",
                         ox - (3 * 2.54) / 2.0, oy, rot_deg=90.0)
    for i, n in enumerate([nets["GND"], nets["VCC_5V"], nets["I2C_SCL"],
                           nets["I2C_SDA"]], 1):
        connect_pad(oled, str(i), n)

    # ---- EC11 rotary encoder with push-switch ----
    _dbg("[5] Rotary encoder")
    ex, ey = ENC_XY
    enc = add_footprint(board, "Rotary_Encoder",
                        "RotaryEncoder_Alps_EC11E-Switch_Vertical_H20mm",
                        "ENC1", "EC11", ex, ey)
    # Pads: A (encoder phase), B (encoder phase), C (common = GND),
    #       MP x2 (mechanical), S1, S2 (push-button switch)
    connect_pad(enc, "A", nets["ENC_A"])
    connect_pad(enc, "B", nets["ENC_B"])
    connect_pad(enc, "C", gnd)
    connect_pad(enc, "S1", nets["ENC_PUSH"])
    connect_pad(enc, "S2", gnd)
    # MP pins are mechanical only — left unconnected (no net assignment).

    # SK6812 LEDs intentionally not placed (hand-wired off XIAO D10).

    # ---- Mounting holes ----
    _dbg("[7] Mounting holes")
    for i, (mx, my) in enumerate(MOUNT_HOLES, 1):
        add_footprint(board, "MountingHole", "MountingHole_3.2mm_M3",
                      f"MH{i}", "M3", mx, my)

    # ---- Edge cuts ----
    _dbg("[8] Edge cuts")
    add_rounded_rect_outline(board, BOARD_W_MM, BOARD_H_MM, BOARD_CORNER_R_MM)

    # ---- Silkscreen branding ----
    _dbg("[9] Silkscreen")
    add_silk_text(board, "HACKPAD", -5, 32, size=2.5)
    add_silk_text(board, "v1.0", 30, 32, size=1.5)

    # ---- Matrix routing only (clean, proven) ----
    # XIAO fanout, OLED, encoder, RGB are left as ratlines for ~5 min of
    # interactive Route > Single Track in the KiCad GUI. See pcb/HOW_TO_FINISH.md.
    _dbg("[10] Routing matrix only")
    _route_matrix(board, nets)

    # ---- GND pour on back ----
    _dbg("[11] GND pour")
    add_gnd_zone(board, gnd, pcbnew.B_Cu, BOARD_W_MM, BOARD_H_MM)

    _dbg(f"[12] Saving {PCB_PATH}")
    os.makedirs(PCB_DIR, exist_ok=True)
    board.Save(PCB_PATH)
    print(f"Wrote {PCB_PATH}")


def _route_matrix(board, nets):
    """COL trunks on F.Cu, ROW trunks on B.Cu, switch->anode bridges on F.Cu."""
    # COL trunks: switch pad 1 at (sx, sy), shared X per column.
    for col in range(2):
        x = SW_X[col]
        ys = sorted(SW_Y)
        add_track(board, (x, ys[0] - 2.0), (x, ys[-1]), nets[f"COL{col}"],
                  layer=pcbnew.F_Cu, width=TRACK_SIG_MM)

    # ROW trunks: anode at (sx - 3.81, sy - 5), cathode at (sx + 3.81, sy - 5).
    # Trunk offset 1.5 mm above pad row (Y = sy - 6.5) on B.Cu with cathode tabs.
    trunk_offset = -1.5
    for row in range(2):
        pad_y = SW_Y[row] + DIODE_DY
        trunk_y = pad_y + trunk_offset
        cathode_xs = sorted(sx + 3.81 for sx in SW_X)
        left = cathode_xs[0] - 2.0
        right = cathode_xs[-1] + 2.0
        add_track(board, (left, trunk_y), (right, trunk_y), nets[f"ROW{row}"],
                  layer=pcbnew.B_Cu, width=TRACK_SIG_MM)
        for sx in SW_X:
            cx = sx + 3.81
            add_track(board, (cx, pad_y), (cx, trunk_y), nets[f"ROW{row}"],
                      layer=pcbnew.B_Cu, width=TRACK_SIG_MM)

    # Switch -> diode anode bridges (L-shape on F.Cu).
    for row in range(2):
        for col in range(2):
            idx = row * 2 + col + 1
            sx, sy = SW_X[col], SW_Y[row]
            sw_p2 = (sx - 6.35, sy + 2.54)
            anode = (sx - 3.81, sy - 5)
            mid = (sx - 6.35, sy - 5)
            add_path(board, [sw_p2, mid, anode], nets[f"SW{idx}_K"],
                     layer=pcbnew.F_Cu, width=TRACK_SIG_MM)


def _route_xiao_to_matrix(board, xiao_left, xiao_right, nets):
    """Fan XIAO COL and ROW pins down to the matrix trunks."""
    # XIAO left pins (X = -7.62), Y from -32.62 (pin 1) to -17.38 (pin 7).
    # Matrix is at Y = -4.525 to +14.525 in switch centers; COL trunk top at
    # Y = SW_Y[0] - 2 = -6.525.
    # ROW trunk Y: row 0 = -10.025, row 1 = +8.95 (with our -1.5 offset).

    # COL0 (XIAO L pin 1, Y=-32.62) -> COL0 trunk at X=-31.525, top Y=-6.525.
    # Use F.Cu. Lane Y = -15 (between XIAO header and matrix).
    col_lane_y_base = -15.0
    col_lane_step = 1.5

    # COL0 fanout: pin -> down to lane -> over to col X -> down to trunk top.
    for c in range(2):
        net = nets[f"COL{c}"]
        x0, y0 = pad_xy(xiao_left, str(c + 1))
        lane_y = col_lane_y_base + c * col_lane_step
        col_x = SW_X[c]
        # First go DOWN (more Y) from pin to lane_y staying at x0.
        # x0 is -7.62 (left pin column). We avoid crossing other left pins by
        # going down first (which moves into clear space below XIAO).
        add_path(board, [(x0, y0), (x0, lane_y), (col_x, lane_y),
                         (col_x, SW_Y[0] - 2.0)],
                 net, layer=pcbnew.F_Cu, width=TRACK_SIG_MM)

    # ROW0 fanout from XIAO L pin 7 at (-7.62, -17.38).
    # ROW0 trunk on B.Cu at Y=-10.025, X range [-31.525-2, -12.475+3.81+2]
    # = [-33.525, -6.665]. Pin X=-7.62, trunk includes X near -7. Direct
    # vertical path on B.Cu would cross through? Pin -> via -> B.Cu route.
    row0_net = nets["ROW0"]
    p7 = pad_xy(xiao_left, "7")  # left pin 7
    row0_trunk_y = SW_Y[0] + DIODE_DY - 1.5
    # Drop via at pin to B.Cu, route on B.Cu directly to leftmost cathode area.
    left_lane_x = -34.0
    add_path(board, [p7, (p7[0], -16.5), (left_lane_x, -16.5),
                     (left_lane_x, row0_trunk_y),
                     (SW_X[0] + 3.81 - 2.0, row0_trunk_y)],
             row0_net, layer=pcbnew.B_Cu, width=TRACK_SIG_MM)

    # ROW1 fanout from XIAO R pin 4 at (7.62, -22.96).
    # ROW1 trunk on B.Cu at Y=8.95. Route through right gutter, but the right
    # side has the encoder and OLED. Go LEFT-DOWN on B.Cu instead.
    row1_net = nets["ROW1"]
    p4r = pad_xy(xiao_right, "4")
    row1_trunk_y = SW_Y[1] + DIODE_DY - 1.5
    # Drop via at pin and route down via the area between matrix and encoder.
    mid_gutter_x = -4.5  # between matrix right edge (SW_X[1]+3.81+~2 = 15) and XIAO right pin (7.62)
    add_path(board, [p4r, (p4r[0], -17.5), (mid_gutter_x, -17.5),
                     (mid_gutter_x, row1_trunk_y),
                     (SW_X[1] + 3.81 + 2.0, row1_trunk_y)],
             row1_net, layer=pcbnew.B_Cu, width=TRACK_SIG_MM)


def _route_oled_i2c(board, xiao_left, oled, nets):
    """SDA/SCL from XIAO left pins 5,6 to OLED pads 4,3."""
    # OLED rotated 90: pad 1 at origin, pads 2,3,4 going +X.
    # OLED placed at (24 - 3.81, -25) = (20.19, -25). After 90 rot, pads at
    # (20.19, -25), (22.73, -25), (25.27, -25), (27.81, -25).
    # Pad 3 (SCL) at (25.27, -25), pad 4 (SDA) at (27.81, -25).
    sda_pin = pad_xy(xiao_left, "5")  # (-7.62, -25.0)
    scl_pin = pad_xy(xiao_left, "6")  # (-7.62, -22.46)
    sda_oled = pad_xy(oled, "4")
    scl_oled = pad_xy(oled, "3")
    # Route on F.Cu, simple horizontal across the top of the board.
    # Lane Y just below XIAO (more Y), but above OLED. OLED at Y=-25 (same as pins).
    # Direct horizontal works because XIAO L pin 5 is at Y=-25 (same Y as OLED).
    # SDA goes from (-7.62, -25) straight to (27.81, -25) but would cross
    # XIAO right pin 5 (7.62, -25) = GND. Need to jog.
    # Route: pin -> down to -19 -> over -> up to OLED.
    lane_y_sda = -19.0
    lane_y_scl = -20.5
    add_path(board, [sda_pin, (sda_pin[0], lane_y_sda),
                     (sda_oled[0], lane_y_sda), sda_oled],
             nets["I2C_SDA"], layer=pcbnew.F_Cu, width=TRACK_SIG_MM)
    add_path(board, [scl_pin, (scl_pin[0], lane_y_scl),
                     (scl_oled[0], lane_y_scl), scl_oled],
             nets["I2C_SCL"], layer=pcbnew.F_Cu, width=TRACK_SIG_MM)


def _route_oled_power(board, xiao_right, oled, nets):
    """5V from XIAO right pin 7 to OLED VCC (pad 2). GND auto via pour."""
    v5_pin = pad_xy(xiao_right, "7")  # (7.62, -17.38)
    oled_vcc = pad_xy(oled, "2")      # (22.73, -25)
    # F.Cu lane below the COL fanout lanes (which are at -15..-12).
    # 5V lane Y=-18 (above XIAO pin 7 at Y=-17.38? no, more negative).
    # XIAO pin 7 is at the BOTTOM of the header (Y=-17.38, which is closer
    # to matrix). 5V can route at Y=-18 just above the pin.
    lane_y = -18.0
    add_path(board, [v5_pin, (v5_pin[0], lane_y),
                     (oled_vcc[0], lane_y), oled_vcc],
             nets["VCC_5V"], layer=pcbnew.F_Cu, width=TRACK_PWR_MM)


def _route_encoder(board, xiao_left, xiao_right, enc, nets):
    """Encoder A, B, push to XIAO."""
    # Encoder placed at (22, 14). Pads from footprint at offsets:
    #   A at (0, 0), C at (0, 2.5), B at (0, 5) -- so absolute:
    #   A (22, 14), C (22, 16.5), B (22, 19)
    #   S1 at (14.5, 5) abs = (36.5, 19), S2 at (14.5, 0) abs = (36.5, 14)
    a_pad = pad_xy(enc, "A")
    b_pad = pad_xy(enc, "B")
    s1_pad = pad_xy(enc, "S1")
    # XIAO left pin 3 (ENC_A) at (-7.62, -27.54). Left pin 4 (ENC_B) at (-7.62, -25.0).
    # XIAO right pin 3 (ENC_PUSH) at (7.62, -27.54).
    # Long routes — use B.Cu to avoid F.Cu congestion.
    enc_a_pin = pad_xy(xiao_left, "3")
    enc_b_pin = pad_xy(xiao_left, "4")
    push_pin = pad_xy(xiao_right, "3")
    # Route on B.Cu under everything, via at each end.
    # Lane Y = -3 (between matrix top -6.525 and OLED -25).
    # Actually the matrix top trunk is at Y=-6.525; let me use Y=+2 (below
    # row 0 trunk at -10.025 — wait row 0 trunk is at Y=-10.025, ROW1 at +8.95).
    # Hmm too crowded. Use F.Cu instead, route around right side.

    # ENC_A: pin (-7.62, -27.54) -> down to lane -17 -> right to 20 -> down to encoder A (22, 14)
    add_path(board, [enc_a_pin, (enc_a_pin[0], -16.0),
                     (a_pad[0] - 4, -16.0), (a_pad[0] - 4, a_pad[1]), a_pad],
             nets["ENC_A"], layer=pcbnew.F_Cu, width=TRACK_SIG_MM)
    # ENC_B: similar but different lane
    add_path(board, [enc_b_pin, (enc_b_pin[0], -13.5),
                     (b_pad[0] - 5, -13.5), (b_pad[0] - 5, b_pad[1]), b_pad],
             nets["ENC_B"], layer=pcbnew.F_Cu, width=TRACK_SIG_MM)
    # ENC_PUSH from right pin 3: pin (7.62, -27.54) -> over to right encoder
    add_path(board, [push_pin, (push_pin[0], -16.5),
                     (s1_pad[0], -16.5), s1_pad],
             nets["ENC_PUSH"], layer=pcbnew.F_Cu, width=TRACK_SIG_MM)


def _route_rgb(board, xiao_right, leds, nets):
    """RGB DIN from XIAO right pin 1 to LED1 DIN. LED chain LED1->LED2."""
    din_pin = pad_xy(xiao_right, "1")  # (7.62, -32.62)
    led1_din = pad_xy(leds[0], "4")
    # LED1 at (-38, 28), LED2 at (-38, -25). Long route to the LEFT side.
    # Route on B.Cu via vias.
    add_path(board, [din_pin, (din_pin[0], -33.5),
                     (-38.0, -33.5), (-38.0, led1_din[1] - 4),
                     (led1_din[0], led1_din[1] - 4), led1_din],
             nets["RGB_DIN"], layer=pcbnew.B_Cu, width=TRACK_SIG_MM)
    # LED1 DOUT (pad 2) -> LED2 DIN (pad 4): both at X=-38, short vertical
    led1_dout = pad_xy(leds[0], "2")
    led2_din = pad_xy(leds[1], "4")
    add_path(board, [led1_dout, (led1_dout[0] - 1, led1_dout[1]),
                     (led1_dout[0] - 1, led2_din[1]), led2_din],
             nets["LED_LINK_1"], layer=pcbnew.F_Cu, width=TRACK_SIG_MM)


if __name__ == "__main__":
    build()
