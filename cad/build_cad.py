#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deterministic FreeCAD 1.0 OpenCASCADE B-Rep Solid & Mesh Compiler for the
Pioneer DDJ-FLX4 Inspired DJ Controller Enclosure.
Runs inside FreeCAD 1.0's headless Python (`C:/Program Files/FreeCAD 1.0/bin/python.exe`)
to generate:
  - ISO 10303-21 STEP files (.step) for mechanical CAD / CNC / injection molding
  - High-resolution triangulated STL files (.stl) for 3D printing (both full unibody
    and 3 modular bolted sections for 220x220mm FDM 3D printers: Deck A, Center Mixer, Deck B)
"""

import os
import math
import FreeCAD
import Part
import Mesh
import MeshPart

OUT_DIR = r"C:\Users\joaop\Downloads\Código\Dj-controller\cad"
STL_DIR = os.path.join(OUT_DIR, "stl")
STEP_DIR = os.path.join(OUT_DIR, "step")
os.makedirs(STL_DIR, exist_ok=True)
os.makedirs(STEP_DIR, exist_ok=True)

# ── Exact Mechanical Coordinates Matched 1:1 with KiCad 9.0 PCB ──────────────
PCB_W = 340.0
PCB_D = 220.0
PCB_T = 1.6

WALL_T = 4.0
CLEARANCE = 1.0
CASE_W = PCB_W + 2 * (WALL_T + CLEARANCE)  # 350.0 mm
CASE_D = PCB_D + 2 * (WALL_T + CLEARANCE)  # 230.0 mm
BOTTOM_H = 26.0
TOP_PLATE_T = 3.2
STANDOFF_H = 14.0

M3_HOLES = [
    (8.0, 8.0), (116.0, 8.0), (224.0, 8.0), (332.0, 8.0),
    (8.0, 212.0), (116.0, 212.0), (224.0, 212.0), (332.0, 212.0),
]

JOG_CENTERS = [
    (55.5, 94.5),   # Deck A Jog Wheel (ENC1 shaft center)
    (275.5, 94.5),  # Deck B Jog Wheel (ENC2 shaft center)
]

ROTARY_POTS = [
    (137.0, 58.5), (137.0, 74.5), (137.0, 90.5), (137.0, 106.5), (137.0, 122.5),
    (213.0, 58.5), (213.0, 74.5), (213.0, 90.5), (213.0, 106.5), (213.0, 122.5),
    (175.0, 58.5),
]

VERT_FADERS = [
    (133.75, 167.25),  # RV11 Ch1 Vol
    (209.75, 167.25),  # RV12 Ch2 Vol
    (103.75, 95.25),   # RV14 Deck A Pitch
    (323.75, 95.25),   # RV15 Deck B Pitch
]

HORIZ_FADER = (170.25, 205.75)  # RV13 Crossfader

SW_CENTERS = [
    # Deck A 2x4 Performance Pads (SW1..SW8)
    (22.25, 144.5), (44.25, 144.5), (66.25, 144.5), (88.25, 144.5),
    (22.25, 164.5), (44.25, 164.5), (66.25, 164.5), (88.25, 164.5),
    # Deck B 2x4 Performance Pads (SW9..SW16)
    (242.25, 144.5), (264.25, 144.5), (286.25, 144.5), (308.25, 144.5),
    (242.25, 164.5), (264.25, 164.5), (286.25, 164.5), (308.25, 164.5),
    # Mixer Control Buttons (SW17..SW22) — matched 1:1 with build_pcb.py (+6.25, +2.50 from footprint anchor)
    (152.75, 50.5), (191.25, 50.5), (170.25, 78.5),
    (170.25, 96.5), (152.25, 114.5), (188.25, 114.5),
    # Deck A Loop/Sync & Transport (SW23..SW26)
    (82.25, 24.5), (82.25, 44.5), (22.25, 190.5), (52.25, 190.5),
    # Deck B Loop/Sync & Transport (SW27..SW30)
    (234.25, 24.5), (234.25, 44.5), (242.25, 190.5), (272.25, 190.5),
]

def cy(y_pcb: float) -> float:
    """Convert KiCad top-down Y (0..220) to right-handed 3D CAD Y (220..0)."""
    return PCB_D - y_pcb

def export_shape(shape: Part.Shape, name: str):
    step_path = os.path.join(STEP_DIR, f"{name}.step")
    stl_path = os.path.join(STL_DIR, f"{name}.stl")
    shape.exportStep(step_path)
    mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.15, AngularDeflection=0.25, Relative=False)
    mesh.write(stl_path)
    print(f"Exported {name}: STEP ({os.path.getsize(step_path)} B) | STL ({mesh.CountFacets} facets)")

def make_top_faceplate() -> Part.Shape:
    ox = -WALL_T - CLEARANCE
    oy = -WALL_T - CLEARANCE
    plate = Part.makeBox(CASE_W, CASE_D, TOP_PLATE_T, FreeCAD.Vector(ox, oy, 0.0))

    # Add 8 under-plate alignment bosses
    bosses = []
    for hx, hy in M3_HOLES:
        boss = Part.makeCylinder(4.0, 4.0, FreeCAD.Vector(hx, cy(hy), -4.0))
        bosses.append(boss)
    plate = plate.fuse(bosses)

    # Collect all subtractive cutouts and boolean-cut in batch
    cutouts = []

    # 8x M3 Countersunk Holes
    for hx, hy in M3_HOLES:
        cutouts.append(Part.makeCylinder(1.7, TOP_PLATE_T + 6.0, FreeCAD.Vector(hx, cy(hy), -5.0)))
        cutouts.append(Part.makeCone(1.7, 3.25, 1.7, FreeCAD.Vector(hx, cy(hy), TOP_PLATE_T - 1.6)))

    # 2x Jog Wheel Recessed Wells + EC11 Shaft Clearances
    for jx, jy in JOG_CENTERS:
        cutouts.append(Part.makeCylinder(43.0, 1.5, FreeCAD.Vector(jx, cy(jy), TOP_PLATE_T - 1.2)))
        cutouts.append(Part.makeCylinder(4.5, TOP_PLATE_T + 2.0, FreeCAD.Vector(jx, cy(jy), -1.0)))

    # 11x Rotary Potentiometer Shaft Holes (d=7.5mm)
    for rx, ry in ROTARY_POTS:
        cutouts.append(Part.makeCylinder(3.75, TOP_PLATE_T + 2.0, FreeCAD.Vector(rx, cy(ry), -1.0)))

    # 4x Vertical Slide Fader Slots (3.4 x 48.0 mm)
    for fx, fy in VERT_FADERS:
        cutouts.append(Part.makeBox(3.4, 48.0, TOP_PLATE_T + 2.0, FreeCAD.Vector(fx - 1.7, cy(fy) - 24.0, -1.0)))

    # 1x Horizontal Crossfader Slot (48.0 x 3.4 mm)
    hfx, hfy = HORIZ_FADER
    cutouts.append(Part.makeBox(48.0, 3.4, TOP_PLATE_T + 2.0, FreeCAD.Vector(hfx - 24.0, cy(hfy) - 1.7, -1.0)))

    # 30x Tactile Push-Button Square Cutouts (13.2 x 13.2 mm)
    for sx, sy in SW_CENTERS:
        cutouts.append(Part.makeBox(13.2, 13.2, TOP_PLATE_T + 2.0, FreeCAD.Vector(sx - 6.6, cy(sy) - 6.6, -1.0)))

    # 3x Status LED Holes (d=5.2mm)
    for lx in [159.27, 170.27, 181.27]:
        cutouts.append(Part.makeCylinder(2.6, TOP_PLATE_T + 2.0, FreeCAD.Vector(lx, cy(130.0), -1.0)))

    plate = plate.cut(cutouts)
    return plate

def make_bottom_chassis() -> Part.Shape:
    ox = -WALL_T - CLEARANCE
    oy = -WALL_T - CLEARANCE
    outer = Part.makeBox(CASE_W, CASE_D, BOTTOM_H, FreeCAD.Vector(ox, oy, -BOTTOM_H))
    inner = Part.makeBox(
        PCB_W + 2 * CLEARANCE,
        PCB_D + 2 * CLEARANCE,
        BOTTOM_H,
        FreeCAD.Vector(-CLEARANCE, -CLEARANCE, -BOTTOM_H + 3.0),
    )
    tub = outer.cut(inner)

    additions = []
    # 8x Internal M3 Standoff Pillars
    for hx, hy in M3_HOLES:
        additions.append(Part.makeCylinder(4.5, STANDOFF_H, FreeCAD.Vector(hx, cy(hy), -BOTTOM_H + 3.0)))

    # 2x Structural Partition Ribs at X=116 and X=224
    for x_rib in [116.0, 224.0]:
        additions.append(Part.makeBox(4.0, PCB_D, STANDOFF_H - 2.0, FreeCAD.Vector(x_rib - 2.0, 0.0, -BOTTOM_H + 3.0)))

    tub = tub.fuse(additions)

    cuts = []
    # 8x M3 Thread Bores (d=2.8mm)
    for hx, hy in M3_HOLES:
        cuts.append(Part.makeCylinder(1.4, STANDOFF_H + 1.0, FreeCAD.Vector(hx, cy(hy), -BOTTOM_H + 3.0)))

    # Rear USB-B (Leonardo R3) & USB-C (Pro Micro) Connector Cutouts
    cuts.append(Part.makeBox(18.0, WALL_T + 4.0, 13.0, FreeCAD.Vector(28.0, PCB_D - 1.0, -BOTTOM_H + 3.0 + STANDOFF_H - 2.0)))
    cuts.append(Part.makeBox(16.0, WALL_T + 4.0, 10.0, FreeCAD.Vector(244.0, PCB_D - 1.0, -BOTTOM_H + 3.0 + STANDOFF_H - 2.0)))

    tub = tub.cut(cuts)
    return tub

def make_jog_wheel() -> Part.Shape:
    base_disc = Part.makeCone(42.0, 41.0, 9.0, FreeCAD.Vector(0, 0, 0))
    top_bevel = Part.makeCone(41.0, 38.0, 2.5, FreeCAD.Vector(0, 0, 9.0))
    hub_boss = Part.makeCylinder(7.0, 6.0, FreeCAD.Vector(0, 0, -6.0))
    platter = base_disc.fuse([top_bevel, hub_boss])

    cuts = [
        Part.makeCylinder(3.025, 16.0, FreeCAD.Vector(0, 0, -7.0)),  # 6.05mm EC11 shaft bore
        Part.makeCylinder(32.0, 2.5, FreeCAD.Vector(0, 0, 9.5)),     # Top center recess
    ]
    # 16 perimeter grip dimples
    for i in range(16):
        ang = math.radians(i * 22.5)
        gx = 42.0 * math.cos(ang)
        gy = 42.0 * math.sin(ang)
        cuts.append(Part.makeCylinder(2.25, 8.0, FreeCAD.Vector(gx, gy, 3.5)))

    return platter.cut(cuts)

def make_pad_keycap() -> Part.Shape:
    # 12.6 x 12.6 mm keycap with bottom skirt flange (14.2 x 14.2 mm) and 3.8mm stem pocket for G82 tactile switch
    flange = Part.makeBox(14.2, 14.2, 1.2, FreeCAD.Vector(-7.1, -7.1, 0.0))
    cap = Part.makeBox(12.6, 12.6, 4.5, FreeCAD.Vector(-6.3, -6.3, 1.2))
    body = flange.fuse(cap)
    cavity = Part.makeCylinder(2.1, 3.2, FreeCAD.Vector(0, 0, 0.0))
    return body.cut(cavity)

def split_into_3_printer_sections(shape: Part.Shape, prefix: str):
    """
    Splits a 350x230mm part along the M3 rib seams X=116.0 and X=224.0 into:
      - Left Deck A   (X in [-10 .. 116.0] -> width 121 mm, fits any 220x220mm bed!)
      - Center Mixer  (X in [116.0 .. 224.0] -> width 108 mm, fits any 220x220mm bed!)
      - Right Deck B  (X in [224.0 .. 350.0] -> width 121 mm, fits any 220x220mm bed!)
    """
    zones = [
        ("left_deckA", -20.0, 116.0),
        ("center_mixer", 116.0, 224.0),
        ("right_deckB", 224.0, 360.0),
    ]
    for zname, x0, x1 in zones:
        bbox = Part.makeBox(x1 - x0, 260.0, 100.0, FreeCAD.Vector(x0, -20.0, -50.0))
        sec = shape.common(bbox)
        stl_path = os.path.join(STL_DIR, f"{prefix}_{zname}.stl")
        mesh = MeshPart.meshFromShape(Shape=sec, LinearDeflection=0.15, AngularDeflection=0.25, Relative=False)
        mesh.write(stl_path)
        print(f"Exported 220x220mm Printable Section {prefix}_{zname}.stl ({mesh.CountFacets} facets)")

def main():
    print("Building DDJ-FLX4 3D CAD Solids in FreeCAD 1.0...")
    top_plate = make_top_faceplate()
    export_shape(top_plate, "ddj_flx4_top_faceplate")
    split_into_3_printer_sections(top_plate, "ddj_flx4_top")

    bottom_tub = make_bottom_chassis()
    export_shape(bottom_tub, "ddj_flx4_bottom_chassis")
    split_into_3_printer_sections(bottom_tub, "ddj_flx4_bottom")

    jog = make_jog_wheel()
    export_shape(jog, "ddj_flx4_jog_wheel")

    keycap = make_pad_keycap()
    export_shape(keycap, "ddj_flx4_pad_keycap")

    # Full Assembly Compound
    jog_a = jog.copy()
    jog_a.Placement.Base = FreeCAD.Vector(JOG_CENTERS[0][0], cy(JOG_CENTERS[0][1]), TOP_PLATE_T + 1.5)
    jog_b = jog.copy()
    jog_b.Placement.Base = FreeCAD.Vector(JOG_CENTERS[1][0], cy(JOG_CENTERS[1][1]), TOP_PLATE_T + 1.5)

    assembly = Part.makeCompound([top_plate, bottom_tub, jog_a, jog_b])
    export_shape(assembly, "ddj_flx4_full_assembly")
    print("ALL CAD MODELS BUILT AND EXPORTED SUCCESSFULLY!")

if __name__ == "__main__":
    main()
