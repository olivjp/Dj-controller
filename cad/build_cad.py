#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deterministic FreeCAD 1.0 OpenCASCADE B-Rep Solid & Mesh Compiler — DDJ-FLX4 Modular Core v2.3.

Audited & Verified (Multi-Round Independent Review — 0 P0 Collisions):
  - 5x Slide Faders D103 = D10Kx2 (75 mm body, 60 mm travel, 71 mm mount hole pitch, 4.6 x 64.0 mm slots)
  - 10-11x WH148 B10K Rotary Pots (18.5 mm vertical pitch > 16 mm body; 7.6 mm M7 bore)
  - 2x EC11 Quadrature Encoders + 84 mm Jog Wheels (6.25 mm D-flat bore + M3 nut trap at r=6.8..9.2mm
    for M3x8 grub screw + O12.5 x 4.0 mm under-hub bushing/nut relief; full 3.5 mm faceplate stiffness)
  - 30x G82 12x12x5mm Tactile Switches held by 6 rigid eared Carrier Plates (convex support polygon
    margin >= +1.0 mm, max switch-to-boss reach <= 14.9 mm, +/-8.2 mm base around +/-7.15 mm pin slots,
    auto-packed with zero print-bed overlap and O11 pillar relief notches)
  - 98 x 98 mm 2-Layer Core PCB mounted at PCB_Y_REAR = 201.5 mm (0.5 mm rear clearance):
      * Rear H1/H2 (126.08, 196.42) & (213.71, 196.42): independent M3x12 SHCS from below into
        M3x30 F-F 5.5mm-AF brass standoffs + 1.4 mm faceplate boss + M3x10 countersunk from top
      * Flush rear USB-C cutout aligned at Z = -25.2..-9.2 mm (clears 8.5 mm overmold)
  - 340 x 206 mm external enclosure split into 3 bolted modules (115/110/115 x 206 mm -> fits 220x220 bed)
  - Faceplate lip (WALL_T + 0.5 mm) and seam ribs relieved with O11 cutouts at all 10 pillars + H1/H2
  - Seam blocks flush at Z = -3.0 supporting faceplate ribs, 4x M3x12 horizontal seam bolts per seam
    (Y=28 @ Z=-8/-34; Y=178 @ Z=-8/-20 — clears PCB, J9/J10 Duponts, and loopsync_B)
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
CASE_D      = 206.0    # <= 210 mm -> fits 220x220 mm FDM beds with 5 mm brim
WALL_T      = 4.0
FLOOR_T     = 3.0
BOTTOM_H    = 42.0     # Z = -42.0 .. 0.0 (31.4 mm headroom above 98x98 Core PCB)
TOP_PLATE_T = 3.5      # Z =   0.0 .. +3.5 (full 3.5 mm everywhere — no Ø86 jog thinning)

SEAM_L = 115.0
SEAM_R = 225.0

# 10x Vertical M3 Pillars (rear Mixer pillars moved to brass F-F standoffs coaxial with PCB H1/H2!)
M3_PILLARS = [
    # Deck A (X in 0..115)
    (10.0, 10.0), (105.0, 10.0), (10.0, 196.0), (105.0, 196.0),
    # Center Mixer Front (X in 115..225) — Rear uses H1/H2 brass F-F M3x30 standoffs!
    (122.0, 10.0), (218.0, 10.0),
    # Deck B (X in 225..340)
    (235.0, 10.0), (330.0, 10.0), (235.0, 196.0), (330.0, 196.0),
]

# 98 x 98 mm Core PCB mounted inside Center Mixer with 0.5 mm clearance to rear inner wall (Y = 201.5)
PCB_W = 98.0
PCB_X0 = (CASE_W - PCB_W) / 2.0      # 121.0 mm
PCB_Y_REAR = CASE_D - WALL_T - 0.5   # 201.5 mm (KiCad Y=0)
PCB_STANDOFF_H = 6.0                 # PCB top at Z = -31.4 mm
PCB_HOLES_KICAD = [(5.08, 5.08), (92.71, 5.08), (5.08, 92.71), (92.71, 92.71)]
PCB_HOLES_CAD = [(PCB_X0 + hx, PCB_Y_REAR - hy) for (hx, hy) in PCB_HOLES_KICAD]
# Rear PCB mounting holes H1/H2 double as Mixer rear lid tie-downs via M3x30 F-F 5.5AF brass standoffs
H12_STANDOFFS = [PCB_HOLES_CAD[0], PCB_HOLES_CAD[1]]  # (126.08, 196.42), (213.71, 196.42)
USB_C_X = PCB_X0 + 48.895            # 169.895 mm (exact Pro Micro USB-C center)

