#!/usr/bin/env python3
"""Build the Hackpad 3D-printed case using cadquery.

Two parts:
  - top.step / top.stl  : switch-plate (5mm) with 14x14mm MX cutouts,
                          encoder shaft hole, OLED window, XIAO USB-C
                          slot in the side wall.
  - bottom.step / bottom.stl: tray (8mm) with M3 heatset insert bosses,
                              PCB rest ledge, screw holes.

Plus an assembled-model.step that combines both halves with a simplified
PCB representation in between - this is the file Hack Club's submission
expects in cad/.
"""

import os

import cadquery as cq

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROD_DIR = os.path.join(ROOT, "production")
CAD_DIR = os.path.join(ROOT, "cad")

# ---- dimensions (mm) ----
PCB_W = 90.0
PCB_H = 70.0
PCB_THK = 1.6
CASE_WALL = 2.0
CASE_W = PCB_W + 2 * CASE_WALL          # = 94
CASE_H = PCB_H + 2 * CASE_WALL          # = 74
TOP_THK = 5.0
BOTTOM_THK = 8.0
PCB_REST_THK = 2.0                       # ledge thickness under PCB
CORNER_R = 3.0

# Switch parameters
MX_CUT = 14.0                            # 14x14 hole per switch
SW_PITCH = 19.05
SW_CENTER_X = -22.0                      # board coords (origin = board center)
SW_CENTER_Y = 5.0
SW_X = [SW_CENTER_X - SW_PITCH / 2, SW_CENTER_X + SW_PITCH / 2]
SW_Y = [SW_CENTER_Y - SW_PITCH / 2, SW_CENTER_Y + SW_PITCH / 2]

# Encoder shaft (EC11): ~7mm threaded bushing
ENC_X = 22.0
ENC_Y = 14.0
ENC_BUSHING_D = 7.5

# OLED window (visible area through cutout): 22mm x 6mm
OLED_X = 24.0
OLED_Y = -25.0
OLED_WIN_W = 22.0
OLED_WIN_H = 6.0

# XIAO USB-C cutout in top of case (USB at the top board edge, Y=-35 in board coords)
XIAO_USB_W = 10.0
XIAO_USB_H = 4.0     # roughly USB-C connector depth

# Mounting holes (M3, in PCB coords)
MOUNT_HOLES = [(-40.0, -30.0), (40.0, -30.0), (40.0, 30.0), (-40.0, 30.0)]
M3_INSERT_D = 4.2     # M3x5x4 heatset insert ~4.2mm OD
M3_BOSS_OD = 6.5      # boss outer diameter for inserts
M3_BOSS_H = 5.0       # boss height in bottom tray
M3_SCREW_D = 3.2      # M3 screw clearance


def rounded_rect_plate(w, h, thk, r):
    """A rounded rectangular plate of the given outer dimensions."""
    return cq.Workplane("XY").rect(w, h).workplane().tag("base") \
        .center(0, 0).rect(w, h).extrude(0).end() \
        .moveTo(0, 0)._tag_select_first("base") if False else \
        cq.Workplane("XY").box(w, h, thk).edges("|Z").fillet(r)


def build_top():
    """Top plate: cutouts for switches, encoder shaft, OLED window."""
    plate = cq.Workplane("XY").box(CASE_W, CASE_H, TOP_THK).edges("|Z").fillet(CORNER_R)

    # MX switch cutouts (centered on each switch position in board coords)
    for sy in SW_Y:
        for sx in SW_X:
            plate = (plate
                     .faces(">Z").workplane(centerOption="CenterOfBoundBox")
                     .center(sx, sy)
                     .rect(MX_CUT, MX_CUT)
                     .cutThruAll())

    # Encoder shaft hole
    plate = (plate
             .faces(">Z").workplane(centerOption="CenterOfBoundBox")
             .center(ENC_X, ENC_Y)
             .circle(ENC_BUSHING_D / 2.0)
             .cutThruAll())

    # OLED window
    plate = (plate
             .faces(">Z").workplane(centerOption="CenterOfBoundBox")
             .center(OLED_X, OLED_Y)
             .rect(OLED_WIN_W, OLED_WIN_H)
             .cutThruAll())

    # XIAO inspection window so the user can see the USB-C
    plate = (plate
             .faces(">Z").workplane(centerOption="CenterOfBoundBox")
             .center(0.0, -25.0)
             .rect(20.0, 18.0)
             .cutThruAll())

    # M3 screw clearance holes through top
    for (mx, my) in MOUNT_HOLES:
        plate = (plate
                 .faces(">Z").workplane(centerOption="CenterOfBoundBox")
                 .center(mx, my)
                 .circle(M3_SCREW_D / 2.0)
                 .cutThruAll())
    return plate


