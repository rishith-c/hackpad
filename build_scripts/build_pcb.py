#!/usr/bin/env python3
"""Build the Hackpad KiCad PCB programmatically with pcbnew.

Design: 12-key macropad (4x3 matrix) + EC11 rotary encoder + 0.91" OLED on a
Seeed XIAO RP2040 - maxes out the kit/rules without going over:
  - PCB <= 100mm x 100mm (this is 95 x 95 mm)
  - < 16 inputs (12 keys + 1 encoder = 13 inputs)
  - 2 layers, through-hole XIAO RP2040
  - OLED pin order: GND - VCC - SCL - SDA (kit standard)

Layout (board origin = center; KiCad +Y is downward):
  - XIAO at top-center (0, -38), USB-C faces top edge
  - OLED 4-pin header at top-left (-26, -36) (rotated 90, pads along +X)
  - EC11 rotary encoder at top-right (30, -28)
  - 4x3 matrix below (12 MX switches) — rows Y = -7, +12.05, +31.1
  - 4 M3 mounting holes at (+/-42, +/-42)

Pin map (XIAO RP2040) — all 11 GPIO used:
   D0 (GP26) = COL0     D6 (GP0)  = ROW0
   D1 (GP27) = COL1     D7 (GP1)  = ROW1
   D2 (GP28) = COL2     D8 (GP2)  = ROW2
   D3 (GP29) = COL3     D9 (GP4)  = ENC_A
   D4 (GP6)  = I2C_SDA  D10 (GP3) = ENC_B
   D5 (GP7)  = I2C_SCL
"""

import os

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
BOARD_W_MM = 95.0
BOARD_H_MM = 95.0
BOARD_CORNER_R_MM = 3.0
TRACK_SIG_MM = 0.25
TRACK_PWR_MM = 0.5
VIA_DRILL_MM = 0.4
VIA_DIA_MM = 0.8
CLEARANCE_MM = 0.2

# Matrix grid (KiCad mm)
SW_PITCH = 19.05
NCOL = 4
NROW = 3
SW_X = [-28.575, -9.525, 9.525, 28.575]               # 4 columns
SW_Y = [-7.0, 12.05, 31.1]                            # 3 rows (19.05 mm pitch)
DIODE_DY = -5.0                                        # diode origin offset from switch (above)

OLED_XY = (-26.0, -36.0)
XIAO_XY = (0.0, -38.0)
ENC_XY  = (30.0, -28.0)
MOUNT_HOLES = [(-42.0, -42.0), (42.0, -42.0), (42.0, 42.0), (-42.0, 42.0)]

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