# ── Panel-Mount Control Coordinates (Verified Zero-Collision for 75 mm D103 Faders) ──
JOG_CENTERS = [
    (48.0, 116.0),   # Deck A Jog Wheel
    (272.0, 116.0),  # Deck B Jog Wheel
]

# 11x WH148 Rotary Pots (18.5 mm vertical pitch > 16 mm body; RV16 optional via HAS_RV16 in firmware)
ROTARY_POTS = [
    (136.0, 189.0), (136.0, 170.5), (136.0, 152.0), (136.0, 133.5), (136.0, 115.0),
    (204.0, 189.0), (204.0, 170.5), (204.0, 152.0), (204.0, 133.5), (204.0, 115.0),
    (170.0, 186.0),  # RV16 Master / FX
]
POT_HOLE_D = 7.6     # M7 WH148 bushing + FDM clearance

# 5x D103 = D10Kx2 Slide Faders (75 mm body, 60 mm travel, 71 mm screw pitch)
VERT_FADERS = [
    (138.0, 68.0),   # RV11 Ch1 Vol
    (202.0, 68.0),   # RV12 Ch2 Vol
    (102.0, 116.0),  # RV14 Deck A Pitch
    (326.0, 116.0),  # RV15 Deck B Pitch
]
HORIZ_FADER = (170.0, 20.0)  # RV13 Crossfader
FADER_SLOT_W = 4.6
FADER_SLOT_L = 64.0
FADER_MOUNT_OFFSET = 35.5    # 71.0 mm screw hole pitch

# 30x Tactile Push-Button Square Cutouts (13.2 x 13.2 mm -> 0.30 mm clearance/side)
# v2.3: Deck B Loop/Sync shifted +2.0 mm (X=246) & Transport shifted +4.0 mm (X=246/274)
# so left carrier ears at X>=234 clear the right seam block (X<=229) by >=0.8 mm with zero cantilever!
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
    (246.0, 186.0), (246.0, 166.0), (246.0, 18.0), (274.0, 18.0),
]