def build_bottom():
    """Bottom tray: walls + PCB rest ledge + M3 heatset bosses + side cutout for USB-C."""
    # Solid block first
    tray = cq.Workplane("XY").box(CASE_W, CASE_H, BOTTOM_THK).edges("|Z").fillet(CORNER_R)

    # Hollow out the interior to leave PCB_REST_THK at the bottom + walls.
    pocket_w = CASE_W - 2 * CASE_WALL
    pocket_h = CASE_H - 2 * CASE_WALL
    pocket_d = BOTTOM_THK - PCB_REST_THK
    tray = (tray
            .faces(">Z").workplane(centerOption="CenterOfBoundBox")
            .rect(pocket_w, pocket_h)
            .cutBlind(-pocket_d))

    # M3 heatset insert bosses (cylinders standing up from the pocket floor).
    # Add the boss as a separate cylinder UNION'd into the tray, then drill the
    # insert hole.
    for (mx, my) in MOUNT_HOLES:
        # Cylinder centered at (mx, my) on the pocket floor.
        # Pocket floor Z is at (BOTTOM_THK/2 - pocket_d) = (4 - 6) = -2 from
        # tray center. We use absolute Z.
        # Easier: just build a boss at the right XYZ and union with tray.
        boss = (cq.Workplane("XY")
                .workplane(offset=-BOTTOM_THK / 2 + PCB_REST_THK)
                .center(mx, my)
                .circle(M3_BOSS_OD / 2.0)
                .extrude(M3_BOSS_H))
        tray = tray.union(boss)
        # Drill the insert hole (slightly undersized, insert melts in).
        tray = (tray
                .faces(">Z").workplane(centerOption="CenterOfBoundBox")
                .center(mx, my)
                .circle(M3_INSERT_D / 2.0)
                .cutBlind(-M3_BOSS_H))

    # USB-C side cutout: notch the wall closest to Y = -CASE_H/2 (top edge of
    # the board in our convention). XIAO USB-C sits at board Y = -35 roughly,
    # which is the BOTTOM Y of the board (Y less = top of board visually,
    # but our board coords have origin at center and USB-C in our PCB layout
    # is at Y = ~-32.6). The case wall on the -Y side needs a notch.
    tray = (tray
            .faces("<Y").workplane(centerOption="CenterOfBoundBox")
            .center(0, 0)
            .rect(XIAO_USB_W, XIAO_USB_H * 2)
            .cutBlind(-CASE_WALL - 0.5))

    return tray


def build_pcb_dummy():
    """Simplified PCB block for the assembled-model preview only."""
    pcb = (cq.Workplane("XY")
           .box(PCB_W, PCB_H, PCB_THK)
           .edges("|Z").fillet(CORNER_R))
    return pcb


def main():
    os.makedirs(PROD_DIR, exist_ok=True)
    os.makedirs(CAD_DIR, exist_ok=True)

    print("[1] Building top plate...")
    top = build_top()
    print("[2] Building bottom tray...")
    bottom = build_bottom()
    print("[3] Building PCB dummy...")
    pcb = build_pcb_dummy()

    # ---- Individual production STLs and STEPs ----
    top_step = os.path.join(PROD_DIR, "Top.step")
    bot_step = os.path.join(PROD_DIR, "Bottom.step")
    top_stl  = os.path.join(PROD_DIR, "Top.stl")
    bot_stl  = os.path.join(PROD_DIR, "Bottom.stl")

    print(f"[4] Export {top_step}")
    cq.exporters.export(top, top_step)
    print(f"[5] Export {bot_step}")
    cq.exporters.export(bottom, bot_step)
    print(f"[6] Export {top_stl}")
    cq.exporters.export(top, top_stl)
    print(f"[7] Export {bot_stl}")
    cq.exporters.export(bottom, bot_stl)

    # ---- Assembled model in cad/ ----
    # Stack: bottom tray (Z 0..8) + PCB (Z 8..9.6) + air gap (1mm) + top plate (Z 10.6..15.6)
    # cadquery centers boxes at origin, so translate accordingly.
    print("[8] Assembling full model")
    bottom_pos = bottom.translate((0, 0, BOTTOM_THK / 2))
    pcb_pos    = pcb.translate((0, 0, BOTTOM_THK + PCB_THK / 2))
    top_pos    = top.translate((0, 0, BOTTOM_THK + PCB_THK + 1.0 + TOP_THK / 2))

    assembly = cq.Assembly()
    assembly.add(bottom_pos, name="bottom", color=cq.Color("black"))
    assembly.add(pcb_pos, name="pcb", color=cq.Color("darkgreen"))
    assembly.add(top_pos, name="top", color=cq.Color("red"))

    assembled_step = os.path.join(CAD_DIR, "assembled-model.step")
    print(f"[9] Export {assembled_step}")
    assembly.save(assembled_step)

    # Also export an STL of the assembly. cq.Assembly doesn't write STL directly,
    # so we union the placed solids into a single compound and export that.
    assembled_stl = os.path.join(CAD_DIR, "assembled-model.stl")
    print(f"[10] Export {assembled_stl}")
    combined = bottom_pos.union(pcb_pos).union(top_pos)
    cq.exporters.export(combined, assembled_stl, tolerance=0.1, angularTolerance=0.1)

    print("Done.")


if __name__ == "__main__":
    main()
