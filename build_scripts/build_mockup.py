#!/usr/bin/env python3
"""Render the assembled Hackpad v2 as a Fusion 360-style isometric PNG mockup.

Saves to assets/mockup.png AND ~/Desktop/hackpad_mockup.png.
"""

import os
import sys

import cadquery as cq
import numpy as np
import trimesh
from matplotlib import pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BUILD_DIR = os.path.join(ROOT, ".build_mockup")
os.makedirs(BUILD_DIR, exist_ok=True)

# Dimensions — keep in sync with build_case.py / build_pcb.py
PCB_W, PCB_H, PCB_THK = 95.0, 95.0, 1.6
CASE_WALL = 2.0
CASE_W = PCB_W + 2 * CASE_WALL
CASE_H = PCB_H + 2 * CASE_WALL
TOP_THK = 5.0
BOTTOM_THK = 8.0
PCB_REST_THK = 2.0
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
    pocket_w = CASE_W - 2 * CASE_WALL
    pocket_h = CASE_H - 2 * CASE_WALL
    pocket_d = BOTTOM_THK - PCB_REST_THK
    tray = (tray.faces(">Z").workplane(centerOption="CenterOfBoundBox")
            .rect(pocket_w, pocket_h).cutBlind(-pocket_d))
    for (mx, my) in MOUNT_HOLES:
        boss = (cq.Workplane("XY")
                .workplane(offset=-BOTTOM_THK / 2 + PCB_REST_THK)
                .center(mx, my).circle(3.25).extrude(5.0))
        tray = tray.union(boss)
        tray = (tray.faces(">Z").workplane(centerOption="CenterOfBoundBox")
                .center(mx, my).circle(2.1).cutBlind(-5.0))
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
    """A short cylinder representing the M3 SHCS head poking through the top plate."""
    return (cq.Workplane("XY")
            .workplane(offset=z_top - 0.5)
            .center(mx, my).circle(2.75).extrude(0.5))


_stl_counter = [0]


def to_trimesh(cq_obj):
    _stl_counter[0] += 1
    stl_path = os.path.join(BUILD_DIR, f"tmp_{_stl_counter[0]}.stl")
    cq.exporters.export(cq_obj, stl_path, tolerance=0.05, angularTolerance=0.08)
    return trimesh.load(stl_path, force="mesh")


def main():
    desktop = os.path.expanduser("~/Desktop")
    desktop_out = os.path.join(desktop, "hackpad_mockup.png")
    repo_out = os.path.join(ROOT, "assets", "mockup.png")

    print("[1] Models")
    top = build_top_plate()
    bot = build_bottom_tray()

    bot_z = 0.0
    top_z = BOTTOM_THK + PCB_THK + 1.0
    keycap_z = top_z + TOP_THK - 1.0
    top_surface_z = top_z + TOP_THK

    caps = [build_keycap(sx, sy, keycap_z) for sy in SW_Y for sx in SW_X]
    knob = build_encoder_knob(ENC_X, ENC_Y, top_z + TOP_THK - 1.0)
    oled = build_oled_face(OLED_X, OLED_Y, top_z + TOP_THK)
    screw_heads = [build_screw_head(mx, my, top_surface_z) for (mx, my) in MOUNT_HOLES]

    print("[2] Meshing")
    top_mesh = to_trimesh(top.translate((0, 0, top_z + TOP_THK / 2)))
    bot_mesh = to_trimesh(bot.translate((0, 0, bot_z + BOTTOM_THK / 2)))
    cap_meshes = [to_trimesh(c) for c in caps]
    knob_mesh = to_trimesh(knob)
    oled_mesh = to_trimesh(oled)
    screw_meshes = [to_trimesh(s) for s in screw_heads]

    print("[3] Rendering")
    bg = "#eef0f4"
    fig = plt.figure(figsize=(14, 10), dpi=150, facecolor=bg)
    ax = fig.add_subplot(111, projection="3d", facecolor=bg)

    # Blue CAD-viewport grid on the ground plane
    grid_color = (0.62, 0.74, 0.92, 0.85)
    for x in range(-100, 101, 6):
        ax.plot([x, x], [-100, 100], [0, 0], color=grid_color, linewidth=0.45, zorder=0)
    for y in range(-100, 101, 6):
        ax.plot([-100, 100], [y, y], [0, 0], color=grid_color, linewidth=0.45, zorder=0)

    parts = [
        (bot_mesh,  (0.10, 0.10, 0.12)),
        (top_mesh,  (0.82, 0.18, 0.18)),
        (oled_mesh, (0.03, 0.03, 0.05)),
        (knob_mesh, (0.18, 0.18, 0.20)),
    ]
    for cap in cap_meshes:
        parts.append((cap, (0.96, 0.96, 0.97)))
    for sm in screw_meshes:
        parts.append((sm, (0.55, 0.55, 0.58)))   # screw heads slightly metallic

    all_tris, all_colors = [], []
    light = np.array([0.35, -0.65, 0.7]); light /= np.linalg.norm(light)
    for mesh, color in parts:
        normals = mesh.face_normals
        intensity = np.clip(normals @ light, 0.0, 1.0) * 0.65 + 0.35
        base = np.array(color)
        shaded = (intensity[:, None] * base[None, :]).clip(0, 1)
        rgba = np.hstack([shaded, np.full((shaded.shape[0], 1), 1.0)])
        all_tris.append(mesh.triangles)
        all_colors.append(rgba)
    tris = np.concatenate(all_tris, axis=0)
    colors = np.concatenate(all_colors, axis=0)

    coll = Poly3DCollection(tris, facecolors=colors, edgecolors='none',
                            linewidths=0, shade=False, zsort='max')
    ax.add_collection3d(coll)

    # "HACK CLUB" decal on the red top plate
    ax.text(-30, 35, top_surface_z + 0.4, "HACK CLUB",
            color="white", fontsize=11, fontweight="bold",
            ha="center", va="center", zorder=10, rotation=-8)

    ax.set_xlim(-60, 60)
    ax.set_ylim(-55, 55)
    ax.set_zlim(0, 32)
    ax.set_box_aspect((CASE_W, CASE_H, 32))
    ax.view_init(elev=32, azim=-58)
    ax.set_axis_off()

    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    for path in (desktop_out, repo_out):
        plt.savefig(path, dpi=180, bbox_inches="tight", pad_inches=0.1,
                    facecolor=fig.get_facecolor())
        print(f"Saved {path}")


if __name__ == "__main__":
    main()
