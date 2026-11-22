// ============================================================================
// Pioneer DDJ-FLX4 Modular Core v2.3 — Parametric OpenSCAD Reference Enclosure
// Canonical STEP/STL generator (including 6 eared G82 switch carriers & jog
// M3 nut-trap): cad/build_cad.py (FreeCAD 1.0 OpenCASCADE).
// ============================================================================
// External dims: 340.0 x 206.0 x 45.5 mm (55.5 mm w/ Jog Wheels)
// Split at X=115 & X=225 -> 115x206, 110x206, 115x206 mm (fits 220x220 bed)
// ============================================================================

$fn = 72;

case_w      = 340.0;
case_d      = 206.0;
wall_t      = 4.0;
floor_t     = 3.0;
bottom_h    = 42.0;
top_plate_t = 3.5;

seam_l = 115.0;
seam_r = 225.0;

// 10x Vertical M3 Pillars (rear Mixer uses brass F-F M3x30 standoffs coaxial with PCB H1/H2)
m3_pillars = [
    [ 10.0,  10.0], [105.0,  10.0], [ 10.0, 196.0], [105.0, 196.0],
    [122.0,  10.0], [218.0,  10.0],
    [235.0,  10.0], [330.0,  10.0], [235.0, 196.0], [330.0, 196.0]
];

pcb_x0 = (case_w - 98.0) / 2.0;        // 121.0
pcb_y_rear = case_d - wall_t - 0.5;    // 201.5 (0.5 mm clearance to rear wall)
usb_c_x = pcb_x0 + 48.895;             // 169.895
pcb_holes = [
    [pcb_x0 +  5.08, pcb_y_rear -  5.08],
    [pcb_x0 + 92.71, pcb_y_rear -  5.08],
    [pcb_x0 +  5.08, pcb_y_rear - 92.71],
    [pcb_x0 + 92.71, pcb_y_rear - 92.71]
];
h12_standoffs = [pcb_holes[0], pcb_holes[1]];

jog_centers = [[48.0, 116.0], [272.0, 116.0]];

rotary_pots = [
    [136.0, 189.0], [136.0, 170.5], [136.0, 152.0], [136.0, 133.5], [136.0, 115.0],
    [204.0, 189.0], [204.0, 170.5], [204.0, 152.0], [204.0, 133.5], [204.0, 115.0],
    [170.0, 186.0]
];

vert_faders = [[138.0, 68.0], [202.0, 68.0], [102.0, 116.0], [326.0, 116.0]];
horiz_fader = [170.0, 20.0];

sw_centers = [
    [ 22.0,  60.0], [ 44.0,  60.0], [ 66.0,  60.0], [ 88.0,  60.0],
    [ 22.0,  40.0], [ 44.0,  40.0], [ 66.0,  40.0], [ 88.0,  40.0],
    [242.0,  60.0], [264.0,  60.0], [286.0,  60.0], [308.0,  60.0],
    [242.0,  40.0], [264.0,  40.0], [286.0,  40.0], [308.0,  40.0],
    [156.0, 160.0], [184.0, 160.0], [170.0, 138.0], [170.0, 118.0],
    [158.0,  86.0], [182.0,  86.0],
    [ 80.0, 186.0], [ 80.0, 166.0], [ 22.0,  18.0], [ 50.0,  18.0],
    [246.0, 186.0], [246.0, 166.0], [246.0,  18.0], [274.0,  18.0]
];

module hex_nut_m3(h = 3.2, af = 5.8) {
    cylinder(r = (af / 2.0) / cos(30), h = h, $fn = 6);
}