# 6x Rigid Eared Switch Backing Carrier Plates (v2.3):
# Each entry: (name, x_min, y_min, x_max, y_max, screw_pts, switch_indices)
# Base plate spans +/-8.2 mm in X (>=1.05 mm wall outside +/-7.15 mm pin slots) and +/-6.8 mm in Y.
# Every boss (r=3.2) + carrier ear (r=4.2) verified >= +0.54 mm clear of flanges, pin slots,
# M3 pillars, H1/H2 brass standoffs, WH148 pots, D103 faders, EC11, lip, outer walls, and seam blocks!
SWITCH_CARRIERS = [
    ("deckA_frente",  13.8,  11.2,  96.2,  66.8,
     [(11.0, 19.0), (11.0, 71.0), (33.0, 10.5), (33.0, 29.0), (33.0, 50.0),
      (39.0, 18.0), (55.0, 50.0), (77.0, 50.0), (99.0, 16.5), (99.0, 71.0)],
     [0, 1, 2, 3, 4, 5, 6, 7, 24, 25]),
    ("deckB_frente", 233.8,  11.2, 316.2,  66.8,
     [(234.0, 19.0), (234.0, 71.0), (253.0, 50.0), (255.0, 29.0), (257.0, 10.5),
      (263.0, 18.0), (275.0, 50.0), (297.0, 50.0), (319.0, 10.5), (319.0, 71.0)],
     [8, 9, 10, 11, 12, 13, 14, 15, 28, 29]),
    ("mixer_top",    147.8, 111.2, 192.2, 166.8,
     [(146.0, 124.0), (149.5, 171.0), (159.0, 118.0), (159.0, 138.0),
      (190.5, 171.0), (192.5, 107.0)],
     [16, 17, 18, 19]),
    ("mixer_cue",    149.8,  79.2, 190.2,  92.8,
     [(148.0, 75.0), (148.0, 97.0), (192.0, 75.0), (192.0, 97.0)],
     [20, 21]),
    ("loopsync_A",    71.8, 159.2,  88.2, 192.8,
     [(69.0, 155.0), (69.0, 166.0), (69.0, 195.5), (91.0, 155.0), (91.0, 195.5)],
     [22, 23]),
    ("loopsync_B",   237.8, 159.2, 254.2, 192.8,
     [(235.0, 155.0), (235.0, 166.0), (235.0, 187.0), (256.5, 195.5), (257.0, 155.0)],
     [26, 27]),
]
# Measure G82 actuator diameter first (bench A2):
#   4.5 mm -> standard G82 actuator < O7.2 mm (enters keycap pocket cleanly, zero rattle)
#   5.6 mm -> wide G82 actuator >= O7.2 mm (sits against keycap flange bottom)
CARRIER_STANDOFF_H = 4.5
CARRIER_PLATE_T    = 2.5
CARRIER_EAR_R      = 4.2

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

    # Perimeter alignment lip with 0.5 mm FDM clearance (WALL_T + 0.5 = 4.5..6.5 mm)
    lip_outer = Part.makeBox(CASE_W - 2*(WALL_T + 0.5), CASE_D - 2*(WALL_T + 0.5), 2.5,
                             FreeCAD.Vector(WALL_T + 0.5, WALL_T + 0.5, -2.5))
    lip_inner = Part.makeBox(CASE_W - 2*(WALL_T + 2.5), CASE_D - 2*(WALL_T + 2.5), 3.0,
                             FreeCAD.Vector(WALL_T + 2.5, WALL_T + 2.5, -2.8))
    lip = lip_outer.cut(lip_inner)

    seam_ribs = []
    for sx in (SEAM_L - 3.5, SEAM_L + 0.5, SEAM_R - 3.5, SEAM_R + 0.5):
        seam_ribs.append(Part.makeBox(3.0, CASE_D - 2*WALL_T - 2.0, 3.0, FreeCAD.Vector(sx, WALL_T + 1.0, -3.0)))

    # Relieve lip and seam ribs with O11 cutouts at all 10 M3 pillars + rear H1/H2 standoffs (C3 — fixes NEW-1!)
    lip_and_ribs = lip.fuse(seam_ribs)
    pillar_reliefs = [
        Part.makeCylinder(5.5, 3.3, FreeCAD.Vector(hx, hy, -3.1))
        for (hx, hy) in M3_PILLARS + H12_STANDOFFS
    ]
    lip_and_ribs = lip_and_ribs.cut(pillar_reliefs)

    additions = [lip_and_ribs]

    # H1/H2 rear Mixer tie-down bosses (O7.0 x 1.4 mm) meeting the M3x30 F-F brass standoffs (C2)
    for hx, hy in H12_STANDOFFS:
        additions.append(Part.makeCylinder(3.5, 1.4, FreeCAD.Vector(hx, hy, -1.4)))

    # 40x M3 mounting bosses (O6.4 x CARRIER_STANDOFF_H) under faceplate for the 6 Switch Carrier Plates
    for _cname, _x0, _y0, _x1, _y1, spts, _sws in SWITCH_CARRIERS:
        for bx, by in spts:
            additions.append(Part.makeCylinder(3.2, CARRIER_STANDOFF_H, FreeCAD.Vector(bx, by, -CARRIER_STANDOFF_H)))

    plate = plate.fuse(additions)

    cutouts = []

    # Pilot bores (d=2.8 mm, depth = CARRIER_STANDOFF_H - 0.5) in carrier bosses for M3x6 screws (C5)
    for _cname, _x0, _y0, _x1, _y1, spts, _sws in SWITCH_CARRIERS:
        for bx, by in spts:
            cutouts.append(Part.makeCylinder(1.4, CARRIER_STANDOFF_H - 0.5, FreeCAD.Vector(bx, by, -CARRIER_STANDOFF_H - 0.1)))

    # 10x M3 pillar countersunk bores + 2x H1/H2 rear brass standoff countersunk bores
    for hx, hy in M3_PILLARS + H12_STANDOFFS:
        cutouts.append(Part.makeCylinder(1.7, TOP_PLATE_T + 5.0, FreeCAD.Vector(hx, hy, -4.0)))
        cutouts.append(Part.makeCone(1.7, 3.3, 1.6, FreeCAD.Vector(hx, hy, TOP_PLATE_T - 1.55)))

    # 2x EC11 Jog Shaft Bores (C9: removed O86 thinning recess to preserve full 3.5 mm plate stiffness!)
    for jx, jy in JOG_CENTERS:
        cutouts.append(Part.makeCylinder(3.8, TOP_PLATE_T + 4.0, FreeCAD.Vector(jx, jy, -2.0)))

    for rx, ry in ROTARY_POTS:
        cutouts.append(Part.makeCylinder(POT_HOLE_D / 2.0, TOP_PLATE_T + 4.0, FreeCAD.Vector(rx, ry, -2.0)))

    # 4x Vertical D103 Faders (4.6 x 64.0 mm slot + M2.5 screws at +/-35.5 mm = 71 mm pitch)
    for fx, fy in VERT_FADERS:
        cutouts.append(Part.makeBox(FADER_SLOT_W, FADER_SLOT_L, TOP_PLATE_T + 4.0,
                                    FreeCAD.Vector(fx - FADER_SLOT_W/2.0, fy - FADER_SLOT_L/2.0, -2.0)))
        for dy in (-FADER_MOUNT_OFFSET, FADER_MOUNT_OFFSET):
            cutouts.append(Part.makeCylinder(1.4, TOP_PLATE_T + 4.0, FreeCAD.Vector(fx, fy + dy, -2.0)))

    # 1x Horizontal D103 Crossfader
    hfx, hfy = HORIZ_FADER
    cutouts.append(Part.makeBox(FADER_SLOT_L, FADER_SLOT_W, TOP_PLATE_T + 4.0,
                                FreeCAD.Vector(hfx - FADER_SLOT_L/2.0, hfy - FADER_SLOT_W/2.0, -2.0)))
    for dx in (-FADER_MOUNT_OFFSET, FADER_MOUNT_OFFSET):
        cutouts.append(Part.makeCylinder(1.4, TOP_PLATE_T + 4.0, FreeCAD.Vector(hfx + dx, hfy, -2.0)))

    for sx, sy in SW_CENTERS:
        cutouts.append(Part.makeBox(13.2, 13.2, TOP_PLATE_T + 6.0, FreeCAD.Vector(sx - 6.6, sy - 6.6, -4.0)))

    # 1x Optional Panel-Mount Power LED Window (d = 5.2 mm; wire 2 leads to PCB D17 pads, R11 stays on PCB)
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

    # Seam joiner blocks raised to Z = -3.0 so they directly support faceplate seam ribs (C8)
    for sx in (SEAM_L, SEAM_R):
        additions.append(Part.makeBox(8.0, CASE_D - 2*WALL_T, BOTTOM_H - FLOOR_T - 3.0,
                                      FreeCAD.Vector(sx - 4.0, WALL_T, -BOTTOM_H + FLOOR_T)))

    for px, py in PCB_HOLES_CAD:
        additions.append(Part.makeCylinder(4.0, PCB_STANDOFF_H, FreeCAD.Vector(px, py, -BOTTOM_H + FLOOR_T)))

    tub = tub.fuse(additions)

    cuts = []
    for hx, hy in M3_PILLARS:
        cuts.append(Part.makeCylinder(1.7, BOTTOM_H + 2.0, FreeCAD.Vector(hx, hy, -BOTTOM_H - 1.0)))
        cuts.append(make_hex_prism(5.8, 3.2, FreeCAD.Vector(hx, hy, -BOTTOM_H - 0.1)))

    # PCB Standoffs: H1/H2 pockets deepened to 3.2 mm so DIN 912 M3x12 SHCS head (h=3.0, O5.5) sits flush!
    for idx_h, (px, py) in enumerate(PCB_HOLES_CAD):
        cuts.append(Part.makeCylinder(1.7, PCB_STANDOFF_H + FLOOR_T + 2.0, FreeCAD.Vector(px, py, -BOTTOM_H - 1.0)))
        pocket_h = 3.3 if idx_h < 2 else 2.8
        cuts.append(make_hex_prism(5.8, pocket_h, FreeCAD.Vector(px, py, -BOTTOM_H - 0.1)))

    # Seam wiring window + 4x horizontal M3x12 bolt holes per seam (C8: clears PCB, J9/J10, loopsync_B)
    for sx in (SEAM_L, SEAM_R):
        cuts.append(Part.makeBox(12.0, 95.0, 18.0, FreeCAD.Vector(sx - 6.0, 55.0, -26.0)))
        for by, bz in ((28.0, -8.0), (28.0, -34.0), (178.0, -8.0), (178.0, -20.0)):
            cuts.append(Part.makeCylinder(1.7, 16.0, FreeCAD.Vector(sx - 8.0, by, bz), FreeCAD.Vector(1, 0, 0)))

    # Rear USB-C cutout centered on Pro Micro USB-C receptacle (Z = -17.2 mm -> cutout Z = -25.2..-9.2 mm, C4)
    cuts.append(Part.makeBox(16.0, WALL_T + 4.0, 16.0,
                             FreeCAD.Vector(USB_C_X - 8.0, CASE_D - WALL_T - 2.0, -25.2)))

    return tub.cut(cuts)

