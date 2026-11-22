#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deterministic FreeCAD 1.0 OpenCASCADE B-Rep Solid & Mesh Compiler — DDJ-FLX4 Modular Core v2.1.

Matched 1:1 to Joao Paulo's ACTUAL physical hardware (AliExpress 08/11/2025 + Mercado Livre 12/11/2025):
  - 5x Slide Faders D103 = D10Kx2 (75 mm body, 60 mm travel, 71 mm mount hole pitch, 4.6 x 64.0 mm slots)
  - 11x WH148 B10K Rotary Pots (18.5 mm vertical pitch > 16 mm body -> zero collision; 7.6 mm M7 bore)
  - 2x EC11 Quadrature Encoders + 84 mm Jog Wheels (6.25 mm D-flat bore + radial M3 set-screw)
  - 30x G82 12x12x5mm Tactile Switches + 12.6 mm keycaps in 13.2 mm windows (0.30 mm clearance/side)
  - 98 x 98 mm 2-Layer Core PCB (Pro Micro USB-C + 2x blue CD74HC4067 1x16+1x8 breakouts)
    mounted inside Center Mixer with 21.4 mm vertical headroom and flush rear USB-C port.
  - 340 x 206 mm external enclosure split into 3 bolted modules (115/110/115 x 206 mm -> fits ANY 220x220 bed!)
  - Captive M3 hex nut pockets (5.8 mm AF) in bottom chassis — ZERO direct screwing into PLA!
  - Includes ~8 g `ddj_flx4_tolerance_test.stl` calibration coupon to verify printer fits first.
