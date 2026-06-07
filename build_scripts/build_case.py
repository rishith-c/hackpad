#!/usr/bin/env python3
"""Build the Hackpad 3D-printed case + screw hardware using cadquery.

Parts produced:
  - production/Top.step / .stl    : top switch-plate (5mm) with 12 MX cutouts,
                                    encoder shaft hole, OLED window, XIAO
                                    inspection window, M3 screw clearance.
  - production/Bottom.step / .stl : bottom tray (8mm) with PCB rest ledge,
                                    4x M3 heatset insert bosses, USB-C side cutout.
  - production/M3x16_Screw.step / .stl : single M3x16 mm SHCS hardware model
                                         (one file, used 4x in the assembly).
  - production/HeatsetInsert_M3x5x4.step / .stl : single brass heatset insert
                                                   hardware model (one file, used 4x).
  - cad/assembled-model.step / .stl : full assembled CAD model (top + bottom +
                                       PCB + 4 screws + 4 inserts).

All hardware is generated parametrically — re-running this script reproduces
every file byte-for-byte.
"""

import os

import cadquery as cq

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROD_DIR = os.path.join(ROOT, "production")
CAD_DIR = os.path.join(ROOT, "cad")

# ---- dimensions (mm) — must match build_pcb.py ---
PCB_W = 95.0
PCB_H = 95.0
PCB_THK = 1.6
CASE_WALL = 2.0
CASE_W = PCB_W + 2 * CASE_WALL          # 99
CASE_H = PCB_H + 2 * CASE_WALL          # 99
TOP_THK = 5.0
BOTTOM_THK = 8.0
PCB_REST_THK = 2.0
CORNER_R = 3.0

# Matrix
MX_CUT = 14.0
SW_PITCH = 19.05
SW_X = [-28.575, -9.525, 9.525, 28.575]   # 4 cols
SW_Y = [-7.0, 12.05, 31.1]                # 3 rows

# Other top-side cutouts
ENC_X, ENC_Y = 30.0, -28.0
ENC_BUSHING_D = 7.5

OLED_X, OLED_Y = -26.0, -36.0
OLED_WIN_W = 22.0
OLED_WIN_H = 6.0

# XIAO inspection window
XIAO_INSPECT_X = 0.0
XIAO_INSPECT_Y = -38.0
XIAO_INSPECT_W = 22.0
XIAO_INSPECT_H = 20.0

# Mounting holes
MOUNT_HOLES = [(-42.0, -42.0), (42.0, -42.0), (42.0, 42.0), (-42.0, 42.0)]
M3_INSERT_OD = 4.2       # heatset insert OD (kit: 4.0)
M3_BOSS_OD = 6.5
M3_BOSS_H = 5.0
M3_SCREW_HEAD_D = 5.5    # SHCS head diameter
M3_SCREW_HEAD_H = 3.0
M3_SCREW_SHAFT_D = 3.0
M3_SCREW_LEN = 16.0      # M3x16 from kit
M3_CLEARANCE = 3.2       # screw clearance hole in top plate

# USB-C
XIAO_USB_W = 10.0
XIAO_USB_H = 4.0


# =============================================================
# Top plate
# =============================================================
def build_top():
    plate = cq.Workplane("XY").box(CASE_W, CASE_H, TOP_THK).edges("|Z").fillet(CORNER_R)

    # MX switch cutouts
    for sy in SW_Y:
        for sx in SW_X:
            plate = (plate.faces(">Z").workplane(centerOption="CenterOfBoundBox")
                     .center(sx, sy).rect(MX_CUT, MX_CUT).cutThruAll())

    # Encoder shaft hole
    plate = (plate.faces(">Z").workplane(centerOption="CenterOfBoundBox")
             .center(ENC_X, ENC_Y).circle(ENC_BUSHING_D / 2.0).cutThruAll())

    # OLED window
    plate = (plate.faces(">Z").workplane(centerOption="CenterOfBoundBox")
             .center(OLED_X, OLED_Y).rect(OLED_WIN_W, OLED_WIN_H).cutThruAll())

    # XIAO inspection window (see USB-C connector + USB connection LED)
    plate = (plate.faces(">Z").workplane(centerOption="CenterOfBoundBox")
             .center(XIAO_INSPECT_X, XIAO_INSPECT_Y)
             .rect(XIAO_INSPECT_W, XIAO_INSPECT_H).cutThruAll())

    # M3 screw clearance through top
    for (mx, my) in MOUNT_HOLES:
        plate = (plate.faces(">Z").workplane(centerOption="CenterOfBoundBox")
                 .center(mx, my).circle(M3_CLEARANCE / 2.0).cutThruAll())
    return plate