def add_silk_text(board, text, x, y, size=2.0, layer=None, mirror=False):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(text)
    t.SetPosition(vp(x, y))
    t.SetLayer(layer if layer is not None else pcbnew.F_SilkS)
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
    tb.SetTitle("Hackpad - 12-Key + Encoder + OLED Macropad")
    tb.SetCompany("Hackpad")
    tb.SetRevision("2.0")
    board.SetTitleBlock(tb)
    dsn = board.GetDesignSettings()
    dsn.m_CopperEdgeClearance = mm(0.3)
    dsn.m_MinClearance = mm(CLEARANCE_MM)

    # ---- nets ----
    names = ["VCC_5V", "GND", "+3V3",
             "I2C_SDA", "I2C_SCL",
             "ENC_A", "ENC_B"]
    names += [f"COL{i}" for i in range(NCOL)]
    names += [f"ROW{i}" for i in range(NROW)]
    names += [f"SW{i+1}_K" for i in range(NCOL * NROW)]
    nets = {n: ensure_net(board, n) for n in names}
    gnd, vcc = nets["GND"], nets["VCC_5V"]

    # ---- 12 switches + 12 diodes ----
    _dbg("[2] Switches + diodes")
    sw_fps, d_fps = {}, {}
    for row in range(NROW):
        for col in range(NCOL):
            idx = row * NCOL + col + 1
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

    # ---- XIAO RP2040: two 1x7 pin headers, 15.24 mm apart ----
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
    # XIAO pin map:
    #  Left  1..7: D0(COL0)  D1(COL1)  D2(COL2)  D3(COL3)  D4(SDA)   D5(SCL)   D6(ROW0)
    #  Right 1..7: D10(ENC_B) D9(ENC_A) D8(ROW2)  D7(ROW1)  GND       3V3       5V
    left_nets = [nets["COL0"], nets["COL1"], nets["COL2"], nets["COL3"],
                 nets["I2C_SDA"], nets["I2C_SCL"], nets["ROW0"]]
    right_nets = [nets["ENC_B"], nets["ENC_A"], nets["ROW2"], nets["ROW1"],
                  nets["GND"], nets["+3V3"], nets["VCC_5V"]]
    for i, n in enumerate(left_nets, 1):
        connect_pad(xiao_left, str(i), n)
    for i, n in enumerate(right_nets, 1):
        connect_pad(xiao_right, str(i), n)

    # ---- OLED 4-pin header (rotated 90° so pads run along +X) ----
    _dbg("[4] OLED header")
    ox, oy = OLED_XY
    oled = add_footprint(board, "Connector_PinHeader_2.54mm",
                         "PinHeader_1x04_P2.54mm_Vertical",
                         "J3", "OLED",
                         ox - (3 * 2.54) / 2.0, oy, rot_deg=90.0)
    # GND - VCC - SCL - SDA
    for i, n in enumerate([nets["GND"], nets["VCC_5V"], nets["I2C_SCL"],
                           nets["I2C_SDA"]], 1):
        connect_pad(oled, str(i), n)

    # ---- EC11 rotary encoder (no push wired) ----
    _dbg("[5] Rotary encoder")
    ex, ey = ENC_XY
    enc = add_footprint(board, "Rotary_Encoder",
                        "RotaryEncoder_Alps_EC11E_Vertical_H20mm",
                        "ENC1", "EC11", ex, ey)
    connect_pad(enc, "A", nets["ENC_A"])
    connect_pad(enc, "B", nets["ENC_B"])
    connect_pad(enc, "C", gnd)
    # MP (mechanical pads) are unconnected by design.

    # ---- Mounting holes ----
    _dbg("[6] Mounting holes")
    for i, (mx, my) in enumerate(MOUNT_HOLES, 1):
        add_footprint(board, "MountingHole", "MountingHole_3.2mm_M3",
                      f"MH{i}", "M3", mx, my)

    # ---- Edge cuts ----
    _dbg("[7] Edge cuts")
    add_rounded_rect_outline(board, BOARD_W_MM, BOARD_H_MM, BOARD_CORNER_R_MM)

    # ---- Silkscreen branding ----
    _dbg("[8] Silkscreen")
    add_silk_text(board, "HACKPAD", -25, 45, size=3.0)
    add_silk_text(board, "v2.0", 35, 45, size=1.8)
    # Back-side silk: project URL (mirrored so it reads correctly through copper)
    add_silk_text(board, "github.com/rishith-c/hackpad",
                  0, 45, size=1.4, layer=pcbnew.B_SilkS, mirror=True)

    # ---- Matrix routing ----
    _dbg("[9] Routing matrix")
    _route_matrix(board, nets)

    # ---- GND pour on back ----
    _dbg("[10] GND pour")
    add_gnd_zone(board, gnd, pcbnew.B_Cu, BOARD_W_MM, BOARD_H_MM)

    _dbg(f"[11] Saving {PCB_PATH}")
    os.makedirs(PCB_DIR, exist_ok=True)
    board.Save(PCB_PATH)
    print(f"Wrote {PCB_PATH}")


def _route_matrix(board, nets):
    """COL trunks on F.Cu, ROW trunks on B.Cu, switch->anode bridges on F.Cu."""
    # COL trunks: shared X per column, span all 3 rows
    for col in range(NCOL):
        x = SW_X[col]
        ys = sorted(SW_Y)
        add_track(board, (x, ys[0] - 2.0), (x, ys[-1]), nets[f"COL{col}"],
                  layer=pcbnew.F_Cu, width=TRACK_SIG_MM)

    # ROW trunks on B.Cu, offset 1.5 mm above the diode pad row to clear anodes
    trunk_offset = -1.5
    for row in range(NROW):
        pad_y = SW_Y[row] + DIODE_DY                  # = sy - 5
        trunk_y = pad_y + trunk_offset                # = sy - 6.5
        cathode_xs = sorted(sx + 3.81 for sx in SW_X)
        left = cathode_xs[0] - 2.0
        right = cathode_xs[-1] + 2.0
        add_track(board, (left, trunk_y), (right, trunk_y), nets[f"ROW{row}"],
                  layer=pcbnew.B_Cu, width=TRACK_SIG_MM)
        for sx in SW_X:
            cx = sx + 3.81
            add_track(board, (cx, pad_y), (cx, trunk_y), nets[f"ROW{row}"],
                      layer=pcbnew.B_Cu, width=TRACK_SIG_MM)

    # Switch -> diode anode L-bridge on F.Cu (vertical at sx-6.35, horizontal at sy-5)
    for row in range(NROW):
        for col in range(NCOL):
            idx = row * NCOL + col + 1
            sx, sy = SW_X[col], SW_Y[row]
            net = nets[f"SW{idx}_K"]
            sw_p2 = (sx - 6.35, sy + 2.54)
            anode = (sx - 3.81, sy - 5)
            mid = (sx - 6.35, sy - 5)
            add_path(board, [sw_p2, mid, anode], net,
                     layer=pcbnew.F_Cu, width=TRACK_SIG_MM)


if __name__ == "__main__":
    build()
