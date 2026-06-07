#!/usr/bin/env python3
"""Build a Fusion360-style isometric mockup PNG of the assembled Hackpad.

Generates a CAD-viewport-styled render of the full assembly (red top plate +
black bottom tray + 4 white MX keycaps + encoder knob + OLED display) and
saves it to ~/Desktop/hackpad_mockup.png.
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

# --- dimensions (mm) — mirror build_case.py ---
PCB_W, PCB_H, PCB_THK = 90.0, 70.0, 1.6
CASE_WALL = 2.0
CASE_W = PCB_W + 2 * CASE_WALL
CASE_H = PCB_H + 2 * CASE_WALL
TOP_THK = 5.0
BOTTOM_THK = 8.0
PCB_REST_THK = 2.0
CORNER_R = 3.0
MX_CUT = 14.0
SW_PITCH = 19.05
SW_CENTER_X = -22.0
SW_CENTER_Y = 5.0
SW_X = [SW_CENTER_X - SW_PITCH / 2, SW_CENTER_X + SW_PITCH / 2]
SW_Y = [SW_CENTER_Y - SW_PITCH / 2, SW_CENTER_Y + SW_PITCH / 2]
ENC_X, ENC_Y = 22.0, 14.0
OLED_X, OLED_Y = 24.0, -25.0
MOUNT_HOLES = [(-40.0, -30.0), (40.0, -30.0), (40.0, 30.0), (-40.0, 30.0)]


def build_top_plate():
    plate = cq.Workplane("XY").box(CASE_W, CASE_H, TOP_THK).edges("|Z").fillet(CORNER_R)
    # switch cutouts
    for sy in SW_Y:
        for sx in SW_X:
            plate = (plate.faces(">Z").workplane(centerOption="CenterOfBoundBox")
                     .center(sx, sy).rect(MX_CUT, MX_CUT).cutThruAll())
    # encoder shaft hole
    plate = (plate.faces(">Z").workplane(centerOption="CenterOfBoundBox")
             .center(ENC_X, ENC_Y).circle(3.75).cutThruAll())
    # OLED window
    plate = (plate.faces(">Z").workplane(centerOption="CenterOfBoundBox")
             .center(OLED_X, OLED_Y).rect(22.0, 6.0).cutThruAll())
    # XIAO inspection window
    plate = (plate.faces(">Z").workplane(centerOption="CenterOfBoundBox")
             .center(0.0, -25.0).rect(20.0, 18.0).cutThruAll())
    # screw clearance
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
    """Truncated pyramid (DSA-ish) keycap centered on (sx, sy), base at z0."""
    base = 17.5
    top = 13.0
    h = 7.0
    cap = (cq.Workplane("XY")
           .workplane(offset=z0)
           .rect(base, base)
           .workplane(offset=h)
           .rect(top, top)
           .loft(combine=True))
    cap = cap.translate((sx, sy, 0))
    return cap


def build_encoder_knob(ex, ey, z0):
    """A short cylindrical encoder knob (with subtle taper)."""
    return (cq.Workplane("XY")
            .workplane(offset=z0)
            .center(ex, ey)
            .circle(7.0)
            .workplane(offset=7.0)
            .circle(6.0)
            .loft(combine=True))


def build_oled_face(ox, oy, z_top):
    """Thin dark rectangle representing the OLED screen, sitting on top of the PCB area."""
    return (cq.Workplane("XY")
            .workplane(offset=z_top - 0.5)
            .center(ox, oy)
            .rect(22.0, 6.0)
            .extrude(0.5))


_stl_counter = [0]


def to_trimesh(cq_obj):
    """cadquery -> trimesh via unique temporary STL."""
    _stl_counter[0] += 1
    stl_path = os.path.join(BUILD_DIR, f"tmp_{_stl_counter[0]}.stl")
    cq.exporters.export(cq_obj, stl_path, tolerance=0.05, angularTolerance=0.08)
    return trimesh.load(stl_path, force="mesh")


def add_mesh(ax, mesh, facecolor, alpha=1.0, zorder=1):
    # Per-triangle Lambert shading from a virtual light source.
    light = np.array([0.35, -0.65, 0.7])
    light = light / np.linalg.norm(light)
    normals = mesh.face_normals
    intensity = np.clip(normals @ light, 0.0, 1.0) * 0.65 + 0.35
    base = np.array(facecolor)
    shaded = (intensity[:, None] * base[None, :]).clip(0, 1)
    rgba = np.hstack([shaded, np.full((shaded.shape[0], 1), alpha)])

    coll = Poly3DCollection(
        mesh.triangles,
        facecolors=rgba,
        edgecolors='none',         # No wireframe edges
        linewidths=0,
        shade=False,
        zsort='max',                # Use MAX z of triangle, not avg, so caps win
    )
    coll.set_zorder(zorder)
    ax.add_collection3d(coll)


def main():
    desktop = os.path.expanduser("~/Desktop")
    out_path = os.path.join(desktop, "hackpad_mockup.png")

    print("[1] Modeling top plate")
    top = build_top_plate()
    print("[2] Modeling bottom tray")
    bot = build_bottom_tray()

    # Stack heights (mm). Bottom tray at z=0..8. PCB at 8..9.6 (skip rendering).
    # Top plate at 10.6..15.6. Keycaps sit on the top plate, base at z = TOP_TOP - 1 = 14.6.
    bot_z = 0.0
    top_z = BOTTOM_THK + PCB_THK + 1.0   # 10.6
    keycap_z = top_z + TOP_THK - 1.0     # 14.6 — slight overlap so they "punch through"

    print("[3] Modeling 4 keycaps")
    caps = [build_keycap(sx, sy, keycap_z) for sy in SW_Y for sx in SW_X]
    print("[4] Modeling encoder knob")
    knob = build_encoder_knob(ENC_X, ENC_Y, top_z + TOP_THK - 1.0)
    print("[5] Modeling OLED face")
    oled = build_oled_face(OLED_X, OLED_Y, top_z + TOP_THK)

    print("[6] Converting to mesh")
    # Translate to stack
    top_mesh = to_trimesh(top.translate((0, 0, top_z + TOP_THK / 2)))
    bot_mesh = to_trimesh(bot.translate((0, 0, bot_z + BOTTOM_THK / 2)))
    cap_meshes = [to_trimesh(c) for c in caps]
    knob_mesh = to_trimesh(knob)
    oled_mesh = to_trimesh(oled)

    print("[7] Rendering")
    bg = "#eef0f4"
    fig = plt.figure(figsize=(14, 9), dpi=150, facecolor=bg)
    ax = fig.add_subplot(111, projection="3d", facecolor=bg)

    # Brighter blue grid background — thin lines on the ground (z=0) plane
    grid_color = (0.62, 0.74, 0.92, 0.85)
    grid_extent = 100
    grid_step = 6
    for x in range(-grid_extent, grid_extent + 1, grid_step):
        ax.plot([x, x], [-grid_extent, grid_extent], [0, 0],
                color=grid_color, linewidth=0.45, zorder=0)
    for y in range(-grid_extent, grid_extent + 1, grid_step):
        ax.plot([-grid_extent, grid_extent], [y, y], [0, 0],
                color=grid_color, linewidth=0.45, zorder=0)

    # Combine all meshes into one Poly3DCollection so matplotlib can sort
    # every triangle globally by depth (separate collections don't interleave).
    parts = [
        (bot_mesh,  (0.10, 0.10, 0.12)),
        (top_mesh,  (0.82, 0.18, 0.18)),
        (oled_mesh, (0.03, 0.03, 0.05)),
        (knob_mesh, (0.18, 0.18, 0.20)),
    ]
    for cap in cap_meshes:
        parts.append((cap, (0.96, 0.96, 0.97)))

    all_tris = []
    all_colors = []
    light = np.array([0.35, -0.65, 0.7])
    light = light / np.linalg.norm(light)
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

    # "HACK CLUB" decal text on the top plate, drawn AFTER the mesh so it
    # appears on the surface, not floating above any geometry.
    ax.text(-5, 27, top_z + TOP_THK + 0.4, "HACK CLUB",
            color="white", fontsize=11, fontweight="bold",
            ha="center", va="center", zorder=10,
            rotation=-8)

    # Camera + framing
    ax.set_xlim(-55, 55)
    ax.set_ylim(-45, 45)
    ax.set_zlim(0, 30)
    ax.set_box_aspect((CASE_W, CASE_H, 30))
    ax.view_init(elev=32, azim=-58)
    ax.set_axis_off()

    # Tighten title bar margins
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    plt.savefig(out_path, dpi=180, bbox_inches="tight", pad_inches=0.1,
                facecolor=fig.get_facecolor())
    print(f"Saved {out_path}")


if __name__ == "__main__":
    main()
