#!/usr/bin/env python3
"""Render a hero shot PNG of the assembled Hackpad on a desk with the USB-C
cable trailing off to a partial laptop edge.

Maxxes out visual content within the Hackpad kit (kit confirmed at
https://hackpad.hackclub.com/parts):
  - 12 / 16 MX keycaps (DSA blank)
  - 1 / 2 EC11 encoder knob
  - 1 / 1 0.91" OLED, illustrated illuminated
  - 4 / 6 M3 socket-head screws (heads visible)
  - 4 / 6 M3 heatset inserts (inside bottom tray)
  - 0 / 20 SK6812 LEDs on PCB; subtle underglow rendered to show
    the optional hand-wire location
  - USB-C cable trailing off-frame upward, hint of a laptop edge

Saves to ~/Desktop/hackpad_hero.png and assets/hero.png.
"""

import os

import cadquery as cq
import numpy as np
import trimesh
from matplotlib import pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection, Line3DCollection

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BUILD_DIR = os.path.join(ROOT, ".build_hero")
os.makedirs(BUILD_DIR, exist_ok=True)

PCB_W, PCB_H, PCB_THK = 95.0, 95.0, 1.6
CASE_WALL = 2.0
CASE_W = PCB_W + 2 * CASE_WALL
CASE_H = PCB_H + 2 * CASE_WALL
TOP_THK = 5.0
BOTTOM_THK = 8.0
CORNER_R = 3.0
MX_CUT = 14.0
SW_X = [-28.575, -9.525, 9.525, 28.575]
SW_Y = [-7.0, 12.05, 31.1]
ENC_X, ENC_Y = 30.0, -28.0
OLED_X, OLED_Y = -26.0, -36.0
MOUNT_HOLES = [(-42.0, -42.0), (42.0, -42.0), (42.0, 42.0), (-42.0, 42.0)]


def build_top_plate():
    plate = cq.Workplane("XY").box(CASE_W, CASE_H, TOP_THK).edges("|Z").fillet(CORNER_R)
    for sy in SW_Y:
        for sx in SW_X:
            plate = (plate.faces(">Z").workplane(centerOption="CenterOfBoundBox")
                     .center(sx, sy).rect(MX_CUT, MX_CUT).cutThruAll())
    plate = (plate.faces(">Z").workplane(centerOption="CenterOfBoundBox")
             .center(ENC_X, ENC_Y).circle(3.75).cutThruAll())
    plate = (plate.faces(">Z").workplane(centerOption="CenterOfBoundBox")
             .center(OLED_X, OLED_Y).rect(22.0, 6.0).cutThruAll())
    plate = (plate.faces(">Z").workplane(centerOption="CenterOfBoundBox")
             .center(0.0, -38.0).rect(22.0, 20.0).cutThruAll())
    for (mx, my) in MOUNT_HOLES:
        plate = (plate.faces(">Z").workplane(centerOption="CenterOfBoundBox")
                 .center(mx, my).circle(1.6).cutThruAll())
    return plate


def build_bottom_tray():
    tray = cq.Workplane("XY").box(CASE_W, CASE_H, BOTTOM_THK).edges("|Z").fillet(CORNER_R)
    tray = (tray.faces(">Z").workplane(centerOption="CenterOfBoundBox")
            .rect(CASE_W - 2 * CASE_WALL, CASE_H - 2 * CASE_WALL).cutBlind(-(BOTTOM_THK - 2.0)))
    tray = (tray.faces("<Y").workplane(centerOption="CenterOfBoundBox")
            .center(0, 0).rect(10.0, 8.0).cutBlind(-2.5))
    return tray


def build_keycap(sx, sy, z0):
    base, top, h = 17.5, 13.0, 7.0
    return (cq.Workplane("XY")
            .workplane(offset=z0).rect(base, base)
            .workplane(offset=h).rect(top, top)
            .loft(combine=True)
            .translate((sx, sy, 0)))


def build_encoder_knob(ex, ey, z0):
    return (cq.Workplane("XY")
            .workplane(offset=z0).center(ex, ey).circle(7.0)
            .workplane(offset=7.0).circle(6.0)
            .loft(combine=True))


def build_oled_face(ox, oy, z_top):
    return (cq.Workplane("XY")
            .workplane(offset=z_top - 0.5)
            .center(ox, oy).rect(22.0, 6.0).extrude(0.5))


