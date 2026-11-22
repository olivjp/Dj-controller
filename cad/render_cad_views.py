#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generates high-resolution 3D Isometric & Multi-View Orthographic Blueprint PNG renders
from the compiled FreeCAD STL meshes (`cad/stl/*.stl`).
"""

import os
import struct
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

CAD_STL_DIR = r"C:\Users\joaop\Downloads\Código\Dj-controller\cad\stl"
RENDER_DIR = r"C:\Users\joaop\Downloads\Código\Dj-controller\renders"
os.makedirs(RENDER_DIR, exist_ok=True)

def load_binary_stl(path: str) -> np.ndarray:
    with open(path, "rb") as f:
        data = f.read()
    # Check if ASCII or Binary STL
    if data.startswith(b"solid") and b"facet normal" in data[:512]:
        verts = []
        for line in data.decode("utf-8", errors="ignore").splitlines():
            line = line.strip()
            if line.startswith("vertex "):
                parts = line.split()
                verts.append([float(parts[1]), float(parts[2]), float(parts[3])])
        arr = np.array(verts, dtype=np.float32)
        return arr.reshape((-1, 3, 3))
    else:
        num_tris = struct.unpack("<I", data[80:84])[0]
        dt = np.dtype([
            ("normal", "<f4", (3,)),
            ("v", "<f4", (3, 3)),
            ("attr", "<u2"),
        ])
        tris = np.frombuffer(data, dtype=dt, count=num_tris, offset=84)
        return tris["v"].copy()

def subdivide_large_triangles(tris: np.ndarray, max_edge: float = 12.0, passes: int = 4) -> np.ndarray:
    """Recursively splits triangles with any edge > max_edge along their longest edge so zsort='average' is exact."""
    cur = tris
    for _ in range(passes):
        v0, v1, v2 = cur[:, 0], cur[:, 1], cur[:, 2]
        e01 = np.linalg.norm(v1 - v0, axis=1)
        e12 = np.linalg.norm(v2 - v1, axis=1)
        e20 = np.linalg.norm(v0 - v2, axis=1)
        max_e = np.maximum(np.maximum(e01, e12), e20)
        mask = max_e > max_edge
        if not np.any(mask):
            break
        keep = cur[~mask]
        big = cur[mask]
        b0, b1, b2 = big[:, 0], big[:, 1], big[:, 2]
        l01 = np.linalg.norm(b1 - b0, axis=1)
        l12 = np.linalg.norm(b2 - b1, axis=1)
        l20 = np.linalg.norm(b0 - b2, axis=1)
        # Split all 3 edges (1-to-4 midpoint subdivision) for uniform mesh density
        m01 = 0.5 * (b0 + b1)
        m12 = 0.5 * (b1 + b2)
        m20 = 0.5 * (b2 + b0)
        t1 = np.stack([b0, m01, m20], axis=1)
        t2 = np.stack([m01, b1, m12], axis=1)
        t3 = np.stack([m20, m12, b2], axis=1)
        t4 = np.stack([m01, m12, m20], axis=1)
        cur = np.concatenate([keep, t1, t2, t3, t4], axis=0)
    return cur

def shade_triangles(tris: np.ndarray, base_rgb: tuple[float, float, float], light_dir=(0.4, -0.6, 0.8)):
    v0, v1, v2 = tris[:, 0], tris[:, 1], tris[:, 2]
    normals = np.cross(v1 - v0, v2 - v0)
    norms = np.linalg.norm(normals, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    normals = normals / norms

    ld = np.array(light_dir, dtype=np.float32)
    ld = ld / np.linalg.norm(ld)
    intensity = np.clip(np.abs(normals @ ld), 0.25, 1.0)
    colors = np.zeros((len(tris), 4), dtype=np.float32)
    colors[:, 0] = np.clip(base_rgb[0] * intensity, 0, 1)
    colors[:, 1] = np.clip(base_rgb[1] * intensity, 0, 1)
    colors[:, 2] = np.clip(base_rgb[2] * intensity, 0, 1)
    colors[:, 3] = 1.0
    return colors

def render_isometric():
    top_tris = subdivide_large_triangles(load_binary_stl(os.path.join(CAD_STL_DIR, "ddj_flx4_top_faceplate.stl")), max_edge=24.0, passes=2)
    bot_tris = subdivide_large_triangles(load_binary_stl(os.path.join(CAD_STL_DIR, "ddj_flx4_bottom_chassis.stl")), max_edge=24.0, passes=2)
    jog_tris = load_binary_stl(os.path.join(CAD_STL_DIR, "ddj_flx4_jog_wheel.stl"))

    bot_shifted = bot_tris.copy()
    bot_shifted[:, :, 2] -= 10.0

    jog_a = jog_tris.copy()
    jog_a[:, :, 0] += 48.0
    jog_a[:, :, 1] += 116.0
    jog_a[:, :, 2] += 5.0

    jog_b = jog_tris.copy()
    jog_b[:, :, 0] += 272.0
    jog_b[:, :, 1] += 116.0
    jog_b[:, :, 2] += 5.0

    parts = [
        (bot_shifted, (0.20, 0.25, 0.34)),
        (top_tris, (0.32, 0.38, 0.48)),
        (jog_a, (0.10, 0.75, 0.98)),
        (jog_b, (0.98, 0.36, 0.30)),
    ]

    all_tris = np.concatenate([p[0] for p in parts], axis=0)
    all_cols = np.concatenate([shade_triangles(p[0], p[1]) for p in parts], axis=0)

    fig = plt.figure(figsize=(18, 9), dpi=180, facecolor="#0d1117")

    # Left Subplot: 3D Isometric Exploded View (Single unified z-sorted collection)
    ax1 = fig.add_subplot(121, projection="3d", facecolor="#0d1117")
    poly1 = Poly3DCollection(all_tris, facecolors=all_cols, edgecolors="none", zsort="average")
    ax1.add_collection3d(poly1)
    ax1.set_xlim(-15, 355)
    ax1.set_ylim(-15, 221)
    ax1.set_zlim(-55, 22)
    ax1.set_box_aspect((370, 236, 77))
    ax1.view_init(elev=36, azim=-60)
    ax1.set_axis_off()
    ax1.set_title("Isometric 3D Printable Assembly v2.3 (Deck A + Mixer + Deck B)", color="#58a6ff", fontsize=12, fontweight="bold", pad=6)

    # Right Subplot: Top-Down Orthographic View
    ax2 = fig.add_subplot(122, projection="3d", facecolor="#0d1117")
    poly2 = Poly3DCollection(all_tris, facecolors=all_cols, edgecolors="none", zsort="average")
    ax2.add_collection3d(poly2)
    ax2.set_xlim(-10, 350)
    ax2.set_ylim(-10, 216)
    ax2.set_zlim(-55, 22)
    ax2.set_box_aspect((360, 226, 77))
    ax2.view_init(elev=88, azim=-90)
    ax2.set_axis_off()
    ax2.set_title("Top Orthographic Control Deck View (340 x 206 x 45.5 mm)", color="#ff7b72", fontsize=12, fontweight="bold", pad=6)

    fig.suptitle(
        "Pioneer DDJ-FLX4 Modular Core v2.3 — FreeCAD 1.0 STEP & 3D-Printable STL CAD Suite\n"
        "Cyan: Deck A 84mm Jog Wheel | Red: Deck B 84mm Jog Wheel | 30x G82 Pads/Transport | 10-11x WH148 Pots | 5x D103 Faders",
        color="#e6edf3",
        fontsize=13,
        fontweight="bold",
        y=0.96,
    )
    plt.subplots_adjust(left=0.02, right=0.98, bottom=0.02, top=0.86, wspace=0.04)
    out_path = os.path.join(RENDER_DIR, "cad_isometric_render.png")
    plt.savefig(out_path, dpi=180, facecolor="#0d1117")
    plt.close(fig)
    print(f"Saved 3D CAD dual-view render: {out_path}")

if __name__ == "__main__":
    render_isometric()