module top_faceplate() {
    difference() {
        union() {
            cube([case_w, case_d, top_plate_t]);
            difference() {
                union() {
                    difference() {
                        translate([wall_t + 0.5, wall_t + 0.5, -2.5])
                            cube([case_w - 2*(wall_t + 0.5), case_d - 2*(wall_t + 0.5), 2.5]);
                        translate([wall_t + 2.5, wall_t + 2.5, -2.8])
                            cube([case_w - 2*(wall_t + 2.5), case_d - 2*(wall_t + 2.5), 3.0]);
                    }
                    for (sx = [seam_l - 3.5, seam_l + 0.5, seam_r - 3.5, seam_r + 0.5])
                        translate([sx, wall_t + 1.0, -3.0]) cube([3.0, case_d - 2*wall_t - 2.0, 3.0]);
                }
                for (p = concat(m3_pillars, h12_standoffs))
                    translate([p[0], p[1], -3.1]) cylinder(d = 11.0, h = 3.3);
            }
            for (h = h12_standoffs)
                translate([h[0], h[1], -1.4]) cylinder(d = 7.0, h = 1.4);
        }
        for (p = concat(m3_pillars, h12_standoffs)) {
            translate([p[0], p[1], -4.0]) cylinder(d = 3.4, h = top_plate_t + 6.0);
            translate([p[0], p[1], top_plate_t - 1.55]) cylinder(d1 = 3.4, d2 = 6.6, h = 1.6);
        }
        for (jc = jog_centers)
            translate([jc[0], jc[1], -2.0]) cylinder(d = 7.6, h = top_plate_t + 4.0);
        for (rp = rotary_pots)
            translate([rp[0], rp[1], -2.0]) cylinder(d = 7.6, h = top_plate_t + 4.0);
        for (vf = vert_faders) {
            translate([vf[0] - 2.3, vf[1] - 32.0, -2.0]) cube([4.6, 64.0, top_plate_t + 4.0]);
            for (dy = [-35.5, 35.5])
                translate([vf[0], vf[1] + dy, -2.0]) cylinder(d = 2.8, h = top_plate_t + 4.0);
        }
        translate([horiz_fader[0] - 32.0, horiz_fader[1] - 2.3, -2.0]) cube([64.0, 4.6, top_plate_t + 4.0]);
        for (dx = [-35.5, 35.5])
            translate([horiz_fader[0] + dx, horiz_fader[1], -2.0]) cylinder(d = 2.8, h = top_plate_t + 4.0);
        for (sc = sw_centers)
            translate([sc[0] - 6.6, sc[1] - 6.6, -4.0]) cube([13.2, 13.2, top_plate_t + 6.0]);
        translate([170.0, 58.0, -2.0]) cylinder(d = 5.2, h = top_plate_t + 4.0);
    }
}

module bottom_chassis() {
    difference() {
        union() {
            difference() {
                translate([0, 0, -bottom_h]) cube([case_w, case_d, bottom_h]);
                translate([wall_t, wall_t, -bottom_h + floor_t])
                    cube([case_w - 2*wall_t, case_d - 2*wall_t, bottom_h]);
            }
            for (p = m3_pillars)
                translate([p[0], p[1], -bottom_h + floor_t]) cylinder(d = 10.0, h = bottom_h - floor_t);
            for (sx = [seam_l, seam_r])
                translate([sx - 4.0, wall_t, -bottom_h + floor_t])
                    cube([8.0, case_d - 2*wall_t, bottom_h - floor_t - 3.0]);
            for (ph = pcb_holes)
                translate([ph[0], ph[1], -bottom_h + floor_t]) cylinder(d = 8.0, h = 6.0);
        }
        for (p = m3_pillars) {
            translate([p[0], p[1], -bottom_h - 1.0]) cylinder(d = 3.4, h = bottom_h + 2.0);
            translate([p[0], p[1], -bottom_h - 0.1]) hex_nut_m3(3.2, 5.8);
        }
        for (i = [0 : 3]) {
            ph = pcb_holes[i];
            translate([ph[0], ph[1], -bottom_h - 1.0]) cylinder(d = 3.4, h = 11.0);
            translate([ph[0], ph[1], -bottom_h - 0.1]) hex_nut_m3(i < 2 ? 3.3 : 2.8, 5.8);
        }
        for (sx = [seam_l, seam_r]) {
            translate([sx - 6.0, 55.0, -26.0]) cube([12.0, 95.0, 18.0]);
            for (b = [[28.0, -8.0], [28.0, -34.0], [178.0, -8.0], [178.0, -20.0]])
                translate([sx - 8.0, b[0], b[1]]) rotate([0, 90, 0]) cylinder(d = 3.4, h = 16.0);
        }
        translate([usb_c_x - 8.0, case_d - wall_t - 2.0, -25.2]) cube([16.0, wall_t + 4.0, 16.0]);
    }
}

top_faceplate();
bottom_chassis();