# =============================================================
# Bottom tray
# =============================================================
def build_bottom():
    tray = cq.Workplane("XY").box(CASE_W, CASE_H, BOTTOM_THK).edges("|Z").fillet(CORNER_R)

    # Hollow interior (PCB pocket)
    pocket_w = CASE_W - 2 * CASE_WALL
    pocket_h = CASE_H - 2 * CASE_WALL
    pocket_d = BOTTOM_THK - PCB_REST_THK
    tray = (tray.faces(">Z").workplane(centerOption="CenterOfBoundBox")
            .rect(pocket_w, pocket_h).cutBlind(-pocket_d))

    # M3 heatset insert bosses (cylinders standing up from pocket floor)
    for (mx, my) in MOUNT_HOLES:
        boss = (cq.Workplane("XY")
                .workplane(offset=-BOTTOM_THK / 2 + PCB_REST_THK)
                .center(mx, my).circle(M3_BOSS_OD / 2.0).extrude(M3_BOSS_H))
        tray = tray.union(boss)
        tray = (tray.faces(">Z").workplane(centerOption="CenterOfBoundBox")
                .center(mx, my).circle(M3_INSERT_OD / 2.0).cutBlind(-M3_BOSS_H))

    # USB-C cutout in side wall
    tray = (tray.faces("<Y").workplane(centerOption="CenterOfBoundBox")
            .center(0, 0).rect(XIAO_USB_W, XIAO_USB_H * 2)
            .cutBlind(-CASE_WALL - 0.5))

    return tray


# =============================================================
# Hardware: M3x16 SHCS screw
# =============================================================
def build_m3_screw():
    """Simplified socket-head cap screw: cylindrical head + threaded shaft.

    Single canonical model — the assembly places 4 copies. Real screws
    have hex sockets and threads; this is a clean stand-in for visualization
    and packing checks. Not a STEP file you'd machine from; the screw is
    purchased hardware (or comes in the Hackpad kit).
    """
    screw = (cq.Workplane("XY")
             .circle(M3_SCREW_SHAFT_D / 2.0)
             .extrude(M3_SCREW_LEN))
    head = (cq.Workplane("XY")
            .workplane(offset=M3_SCREW_LEN)
            .circle(M3_SCREW_HEAD_D / 2.0)
            .extrude(M3_SCREW_HEAD_H))
    return screw.union(head)


# =============================================================
# Hardware: M3 x 5 x 4 brass heatset insert
# =============================================================
def build_heatset_insert():
    """Brass heatset insert: hollow cylinder with knurled OD (simplified)."""
    od = 4.0
    id_ = 2.5
    length = 5.0
    body = (cq.Workplane("XY").circle(od / 2.0).extrude(length))
    bore = (cq.Workplane("XY").circle(id_ / 2.0).extrude(length))
    return body.cut(bore)


# =============================================================
# PCB stand-in (block)
# =============================================================
def build_pcb_dummy():
    return (cq.Workplane("XY")
            .box(PCB_W, PCB_H, PCB_THK)
            .edges("|Z").fillet(CORNER_R))