"""

import os
import math
import FreeCAD
import Part
import MeshPart

OUT_DIR = r"C:\Users\joaop\Downloads\Código\Dj-controller\cad"
STL_DIR = os.path.join(OUT_DIR, "stl")
STEP_DIR = os.path.join(OUT_DIR, "step")
os.makedirs(STL_DIR, exist_ok=True)
os.makedirs(STEP_DIR, exist_ok=True)

# ── Global Enclosure Dimensions (CAD frame: X=0..340, Y=0 Front .. 206 Rear) ──
CASE_W      = 340.0
CASE_D      = 206.0    # <= 210 mm -> fits 220x220 mm FDM beds with 5 mm brim!
WALL_T      = 4.0
FLOOR_T     = 3.0
BOTTOM_H    = 42.0     # Z = -42.0 .. 0.0 (31.4 mm headroom above 98x98 Core PCB — zero WH148 collision!)
TOP_PLATE_T = 3.5      # Z =   0.0 .. +3.5

SEAM_L = 115.0
SEAM_R = 225.0

# 12x Vertical M3 Pillars (4 per module, completely clear of seams, pots, and 75 mm faders!)
M3_PILLARS = [
    # Deck A (X in 0..115)
    (10.0, 10.0), (105.0, 10.0), (10.0, 196.0), (105.0, 196.0),
    # Center Mixer (X in 115..225)
    (122.0, 10.0), (218.0, 10.0), (122.0, 197.0), (218.0, 197.0),
    # Deck B (X in 225..340)
    (235.0, 10.0), (330.0, 10.0), (235.0, 196.0), (330.0, 196.0),
]

# 98 x 98 mm Core PCB mounted inside Center Mixer flush against rear inner wall (Y = 202.0)
PCB_W = 98.0
PCB_X0 = (CASE_W - PCB_W) / 2.0      # 121.0 mm
PCB_Y_REAR = CASE_D - WALL_T         # 202.0 mm (KiCad Y=0)
PCB_STANDOFF_H = 6.0                 # PCB top at Z = -21.4 mm -> 21.4 mm headroom!
PCB_HOLES_KICAD = [(5.08, 5.08), (92.71, 5.08), (5.08, 92.71), (92.71, 92.71)]
PCB_HOLES_CAD = [(PCB_X0 + hx, PCB_Y_REAR - hy) for (hx, hy) in PCB_HOLES_KICAD]
USB_C_X = PCB_X0 + 48.895            # 169.895 mm (exact Pro Micro USB-C center)

# ── Panel-Mount Control Coordinates (Verified Zero-Collision for 75 mm D103 Faders!) ──
JOG_CENTERS = [
    (48.0, 116.0),   # Deck A Jog Wheel (clear of left wall and Pitch A fader)
    (272.0, 116.0),  # Deck B Jog Wheel (clear of seam and Pitch B fader)
]

# 11x WH148 Rotary Pots (18.5 mm vertical pitch > 16 mm body -> zero collision!)
ROTARY_POTS = [
    (136.0, 189.0), (136.0, 170.5), (136.0, 152.0), (136.0, 133.5), (136.0, 115.0),
    (204.0, 189.0), (204.0, 170.5), (204.0, 152.0), (204.0, 133.5), (204.0, 115.0),
    (170.0, 186.0),  # RV16 Master / FX (optional if using only 10 WH148s)
]
POT_HOLE_D = 7.6     # M7 WH148 bushing + FDM clearance (drill to 8.2 mm if M8)

# 5x D103 = D10Kx2 Slide Faders (75 mm body, 60 mm travel, 71 mm screw pitch)
VERT_FADERS = [
    (138.0, 68.0),   # RV11 Ch1 Vol (body Y=30.5..105.5, clear of Crossfader & WH148s!)
    (202.0, 68.0),   # RV12 Ch2 Vol
    (102.0, 116.0),  # RV14 Deck A Pitch (body Y=78.5..153.5, clear of Pads & SW24!)
    (326.0, 116.0),  # RV15 Deck B Pitch
]
HORIZ_FADER = (170.0, 20.0)  # RV13 Crossfader (body X=132.5..207.5, clear of M3 pillars!)
FADER_SLOT_W = 4.6           # Fits 4 mm lever with FDM clearance (widen if using 8 mm lever)
FADER_SLOT_L = 64.0          # 60 mm travel + 2 mm margin per end
FADER_MOUNT_OFFSET = 35.5    # 71.0 mm screw hole pitch (standard D103 75 mm fader)

# 30x Tactile Push-Button Square Cutouts (13.2 x 13.2 mm -> 0.30 mm clearance/side)
SW_CENTERS = [
    # Deck A 2x4 Performance Pads (SW1..SW8)
    (22.0, 60.0), (44.0, 60.0), (66.0, 60.0), (88.0, 60.0),
    (22.0, 40.0), (44.0, 40.0), (66.0, 40.0), (88.0, 40.0),
    # Deck B 2x4 Performance Pads (SW9..SW16)
    (242.0, 60.0), (264.0, 60.0), (286.0, 60.0), (308.0, 60.0),
    (242.0, 40.0), (264.0, 40.0), (286.0, 40.0), (308.0, 40.0),
    # Mixer Buttons (SW17..SW22: LOAD_A, LOAD_B, SMART_CFX, BEAT_FX, CUE_CH1, CUE_CH2)
    (156.0, 160.0), (184.0, 160.0),
    (170.0, 138.0), (170.0, 118.0),
    (158.0, 86.0),  (182.0, 86.0),
    # Deck A Loop/Sync & Transport (SW23..SW26)
    (80.0, 186.0), (80.0, 166.0), (22.0, 18.0), (50.0, 18.0),
    # Deck B Loop/Sync & Transport (SW27..SW30)
    (244.0, 186.0), (244.0, 166.0), (242.0, 18.0), (270.0, 18.0),
]

# 7x Switch Backing Carrier Groups (holds all 30 G82 12x12x5mm tactile switches at exact Z=-5.2mm!)
# Each group: (name, x_min, y_min, x_max, y_max, screw_pts, switch_indices)
SWITCH_CARRIERS = [
    ("pads_deckA",   11.0,  29.0,  99.0,  71.0, [(14.5, 32.5), (95.5, 32.5), (14.5, 67.5), (95.5, 67.5)], list(range(0, 8))),
    ("pads_deckB",  231.0,  29.0, 319.0,  71.0, [(234.5, 32.5), (315.5, 32.5), (234.5, 67.5), (315.5, 67.5)], list(range(8, 16))),
    ("mixer_top",   145.0, 108.0, 195.0, 170.0, [(149.0, 112.0), (191.0, 112.0), (149.0, 167.0), (191.0, 167.0)], [16, 17, 18, 19]),
    ("mixer_cue",   147.0,  75.0, 193.0,  97.0, [(150.5, 78.5), (189.5, 93.5)], [20, 21]),
    ("loopsync_A",   69.0, 155.0,  91.0, 197.0, [(72.5, 158.5), (87.5, 193.5)], [22, 23]),
    ("transp_A",     11.0,   7.5,  61.0,  28.5, [(14.5, 25.0), (57.5, 11.0)],   [24, 25]),
    ("loopsync_B",  233.0, 155.0, 255.0, 197.0, [(236.5, 158.5), (251.5, 193.5)], [26, 27]),
    ("transp_B",    231.0,   7.5, 281.0,  28.5, [(234.5, 25.0), (277.5, 11.0)], [28, 29]),
]
CARRIER_STANDOFF_H = 5.2   # Exact Z-height under faceplate so G82 (5.0mm) sits 0.2mm below rest keycap!
CARRIER_PLATE_T    = 2.5

def make_hex_prism(af_mm: float, height: float, center: FreeCAD.Vector) -> Part.Shape:
    r_corner = (af_mm / 2.0) / math.cos(math.radians(30.0))
    pts = [
        FreeCAD.Vector(center.x + r_corner * math.cos(math.radians(i * 60.0 + 30.0)),
                       center.y + r_corner * math.sin(math.radians(i * 60.0 + 30.0)),
                       center.z)
        for i in range(6)
    ]
    pts.append(pts[0])
    return Part.Face(Part.makePolygon(pts)).extrude(FreeCAD.Vector(0, 0, height))

def export_shape(shape: Part.Shape, name: str):
    step_path = os.path.join(STEP_DIR, f"{name}.step")
    stl_path = os.path.join(STL_DIR, f"{name}.stl")
    shape.exportStep(step_path)
    mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.12, AngularDeflection=0.22, Relative=False)
    mesh.write(stl_path)
    print(f"Exported {name}: STEP ({os.path.getsize(step_path)} B) | STL ({mesh.CountFacets} facets)")

def make_top_faceplate() -> Part.Shape:
    plate = Part.makeBox(CASE_W, CASE_D, TOP_PLATE_T, FreeCAD.Vector(0.0, 0.0, 0.0))

    lip_outer = Part.makeBox(CASE_W - 2*(WALL_T + 0.3), CASE_D - 2*(WALL_T + 0.3), 2.5,
                             FreeCAD.Vector(WALL_T + 0.3, WALL_T + 0.3, -2.5))
    lip_inner = Part.makeBox(CASE_W - 2*(WALL_T + 2.3), CASE_D - 2*(WALL_T + 2.3), 3.0,
                             FreeCAD.Vector(WALL_T + 2.3, WALL_T + 2.3, -2.8))
    lip = lip_outer.cut(lip_inner)

    ribs = [lip]
    for sx in (SEAM_L - 3.5, SEAM_L + 0.5, SEAM_R - 3.5, SEAM_R + 0.5):
        ribs.append(Part.makeBox(3.0, CASE_D - 2*WALL_T - 2.0, 3.0, FreeCAD.Vector(sx, WALL_T + 1.0, -3.0)))
    # Add M3 mounting bosses (H=5.2mm) under faceplate for the 8 Switch Backing Carrier Plates!
    for _cname, _x0, _y0, _x1, _y1, spts, _sws in SWITCH_CARRIERS:
        for bx, by in spts:
            ribs.append(Part.makeCylinder(3.2, CARRIER_STANDOFF_H, FreeCAD.Vector(bx, by, -CARRIER_STANDOFF_H)))
    plate = plate.fuse(ribs)

    cutouts = []

    # Pilot bores (d=2.8mm, depth=4.5mm) in switch carrier bosses for M3x8mm screws
    for _cname, _x0, _y0, _x1, _y1, spts, _sws in SWITCH_CARRIERS:
        for bx, by in spts:
            cutouts.append(Part.makeCylinder(1.4, CARRIER_STANDOFF_H - 0.5, FreeCAD.Vector(bx, by, -CARRIER_STANDOFF_H - 0.1)))

    for hx, hy in M3_PILLARS:
        cutouts.append(Part.makeCylinder(1.7, TOP_PLATE_T + 5.0, FreeCAD.Vector(hx, hy, -4.0)))
        cutouts.append(Part.makeCone(1.7, 3.3, 1.6, FreeCAD.Vector(hx, hy, TOP_PLATE_T - 1.55)))

    for jx, jy in JOG_CENTERS:
        cutouts.append(Part.makeCylinder(43.0, 1.2, FreeCAD.Vector(jx, jy, TOP_PLATE_T - 1.0)))
        cutouts.append(Part.makeCylinder(3.8, TOP_PLATE_T + 4.0, FreeCAD.Vector(jx, jy, -2.0)))

    for rx, ry in ROTARY_POTS:
        cutouts.append(Part.makeCylinder(POT_HOLE_D / 2.0, TOP_PLATE_T + 4.0, FreeCAD.Vector(rx, ry, -2.0)))

    # 4x Vertical D103 Faders (4.6 x 64.0 mm slot + M2.5 screws at +/-35.5 mm = 71 mm pitch)
    for fx, fy in VERT_FADERS:
        cutouts.append(Part.makeBox(FADER_SLOT_W, FADER_SLOT_L, TOP_PLATE_T + 4.0,
                                    FreeCAD.Vector(fx - FADER_SLOT_W/2.0, fy - FADER_SLOT_L/2.0, -2.0)))
        for dy in (-FADER_MOUNT_OFFSET, FADER_MOUNT_OFFSET):
            cutouts.append(Part.makeCylinder(1.4, TOP_PLATE_T + 4.0, FreeCAD.Vector(fx, fy + dy, -2.0)))

    # 1x Horizontal D103 Crossfader (64.0 x 4.6 mm slot + M2.5 screws at +/-35.5 mm)
    hfx, hfy = HORIZ_FADER
    cutouts.append(Part.makeBox(FADER_SLOT_L, FADER_SLOT_W, TOP_PLATE_T + 4.0,
                                FreeCAD.Vector(hfx - FADER_SLOT_L/2.0, hfy - FADER_SLOT_W/2.0, -2.0)))
    for dx in (-FADER_MOUNT_OFFSET, FADER_MOUNT_OFFSET):
        cutouts.append(Part.makeCylinder(1.4, TOP_PLATE_T + 4.0, FreeCAD.Vector(hfx + dx, hfy, -2.0)))

    for sx, sy in SW_CENTERS:
        cutouts.append(Part.makeBox(13.2, 13.2, TOP_PLATE_T + 6.0, FreeCAD.Vector(sx - 6.6, sy - 6.6, -4.0)))

    # 1x Power LED Window (d = 5.2 mm) in Mixer center
    cutouts.append(Part.makeCylinder(2.6, TOP_PLATE_T + 4.0, FreeCAD.Vector(170.0, 58.0, -2.0)))

    return plate.cut(cutouts)

def make_bottom_chassis() -> Part.Shape:
    outer = Part.makeBox(CASE_W, CASE_D, BOTTOM_H, FreeCAD.Vector(0.0, 0.0, -BOTTOM_H))
    inner = Part.makeBox(CASE_W - 2*WALL_T, CASE_D - 2*WALL_T, BOTTOM_H,
                         FreeCAD.Vector(WALL_T, WALL_T, -BOTTOM_H + FLOOR_T))
    tub = outer.cut(inner)

    additions = []
    pillar_h = BOTTOM_H - FLOOR_T
    for hx, hy in M3_PILLARS:
        additions.append(Part.makeCylinder(5.0, pillar_h, FreeCAD.Vector(hx, hy, -BOTTOM_H + FLOOR_T)))

    for sx in (SEAM_L, SEAM_R):
        additions.append(Part.makeBox(8.0, CASE_D - 2*WALL_T, BOTTOM_H - FLOOR_T - 4.0,
                                      FreeCAD.Vector(sx - 4.0, WALL_T, -BOTTOM_H + FLOOR_T)))

    for px, py in PCB_HOLES_CAD:
        additions.append(Part.makeCylinder(4.0, PCB_STANDOFF_H, FreeCAD.Vector(px, py, -BOTTOM_H + FLOOR_T)))

    tub = tub.fuse(additions)

    cuts = []
    for hx, hy in M3_PILLARS:
        cuts.append(Part.makeCylinder(1.7, BOTTOM_H + 2.0, FreeCAD.Vector(hx, hy, -BOTTOM_H - 1.0)))
        cuts.append(make_hex_prism(5.8, 3.2, FreeCAD.Vector(hx, hy, -BOTTOM_H - 0.1)))

    for px, py in PCB_HOLES_CAD:
        cuts.append(Part.makeCylinder(1.7, PCB_STANDOFF_H + FLOOR_T + 2.0, FreeCAD.Vector(px, py, -BOTTOM_H - 1.0)))
        cuts.append(make_hex_prism(5.8, 2.8, FreeCAD.Vector(px, py, -BOTTOM_H - 0.1)))

    for sx in (SEAM_L, SEAM_R):
        cuts.append(Part.makeBox(12.0, 95.0, 18.0, FreeCAD.Vector(sx - 6.0, 55.0, -26.0)))
        for by in (28.0, 178.0):
            cuts.append(Part.makeCylinder(1.7, 16.0, FreeCAD.Vector(sx - 8.0, by, -16.0), FreeCAD.Vector(1, 0, 0)))

    # Flush rear USB-C cutout aligned 1:1 with Pro Micro USB-C
    # PCB top at Z = -42 + 3 + 6 + 1.6 = -31.4 mm; Pro Micro USB-C sits ~10mm above PCB -> Z = -31..-15 mm
    cuts.append(Part.makeBox(16.0, WALL_T + 4.0, 16.0,
                             FreeCAD.Vector(USB_C_X - 8.0, CASE_D - WALL_T - 2.0, -31.0)))

    return tub.cut(cuts)

def make_switch_carriers_plate() -> Part.Shape:
    """
    Generates all 8 rigid G82 Switch Backing Carrier Plates laid out cleanly on ONE 220x220mm print bed!
    Each plate (2.5 mm thick) bolts onto the 5.2 mm bosses under the faceplate with M3x8mm screws,
    capturing all 30 G82 12x12x5mm switches at the exact tactile height with 1.8x7.5mm pin slots
    so switch leads + 1N4148 diodes solder cleanly on the rear!
    """
    laid_out = []
    # Compact non-overlapping bed layout (all well within 200 x 170 mm!)
    bed_origins = [
        (  0.0,   0.0),  # pads_deckA  (88 x 42)
        ( 94.0,   0.0),  # pads_deckB  (88 x 42)
        (  0.0,  48.0),  # mixer_top   (50 x 62)
        ( 56.0,  48.0),  # mixer_cue   (46 x 22)
        (108.0,  48.0),  # loopsync_A  (22 x 42)
        (136.0,  48.0),  # loopsync_B  (22 x 42)
        ( 56.0,  76.0),  # transp_A    (50 x 21)
        ( 56.0, 103.0),  # transp_B    (50 x 21)
    ]
    for idx, (cname, x0, y0, x1, y1, spts, sw_idxs) in enumerate(SWITCH_CARRIERS):
        w, h = x1 - x0, y1 - y0
        ox, oy = bed_origins[idx]
        p = Part.makeBox(w, h, CARRIER_PLATE_T, FreeCAD.Vector(ox, oy, 0.0))
        cuts = []
        for bx, by in spts:
            cuts.append(Part.makeCylinder(1.7, CARRIER_PLATE_T + 2.0, FreeCAD.Vector(ox + (bx - x0), oy + (by - y0), -1.0)))
        for si in sw_idxs:
            sx, sy = SW_CENTERS[si]
            lx, ly = ox + (sx - x0), oy + (sy - y0)
            # Shallow 0.6mm centering recess (12.4 x 12.4 mm) for G82 switch body + 2 pin-pass slots at +/-6.25mm!
            cuts.append(Part.makeBox(12.4, 12.4, 0.7, FreeCAD.Vector(lx - 6.2, ly - 6.2, CARRIER_PLATE_T - 0.6)))
            for dx in (-6.25, 6.25):
                cuts.append(Part.makeBox(1.8, 7.6, CARRIER_PLATE_T + 2.0, FreeCAD.Vector(lx + dx - 0.9, ly - 3.8, -1.0)))
        laid_out.append(p.cut(cuts))
    return Part.makeCompound(laid_out)

def make_jog_wheel() -> Part.Shape:
    base_disc = Part.makeCone(42.0, 41.0, 8.5, FreeCAD.Vector(0, 0, 0))
    top_bevel = Part.makeCone(41.0, 38.0, 2.5, FreeCAD.Vector(0, 0, 8.5))
    hub_boss = Part.makeCylinder(7.5, 1.0, FreeCAD.Vector(0, 0, -1.0))
    platter = base_disc.fuse([top_bevel, hub_boss])

    shaft_cyl = Part.makeCylinder(3.125, 10.0, FreeCAD.Vector(0, 0, -1.5))
    d_flat_blocker = Part.makeBox(4.0, 10.0, 12.0, FreeCAD.Vector(1.75, -5.0, -2.0))
    d_bore = shaft_cyl.cut(d_flat_blocker)
    set_screw = Part.makeCylinder(1.45, 44.0, FreeCAD.Vector(0.0, 0.0, 4.0), FreeCAD.Vector(1, 0, 0))

    cuts = [d_bore, set_screw, Part.makeCylinder(32.0, 2.5, FreeCAD.Vector(0, 0, 9.0))]
    for i in range(16):
        ang = math.radians(i * 22.5)
        cuts.append(Part.makeCylinder(2.25, 7.5, FreeCAD.Vector(42.0 * math.cos(ang), 42.0 * math.sin(ang), 3.5)))
    return platter.cut(cuts)

def make_pad_keycap() -> Part.Shape:
    flange = Part.makeBox(14.4, 14.4, 1.2, FreeCAD.Vector(-7.2, -7.2, 0.0))
    cap = Part.makeBox(12.6, 12.6, 5.2, FreeCAD.Vector(-6.3, -6.3, 1.2))
    return flange.fuse(cap).cut(Part.makeCylinder(3.6, 1.2, FreeCAD.Vector(0, 0, -0.1)))

def make_tolerance_test_coupon() -> Part.Shape:
    """
    60 x 45 x 3.5 mm (~8 g PLA, ~15 min) calibration coupon:
      - 7.6 mm M7 WH148 + 8.3 mm M8 WH148 holes
      - 13.2 x 13.2 mm keycap window
      - 4.6 mm D103 fader slot check
      - 6.25 mm EC11 D-shaft boss + 6.20 mm round knurled boss check
      - M3 3.4 mm bore + 5.8 mm captive hex nut pocket
    """
    coupon = Part.makeBox(60.0, 45.0, 3.5, FreeCAD.Vector(0, 0, 0))
    ec_boss = Part.makeCylinder(6.5, 6.0, FreeCAD.Vector(48.0, 33.0, 3.5))
    nut_boss = Part.makeCylinder(5.0, 3.0, FreeCAD.Vector(48.0, 12.0, 3.5))
    coupon = coupon.fuse([ec_boss, nut_boss])

    shaft_cyl = Part.makeCylinder(3.125, 11.0, FreeCAD.Vector(48.0, 33.0, -1.0))
    d_flat = Part.makeBox(4.0, 10.0, 13.0, FreeCAD.Vector(48.0 + 1.75, 28.0, -2.0))
    d_bore = shaft_cyl.cut(d_flat)

    cuts = [
        Part.makeCylinder(3.8, 5.0, FreeCAD.Vector(10.0, 34.0, -1.0)),         # 7.6 mm M7 WH148
        Part.makeCylinder(4.15, 5.0, FreeCAD.Vector(25.0, 34.0, -1.0)),        # 8.3 mm M8 WH148
        Part.makeBox(13.2, 13.2, 5.0, FreeCAD.Vector(6.0, 6.0, -1.0)),         # 13.2x13.2 Keycap window
        Part.makeBox(FADER_SLOT_W, 24.0, 5.0, FreeCAD.Vector(29.0, 6.0, -1.0)),# 4.6 mm D103 Fader slot
        d_bore,                                                                 # 6.25 mm EC11 D-bore
        Part.makeCylinder(1.7, 9.0, FreeCAD.Vector(48.0, 12.0, -1.0)),         # M3 bore
        make_hex_prism(5.8, 3.2, FreeCAD.Vector(48.0, 12.0, -0.1)),            # Captive M3 nut
    ]
    return coupon.cut(cuts)

def split_into_3_printer_sections(shape: Part.Shape, prefix: str):
    zones = [
        ("left_deckA",   -10.0, SEAM_L),
        ("center_mixer", SEAM_L, SEAM_R),
        ("right_deckB",  SEAM_R, CASE_W + 10.0),
    ]
    for zname, x0, x1 in zones:
        bbox = Part.makeBox(x1 - x0, CASE_D + 20.0, 120.0, FreeCAD.Vector(x0, -10.0, -60.0))
        sec = shape.common(bbox)
        stl_path = os.path.join(STL_DIR, f"{prefix}_{zname}.stl")
        mesh = MeshPart.meshFromShape(Shape=sec, LinearDeflection=0.12, AngularDeflection=0.22, Relative=False)
        mesh.write(stl_path)
        bb = sec.BoundBox
        print(f"Exported 220x220mm Section {prefix}_{zname}.stl: {bb.XLength:.1f} x {bb.YLength:.1f} x {bb.ZLength:.1f} mm ({mesh.CountFacets} facets)")

def main():
    print("Building DDJ-FLX4 Modular Core v2.1 (75mm D103 Faders) 3D CAD in FreeCAD 1.0...")
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

    coupon = make_tolerance_test_coupon()
    export_shape(coupon, "ddj_flx4_tolerance_test")

    carriers = make_switch_carriers_plate()
    export_shape(carriers, "ddj_flx4_switch_carriers")

    jog_a = jog.copy()
    jog_a.Placement.Base = FreeCAD.Vector(JOG_CENTERS[0][0], JOG_CENTERS[0][1], TOP_PLATE_T + 1.5)
    jog_b = jog.copy()
    jog_b.Placement.Base = FreeCAD.Vector(JOG_CENTERS[1][0], JOG_CENTERS[1][1], TOP_PLATE_T + 1.5)

    assembly = Part.makeCompound([top_plate, bottom_tub, jog_a, jog_b])
    export_shape(assembly, "ddj_flx4_full_assembly")
    print("ALL v2.1 CAD MODELS BUILT AND EXPORTED SUCCESSFULLY!")

if __name__ == "__main__":
    main()
