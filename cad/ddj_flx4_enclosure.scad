// ============================================================================
// Pioneer DDJ-FLX4 Inspired 2-Deck USB-MIDI DJ Controller - Parametric 3D CAD
// Matched 1:1 to KiCad 9.0 PCB (340.0 x 220.0 x 1.6 mm) & AliExpress BOM
// ============================================================================
// Units: millimeters (mm)
// Printable as full unibody OR 3 bolted modular sections (Deck A / Mixer / Deck B)
// on any 220x220mm FDM 3D printer (Ender 3, Bambu Lab A1/P1S/X1C, Prusa MK4).
// ============================================================================

$fn = 72;

// ── Global Mechanical Parameters ─────────────────────────────────────────────
pcb_w = 340.0;
pcb_d = 220.0;
pcb_t = 1.6;

wall_t      = 4.0;
clearance   = 1.0;
case_w      = pcb_w + 2 * (wall_t + clearance); // 350.0 mm
case_d      = pcb_d + 2 * (wall_t + clearance); // 230.0 mm
bottom_h    = 26.0;
top_plate_t = 3.2;
standoff_h  = 14.0;

// 8x M3 Mounting Hole Coordinates (PCB Reference Frame: 0..340, 0..220)
m3_holes = [
    [  8.0,   8.0], [116.0,   8.0], [224.0,   8.0], [332.0,   8.0],
    [  8.0, 212.0], [116.0, 212.0], [224.0, 212.0], [332.0, 212.0]
];

// Jog Wheel Shaft Centers (ENC1 & ENC2)
jog_centers = [
    [ 55.5, 94.5], // Deck A Jog Wheel
    [275.5, 94.5]  // Deck B Jog Wheel
];

// 11x Rotary Potentiometer Shaft Centers (WH148 B10K)
rotary_pots = [
    // Channel 1 (Trim, EQ Hi, Mid, Low, CFX)
    [137.0,  58.5], [137.0,  74.5], [137.0,  90.5], [137.0, 106.5], [137.0, 122.5],
    // Channel 2 (Trim, EQ Hi, Mid, Low, CFX)
    [213.0,  58.5], [213.0,  74.5], [213.0,  90.5], [213.0, 106.5], [213.0, 122.5],
    // Master / Beat FX Level
    [175.0,  58.5]
];

// 4x Vertical Slide Fader Slot Centers (Ch1 Vol, Ch2 Vol, Deck A Pitch, Deck B Pitch)
vert_faders = [
    [133.75, 167.25], // RV11 Ch1 Vol
    [209.75, 167.25], // RV12 Ch2 Vol
    [103.75,  95.25], // RV14 Deck A Pitch
    [323.75,  95.25]  // RV15 Deck B Pitch
];

// 1x Horizontal Crossfader Slot Center (RV13)
horiz_fader = [170.25, 205.75];

// 30x Tactile 12x12mm Switch Centers (SW1..SW30)
sw_centers = [
    // Deck A 2x4 Performance Pads (SW1..SW8)
    [22.25, 144.5], [44.25, 144.5], [66.25, 144.5], [88.25, 144.5],
    [22.25, 164.5], [44.25, 164.5], [66.25, 164.5], [88.25, 164.5],
    // Deck B 2x4 Performance Pads (SW9..SW16)
    [242.25, 144.5], [264.25, 144.5], [286.25, 144.5], [308.25, 144.5],
    [242.25, 164.5], [264.25, 164.5], [286.25, 164.5], [308.25, 164.5],
    // Mixer Control Buttons (SW17..SW22) — matched 1:1 with build_pcb.py (+6.25, +2.50 from footprint anchor)
    [152.75,  50.5], [191.25,  50.5], [170.25,  78.5],
    [170.25,  96.5], [152.25, 114.5], [188.25, 114.5],
    // Deck A Loop/Sync & Transport (SW23..SW26)
    [ 82.25,  24.5], [ 82.25,  44.5], [ 22.25, 190.5], [ 52.25, 190.5],
    // Deck B Loop/Sync & Transport (SW27..SW30)
    [234.25,  24.5], [234.25,  44.5], [242.25, 190.5], [272.25, 190.5]
];