def build_screw_head(mx, my, z_top):
    return (cq.Workplane("XY")
            .workplane(offset=z_top - 0.5)
            .center(mx, my).circle(2.75).extrude(0.5))


def build_usbc_plug():
    return cq.Workplane("XY").box(8.4, 6.5, 2.5)


_stl_counter = [0]


def to_trimesh(cq_obj):
    _stl_counter[0] += 1
    p = os.path.join(BUILD_DIR, f"tmp_{_stl_counter[0]}.stl")
    cq.exporters.export(cq_obj, p, tolerance=0.05, angularTolerance=0.08)
    return trimesh.load(p, force="mesh")


def main():
    desktop = os.path.expanduser("~/Desktop")
    desktop_out = os.path.join(desktop, "hackpad_hero.png")
    repo_out = os.path.join(ROOT, "assets", "hero.png")

    print("[1] Models")
    top = build_top_plate()
    bot = build_bottom_tray()
    top_z = BOTTOM_THK + PCB_THK + 1.0
    top_surface_z = top_z + TOP_THK
    keycap_z = top_z + TOP_THK - 1.0

    caps = [build_keycap(sx, sy, keycap_z) for sy in SW_Y for sx in SW_X]
    knob = build_encoder_knob(ENC_X, ENC_Y, top_z + TOP_THK - 1.0)
    oled = build_oled_face(OLED_X, OLED_Y, top_z + TOP_THK)
    screws = [build_screw_head(mx, my, top_surface_z) for (mx, my) in MOUNT_HOLES]
    usbc = build_usbc_plug().translate((0, -CASE_H / 2.0 - 2.0, BOTTOM_THK / 2.0))

    print("[2] Meshing")
    top_mesh = to_trimesh(top.translate((0, 0, top_z + TOP_THK / 2)))
    bot_mesh = to_trimesh(bot.translate((0, 0, BOTTOM_THK / 2)))
    cap_meshes = [to_trimesh(c) for c in caps]
    knob_mesh = to_trimesh(knob)
    oled_mesh = to_trimesh(oled)
    screw_meshes = [to_trimesh(s) for s in screws]
    usbc_mesh = to_trimesh(usbc)

    print("[3] Rendering")
    bg = "#1d2026"               # dark "studio" backdrop
    fig = plt.figure(figsize=(16, 10), dpi=180, facecolor=bg)
    ax = fig.add_subplot(111, projection="3d", facecolor=bg)

    # ---- Build ONE combined mesh ----
    desk_z = -0.5
    desk_tris = np.array([
        [[-220, -180, desk_z], [220, -180, desk_z], [220, 120, desk_z]],
        [[-220, -180, desk_z], [220, 120, desk_z], [-220, 120, desk_z]],
    ])

    parts = [
        (bot_mesh,    (0.10, 0.10, 0.12)),
        (top_mesh,    (0.85, 0.16, 0.16)),
        (oled_mesh,   (0.05, 0.08, 0.16)),
        (knob_mesh,   (0.14, 0.14, 0.16)),
        (usbc_mesh,   (0.18, 0.18, 0.20)),
    ]
    for cap in cap_meshes:
        parts.append((cap, (0.96, 0.96, 0.97)))
    for sm in screw_meshes:
        parts.append((sm, (0.62, 0.62, 0.66)))

    all_tris, all_colors = [], []
    light = np.array([0.30, -0.55, 0.78]); light /= np.linalg.norm(light)
    for mesh, color in parts:
        normals = mesh.face_normals
        intensity = np.clip(normals @ light, 0.0, 1.0) * 0.65 + 0.35
        base = np.array(color)
        shaded = (intensity[:, None] * base[None, :]).clip(0, 1)
        rgba = np.hstack([shaded, np.full((shaded.shape[0], 1), 1.0)])
        all_tris.append(mesh.triangles)
        all_colors.append(rgba)

    # Desk added LAST so its triangles' max-z (=-0.5) is below everything else.
    desk_color = np.array([0.13, 0.14, 0.16])     # dark desk to match bg
    desk_rgba = np.hstack([desk_color, np.array([1.0])])
    all_tris.append(desk_tris)
    all_colors.append(np.tile(desk_rgba, (2, 1)))

    tris = np.concatenate(all_tris, axis=0)
    colors = np.concatenate(all_colors, axis=0)
    coll = Poly3DCollection(tris, facecolors=colors, edgecolors='none',
                            linewidths=0, shade=False, zsort='max')
    ax.add_collection3d(coll)

    # ---- Underglow ring (visual hint of SK6812 underglow, not on PCB) ----
    underglow_n = 80
    glow_theta = np.linspace(0, 2 * np.pi, underglow_n)
    glow_x = (CASE_W / 2 + 6) * np.cos(glow_theta) * 0.92
    glow_y = (CASE_H / 2 + 6) * np.sin(glow_theta) * 0.92 + 0
    glow_z = np.full_like(glow_x, 0.3)
    glow_verts = np.column_stack([glow_x, glow_y, glow_z])
    glow_segs = [(glow_verts[i], glow_verts[i + 1]) for i in range(underglow_n - 1)]
    glow_colors = []
    for i in range(underglow_n - 1):
        h = (i / underglow_n) * 360
        c = abs(((h / 60.0) % 2) - 1)
        if h < 60:    rgb = (1, c, 0)
        elif h < 120: rgb = (c, 1, 0)
        elif h < 180: rgb = (0, 1, c)
        elif h < 240: rgb = (0, c, 1)
        elif h < 300: rgb = (c, 0, 1)
        else:         rgb = (1, 0, c)
        glow_colors.append((*rgb, 0.55))
    ax.add_collection3d(
        Line3DCollection(glow_segs, colors=glow_colors, linewidths=7, zorder=2)
    )

    # ---- USB-C cable trailing off-frame upward (toward laptop) ----
    n = 80
    t = np.linspace(0, 1, n)
    cable_start = np.array([0, -CASE_H / 2.0 - 4.0, BOTTOM_THK / 2.0])
    cable_end = np.array([15, -170, 35])
    ctrl1 = np.array([5, -85, 4])
    ctrl2 = np.array([12, -140, 20])
    pts = (
        (1 - t)[:, None] ** 3 * cable_start
        + 3 * ((1 - t) ** 2)[:, None] * t[:, None] * ctrl1
        + 3 * ((1 - t))[:, None] * (t ** 2)[:, None] * ctrl2
        + (t ** 3)[:, None] * cable_end
    )
    cable_segs = [(pts[i], pts[i + 1]) for i in range(n - 1)]
    ax.add_collection3d(
        Line3DCollection(cable_segs, colors='#222428',
                         linewidths=5.0, zorder=15)
    )
    # Cable highlight along the top for depth
    pts_hl = pts.copy()
    pts_hl[:, 2] += 0.4
    hl_segs = [(pts_hl[i], pts_hl[i + 1]) for i in range(n - 1)]
    ax.add_collection3d(
        Line3DCollection(hl_segs, colors='#4a4d54',
                         linewidths=1.8, zorder=16)
    )

    # Floating terminal overlay (suggests "plugged into laptop" without
    # needing a full laptop mesh that matplotlib's z-sort can't handle).
    ax.text(-30, -90, 25, "$ cp main.py /Volumes/CIRCUITPY/\nhackpad → ready ✓",
            color="#a1c4ff", fontsize=9, ha="center", va="center",
            zorder=22, family="monospace")

    # ---- OLED tiny text ----
    ax.text(OLED_X, OLED_Y, top_surface_z + 0.5, "Hackpad\nL0",
            color="#9ec0ff", fontsize=6, fontweight="bold",
            ha="center", va="center", zorder=25, family="monospace")

    # ---- HACK CLUB decal ----
    ax.text(-28, 36, top_surface_z + 0.4, "HACK CLUB",
            color="white", fontsize=11, fontweight="bold",
            ha="center", va="center", zorder=22, rotation=-8)

    # ---- Camera + framing — tight crop on the macropad ----
    ax.set_xlim(-75, 80)
    ax.set_ylim(-120, 65)
    ax.set_zlim(0, 60)
    ax.set_box_aspect((155, 185, 60))
    ax.view_init(elev=28, azim=-62)
    ax.set_axis_off()

    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    for path in (desktop_out, repo_out):
        plt.savefig(path, dpi=180, bbox_inches="tight", pad_inches=0.05,
                    facecolor=fig.get_facecolor())
        print(f"Saved {path}")


if __name__ == "__main__":
    main()