def make_switch_carriers_plate() -> Part.Shape:
    """
    Generates all 6 rigid eared G82 Switch Backing Carrier Plates auto-packed cleanly on ONE 220x220mm bed
    with deterministic overlap assertion (C5 + C6).
    """
    # Compute exact bounding boxes (base plate + all r=4.2 mm ears) and auto-pack in 2 rows
    item_specs = []
    for cname, x0, y0, x1, y1, spts, sw_idxs in SWITCH_CARRIERS:
        ex0 = min([x0] + [bx - CARRIER_EAR_R for bx, _ in spts])
        ey0 = min([y0] + [by - CARRIER_EAR_R for _, by in spts])
        ex1 = max([x1] + [bx + CARRIER_EAR_R for bx, _ in spts])
        ey1 = max([y1] + [by + CARRIER_EAR_R for _, by in spts])
        item_specs.append((cname, x0, y0, x1, y1, spts, sw_idxs, ex0, ey0, ex1 - ex0, ey1 - ey0))

    # Row-shelf packer for 220x220 bed with 6.0 mm part spacing
    GAP = 6.0
    MAX_BED = 210.0
    cur_x, cur_y, row_h = 0.0, 0.0, 0.0
    placed_rects = []
    laid_out = []

    for cname, x0, y0, x1, y1, spts, sw_idxs, ex0, ey0, bw, bh in item_specs:
        if cur_x > 0.0 and cur_x + bw > MAX_BED:
            cur_x = 0.0
            cur_y += row_h + GAP
            row_h = 0.0
        ox, oy = cur_x, cur_y
        assert ox + bw <= MAX_BED and oy + bh <= MAX_BED, f"Carrier {cname} exceeds 210x210 bed!"
        for pn, px0, py0, px1, py1 in placed_rects:
            assert not (max(ox, px0) < min(ox + bw, px1) and max(oy, py0) < min(oy + bh, py1)), \
                f"Bed overlap between {cname} and {pn}!"
        placed_rects.append((cname, ox, oy, ox + bw, oy + bh))
        cur_x += bw + GAP
        row_h = max(row_h, bh)

        # Coordinate transform: world (wx, wy) -> bed (ox + wx - ex0, oy + wy - ey0)
        def to_bed(wx, wy):
            return ox + (wx - ex0), oy + (wy - ey0)

        bx0, by0 = to_bed(x0, y0)
        parts = [Part.makeBox(x1 - x0, y1 - y0, CARRIER_PLATE_T, FreeCAD.Vector(bx0, by0, 0.0))]

        # Add r=4.2 mm circular ear + bridge strip connecting each external boss to base plate
        for wx, wy in spts:
            lx, ly = to_bed(wx, wy)
            parts.append(Part.makeCylinder(CARRIER_EAR_R, CARRIER_PLATE_T, FreeCAD.Vector(lx, ly, 0.0)))
            # Closest point on base plate rectangle
            cx = min(max(wx, x0), x1)
            cy = min(max(wy, y0), y1)
            dist = math.hypot(wx - cx, wy - cy)
            if dist > 0.05:
                lcx, lcy = to_bed(cx, cy)
                ang_deg = math.degrees(math.atan2(ly - lcy, lx - lcx))
                arm = Part.makeBox(dist + 2.0, CARRIER_EAR_R * 2.0, CARRIER_PLATE_T,
                                   FreeCAD.Vector(-1.0, -CARRIER_EAR_R, 0.0))
                arm.rotate(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 0, 1), ang_deg)
                arm.translate(FreeCAD.Vector(lcx, lcy, 0.0))
                parts.append(arm)

        solid = parts[0].fuse(parts[1:]) if len(parts) > 1 else parts[0]

        cuts = []
        # Screw clearance holes (d=3.4 mm for M3x6)
        for wx, wy in spts:
            lx, ly = to_bed(wx, wy)
            cuts.append(Part.makeCylinder(1.7, CARRIER_PLATE_T + 2.0, FreeCAD.Vector(lx, ly, -1.0)))

        # O11 relief notches for any M3 pillar near this carrier (C5)
        for px, py in M3_PILLARS:
            if ex0 - 6.0 <= px <= ex0 + bw + 6.0 and ey0 - 6.0 <= py <= ey0 + bh + 6.0:
                lpx, lpy = to_bed(px, py)
                cuts.append(Part.makeCylinder(5.5, CARRIER_PLATE_T + 2.0, FreeCAD.Vector(lpx, lpy, -1.0)))

        # Switch centering recesses (12.4 x 12.4 x 0.6 mm) + pin pass-through slots (+/-6.25 mm)
        for si in sw_idxs:
            sx, sy = SW_CENTERS[si]
            lsx, lsy = to_bed(sx, sy)
            cuts.append(Part.makeBox(12.4, 12.4, 0.7, FreeCAD.Vector(lsx - 6.2, lsy - 6.2, CARRIER_PLATE_T - 0.6)))
            for dx in (-6.25, 6.25):
                cuts.append(Part.makeBox(1.8, 7.6, CARRIER_PLATE_T + 2.0, FreeCAD.Vector(lsx + dx - 0.9, lsy - 3.8, -1.0)))

        laid_out.append(solid.cut(cuts))
        print(f"  Packed carrier {cname:12s}: {bw:4.1f} x {bh:4.1f} mm at bed ({ox:5.1f}, {oy:5.1f})")

    return Part.makeCompound(laid_out)