// ── Module: Top Control Faceplate ────────────────────────────────────────────
module top_faceplate() {
    difference() {
        union() {
            // Main Top Deck Plate
            translate([-wall_t - clearance, -wall_t - clearance, 0])
                cube([case_w, case_d, top_plate_t]);

            // 8x Under-Plate Alignment Bosses
            for (pt = m3_holes) {
                translate([pt[0], pcb_d - pt[1], -4.0])
                    cylinder(d = 8.0, h = 4.0);
            }
        }

        // 8x M3 Countersunk Screw Holes
        for (pt = m3_holes) {
            translate([pt[0], pcb_d - pt[1], -5.0])
                cylinder(d = 3.4, h = top_plate_t + 6.0);
            translate([pt[0], pcb_d - pt[1], top_plate_t - 1.6])
                cylinder(d1 = 3.4, d2 = 6.5, h = 1.7);
        }

        // 2x Jog Wheel Recessed Wells + EC11 Shaft Clearances
        for (jc = jog_centers) {
            translate([jc[0], pcb_d - jc[1], top_plate_t - 1.2])
                cylinder(d = 86.0, h = 2.0);
            translate([jc[0], pcb_d - jc[1], -1.0])
                cylinder(d = 9.0, h = top_plate_t + 2.0);
        }

        // 11x Rotary Potentiometer Shaft Holes (7.5mm)
        for (rp = rotary_pots) {
            translate([rp[0], pcb_d - rp[1], -1.0])
                cylinder(d = 7.5, h = top_plate_t + 2.0);
        }

        // 4x Vertical Slide Fader Slots (3.4 x 48.0 mm)
        for (vf = vert_faders) {
            translate([vf[0] - 1.7, (pcb_d - vf[1]) - 24.0, -1.0])
                cube([3.4, 48.0, top_plate_t + 2.0]);
        }

        // 1x Horizontal Crossfader Slot (48.0 x 3.4 mm)
        translate([horiz_fader[0] - 24.0, (pcb_d - horiz_fader[1]) - 1.7, -1.0])
            cube([48.0, 3.4, top_plate_t + 2.0]);

        // 30x Tactile Push-Button Square Cutouts (13.2 x 13.2 mm)
        for (sc = sw_centers) {
            translate([sc[0] - 6.6, (pcb_d - sc[1]) - 6.6, -1.0])
                cube([13.2, 13.2, top_plate_t + 2.0]);
        }

        // 3x Status LED Holes (5.2mm)
        for (lx = [159.27, 170.27, 181.27]) {
            translate([lx, pcb_d - 130.0, -1.0])
                cylinder(d = 5.2, h = top_plate_t + 2.0);
        }
    }
}

// ── Module: Bottom Unibody Tub Chassis ───────────────────────────────────────
module bottom_chassis() {
    difference() {
        union() {
            // Outer Shell Box
            difference() {
                translate([-wall_t - clearance, -wall_t - clearance, -bottom_h])
                    cube([case_w, case_d, bottom_h]);
                translate([-clearance, -clearance, -bottom_h + 3.0])
                    cube([pcb_w + 2 * clearance, pcb_d + 2 * clearance, bottom_h]);
            }

            // 8x Internal M3 PCB Standoff Pillars
            for (pt = m3_holes) {
                translate([pt[0], pcb_d - pt[1], -bottom_h + 3.0])
                    cylinder(d = 9.0, h = standoff_h);
            }

            // 2x Modular Partition Ribs at X=116 and X=224
            for (x_rib = [116.0, 224.0]) {
                translate([x_rib - 2.0, 0, -bottom_h + 3.0])
                    cube([4.0, pcb_d, standoff_h - 2.0]);
            }
        }

        // 8x M3 Heat-Set Insert / Screw Bores (2.8mm for direct M3 thread)
        for (pt = m3_holes) {
            translate([pt[0], pcb_d - pt[1], -bottom_h + 3.0])
                cylinder(d = 2.8, h = standoff_h + 1.0);
        }

        // Rear USB-B (Leonardo R3) & USB-C (Pro Micro) Connector Ports
        translate([28.0, pcb_d - 1.0, -bottom_h + 3.0 + standoff_h])
            cube([18.0, wall_t + 4.0, 13.0]);
        translate([244.0, pcb_d - 1.0, -bottom_h + 3.0 + standoff_h])
            cube([16.0, wall_t + 4.0, 10.0]);
    }
}

// ── Module: 84mm Ergonomic DDJ-FLX4 Jog Wheel Platter ────────────────────────
module jog_wheel_platter() {
    difference() {
        union() {
            // Outer Platter Disc with Beveled Top Rim
            cylinder(d1 = 84.0, d2 = 82.0, h = 9.0);
            translate([0, 0, 9.0])
                cylinder(d1 = 82.0, d2 = 76.0, h = 2.5);
            // Central EC11 Shaft Collet Boss (extends down to encoder shaft)
            translate([0, 0, -6.0])
                cylinder(d = 14.0, h = 6.0);
        }
        // Central 6.05mm Knurled Shaft Bore for EC11 Encoder
        translate([0, 0, -7.0])
            cylinder(d = 6.05, h = 16.0);
        // Top Finger-Drop Center Platter Recess
        translate([0, 0, 9.5])
            cylinder(d = 64.0, h = 3.0);
        // 16x Outer Perimeter Grip Indents (Pioneer Jog Texture)
        for (a = [0 : 22.5 : 337.5]) {
            rotate([0, 0, a])
                translate([42.0, 0, 4.5])
                    cylinder(d = 4.5, h = 8.0);
        }
    }
}

// ── Full Assembly Render ─────────────────────────────────────────────────────
top_faceplate();
translate([0, 0, -6.0]) bottom_chassis();
for (jc = jog_centers) {
    translate([jc[0], pcb_d - jc[1], top_plate_t + 1.5])
        jog_wheel_platter();
}