def main():
    os.makedirs(PROD_DIR, exist_ok=True)
    os.makedirs(CAD_DIR, exist_ok=True)

    print("[1] Top plate")
    top = build_top()
    print("[2] Bottom tray")
    bot = build_bottom()
    print("[3] M3 screw")
    screw = build_m3_screw()
    print("[4] Heatset insert")
    insert = build_heatset_insert()
    print("[5] PCB dummy")
    pcb = build_pcb_dummy()

    # ---- Production parts (per-file) ----
    parts = [
        (top,    "Top",                       True),   # 3D-printable
        (bot,    "Bottom",                    True),   # 3D-printable
        (screw,  "M3x16_Screw",               False),  # hardware (visualization)
        (insert, "HeatsetInsert_M3x5x4",      False),  # hardware (visualization)
    ]
    for solid, name, _printable in parts:
        step_path = os.path.join(PROD_DIR, f"{name}.step")
        stl_path  = os.path.join(PROD_DIR, f"{name}.stl")
        print(f"[6] Export {step_path}")
        cq.exporters.export(solid, step_path)
        print(f"[7] Export {stl_path}")
        cq.exporters.export(solid, stl_path, tolerance=0.05, angularTolerance=0.1)

    # ---- Assembly ----
    # Stack heights: bottom tray Z 0..8, PCB Z 8..9.6, top plate Z 10.6..15.6
    print("[8] Assembling")
    bottom_pos = bot.translate((0, 0, BOTTOM_THK / 2))
    pcb_pos    = pcb.translate((0, 0, BOTTOM_THK + PCB_THK / 2))
    top_pos    = top.translate((0, 0, BOTTOM_THK + PCB_THK + 1.0 + TOP_THK / 2))

    # Heatset inserts melt into the bottom-tray bosses (top of boss at z = PCB_REST_THK + M3_BOSS_H = 7)
    inserts = []
    insert_top_z = PCB_REST_THK + M3_BOSS_H  # boss top in tray frame; tray bottom at z=0 here
    for (mx, my) in MOUNT_HOLES:
        # insert occupies last 5mm of boss height, top flush with boss top
        ins = insert.translate((mx, my, insert_top_z - 5.0))
        inserts.append(ins)

    # Screws drop through the top plate clearance holes into the heatset
    # inserts. Head sits flush with the top plate top surface.
    screws_placed = []
    top_plate_top_z = BOTTOM_THK + PCB_THK + 1.0 + TOP_THK  # = 15.6
    for (mx, my) in MOUNT_HOLES:
        # Screw shaft extends 16mm DOWN from head. Head top at top_plate_top_z.
        sc = screw.translate((mx, my, top_plate_top_z - M3_SCREW_LEN))
        screws_placed.append(sc)

    asm = cq.Assembly()
    asm.add(bottom_pos, name="bottom", color=cq.Color("black"))
    asm.add(pcb_pos,    name="pcb",    color=cq.Color("darkgreen"))
    asm.add(top_pos,    name="top",    color=cq.Color("red"))
    for i, ins in enumerate(inserts, 1):
        asm.add(ins, name=f"insert{i}", color=cq.Color("goldenrod"))
    for i, sc in enumerate(screws_placed, 1):
        asm.add(sc, name=f"screw{i}", color=cq.Color("gray"))

    assembled_step = os.path.join(CAD_DIR, "assembled-model.step")
    print(f"[9] Export {assembled_step}")
    asm.save(assembled_step)

    # Single-mesh STL of the assembly (matplotlib / GitHub render likes this)
    assembled_stl = os.path.join(CAD_DIR, "assembled-model.stl")
    print(f"[10] Export {assembled_stl}")
    combined = bottom_pos.union(pcb_pos).union(top_pos)
    for ins in inserts:
        combined = combined.union(ins)
    for sc in screws_placed:
        combined = combined.union(sc)
    cq.exporters.export(combined, assembled_stl, tolerance=0.1, angularTolerance=0.1)

    print("Done.")


if __name__ == "__main__":
    main()