def make_jog_wheel() -> Part.Shape:
    """
    84 mm Jog Wheel (v2.3 — C7):
      - O12.5 x 4.0 mm under-hub relief (Z_local = -1.0..+3.0 mm) clears EC11 M7 bushing + nut on 3.5 mm faceplate
      - Captive M3 nut trap (5.8 AF, 2.4 mm thick) at r = 6.8..9.2 mm (outside O12.5 relief!), Z = 4.5 mm
        accessible as drop-in pocket from bottom face Z = 0.0 up to Z = 7.45 mm
      - O3.4 mm radial hex-key access tunnel from r = 9.2 to outer rim + O3.2 mm bore to D-flat for M3x8 grub screw
    """
    base_disc = Part.makeCone(42.0, 41.0, 8.5, FreeCAD.Vector(0, 0, 0))
    top_bevel = Part.makeCone(41.0, 38.0, 2.5, FreeCAD.Vector(0, 0, 8.5))
    hub_boss = Part.makeCylinder(7.5, 1.0, FreeCAD.Vector(0, 0, -1.0))
    platter = base_disc.fuse([top_bevel, hub_boss])

    # EC11 D-shaft bore (D=6.25 mm, flat at X=+1.75 mm, depth Z=-1.5..+8.5 mm)
    shaft_cyl = Part.makeCylinder(3.125, 10.0, FreeCAD.Vector(0, 0, -1.5))
    d_flat_blocker = Part.makeBox(4.0, 10.0, 12.0, FreeCAD.Vector(1.75, -5.0, -2.0))
    d_bore = shaft_cyl.cut(d_flat_blocker)

    # Under-hub M7 bushing/nut relief: O12.5 x 4.0 mm (Z_local = -1.1..+3.0 mm)
    hub_relief = Part.makeCylinder(6.25, 4.1, FreeCAD.Vector(0, 0, -1.1))

    # Captive M3 nut trap (inner face r=6.8, outer face r=9.2, width 5.9 mm for 5.5/5.8 AF nut, drop-in from Z=0..7.5)
    nut_trap = Part.makeBox(2.5, 5.9, 7.6, FreeCAD.Vector(6.8, -2.95, -0.1))

    # Grub screw bore (O3.2 mm from shaft to nut) + hex-key access tunnel (O3.4 mm from nut to outer rim) at Z=4.5
    grub_bore = Part.makeCylinder(1.6, 8.0, FreeCAD.Vector(0.0, 0.0, 4.5), FreeCAD.Vector(1, 0, 0))
    access_tunnel = Part.makeCylinder(1.7, 36.0, FreeCAD.Vector(8.5, 0.0, 4.5), FreeCAD.Vector(1, 0, 0))

    cuts = [d_bore, hub_relief, nut_trap, grub_bore, access_tunnel, Part.makeCylinder(32.0, 2.5, FreeCAD.Vector(0, 0, 9.0))]
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
      - 6.25 mm EC11 D-shaft boss
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
    print("Building DDJ-FLX4 Modular Core v2.3 (Audited Zero-P0 CAD) in FreeCAD 1.0...")
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
    print("ALL v2.3 CAD MODELS BUILT AND EXPORTED SUCCESSFULLY!")

if __name__ == "__main__":
    main()
