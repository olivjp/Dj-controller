#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deterministic KiCad 9.0 Schematic Synthesizer for DDJ-FLX4 Inspired DJ Controller.
Extracts official KiCad 9.0 library symbols from C:/Program Files/KiCad/9.0/share/kicad/symbols
and generates a complete, ERC-clean (.kicad_sch) + (.kicad_pro) hardware design.
"""

import os
import re
import uuid
import json

SYM_DIR = r"C:\Program Files\KiCad\9.0\share\kicad\symbols"
OUT_DIR = r"C:\Users\joaop\Downloads\Código\Dj-controller\hardware"
ONE_DRIVE_DIR = r"C:\Users\joaop\OneDrive\Documentos\Projeto Mesa"

os.makedirs(OUT_DIR, exist_ok=True)

def det_uuid(seed_str: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"ddj-flx4-kicad9-{seed_str}"))

def extract_lib_symbol(sym_file: str, sym_name: str, lib_prefix: str) -> tuple[str, dict]:
    path = os.path.join(SYM_DIR, sym_file)
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    pattern = f'(symbol "{sym_name}"'
    idx = text.find(pattern)
    if idx == -1:
        raise RuntimeError(f"Symbol {sym_name} not found in {sym_file}")
    depth = 0
    end = idx
    for i in range(idx, len(text)):
        if text[i] == '(':
            depth += 1
        elif text[i] == ')':
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    raw_block = text[idx:end]
    # Prefix top-level symbol name with library prefix (e.g. "74xx:CD74HC4067M")
    prefixed_block = raw_block.replace(f'(symbol "{sym_name}"', f'(symbol "{lib_prefix}:{sym_name}"', 1)

    # Parse pin positions in symbol local coords: pin_number -> (px, py, rot, name, etype)
    pins = {}
    for m in re.finditer(
        r'\(pin\s+(\w+)\s+\w+\s+\(at\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\).*?\(name\s+"([^"]+)".*?\(number\s+"([^"]+)"',
        raw_block,
        re.S,
    ):
        etype, px, py, rot, pname, pnum = m.groups()
        pins[pnum] = (float(px), float(py), int(float(rot)), pname, etype)
    return prefixed_block, pins

# Load all required official KiCad 9.0 symbols
REQUIRED_SYMBOLS = [
    ("MCU_Module.kicad_sym", "Arduino_Leonardo", "MCU_Module"),
    ("74xx.kicad_sym", "CD74HC4067M", "74xx"),
    ("Device.kicad_sym", "R_Potentiometer", "Device"),
    ("Device.kicad_sym", "RotaryEncoder_Switch", "Device"),
    ("Device.kicad_sym", "R", "Device"),
    ("Device.kicad_sym", "C", "Device"),
    ("Device.kicad_sym", "D", "Device"),
    ("Device.kicad_sym", "LED", "Device"),
    ("Switch.kicad_sym", "SW_Push", "Switch"),
    ("Connector_Generic.kicad_sym", "Conn_01x12", "Connector_Generic"),
    ("Mechanical.kicad_sym", "MountingHole_Pad", "Mechanical"),
    ("power.kicad_sym", "+5V", "power"),
    ("power.kicad_sym", "GND", "power"),
    ("power.kicad_sym", "PWR_FLAG", "power"),
]

LIB_BLOCKS = []
PIN_DB = {}
for fn, sname, prefix in REQUIRED_SYMBOLS:
    blk, pmap = extract_lib_symbol(fn, sname, prefix)
    LIB_BLOCKS.append(blk)
    PIN_DB[f"{prefix}:{sname}"] = pmap

ROOT_UUID = det_uuid("root-sheet")

class SchematicBuilder:
    def __init__(self):
        self.symbols = []
        self.wires = []
        self.labels = []
        self.no_connects = []
        self.texts = []
        self.pwr_idx = 1

    def pin_sheet_xy(self, lib_id: str, sx: float, sy: float, pnum: str) -> tuple[float, float]:
        px, py, _rot, _name, _etype = PIN_DB[lib_id][str(pnum)]
        # In KiCad schematic coordinates (rot=0): X_sheet = sx + px, Y_sheet = sy - py
        return round(sx + px, 2), round(sy - py, 2)

    def add_symbol(self, lib_id: str, ref: str, val: str, footprint: str, sx: float, sy: float, in_bom="yes", on_board="yes"):
        suuid = det_uuid(f"sym-{ref}")
        pins = PIN_DB[lib_id]
        pin_lines = []
        for pnum in pins:
            puuid = det_uuid(f"pin-{ref}-{pnum}")
            pin_lines.append(f'\t\t(pin "{pnum}"\n\t\t\t(uuid "{puuid}")\n\t\t)')
        pins_str = "\n".join(pin_lines)
        hide_ref = " (hide yes)" if ref.startswith("#PWR") else ""
        block = f"""\t(symbol
\t\t(lib_id "{lib_id}")
\t\t(at {sx:.2f} {sy:.2f} 0)
\t\t(unit 1)
\t\t(exclude_from_sim no)
\t\t(in_bom {in_bom})
\t\t(on_board {on_board})
\t\t(dnp no)
\t\t(fields_autoplaced yes)
\t\t(uuid "{suuid}")
\t\t(property "Reference" "{ref}"
\t\t\t(at {sx:.2f} {sy - 5.08:.2f} 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t){hide_ref}
\t\t\t)
\t\t)
\t\t(property "Value" "{val}"
\t\t\t(at {sx:.2f} {sy - 2.54:.2f} 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t)
\t\t)
\t\t(property "Footprint" "{footprint}"
\t\t\t(at {sx:.2f} {sy:.2f} 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t\t(hide yes)
\t\t\t)
\t\t)
\t\t(property "Datasheet" "~"
\t\t\t(at {sx:.2f} {sy:.2f} 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t\t(hide yes)
\t\t\t)
\t\t)
{pins_str}
\t\t(instances
\t\t\t(project "ddj_flx4_controller"
\t\t\t\t(path "/{ROOT_UUID}"
\t\t\t\t\t(reference "{ref}")
\t\t\t\t\t(unit 1)
\t\t\t\t)
\t\t\t)
\t\t\t(project "Projeto Mesa"
\t\t\t\t(path "/{ROOT_UUID}"
\t\t\t\t\t(reference "{ref}")
\t\t\t\t\t(unit 1)
\t\t\t\t)
\t\t\t)
\t\t)
\t)"""
        self.symbols.append(block)

    def add_wire(self, x1: float, y1: float, x2: float, y2: float, tag: str):
        wuuid = det_uuid(f"wire-{tag}-{x1}-{y1}-{x2}-{y2}")
        self.wires.append(f"""\t(wire
\t\t(pts
\t\t\t(xy {x1:.2f} {y1:.2f}) (xy {x2:.2f} {y2:.2f})
\t\t)
\t\t(stroke
\t\t\t(width 0)
\t\t\t(type default)
\t\t)
\t\t(uuid "{wuuid}")
\t)""")

    def add_label(self, net_name: str, x: float, y: float, angle: int = 0):
        luuid = det_uuid(f"lbl-{net_name}-{x}-{y}-{angle}")
        just = "left bottom" if angle == 0 else "right bottom"
        self.labels.append(f"""\t(label "{net_name}"
\t\t(at {x:.2f} {y:.2f} {angle})
\t\t(fields_autoplaced yes)
\t\t(effects
\t\t\t(font
\t\t\t\t(size 1.27 1.27)
\t\t\t)
\t\t\t(justify {just})
\t\t)
\t\t(uuid "{luuid}")
\t)""")

    def add_no_connect(self, x: float, y: float):
        ncuuid = det_uuid(f"nc-{x}-{y}")
        self.no_connects.append(f"""\t(no_connect
\t\t(at {x:.2f} {y:.2f})
\t\t(uuid "{ncuuid}")
\t)""")

    def connect_pin_to_net(self, lib_id: str, sx: float, sy: float, pnum: str, net_name: str, stub_dx: float = 5.08, stub_dy: float = 0.0):
        x1, y1 = self.pin_sheet_xy(lib_id, sx, sy, pnum)
        x2, y2 = round(x1 + stub_dx, 2), round(y1 + stub_dy, 2)
        self.add_wire(x1, y1, x2, y2, f"{lib_id}-{sx}-{sy}-{pnum}-{net_name}")
        angle = 180 if stub_dx < 0 else 0
        self.add_label(net_name, x2, y2, angle)

    def mark_pin_nc(self, lib_id: str, sx: float, sy: float, pnum: str):
        x1, y1 = self.pin_sheet_xy(lib_id, sx, sy, pnum)
        self.add_no_connect(x1, y1)

    def add_text_box(self, title: str, x: float, y: float):
        tuuid = det_uuid(f"txt-{title}-{x}-{y}")
        self.texts.append(f"""\t(text "{title}"
\t\t(exclude_from_sim no)
\t\t(at {x:.2f} {y:.2f} 0)
\t\t(effects
\t\t\t(font
\t\t\t\t(size 2.54 2.54)
\t\t\t\t(bold yes)
\t\t\t)
\t\t\t(justify left bottom)
\t\t)
\t\t(uuid "{tuuid}")
\t)""")

def build():
    sb = SchematicBuilder()

    # ── 0. Power Rails & PWR_FLAGs (Ensures 0 ERC Power-Pin Errors) ──────────
    sb.add_text_box("1. POWER RAILS & MCU CORE (ATmega32U4: Leonardo R3 + Pro Micro Type-C)", 20.32, 15.24)

    # Place GND power symbol tied to PWR_FLAG (+5V is already driven by A1 pin 5 power_out)
    sb.add_symbol("power:GND", "#PWR02", "GND", "", 40.64, 30.48, in_bom="yes", on_board="yes")
    sb.add_wire(40.64, 30.48, 40.64, 25.40, "pwr-gnd-flag")
    sb.add_label("GND", 40.64, 27.94, 0)
    sb.add_symbol("power:PWR_FLAG", "#FLG02", "PWR_FLAG", "", 40.64, 25.40, in_bom="yes", on_board="yes")

    # ── 1. Primary MCU: A1 (Arduino Leonardo R3 - ATmega32U4) ────────────────
    a1_lib = "MCU_Module:Arduino_Leonardo"
    a1_x, a1_y = 76.20, 60.96
    sb.add_symbol(a1_lib, "A1", "Arduino_Leonardo_R3", "Module:Arduino_UNO_R3", a1_x, a1_y)

    a1_pin_nets = {
        "15": ("ENC2_A", -7.62, 0),    # D0 / INT2
        "16": ("ENC2_B", -7.62, 0),    # D1 / INT3
        "17": ("ENC1_A", -7.62, 0),    # D2 / INT1
        "18": ("ENC1_B", -7.62, 0),    # D3 / INT0
        "19": ("MUX_S0", -7.62, 0),    # D4
        "20": ("MUX_S1", -7.62, 0),    # D5
        "21": ("MUX_S2", -7.62, 0),    # D6
        "22": ("MUX_S3", -7.62, 0),    # D7
        "23": ("ROW0", -7.62, 0),      # D8
        "24": ("ROW1", -7.62, 0),      # D9
        "25": ("ROW2", -7.62, 0),      # D10
        "26": ("ROW3", -7.62, 0),      # D11
        "27": ("COL0", -7.62, 0),      # D12
        "28": ("COL1", -7.62, 0),      # D13
        "5":  ("+5V", 0, -5.08),       # +5V
        "8":  ("+5V", 0, -5.08),       # VIN tied to +5V rail
        "6":  ("GND", 0, 5.08),        # GND
        "7":  ("GND", 0, 5.08),        # GND
        "29": ("GND", 0, 5.08),        # GND
        "9":  ("MUX1_ADC", 7.62, 0),   # A0 (Analog Pots/Faders via RC filter)
        "10": ("MUX2_COM", 7.62, 0),   # A1 (16 Performance Pads)
        "11": ("COL2", 7.62, 0),       # A2
        "12": ("COL3", 7.62, 0),       # A3
        "13": ("LED_DECKA_DRV", 7.62, 0), # A4
        "14": ("LED_DECKB_DRV", 7.62, 0), # A5
    }
    for pnum in PIN_DB[a1_lib]:
        if pnum in a1_pin_nets:
            net, dx, dy = a1_pin_nets[pnum]
            sb.connect_pin_to_net(a1_lib, a1_x, a1_y, pnum, net, dx, dy)
        else:
            sb.mark_pin_nc(a1_lib, a1_x, a1_y, pnum)

    # ── 2. Parallel Pro Micro Type-C Headers (J1 & J2 - 2x12 Socket) ─────────
    conn_lib = "Connector_Generic:Conn_01x12"
    j1_x, j1_y = 132.08, 55.88
    j2_x, j2_y = 162.56, 55.88
    sb.add_symbol(conn_lib, "J1", "ProMicro_Left_1x12", "Connector_PinHeader_2.54mm:PinHeader_1x12_P2.54mm_Vertical", j1_x, j1_y)
    sb.add_symbol(conn_lib, "J2", "ProMicro_Right_1x12", "Connector_PinHeader_2.54mm:PinHeader_1x12_P2.54mm_Vertical", j2_x, j2_y)

    j1_nets = {
        "1": "ENC2_B", "2": "ENC2_A", "3": "GND", "4": "GND",
        "5": "ENC1_A", "6": "ENC1_B", "7": "MUX_S0", "8": "MUX_S1",
        "9": "MUX_S2", "10": "MUX_S3", "11": "ROW0", "12": "ROW1",
    }
    for pnum, net in j1_nets.items():
        sb.connect_pin_to_net(conn_lib, j1_x, j1_y, pnum, net, -7.62, 0)

    j2_nets = {
        "1": "+5V", "2": "GND", "3": "GND", "4": "+5V",
        "5": "COL3", "6": "COL2", "7": "MUX2_COM", "8": "MUX1_ADC",
        "9": "COL1", "10": "COL0", "11": "ROW3", "12": "ROW2",
    }
    for pnum, net in j2_nets.items():
        sb.connect_pin_to_net(conn_lib, j2_x, j2_y, pnum, net, -7.62, 0)

    # ── 3. U1 & U2 (2x CD74HC4067M 16-Ch Multiplexers) ───────────────────────
    sb.add_text_box("2. DUAL 16-CH MULTIPLEXERS (U1: 16 ANALOG POTS/FADERS, U2: 16 PERFORMANCE PADS)", 203.20, 15.24)
    mux_lib = "74xx:CD74HC4067M"
    u1_x, u1_y = 223.52, 60.96
    u2_x, u2_y = 284.48, 60.96
    sb.add_symbol(mux_lib, "U1", "CD74HC4067M", "Package_SO:SOIC-24W_7.5x15.4mm_P1.27mm", u1_x, u1_y)
    sb.add_symbol(mux_lib, "U2", "CD74HC4067M", "Package_SO:SOIC-24W_7.5x15.4mm_P1.27mm", u2_x, u2_y)

    mux_ch_pins = [
        ("9", 0), ("8", 1), ("7", 2), ("6", 3), ("5", 4), ("4", 5), ("3", 6), ("2", 7),
        ("23", 8), ("22", 9), ("21", 10), ("20", 11), ("19", 12), ("18", 13), ("17", 14), ("16", 15),
    ]

    for ux, uy, com_net, ch_prefix in [(u1_x, u1_y, "MUX1_COM", "POT_CH"), (u2_x, u2_y, "MUX2_COM", "PAD_CH")]:
        sb.connect_pin_to_net(mux_lib, ux, uy, "1", com_net, -7.62, 0)
        sb.connect_pin_to_net(mux_lib, ux, uy, "10", "MUX_S0", -7.62, 0)
        sb.connect_pin_to_net(mux_lib, ux, uy, "11", "MUX_S1", -7.62, 0)
        sb.connect_pin_to_net(mux_lib, ux, uy, "14", "MUX_S2", -7.62, 0)
        sb.connect_pin_to_net(mux_lib, ux, uy, "13", "MUX_S3", -7.62, 0)
        sb.connect_pin_to_net(mux_lib, ux, uy, "15", "GND", -7.62, 0)   # ~{E} active low tied to GND
        sb.connect_pin_to_net(mux_lib, ux, uy, "24", "+5V", 0, -5.08)   # VCC
        sb.connect_pin_to_net(mux_lib, ux, uy, "12", "GND", 0, 5.08)    # GND
        for pnum, ch_idx in mux_ch_pins:
            sb.connect_pin_to_net(mux_lib, ux, uy, pnum, f"{ch_prefix}{ch_idx}", 7.62, 0)

    # ── 4. Analog Section: 16 Potentiometers & Slide Faders (RV1..RV16) ──────
    sb.add_text_box("3. ANALOG MIXER, EQ, CFX & PITCH FADERS (11x ROTARY B10K + 5x SLIDE FADERS B10K)", 20.32, 106.68)
    pot_lib = "Device:R_Potentiometer"
    pot_names = [
        ("RV1", "10k_CH1_TRIM", False),
        ("RV2", "10k_CH1_EQ_HI", False),
        ("RV3", "10k_CH1_EQ_MID", False),
        ("RV4", "10k_CH1_EQ_LOW", False),
        ("RV5", "10k_CH1_CFX", False),
        ("RV6", "10k_CH2_TRIM", False),
        ("RV7", "10k_CH2_EQ_HI", False),
        ("RV8", "10k_CH2_EQ_MID", False),
        ("RV9", "10k_CH2_EQ_LOW", False),
        ("RV10", "10k_CH2_CFX", False),
        ("RV11", "10k_CH1_VOL_FADER", True),
        ("RV12", "10k_CH2_VOL_FADER", True),
        ("RV13", "10k_CROSSFADER", True),
        ("RV14", "10k_DECKA_PITCH", True),
        ("RV15", "10k_DECKB_PITCH", True),
        ("RV16", "10k_MASTER_FX", False),
    ]
    for idx, (ref, val, is_slide) in enumerate(pot_names):
        col = idx % 8
        row = idx // 8
        px = 25.40 + col * 25.40
        py = 127.00 + row * 30.48
        fp = (
            "Potentiometer_THT:Potentiometer_Bourns_PTA4543_Single_Slide"
            if is_slide
            else "Potentiometer_THT:Potentiometer_Alps_RK09K_Single_Vertical"
        )
        sb.add_symbol(pot_lib, ref, val, fp, px, py)
        sb.connect_pin_to_net(pot_lib, px, py, "1", "+5V", 0, -3.81)
        sb.connect_pin_to_net(pot_lib, px, py, "2", f"POT_CH{idx}", 5.08, 0)
        sb.connect_pin_to_net(pot_lib, px, py, "3", "GND", 0, 3.81)

    # ── 5. Performance Pads: 16 Tactile Switches 12x12mm (SW1..SW16) ─────────
    sb.add_text_box("4. PERFORMANCE PADS 2x8 (16x TACTILE 12x12mm G82 -> U2 CD74HC4067M)", 233.68, 106.68)
    sw_lib = "Switch:SW_Push"
    sw_fp = "Button_Switch_THT:SW_PUSH-12mm"
    for idx in range(16):
        col = idx % 4
        row = idx // 4
        sx = 243.84 + col * 25.40
        sy = 121.92 + row * 15.24
        deck = "A" if idx < 8 else "B"
        pad_num = (idx % 8) + 1
        ref = f"SW{idx + 1}"
        val = f"PAD_{deck}{pad_num}"
        sb.add_symbol(sw_lib, ref, val, sw_fp, sx, sy)
        sb.connect_pin_to_net(sw_lib, sx, sy, "1", f"PAD_CH{idx}", -5.08, 0)
        sb.connect_pin_to_net(sw_lib, sx, sy, "2", "GND", 5.08, 0)

    # ── 6. 4x4 Diode-Isolated Transport/Mixer Matrix (SW17..SW30 + ENC1/2 SW)
    sb.add_text_box("5. 4x4 DIODE-ISOLATED TRANSPORT & MIXER MATRIX (14x 12x12mm SW + 2x JOG PUSH + 16x 1N4148)", 20.32, 185.42)
    d_lib = "Device:D"
    d_fp = "Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal"
    matrix_sw_names = [
        ("SW17", "LOAD_A", 0, 0),
        ("SW18", "LOAD_B", 0, 1),
        ("SW19", "SMART_CFX", 0, 2),
        ("SW20", "BEAT_FX", 0, 3),
        ("SW21", "CUE_CH1", 1, 0),
        ("SW22", "CUE_CH2", 1, 1),
        ("SW23", "LOOP_A", 1, 2),
        ("SW24", "SYNC_A", 1, 3),
        ("SW25", "CUE_A", 2, 0),
        ("SW26", "PLAY_A", 2, 1),
        ("SW27", "LOOP_B", 2, 2),
        ("SW28", "SYNC_B", 2, 3),
        ("SW29", "CUE_B", 3, 0),
        ("SW30", "PLAY_B", 3, 1),
    ]
    for idx, (ref, val, r, c) in enumerate(matrix_sw_names):
        sx = 25.40 + c * 45.72
        sy = 200.66 + r * 17.78
        mid_net = f"MAT_N_{r}_{c}"
        sb.add_symbol(sw_lib, ref, val, sw_fp, sx, sy)
        sb.connect_pin_to_net(sw_lib, sx, sy, "1", f"COL{c}", -5.08, 0)
        sb.connect_pin_to_net(sw_lib, sx, sy, "2", mid_net, 5.08, 0)

        dx = sx + 20.32
        dy = sy
        d_ref = f"D{idx + 1}"
        sb.add_symbol(d_lib, d_ref, "1N4148", d_fp, dx, dy)
        # Device:D pin 2 is Anode (A), pin 1 is Cathode (K -> ROW)
        sb.connect_pin_to_net(d_lib, dx, dy, "2", mid_net, 5.08, 0)
        sb.connect_pin_to_net(d_lib, dx, dy, "1", f"ROW{r}", -5.08, 0)

    # ── 7. Dual Jog Wheel Rotary Encoders EC11 (ENC1 & ENC2 + D15/D16 Matrix)
    sb.add_text_box("6. JOG WHEEL QUADRATURE ENCODERS (2x EC11 WITH PUSH SWITCH & RC DEBOUNCE)", 218.44, 185.42)
    enc_lib = "Device:RotaryEncoder_Switch"
    enc_fp = "Rotary_Encoder:RotaryEncoder_Alps_EC11E-Switch_Vertical_H20mm"
    enc_configs = [
        ("ENC1", "JOG_DECK_A_EC11", 233.68, 205.74, "ENC1_A", "ENC1_B", 3, 2, "D15"),
        ("ENC2", "JOG_DECK_B_EC11", 233.68, 236.22, "ENC2_A", "ENC2_B", 3, 3, "D16"),
    ]
    for ref, val, ex, ey, net_a, net_b, mr, mc, d_ref in enc_configs:
        mid_net = f"MAT_N_{mr}_{mc}"
        sb.add_symbol(enc_lib, ref, val, enc_fp, ex, ey)
        sb.connect_pin_to_net(enc_lib, ex, ey, "A", net_a, -5.08, 0)
        sb.connect_pin_to_net(enc_lib, ex, ey, "C", "GND", -5.08, 0)
        sb.connect_pin_to_net(enc_lib, ex, ey, "B", net_b, -5.08, 0)
        sb.connect_pin_to_net(enc_lib, ex, ey, "S1", f"COL{mc}", 5.08, 0)
        sb.connect_pin_to_net(enc_lib, ex, ey, "S2", mid_net, 5.08, 0)

        dx, dy = ex + 30.48, ey
        sb.add_symbol(d_lib, d_ref, "1N4148", d_fp, dx, dy)
        sb.connect_pin_to_net(d_lib, dx, dy, "2", mid_net, 5.08, 0)
        sb.connect_pin_to_net(d_lib, dx, dy, "1", f"ROW{mr}", -5.08, 0)

    # ── 8. Passives: RC Filter, Pull-Ups, Decoupling Caps, Status LEDs, M3 Holes
    sb.add_text_box("7. CONDITIONING PASSIVES, DECOUPLING, STATUS LEDS & M3 CHASSIS GROUND", 284.48, 185.42)
    r_lib = "Device:R"
    r_fp = "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal"
    c_lib = "Device:C"
    c_fp = "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm"
    led_lib = "Device:LED"
    led_fp = "LED_THT:LED_D5.0mm"

    # R1 (100R series anti-aliasing filter between MUX1_COM and MUX1_ADC)
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
    for idx, (ref, val, net1, net2) in enumerate(resistors):
        rx = 289.56 + (idx % 5) * 17.78
        ry = 200.66 + (idx // 5) * 22.86
        sb.add_symbol(r_lib, ref, val, r_fp, rx, ry)
        sb.connect_pin_to_net(r_lib, rx, ry, "1", net1, 0, -3.81)
        sb.connect_pin_to_net(r_lib, rx, ry, "2", net2, 0, 3.81)

    # Capacitors: C1 (U1 100nF), C2 (U2 100nF), C3 (ADC RC 100nF), C4..C7 (Encoder debounce 10nF)
    capacitors = [
        ("C1", "100nF_U1_DEC", "+5V", "GND"),
        ("C2", "100nF_U2_DEC", "+5V", "GND"),
        ("C3", "100nF_ADC_FILT", "MUX1_ADC", "GND"),
        ("C4", "10nF_ENC1A", "ENC1_A", "GND"),
        ("C5", "10nF_ENC1B", "ENC1_B", "GND"),
        ("C6", "10nF_ENC2A", "ENC2_A", "GND"),
        ("C7", "10nF_ENC2B", "ENC2_B", "GND"),
    ]
    for idx, (ref, val, net1, net2) in enumerate(capacitors):
        cx = 381.00 + (idx % 4) * 17.78
        cy = 200.66 + (idx // 4) * 22.86
        sb.add_symbol(c_lib, ref, val, c_fp, cx, cy)
        sb.connect_pin_to_net(c_lib, cx, cy, "1", net1, 0, -3.81)
        sb.connect_pin_to_net(c_lib, cx, cy, "2", net2, 0, 3.81)

    # Status LEDs: D17 (Power), D18 (Deck A), D19 (Deck B)
    leds = [
        ("D17", "LED_PWR_GREEN", "LED_PWR_A"),
        ("D18", "LED_DECKA_BLUE", "LED_DECKA_A"),
        ("D19", "LED_DECKB_RED", "LED_DECKB_A"),
    ]
    for idx, (ref, val, anode_net) in enumerate(leds):
        lx = 381.00 + idx * 22.86
        ly = 248.92
        sb.add_symbol(led_lib, ref, val, led_fp, lx, ly)
        # Device:LED pin 2 is Anode (A), pin 1 is Cathode (K)
        sb.connect_pin_to_net(led_lib, lx, ly, "2", anode_net, 5.08, 0)
        sb.connect_pin_to_net(led_lib, lx, ly, "1", "GND", -5.08, 0)

    # 8x M3 Mounting Holes tied to Chassis/Signal GND
    mh_lib = "Mechanical:MountingHole_Pad"
    mh_fp = "MountingHole:MountingHole_3.2mm_M3_Pad"
    for idx in range(8):
        hx = 289.56 + idx * 12.70
        hy = 266.70
        ref = f"H{idx + 1}"
        sb.add_symbol(mh_lib, ref, "M3_Mount_GND", mh_fp, hx, hy)
        sb.connect_pin_to_net(mh_lib, hx, hy, "1", "GND", 0, 3.81)

    lib_symbols_str = "\n".join(LIB_BLOCKS)
    symbols_str = "\n".join(sb.symbols)
    wires_str = "\n".join(sb.wires)
    labels_str = "\n".join(sb.labels)
    ncs_str = "\n".join(sb.no_connects)
    texts_str = "\n".join(sb.texts)

    sch_content = f"""(kicad_sch
\t(version 20250114)
\t(generator "eeschema")
\t(generator_version "9.0")
\t(uuid "{ROOT_UUID}")
\t(paper "A2")
\t(title_block
\t\t(title "Pioneer DDJ-FLX4 Inspired 2-Deck USB-MIDI DJ Controller")
\t\t(date "2026-11-21")
\t\t(rev "v2.0-Argon")
\t\t(company "Joao Paulo Ferreira - Club AI / UFSCar")
\t\t(comment 1 "MCU: ATmega32U4 Dual-Footprint (Arduino Leonardo R3 + Pro Micro USB-C)")
\t\t(comment 2 "Analog: 16x B10K Pots/Faders via U1 (CD74HC4067M) + RC Anti-Jitter Filter")
\t\t(comment 3 "Digital: 16x Performance Pads via U2 (CD74HC4067M) + 4x4 Diode Matrix + 2x EC11 Jog Wheels")
\t)
\t(lib_symbols
{lib_symbols_str}
\t)
{texts_str}
{ncs_str}
{wires_str}
{labels_str}
{symbols_str}
\t(sheet_instances
\t\t(path "/"
\t\t\t(page "1")
\t\t)
\t)
\t(embedded_fonts no)
)
"""
    out_sch = os.path.join(OUT_DIR, "ddj_flx4_controller.kicad_sch")
    with open(out_sch, "w", encoding="utf-8") as f:
        f.write(sch_content)

    # Also write .kicad_pro
    pro_data = {
        "board": {
            "design_settings": {
                "defaults": {
                    "board_outline_line_width": 0.15,
                    "copper_line_width": 0.25,
                    "copper_text_size_h": 1.5,
                    "copper_text_size_v": 1.5,
                    "copper_text_thickness": 0.3
                },
                "rules": {
                    "min_clearance": 0.2,
                    "min_track_width": 0.2,
                    "min_via_annular_width": 0.15,
                    "min_via_diameter": 0.6
                }
            }
        },
        "meta": {
            "filename": "ddj_flx4_controller.kicad_pro",
            "version": 1
        },
        "schematic": {
            "meta": {
                "version": 1
            }
        }
    }
    out_pro = os.path.join(OUT_DIR, "ddj_flx4_controller.kicad_pro")
    with open(out_pro, "w", encoding="utf-8") as f:
        json.dump(pro_data, f, indent=2)

    # Sync to user's OneDrive "Projeto Mesa" folder as well
    if os.path.exists(ONE_DRIVE_DIR):
        with open(os.path.join(ONE_DRIVE_DIR, "Projeto Mesa.kicad_sch"), "w", encoding="utf-8") as f:
            f.write(sch_content)

    print(f"SUCCESS: Generated {out_sch} ({len(sch_content)} bytes, {len(sb.symbols)} symbols)")

if __name__ == "__main__":
    build()
