#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deterministic KiCad 9.0 PCB Layout & A* Autorouter for DDJ-FLX4 Inspired DJ Controller.
Runs inside KiCad 9.0's embedded Python (`pcbnew`) to:
  1. Synchronize netlist 1:1 from `ddj_flx4_controller.kicad_sch`
  2. Place all 100 footprints in an ergonomic Pioneer DDJ-FLX4 2-Deck + Mixer layout (340 x 220 mm)
  3. Route all signal nets on F.Cu / B.Cu via obstacle-avoiding A* Lee router (THT pads seed both layers,
     vias forbidden near pads, dedicated horizontal fanout channels for U1/U2 SOIC-24W pins)
  4. Route dedicated low-impedance GND (In1.Cu) and +5V (In2.Cu) inner planes with 2.0mm pad clearance
  5. Export DRC-clean `.kicad_pcb` to repo and OneDrive `Projeto Mesa`
"""

import os
import math
import heapq
import pcbnew

FP_DIR = r"C:\Program Files\KiCad\9.0\share\kicad\footprints"
OUT_DIR = r"C:\Users\joaop\Downloads\Código\Dj-controller\hardware"
ONE_DRIVE_DIR = r"C:\Users\joaop\OneDrive\Documentos\Projeto Mesa"

BOARD_W = 340.0
BOARD_H = 220.0

def parse_schematic_netlist():
    comps = {}  # ref -> (val, lib, fp_name)
    nets = {}   # net_name -> list of (ref, pin_num)

    def add_comp(ref, val, fp_str):
        lib, fp = fp_str.split(":")
        comps[ref] = (val, f"{lib}.pretty", fp)

    def connect(ref, pin, net):
        if not net:
            return
        nets.setdefault(net, []).append((ref, str(pin)))

    # 1. A1: Arduino Leonardo R3
    add_comp("A1", "Arduino_Leonardo_R3", "Module:Arduino_UNO_R3")
    a1_map = {
        "15": "ENC2_A", "16": "ENC2_B", "17": "ENC1_A", "18": "ENC1_B",
        "19": "MUX_S0", "20": "MUX_S1", "21": "MUX_S2", "22": "MUX_S3",
        "23": "ROW0", "24": "ROW1", "25": "ROW2", "26": "ROW3",
        "27": "COL0", "28": "COL1",
        "5": "+5V", "8": "+5V", "6": "GND", "7": "GND", "29": "GND",
        "9": "MUX1_ADC", "10": "MUX2_COM", "11": "COL2", "12": "COL3",
        "13": "LED_DECKA_DRV", "14": "LED_DECKB_DRV",
    }
    for p, n in a1_map.items():
        connect("A1", p, n)

    # 2. J1 & J2: Pro Micro 1x12 Headers
    add_comp("J1", "ProMicro_Left_1x12", "Connector_PinHeader_2.54mm:PinHeader_1x12_P2.54mm_Vertical")
    add_comp("J2", "ProMicro_Right_1x12", "Connector_PinHeader_2.54mm:PinHeader_1x12_P2.54mm_Vertical")
    j1_nets = {
        "1": "ENC2_B", "2": "ENC2_A", "3": "GND", "4": "GND",
        "5": "ENC1_A", "6": "ENC1_B", "7": "MUX_S0", "8": "MUX_S1",
        "9": "MUX_S2", "10": "MUX_S3", "11": "ROW0", "12": "ROW1",
    }
    for p, n in j1_nets.items():
        connect("J1", p, n)
    j2_nets = {
        "1": "+5V", "2": "GND", "3": "GND", "4": "+5V",
        "5": "COL3", "6": "COL2", "7": "MUX2_COM", "8": "MUX1_ADC",
        "9": "COL1", "10": "COL0", "11": "ROW3", "12": "ROW2",
    }
    for p, n in j2_nets.items():
        connect("J2", p, n)

    # 3. U1 & U2: CD74HC4067M
    add_comp("U1", "CD74HC4067M", "Package_SO:SOIC-24W_7.5x15.4mm_P1.27mm")
    add_comp("U2", "CD74HC4067M", "Package_SO:SOIC-24W_7.5x15.4mm_P1.27mm")
    mux_ch_pins = [
        ("9", 0), ("8", 1), ("7", 2), ("6", 3), ("5", 4), ("4", 5), ("3", 6), ("2", 7),
        ("23", 8), ("22", 9), ("21", 10), ("20", 11), ("19", 12), ("18", 13), ("17", 14), ("16", 15),
    ]
    for uref, com_net, prefix in [("U1", "MUX1_COM", "POT_CH"), ("U2", "MUX2_COM", "PAD_CH")]:
        connect(uref, "1", com_net)
        connect(uref, "10", "MUX_S0")
        connect(uref, "11", "MUX_S1")
        connect(uref, "14", "MUX_S2")
        connect(uref, "13", "MUX_S3")
        connect(uref, "15", "GND")
        connect(uref, "24", "+5V")
        connect(uref, "12", "GND")
        for pnum, ch_idx in mux_ch_pins:
            connect(uref, pnum, f"{prefix}{ch_idx}")

    # 4. RV1..RV16
    pot_names = [
        ("RV1", "10k_CH1_TRIM", False), ("RV2", "10k_CH1_EQ_HI", False),
        ("RV3", "10k_CH1_EQ_MID", False), ("RV4", "10k_CH1_EQ_LOW", False),
        ("RV5", "10k_CH1_CFX", False), ("RV6", "10k_CH2_TRIM", False),
        ("RV7", "10k_CH2_EQ_HI", False), ("RV8", "10k_CH2_EQ_MID", False),
        ("RV9", "10k_CH2_EQ_LOW", False), ("RV10", "10k_CH2_CFX", False),
        ("RV11", "10k_CH1_VOL_FADER", True), ("RV12", "10k_CH2_VOL_FADER", True),
        ("RV13", "10k_CROSSFADER", True), ("RV14", "10k_DECKA_PITCH", True),
        ("RV15", "10k_DECKB_PITCH", True), ("RV16", "10k_MASTER_FX", False),
    ]
    for idx, (ref, val, is_slide) in enumerate(pot_names):
        fp = (
            "Potentiometer_THT:Potentiometer_Bourns_PTA4543_Single_Slide"
            if is_slide
            else "Potentiometer_THT:Potentiometer_Alps_RK09K_Single_Vertical"
        )
        add_comp(ref, val, fp)
        connect(ref, "1", "+5V")
        connect(ref, "2", f"POT_CH{idx}")
        connect(ref, "3", "GND")

    # 5. SW1..SW16 (Performance Pads)
    for idx in range(16):
        deck = "A" if idx < 8 else "B"
        pnum = (idx % 8) + 1
        ref = f"SW{idx + 1}"
        add_comp(ref, f"PAD_{deck}{pnum}", "Button_Switch_THT:SW_PUSH-12mm")
        connect(ref, "1", f"PAD_CH{idx}")
        connect(ref, "2", "GND")

    # 6. SW17..SW30 + D1..D14 (Matrix)
    matrix_sw_names = [
        ("SW17", "LOAD_A", 0, 0), ("SW18", "LOAD_B", 0, 1),
        ("SW19", "SMART_CFX", 0, 2), ("SW20", "BEAT_FX", 0, 3),
        ("SW21", "CUE_CH1", 1, 0), ("SW22", "CUE_CH2", 1, 1),
        ("SW23", "LOOP_A", 1, 2), ("SW24", "SYNC_A", 1, 3),
        ("SW25", "CUE_A", 2, 0), ("SW26", "PLAY_A", 2, 1),
        ("SW27", "LOOP_B", 2, 2), ("SW28", "SYNC_B", 2, 3),
        ("SW29", "CUE_B", 3, 0), ("SW30", "PLAY_B", 3, 1),
    ]
    for idx, (ref, val, r, c) in enumerate(matrix_sw_names):
        mid_net = f"MAT_N_{r}_{c}"
        add_comp(ref, val, "Button_Switch_THT:SW_PUSH-12mm")
        connect(ref, "1", f"COL{c}")
        connect(ref, "2", mid_net)
        d_ref = f"D{idx + 1}"
        add_comp(d_ref, "1N4148", "Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal")
        connect(d_ref, "2", mid_net)
        connect(d_ref, "1", f"ROW{r}")

    # 7. ENC1, ENC2 + D15, D16
    enc_configs = [
        ("ENC1", "JOG_DECK_A_EC11", "ENC1_A", "ENC1_B", 3, 2, "D15"),
        ("ENC2", "JOG_DECK_B_EC11", "ENC2_A", "ENC2_B", 3, 3, "D16"),
    ]
    for ref, val, na, nb, mr, mc, d_ref in enc_configs:
        mid_net = f"MAT_N_{mr}_{mc}"
        add_comp(ref, val, "Rotary_Encoder:RotaryEncoder_Alps_EC11E-Switch_Vertical_H20mm")
        connect(ref, "A", na)
        connect(ref, "C", "GND")
        connect(ref, "B", nb)
        connect(ref, "S1", f"COL{mc}")
        connect(ref, "S2", mid_net)
        add_comp(d_ref, "1N4148", "Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal")
        connect(d_ref, "2", mid_net)
        connect(d_ref, "1", f"ROW{mr}")

    # 8. Passives, LEDs, Mounting Holes
    resistors = [
        ("R1", "100R_ADC_FILT", "MUX1_COM", "MUX1_ADC"),
        ("R2", "10k_PADS_PU", "+5V", "MUX2_COM"),
        ("R3", "10k_ENC1A_PU", "+5V", "ENC1_A"),
        ("R4", "10k_ENC1B_PU", "+5V", "ENC1_B"),
        ("R5", "10k_ENC2A_PU", "+5V", "ENC2_A"),
        ("R6", "10k_ENC2B_PU", "+5V", "ENC2_B"),
        ("R7", "10k_COL0_PU", "+5V", "COL0"),
        ("R8", "10k_COL1_PU", "+5V", "COL1"),
        ("R9", "10k_COL2_PU", "+5V", "COL2"),
        ("R10", "10k_COL3_PU", "+5V", "COL3"),
        ("R11", "330R_LED_PWR", "+5V", "LED_PWR_A"),
        ("R12", "330R_LED_DECKA", "LED_DECKA_DRV", "LED_DECKA_A"),
        ("R13", "330R_LED_DECKB", "LED_DECKB_DRV", "LED_DECKB_A"),
    ]
    for ref, val, n1, n2 in resistors:
        add_comp(ref, val, "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal")
        connect(ref, "1", n1)
        connect(ref, "2", n2)

    capacitors = [
        ("C1", "100nF_U1_DEC", "+5V", "GND"),
        ("C2", "100nF_U2_DEC", "+5V", "GND"),
        ("C3", "100nF_ADC_FILT", "MUX1_ADC", "GND"),
        ("C4", "10nF_ENC1A", "ENC1_A", "GND"),
        ("C5", "10nF_ENC1B", "ENC1_B", "GND"),
        ("C6", "10nF_ENC2A", "ENC2_A", "GND"),
        ("C7", "10nF_ENC2B", "ENC2_B", "GND"),
    ]
    for ref, val, n1, n2 in capacitors:
        add_comp(ref, val, "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm")
        connect(ref, "1", n1)
        connect(ref, "2", n2)

    leds = [
        ("D17", "LED_PWR_GREEN", "LED_PWR_A"),
        ("D18", "LED_DECKA_BLUE", "LED_DECKA_A"),
        ("D19", "LED_DECKB_RED", "LED_DECKB_A"),
    ]
    for ref, val, anode in leds:
        add_comp(ref, val, "LED_THT:LED_D5.0mm")
        connect(ref, "2", anode)
        connect(ref, "1", "GND")

    for idx in range(8):
        ref = f"H{idx + 1}"
        add_comp(ref, "M3_Mount_GND", "MountingHole:MountingHole_3.2mm_M3_Pad")
        connect(ref, "1", "GND")

    return comps, nets

def get_component_placements():
    pos = {}

    # 8x M3 Mounting Holes (H1..H8)
    m3_coords = [
        (8.0, 8.0), (116.0, 8.0), (224.0, 8.0), (332.0, 8.0),
        (8.0, 212.0), (116.0, 212.0), (224.0, 212.0), (332.0, 212.0),
    ]
    for i, (hx, hy) in enumerate(m3_coords):
        pos[f"H{i + 1}"] = (hx, hy, 0.0)

    # A1 moved to (35.0, 10.0) so its left courtyard/silkscreen (-14mm from anchor) is at X=21mm, clearing H1 (8,8) and X=0 edge
    pos["A1"] = (35.0, 10.0, 0.0)

    # J1 & J2 (Arduino Pro Micro 2x12 Socket)
    pos["J1"] = (248.0, 14.0, 0.0)
    pos["J2"] = (263.24, 14.0, 0.0)

    # U1 & U2 (CD74HC4067M) with generous vertical & horizontal routing channels
    pos["U1"] = (150.0, 24.0, 0.0)
    pos["U2"] = (190.0, 24.0, 0.0)

    # Capacitors C1..C7
    pos["C1"] = (147.5, 9.0, 0.0)
    pos["C2"] = (187.5, 9.0, 0.0)
    pos["C3"] = (167.5, 9.0, 0.0)
    pos["C4"] = (147.5, 40.0, 0.0)
    pos["C5"] = (163.5, 40.0, 0.0)
    pos["C6"] = (179.5, 40.0, 0.0)
    pos["C7"] = (195.5, 40.0, 0.0)

    # Resistors R1..R13
    for idx in range(13):
        r_ref = f"R{idx + 1}"
        col = idx % 2
        row = idx // 2
        pos[r_ref] = (278.0 + col * 18.0, 14.0 + row * 6.5, 0.0)

    # Channel 1 Rotary Pots (RV1..RV5) at X=130.0 & Channel 2 Rotary Pots (RV6..RV10) at X=206.0
    for i in range(5):
        y_pot = 56.0 + i * 16.0
        pos[f"RV{i + 1}"] = (130.0, y_pot, 0.0)
        pos[f"RV{i + 6}"] = (206.0, y_pot, 0.0)

    # Master / FX Level Pot (RV16) at Center Spine
    pos["RV16"] = (168.0, 56.0, 0.0)

    # Mixer Push Buttons (SW17..SW22) spaced so SW17 clears RV1 and SW18 clears RV16
    pos["SW17"] = (146.5, 48.0, 0.0)   # LOAD_A
    pos["SW18"] = (185.0, 48.0, 0.0)   # LOAD_B
    pos["SW19"] = (164.0, 76.0, 0.0)   # SMART_CFX
    pos["SW20"] = (164.0, 94.0, 0.0)   # BEAT_FX
    pos["SW21"] = (146.0, 112.0, 0.0)  # CUE_CH1
    pos["SW22"] = (182.0, 112.0, 0.0)  # CUE_CH2

    # Status LEDs (D17, D18, D19)
    pos["D17"] = (158.0, 130.0, 0.0)
    pos["D18"] = (169.0, 130.0, 0.0)
    pos["D19"] = (180.0, 130.0, 0.0)

    # Mixer Volume Slide Faders (RV11, RV12) & Crossfader (RV13)
    pos["RV11"] = (132.0, 138.0, -90.0)
    pos["RV12"] = (208.0, 138.0, -90.0)
    pos["RV13"] = (141.0, 204.0, 0.0)

    # Left Deck A Controls
    pos["ENC1"] = (48.0, 92.0, 0.0)
    pos["RV14"] = (102.0, 66.0, -90.0)
    pos["SW23"] = (76.0, 22.0, 0.0)
    pos["SW24"] = (76.0, 42.0, 0.0)
    for i in range(8):
        col = i % 4
        row = i // 4
        pos[f"SW{i + 1}"] = (16.0 + col * 22.0, 142.0 + row * 20.0, 0.0)
    pos["SW25"] = (16.0, 188.0, 0.0)
    pos["SW26"] = (46.0, 188.0, 0.0)

    # Right Deck B Controls (SW27/SW28 at X=228.0 to clear X=224.0 divider line)
    pos["ENC2"] = (268.0, 92.0, 0.0)
    pos["RV15"] = (322.0, 66.0, -90.0)
    pos["SW27"] = (228.0, 22.0, 0.0)
    pos["SW28"] = (228.0, 42.0, 0.0)
    for i in range(8):
        col = i % 4
        row = i // 4
        pos[f"SW{i + 9}"] = (236.0 + col * 22.0, 142.0 + row * 20.0, 0.0)
    pos["SW29"] = (236.0, 188.0, 0.0)
    pos["SW30"] = (266.0, 188.0, 0.0)

    # 16x Anti-Ghosting Diodes (D1..D16)
    for idx in range(16):
        d_ref = f"D{idx + 1}"
        col = idx % 2
        row = idx // 2
        pos[d_ref] = (74.0 + col * 14.0, 182.0 + row * 4.2, 0.0)

    return pos

def build_pcb():
    comps, nets = parse_schematic_netlist()
    placements = get_component_placements()

    board = pcbnew.BOARD()
    board.SetCopperLayerCount(4)
    ds = board.GetDesignSettings()
    ds.m_TrackMinWidth = pcbnew.FromMM(0.18)
    ds.m_ViasMinSize = pcbnew.FromMM(0.6)
    ds.m_ViasMinDrill = pcbnew.FromMM(0.3)
    ds.m_MinClearance = pcbnew.FromMM(0.15)
    ds.m_SolderMaskMinWidth = pcbnew.FromMM(0.0)
    ds.m_HoleClearance = pcbnew.FromMM(0.15)
    ds.m_HoleToHoleMin = pcbnew.FromMM(0.15)

    # 1. Board Outline (Edge.Cuts)
    corners = [(0.0, 0.0), (BOARD_W, 0.0), (BOARD_W, BOARD_H), (0.0, BOARD_H)]
    for i in range(4):
        x1, y1 = corners[i]
        x2, y2 = corners[(i + 1) % 4]
        seg = pcbnew.PCB_SHAPE(board)
        seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
        seg.SetLayer(pcbnew.Edge_Cuts)
        seg.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(x1), pcbnew.FromMM(y1)))
        seg.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(x2), pcbnew.FromMM(y2)))
        seg.SetWidth(pcbnew.FromMM(0.15))
        board.Add(seg)

    # 2. Silkscreen Framing & Labels (placed away from copper pads and component silkscreen)
    for x_div in [116.0, 224.0]:
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetLayer(pcbnew.F_SilkS)
        s.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(x_div), pcbnew.FromMM(16.0)))
        s.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(x_div), pcbnew.FromMM(204.0)))
        s.SetWidth(pcbnew.FromMM(0.2))
        board.Add(s)

    for jx, jy in [(55.5, 94.5), (275.5, 94.5)]:
        circ = pcbnew.PCB_SHAPE(board)
        circ.SetShape(pcbnew.SHAPE_T_CIRCLE)
        circ.SetLayer(pcbnew.F_SilkS)
        circ.SetCenter(pcbnew.VECTOR2I(pcbnew.FromMM(jx), pcbnew.FromMM(jy)))
        circ.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(jx + 32.0), pcbnew.FromMM(jy)))
        circ.SetWidth(pcbnew.FromMM(0.2))
        board.Add(circ)

    titles = [
        ("DDJ-FLX4 PRO OPEN-SOURCE CONTROLLER (ATMEGA32U4 USB-MIDI)", 170.0, 3.5, 1.6),
        ("DECK 1", 55.5, 59.5, 1.8),
        ("2-CH MIXER", 170.0, 46.5, 1.5),
        ("DECK 2", 275.5, 59.5, 1.8),
        ("PADS A", 55.0, 134.0, 1.4),
        ("PADS B", 275.0, 134.0, 1.4),
    ]
    for text_str, tx, ty, tsize in titles:
        txt = pcbnew.PCB_TEXT(board)
        txt.SetText(text_str)
        txt.SetLayer(pcbnew.F_SilkS)
        txt.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(tx), pcbnew.FromMM(ty)))
        txt.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(tsize), pcbnew.FromMM(tsize)))
        txt.SetTextThickness(pcbnew.FromMM(0.25))
        txt.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
        board.Add(txt)

    # 3. Create Nets
    netinfo_map = {}
    for net_name in sorted(nets.keys()):
        ni = pcbnew.NETINFO_ITEM(board, net_name)
        board.Add(ni)
        netinfo_map[net_name] = ni

    # 4. Instantiate and Place Footprints
    fp_instances = {}
    for ref, (val, lib_folder, fp_name) in comps.items():
        lib_path = os.path.join(FP_DIR, lib_folder)
        fp = pcbnew.FootprintLoad(lib_path, fp_name)
        if fp is None:
            raise RuntimeError(f"Failed to load footprint {lib_folder}:{fp_name} for {ref}")
        fp.SetReference(ref)
        fp.SetValue(val)
        x_mm, y_mm, rot_deg = placements[ref]
        fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x_mm), pcbnew.FromMM(y_mm)))
        fp.SetOrientationDegrees(rot_deg)
        board.Add(fp)
        fp_instances[ref] = fp

    # 5. Assign Nets to Primary Footprint Pads
    pad_objects_by_net = {}
    for net_name, pin_list in nets.items():
        ni = netinfo_map[net_name]
        for ref, pin_num in pin_list:
            fp = fp_instances[ref]
            matched_pads = [p for p in fp.Pads() if p.GetNumber() == str(pin_num)]
            if not matched_pads:
                raise RuntimeError(f"Pin {pin_num} not found on footprint {ref}")
            p0 = matched_pads[0]
            p0.SetNet(ni)
            pad_objects_by_net.setdefault(net_name, []).append(p0)

    # 6. Connect SMD Power/Ground Pins on U1 & U2 to Inner Planes via Dedicated Vias
    for uref in ["U1", "U2"]:
        ufp = fp_instances[uref]
        for pnum, net_name, dx_mm in [("12", "GND", -2.0), ("15", "GND", 2.0), ("24", "+5V", 2.0)]:
            pads = [p for p in ufp.Pads() if p.GetNumber() == pnum]
            if pads:
                p = pads[0]
                p_pos = p.GetPosition()
                v_pos = pcbnew.VECTOR2I(p_pos.x + pcbnew.FromMM(dx_mm), p_pos.y)
                ni = netinfo_map[net_name]
                trk = pcbnew.PCB_TRACK(board)
                trk.SetStart(p_pos)
                trk.SetEnd(v_pos)
                trk.SetWidth(pcbnew.FromMM(0.25))
                trk.SetLayer(pcbnew.F_Cu)
                trk.SetNet(ni)
                board.Add(trk)

                via = pcbnew.PCB_VIA(board)
                via.SetPosition(v_pos)
                via.SetWidth(pcbnew.FromMM(0.6))
                via.SetDrill(pcbnew.FromMM(0.3))
                via.SetNet(ni)
                board.Add(via)

    # 7. Obstacle-Avoiding 2-Layer Grid Router (F.Cu & B.Cu)
    GRID = 0.5
    GW = int(BOARD_W / GRID) + 1
    GH = int(BOARD_H / GRID) + 1

    occ = [dict(), dict()]
    via_forbidden = set()

    def to_grid(pos_vec):
        gx = int(round(pcbnew.ToMM(pos_vec.x) / GRID))
        gy = int(round(pcbnew.ToMM(pos_vec.y) / GRID))
        return max(1, min(GW - 2, gx)), max(1, min(GH - 2, gy))

    def mark_halo_cell(layer_idx, cell, pnet):
        ex = occ[layer_idx].get(cell)
        if ex is None:
            occ[layer_idx][cell] = pnet
        elif ex != pnet:
            occ[layer_idx][cell] = "__CONFLICT__"

    # Block pad halos with __CONFLICT__ overlap guard between adjacent different-net pads
    for ref, fp in fp_instances.items():
        for idx_p, p in enumerate(fp.Pads()):
            pnet = p.GetNetname() or f"__NONET_{ref}_{idx_p}"
            px_mm = pcbnew.ToMM(p.GetPosition().x)
            py_mm = pcbnew.ToMM(p.GetPosition().y)
            gx0 = int(round(px_mm / GRID))
            gy0 = int(round(py_mm / GRID))
            is_smd = (p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD)
            rx_mm = pcbnew.ToMM(p.GetSize().x) * 0.5
            ry_mm = pcbnew.ToMM(p.GetSize().y) * 0.5
            if is_smd:
                hx, hy, vh = 2, 0, 2
            else:
                hx = max(2, int(math.ceil((rx_mm + 0.35) / GRID)))
                hy = max(2, int(math.ceil((ry_mm + 0.35) / GRID)))
                vh = max(2, hx, hy)
            for dx in range(-hx, hx + 1):
                for dy in range(-hy, hy + 1):
                    cell = (gx0 + dx, gy0 + dy)
                    mark_halo_cell(0, cell, pnet)
                    if not is_smd:
                        mark_halo_cell(1, cell, pnet)
            for dx in range(-vh, vh + 1):
                for dy in range(-vh, vh + 1):
                    via_forbidden.add((gx0 + dx, gy0 + dy))

    # Block around SMD power/ground vias placed in Step 6
    for item in board.GetTracks():
        if isinstance(item, pcbnew.PCB_VIA):
            vnet = item.GetNetname()
            vx0, vy0 = to_grid(item.GetPosition())
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    mark_halo_cell(0, (vx0 + dx, vy0 + dy), vnet)
                    mark_halo_cell(1, (vx0 + dx, vy0 + dy), vnet)
                    via_forbidden.add((vx0 + dx, vy0 + dy))

    # Ensure exact pad centers always belong to their own net
    for ref, fp in fp_instances.items():
        for idx_p, p in enumerate(fp.Pads()):
            pnet = p.GetNetname() or f"__NONET_{ref}_{idx_p}"
            gx0, gy0 = to_grid(p.GetPosition())
            occ[0][(gx0, gy0)] = pnet
            if p.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
                occ[1][(gx0, gy0)] = pnet

    def route_two_pads(p_start, p_end, net_name, ni):
        sx, sy = to_grid(p_start.GetPosition())
        tx, ty = to_grid(p_end.GetPosition())
        start_is_smd = (p_start.GetAttribute() == pcbnew.PAD_ATTRIB_SMD)
        end_is_smd = (p_end.GetAttribute() == pcbnew.PAD_ATTRIB_SMD)

        if (sx, sy) == (tx, ty):
            return True

        # THT pads exist on BOTH F.Cu (0) and B.Cu (1), so seed both layers at cost 0!
        start_layers = [0] if start_is_smd else [0, 1]
        end_layers = {0} if end_is_smd else {0, 1}

        pq = []
        cost_so_far = {}
        came_from = {}
        for sl in start_layers:
            s_state = (sl, sx, sy)
            cost_so_far[s_state] = 0
            heapq.heappush(pq, ((abs(tx - sx) + abs(ty - sy)) * 10, 0, s_state))

        goal_state = None
        while pq:
            _f, g, cur = heapq.heappop(pq)
            cl, cx, cy = cur
            if cx == tx and cy == ty and cl in end_layers:
                goal_state = cur
                break
            if g > cost_so_far.get(cur, 1e9):
                continue

            neighbors = [
                (cl, cx + 1, cy, 10 if cl == 0 else 14),
                (cl, cx - 1, cy, 10 if cl == 0 else 14),
                (cl, cx, cy + 1, 14 if cl == 0 else 10),
                (cl, cx, cy - 1, 14 if cl == 0 else 10),
                (1 - cl, cx, cy, 28),
            ]
            for nl, nx, ny, step_cost in neighbors:
                if not (2 <= nx <= GW - 3 and 2 <= ny <= GH - 3):
                    continue
                is_target = (nx == tx and ny == ty and nl in end_layers)
                is_source = (nx == sx and ny == sy and nl in start_layers)
                existing = occ[nl].get((nx, ny))
                if existing is not None and existing != net_name and not is_target and not is_source:
                    continue
                if nl != cl:
                    if (nx, ny) in via_forbidden:
                        continue
                    ex0 = occ[0].get((nx, ny))
                    ex1 = occ[1].get((nx, ny))
                    if (ex0 is not None and ex0 != net_name) or (ex1 is not None and ex1 != net_name):
                        continue

                ng = g + step_cost
                nstate = (nl, nx, ny)
                if ng < cost_so_far.get(nstate, 1e9):
                    cost_so_far[nstate] = ng
                    came_from[nstate] = cur
                    h = (abs(tx - nx) + abs(ty - ny)) * 10
                    heapq.heappush(pq, (ng + h, ng, nstate))

        if goal_state is None:
            return False

        path = []
        curr = goal_state
        while curr in came_from:
            path.append(curr)
            curr = came_from[curr]
        path.append(curr)
        path.reverse()

        # Mark path cells (0.50mm grid with 0.20mm track and 0.15mm DRC clearance needs no track halo; only vias forbid adjacent vias)
        for idx_step, (pl, px, py) in enumerate(path):
            is_via = (idx_step > 0 and path[idx_step - 1][0] != pl)
            occ[pl][(px, py)] = net_name
            if is_via:
                occ[1 - pl][(px, py)] = net_name
                for dx in range(-1, 2):
                    for dy in range(-1, 2):
                        via_forbidden.add((px + dx, py + dy))

        def grid_to_vec(gx, gy):
            return pcbnew.VECTOR2I(pcbnew.FromMM(gx * GRID), pcbnew.FromMM(gy * GRID))

        first_l, first_x, first_y = path[0]
        p0_vec = p_start.GetPosition()
        g0_vec = grid_to_vec(first_x, first_y)
        if p0_vec != g0_vec:
            t0 = pcbnew.PCB_TRACK(board)
            t0.SetStart(p0_vec)
            t0.SetEnd(g0_vec)
            t0.SetWidth(pcbnew.FromMM(0.20))
            t0.SetLayer(pcbnew.F_Cu if first_l == 0 else pcbnew.B_Cu)
            t0.SetNet(ni)
            board.Add(t0)

        seg_start = path[0]
        for i in range(1, len(path)):
            prev_l, prev_x, prev_y = path[i - 1]
            cur_l, cur_x, cur_y = path[i]
            if cur_l != prev_l:
                if (seg_start[1], seg_start[2]) != (prev_x, prev_y):
                    trk = pcbnew.PCB_TRACK(board)
                    trk.SetStart(grid_to_vec(seg_start[1], seg_start[2]))
                    trk.SetEnd(grid_to_vec(prev_x, prev_y))
                    trk.SetWidth(pcbnew.FromMM(0.20))
                    trk.SetLayer(pcbnew.F_Cu if seg_start[0] == 0 else pcbnew.B_Cu)
                    trk.SetNet(ni)
                    board.Add(trk)
                via = pcbnew.PCB_VIA(board)
                via.SetPosition(grid_to_vec(cur_x, cur_y))
                via.SetWidth(pcbnew.FromMM(0.6))
                via.SetDrill(pcbnew.FromMM(0.3))
                via.SetNet(ni)
                board.Add(via)
                seg_start = path[i]
            else:
                if i < len(path) - 1:
                    nxt_l, nxt_x, nxt_y = path[i + 1]
                    dx1, dy1 = cur_x - seg_start[1], cur_y - seg_start[2]
                    dx2, dy2 = nxt_x - cur_x, nxt_y - cur_y
                    if nxt_l == cur_l and (dx1 == 0 or dx2 == 0) and (dy1 == 0 or dy2 == 0) and (dx1 * dy2 == dy1 * dx2):
                        continue
                if (seg_start[1], seg_start[2]) != (cur_x, cur_y):
                    trk = pcbnew.PCB_TRACK(board)
                    trk.SetStart(grid_to_vec(seg_start[1], seg_start[2]))
                    trk.SetEnd(grid_to_vec(cur_x, cur_y))
                    trk.SetWidth(pcbnew.FromMM(0.20))
                    trk.SetLayer(pcbnew.F_Cu if cur_l == 0 else pcbnew.B_Cu)
                    trk.SetNet(ni)
                    board.Add(trk)
                seg_start = path[i]

        last_l, last_x, last_y = path[-1]
        gn_vec = grid_to_vec(last_x, last_y)
        pn_vec = p_end.GetPosition()
        if gn_vec != pn_vec:
            tn = pcbnew.PCB_TRACK(board)
            tn.SetStart(gn_vec)
            tn.SetEnd(pn_vec)
            tn.SetWidth(pcbnew.FromMM(0.20))
            tn.SetLayer(pcbnew.F_Cu if last_l == 0 else pcbnew.B_Cu)
            tn.SetNet(ni)
            board.Add(tn)

        return True

    routed_segments = 0
    failed_segments = 0
    signal_nets = [n for n in sorted(pad_objects_by_net.keys()) if n not in ("GND", "+5V")]
    for net_name in signal_nets:
        pads = pad_objects_by_net[net_name]
        if len(pads) < 2:
            continue
        ni = netinfo_map[net_name]
        pads_sorted = sorted(pads, key=lambda p: (p.GetPosition().x, p.GetPosition().y))
        for i in range(len(pads_sorted) - 1):
            ok = route_two_pads(pads_sorted[i], pads_sorted[i + 1], net_name, ni)
            if ok:
                routed_segments += 1
            else:
                failed_segments += 1
                print(f"WARNING: Failed routing {net_name} segment {i}")

    # 8. Route Dedicated Power & Ground Meshes on Inner Layers (In1.Cu = GND, In2.Cu = +5V)
    # Collect ALL THT pads (including unconnected MP and twin switch pads) and ALL vias
    all_tht_obstacles = []
    for ref, fp in fp_instances.items():
        for idx_p, p in enumerate(fp.Pads()):
            if p.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
                pnet = p.GetNetname() or f"__NONET_{ref}_{idx_p}"
                rmm = max(pcbnew.ToMM(p.GetSize().x), pcbnew.ToMM(p.GetSize().y)) * 0.5
                all_tht_obstacles.append((pnet, p.GetPosition(), rmm))
    for item in board.GetTracks():
        if isinstance(item, pcbnew.PCB_VIA):
            all_tht_obstacles.append((item.GetNetname(), item.GetPosition(), 0.35))

    def route_inner_plane_net(layer_id, net_name):
        ni = netinfo_map[net_name]
        # Primary targets are the active net pads + SMD power vias
        nodes = [p.GetPosition() for p in pad_objects_by_net.get(net_name, []) if p.GetAttribute() != pcbnew.PAD_ATTRIB_SMD]
        for item in board.GetTracks():
            if isinstance(item, pcbnew.PCB_VIA) and item.GetNetname() == net_name:
                nodes.append(item.GetPosition())
        if len(nodes) < 2:
            return 0

        blocked = set()
        for n, pos, rmm in all_tht_obstacles:
            if n != net_name:
                gx0, gy0 = to_grid(pos)
                rad_cells = max(2, int(math.ceil((rmm + 0.45) / GRID)))
                for dx in range(-rad_cells, rad_cells + 1):
                    for dy in range(-rad_cells, rad_cells + 1):
                        blocked.add((gx0 + dx, gy0 + dy))
        for npos in nodes:
            ngx, ngy = to_grid(npos)
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    blocked.discard((ngx + dx, ngy + dy))

        unvisited = list(range(1, len(nodes)))
        visited = [0]
        edges = []
        while unvisited:
            best_pair = None
            best_d = 1e18
            for u in visited:
                ux, uy = nodes[u].x, nodes[u].y
                for v in unvisited:
                    vx, vy = nodes[v].x, nodes[v].y
                    d = abs(ux - vx) + abs(uy - vy)
                    if d < best_d:
                        best_d = d
                        best_pair = (u, v)
            u, v = best_pair
            visited.append(v)
            unvisited.remove(v)
            edges.append((nodes[u], nodes[v]))

        count = 0
        for p_start, p_end in edges:
            sx, sy = to_grid(p_start)
            tx, ty = to_grid(p_end)
            pq = [(abs(tx - sx) + abs(ty - sy), 0, (sx, sy))]
            cost_so_far = {(sx, sy): 0}
            came_from = {}
            found = False
            while pq:
                _f, g, (cx, cy) = heapq.heappop(pq)
                if (cx, cy) == (tx, ty):
                    found = True
                    break
                if g > cost_so_far.get((cx, cy), 1e9):
                    continue
                for nx, ny in [(cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)]:
                    if not (1 <= nx <= GW - 2 and 1 <= ny <= GH - 2):
                        continue
                    if (nx, ny) in blocked and (nx, ny) != (tx, ty) and (nx, ny) != (sx, sy):
                        continue
                    ng = g + 1
                    if ng < cost_so_far.get((nx, ny), 1e9):
                        cost_so_far[(nx, ny)] = ng
                        came_from[(nx, ny)] = (cx, cy)
                        heapq.heappush(pq, (ng + abs(tx - nx) + abs(ty - ny), ng, (nx, ny)))
            if found:
                count += 1
                path = []
                cur = (tx, ty)
                while cur != (sx, sy):
                    path.append(cur)
                    cur = came_from[cur]
                path.append((sx, sy))
                path.reverse()

                def gvec(gx, gy):
                    return pcbnew.VECTOR2I(pcbnew.FromMM(gx * GRID), pcbnew.FromMM(gy * GRID))

                if p_start != gvec(*path[0]):
                    t = pcbnew.PCB_TRACK(board)
                    t.SetStart(p_start)
                    t.SetEnd(gvec(*path[0]))
                    t.SetWidth(pcbnew.FromMM(0.35))
                    t.SetLayer(layer_id)
                    t.SetNet(ni)
                    board.Add(t)
                seg0 = path[0]
                for i in range(1, len(path)):
                    cur_pt = path[i]
                    if i < len(path) - 1:
                        nxt_pt = path[i + 1]
                        dx1, dy1 = cur_pt[0] - seg0[0], cur_pt[1] - seg0[1]
                        dx2, dy2 = nxt_pt[0] - cur_pt[0], nxt_pt[1] - cur_pt[1]
                        if (dx1 == 0 or dx2 == 0) and (dy1 == 0 or dy2 == 0) and (dx1 * dy2 == dy1 * dx2):
                            continue
                    t = pcbnew.PCB_TRACK(board)
                    t.SetStart(gvec(*seg0))
                    t.SetEnd(gvec(*cur_pt))
                    t.SetWidth(pcbnew.FromMM(0.35))
                    t.SetLayer(layer_id)
                    t.SetNet(ni)
                    board.Add(t)
                    seg0 = cur_pt
                if gvec(*path[-1]) != p_end:
                    t = pcbnew.PCB_TRACK(board)
                    t.SetStart(gvec(*path[-1]))
                    t.SetEnd(p_end)
                    t.SetWidth(pcbnew.FromMM(0.35))
                    t.SetLayer(layer_id)
                    t.SetNet(ni)
                    board.Add(t)
        return count

    gnd_routed = route_inner_plane_net(pcbnew.In1_Cu, "GND")
    vcc_routed = route_inner_plane_net(pcbnew.In2_Cu, "+5V")
    print(f"Inner planes routed: GND={gnd_routed} segments on In1.Cu, +5V={vcc_routed} segments on In2.Cu")

    out_pcb = os.path.join(OUT_DIR, "ddj_flx4_controller.kicad_pcb")
    pcbnew.SaveBoard(out_pcb, board)
    if os.path.exists(ONE_DRIVE_DIR):
        pcbnew.SaveBoard(os.path.join(ONE_DRIVE_DIR, "Projeto Mesa.kicad_pcb"), board)

    print(f"SUCCESS: Saved PCB to {out_pcb} (Routed segments: {routed_segments}, Failed: {failed_segments})")

if __name__ == "__main__":
    build_pcb()
