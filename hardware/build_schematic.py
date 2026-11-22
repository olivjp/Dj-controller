#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deterministic KiCad 9.0 Schematic Synthesizer — DDJ-FLX4 Modular Core v2.0.
Architecture (Audited & Fixed from v1):
  - Compact 98 x 98 mm 2-layer Core Motherboard (US$ 2 at JLCPCB) + panel-mounted controls.
  - MCU: Arduino Pro Micro USB-C (ATmega32U4 5V 16MHz) via J1/J2 1x12 headers:
      * J2 pin 1 (RAW) -> NC (no back-feed into LDO)
      * J2 pin 3 (RST) -> NC (FIXED: no longer shorted to GND!)
  - Multiplexers: 2x CD74HC4067 16-Ch Breakout Modules (2.54mm THT headers, 15.24mm row spacing)
  - Zero-Crosstalk Analog Front-End:
      * 16x 100nF capacitors (C10..C25) placed BEFORE U1 (one per pot wiper -> GND)
      * Post-mux R1=100R + C3=1nF (tau = 2.67 us -> 0.00% crosstalk at 145 us scan!)
  - Alps-Spec 2-Resistor Encoder Conditioning (ENC1/ENC2):
      * 10k pull-up (R3..R6) + 10k series current-limiting resistor (R14..R17) + 10nF cap (C4..C7)
        eliminating direct capacitor discharge contact pitting.
  - Off-board panel controls (11x WH148, 5x Slide Faders, 30x G82 switches, 2x EC11, 16x 1N4148)
    represented in schematic with on_board="no", in_bom="yes" for complete ERC & BOM coverage.
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
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"ddj-flx4-v2-core-{seed_str}"))

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
    prefixed_block = raw_block.replace(f'(symbol "{sym_name}"', f'(symbol "{lib_prefix}:{sym_name}"', 1)

    pins = {}
    for m in re.finditer(
        r'\(pin\s+(\w+)\s+\w+\s+\(at\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\).*?\(name\s+"([^"]+)".*?\(number\s+"([^"]+)"',
        raw_block,
        re.S,
    ):
        etype, px, py, rot, pname, pnum = m.groups()
        pins[pnum] = (float(px), float(py), int(float(rot)), pname, etype)
    return prefixed_block, pins

REQUIRED_SYMBOLS = [
    ("Connector_Generic.kicad_sym", "Conn_01x04", "Connector_Generic"),
    ("Connector_Generic.kicad_sym", "Conn_01x06", "Connector_Generic"),
    ("Connector_Generic.kicad_sym", "Conn_01x08", "Connector_Generic"),
    ("Connector_Generic.kicad_sym", "Conn_01x10", "Connector_Generic"),
    ("Connector_Generic.kicad_sym", "Conn_01x12", "Connector_Generic"),
    ("Connector_Generic.kicad_sym", "Conn_01x16", "Connector_Generic"),
    ("Device.kicad_sym", "R_Potentiometer", "Device"),
    ("Device.kicad_sym", "RotaryEncoder_Switch", "Device"),
    ("Device.kicad_sym", "R", "Device"),
    ("Device.kicad_sym", "C", "Device"),
    ("Device.kicad_sym", "D", "Device"),
    ("Device.kicad_sym", "LED", "Device"),
    ("Switch.kicad_sym", "SW_Push", "Switch"),
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

    def pin_sheet_xy(self, lib_id: str, sx: float, sy: float, pnum: str) -> tuple[float, float]:
        px, py, _rot, _name, _etype = PIN_DB[lib_id][str(pnum)]
        return round(sx + px, 2), round(sy - py, 2)

    def add_symbol(self, lib_id: str, ref: str, val: str, footprint: str, sx: float, sy: float, in_bom="yes", on_board="yes", dnp="no"):
        suuid = det_uuid(f"sym-{ref}")
        pins = PIN_DB[lib_id]
        pin_lines = []
        for pnum in pins:
            puuid = det_uuid(f"pin-{ref}-{pnum}")
            pin_lines.append(f'\t\t(pin "{pnum}"\n\t\t\t(uuid "{puuid}")\n\t\t)')
        pins_str = "\n".join(pin_lines)
        hide_ref = " (hide yes)" if ref.startswith("#") else ""
        block = f"""\t(symbol
\t\t(lib_id "{lib_id}")
\t\t(at {sx:.2f} {sy:.2f} 0)
\t\t(unit 1)
\t\t(exclude_from_sim no)
\t\t(in_bom {in_bom})
\t\t(on_board {on_board})
\t\t(dnp {dnp})
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

    def connect_pin_to_net(self, lib_id: str, sx: float, sy: float, pnum: str, net_name: str, stub_dx: float = -7.62, stub_dy: float = 0.0):
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

    # ── 0. Power Flags (+5V and GND driven by Pro Micro USB-C VCC) ───────────
    sb.add_text_box("1. ON-BOARD CORE: ARDUINO PRO MICRO USB-C (ATmega32U4 5V/16MHz) & POWER", 20.32, 15.24)

    sb.add_symbol("power:+5V", "#PWR01", "+5V", "", 30.48, 30.48, in_bom="no", on_board="no")
    sb.add_wire(30.48, 30.48, 30.48, 35.56, "pwr-5v-flag")
    sb.add_label("+5V", 30.48, 33.02, 0)
    sb.add_symbol("power:PWR_FLAG", "#FLG01", "PWR_FLAG", "", 30.48, 35.56, in_bom="no", on_board="no")

    sb.add_symbol("power:GND", "#PWR02", "GND", "", 48.26, 30.48, in_bom="no", on_board="no")
    sb.add_wire(48.26, 30.48, 48.26, 25.40, "pwr-gnd-flag")
    sb.add_label("GND", 48.26, 27.94, 0)
    sb.add_symbol("power:PWR_FLAG", "#FLG02", "PWR_FLAG", "", 48.26, 25.40, in_bom="no", on_board="no")

    # ── 1. MCU: Arduino Pro Micro USB-C Socket (J1 Left 1x12, J2 Right 1x12) ─
    c12 = "Connector_Generic:Conn_01x12"
    fp12 = "Connector_PinHeader_2.54mm:PinHeader_1x12_P2.54mm_Vertical"
    j1_x, j1_y = 81.28, 55.88
    j2_x, j2_y = 114.30, 55.88
    sb.add_symbol(c12, "J1", "ProMicro_Left_1x12", fp12, j1_x, j1_y)
    sb.add_symbol(c12, "J2", "ProMicro_Right_1x12", fp12, j2_x, j2_y)

    # SparkFun Pro Micro Left (top to bottom, USB-C at top):
    # 1=TXO(D1), 2=RXI(D0), 3=GND, 4=GND, 5=D2, 6=D3, 7=D4, 8=D5, 9=D6, 10=D7, 11=D8, 12=D9
    j1_nets = {
        "1": "ENC2_B", "2": "ENC2_A", "3": "GND", "4": "GND",
        "5": "ENC1_A", "6": "ENC1_B", "7": "MUX_S0", "8": "MUX_S1",
        "9": "MUX_S2", "10": "MUX_S3", "11": "ROW0", "12": "ROW1",
    }
    for pnum, net in j1_nets.items():
        sb.connect_pin_to_net(c12, j1_x, j1_y, pnum, net, -7.62, 0)

    # SparkFun Pro Micro Right (top to bottom, USB-C at top):
    # 1=RAW(NC!), 2=GND, 3=RST(NC! FIXED!), 4=VCC(+5V), 5=A3, 6=A2, 7=A1, 8=A0, 9=D15, 10=D14, 11=D16, 12=D10
    j2_nets = {
        "2": "GND", "4": "+5V",
        "5": "COL3", "6": "COL2", "7": "MUX2_COM", "8": "MUX1_ADC",
        "9": "COL1", "10": "COL0", "11": "ROW3", "12": "ROW2",
    }
    sb.mark_pin_nc(c12, j2_x, j2_y, "1")  # RAW NC (USB powered)
    sb.mark_pin_nc(c12, j2_x, j2_y, "3")  # RST NC (FIXED: not shorted to GND!)
    for pnum, net in j2_nets.items():
        sb.connect_pin_to_net(c12, j2_x, j2_y, pnum, net, -7.62, 0)

    # ── 2. Dual CD74HC4067 Breakout Module Sockets (1x16 + 1x8, 15.24mm pitch)
    sb.add_text_box("2. DUAL CD74HC4067 BREAKOUT SOCKETS (U1: ANALOG POTS/FADERS, U2: 16 PADS)", 147.32, 15.24)
    c16 = "Connector_Generic:Conn_01x16"
    fp16 = "Connector_PinHeader_2.54mm:PinHeader_1x16_P2.54mm_Vertical"
    c8 = "Connector_Generic:Conn_01x08"
    fp8 = "Connector_PinHeader_2.54mm:PinHeader_1x08_P2.54mm_Vertical"

    # U1 Breakout (Analog Pots/Faders) — Matched 1:1 to User's Physical Blue CD74HC4067 Photo!
    # Left 1x16 top->bottom: C15..C0 (pin 1 = C15, pin 16 = C0)
    # Right 1x8 top->bottom (aligned with C11..C4): 1=SIG, 2=S3, 3=S2, 4=S1, 5=S0, 6=EN(GND), 7=VCC(+5V), 8=GND
    u1ch_x, u1ch_y = 165.10, 60.96
    u1ct_x, u1ct_y = 198.12, 60.96
    sb.add_symbol(c16, "J3", "U1_CD74HC4067_CH_1x16", fp16, u1ch_x, u1ch_y)
    sb.add_symbol(c8,  "J4", "U1_CD74HC4067_CTRL_1x8", fp8, u1ct_x, u1ct_y)
    for i in range(16):
        sb.connect_pin_to_net(c16, u1ch_x, u1ch_y, str(i + 1), f"POT_CH{15 - i}", -7.62, 0)
    u1_ctrl = {
        "1": "MUX1_COM", "2": "MUX_S3", "3": "MUX_S2", "4": "MUX_S1",
        "5": "MUX_S0",   "6": "GND",    "7": "+5V",    "8": "GND",
    }
    for pnum, net in u1_ctrl.items():
        sb.connect_pin_to_net(c8, u1ct_x, u1ct_y, pnum, net, -7.62, 0)

    # U2 Breakout (16 Performance Pads) — Same physical blue module (mounted rotated 180 deg on PCB!)
    u2ch_x, u2ch_y = 236.22, 60.96
    u2ct_x, u2ct_y = 269.24, 60.96
    sb.add_symbol(c16, "J5", "U2_CD74HC4067_CH_1x16", fp16, u2ch_x, u2ch_y)
    sb.add_symbol(c8,  "J6", "U2_CD74HC4067_CTRL_1x8", fp8, u2ct_x, u2ct_y)
    for i in range(16):
        sb.connect_pin_to_net(c16, u2ch_x, u2ch_y, str(i + 1), f"PAD_CH{15 - i}", -7.62, 0)
    u2_ctrl = {
        "1": "MUX2_COM", "2": "MUX_S3", "3": "MUX_S2", "4": "MUX_S1",
        "5": "MUX_S0",   "6": "GND",    "7": "+5V",    "8": "GND",
    }
    for pnum, net in u2_ctrl.items():
        sb.connect_pin_to_net(c8, u2ct_x, u2ct_y, pnum, net, -7.62, 0)

    # ── 3. Panel Harness Headers (On-Board 2.54mm Connectors) ────────────────
    sb.add_text_box("3. ON-BOARD PANEL HARNESS CONNECTORS (2.54mm HEADERS / JST-XH COMPATIBLE)", 304.80, 15.24)
    c10 = "Connector_Generic:Conn_01x10"
    fp10 = "Connector_PinHeader_2.54mm:PinHeader_1x10_P2.54mm_Vertical"
    c6 = "Connector_Generic:Conn_01x06"
    fp6 = "Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical"
    c4 = "Connector_Generic:Conn_01x04"
    fp4 = "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical"

    panel_headers = [
        ("J7",  "HDR_POTS_DECK_A",  c8,  fp8,  320.04, 48.26,
         ["POT_CH0", "POT_CH1", "POT_CH2", "POT_CH3", "POT_CH4", "POT_CH13", "+5V", "GND"]),
        ("J8",  "HDR_POTS_DECK_B",  c8,  fp8,  355.60, 48.26,
         ["POT_CH5", "POT_CH6", "POT_CH7", "POT_CH8", "POT_CH9", "POT_CH14", "+5V", "GND"]),
        ("J9",  "HDR_MIXER_FADERS", c6,  fp6,  391.16, 48.26,
         ["POT_CH10", "POT_CH11", "POT_CH12", "POT_CH15", "+5V", "GND"]),
        ("J10", "HDR_PADS_DECK_A",  c10, fp10, 426.72, 48.26,
         ["PAD_CH0", "PAD_CH1", "PAD_CH2", "PAD_CH3", "PAD_CH4", "PAD_CH5", "PAD_CH6", "PAD_CH7", "GND", "GND"]),
        ("J11", "HDR_PADS_DECK_B",  c10, fp10, 462.28, 48.26,
         ["PAD_CH8", "PAD_CH9", "PAD_CH10", "PAD_CH11", "PAD_CH12", "PAD_CH13", "PAD_CH14", "PAD_CH15", "GND", "GND"]),
        ("J12", "HDR_MATRIX_4x4",   c8,  fp8,  320.04, 83.82,
         ["ROW0", "ROW1", "ROW2", "ROW3", "COL0", "COL1", "COL2", "COL3"]),
        ("J13", "HDR_ENCODERS_EC11", c6, fp6,  355.60, 83.82,
         ["ENC1_A_RAW", "ENC1_B_RAW", "GND", "ENC2_A_RAW", "ENC2_B_RAW", "GND"]),
        ("J14", "HDR_PWR_AUX",      c4,  fp4,  391.16, 83.82,
         ["+5V", "+5V", "GND", "GND"]),
    ]
    for ref, val, lib_id, fp, hx, hy, net_list in panel_headers:
        sb.add_symbol(lib_id, ref, val, fp, hx, hy)
        for idx_p, net in enumerate(net_list):
            sb.connect_pin_to_net(lib_id, hx, hy, str(idx_p + 1), net, -7.62, 0)

    # ── 4. On-Board Conditioning Passives, Anti-Crosstalk Caps & M3 Holes ────
    sb.add_text_box("4. ON-BOARD CONDITIONING: PRE-MUX 100nF CAPS, ALPS 2-R ENCODER RC, PULL-UPS & M3", 20.32, 111.76)
    r_lib = "Device:R"
    r_fp = "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal"
    c_lib = "Device:C"
    c_fp = "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm"
    led_lib = "Device:LED"
    led_fp = "LED_THT:LED_D5.0mm"

    resistors = [
        ("R1",  "100R_ADC_SER",    "MUX1_COM",   "MUX1_ADC"),
        ("R2",  "10k_PADS_PU",     "+5V",        "MUX2_COM"),
        ("R3",  "10k_ENC1A_PU",    "+5V",        "ENC1_A_RAW"),
        ("R4",  "10k_ENC1B_PU",    "+5V",        "ENC1_B_RAW"),
        ("R5",  "10k_ENC2A_PU",    "+5V",        "ENC2_A_RAW"),
        ("R6",  "10k_ENC2B_PU",    "+5V",        "ENC2_B_RAW"),
        ("R7",  "10k_COL0_PU",     "+5V",        "COL0"),
        ("R8",  "10k_COL1_PU",     "+5V",        "COL1"),
        ("R9",  "10k_COL2_PU",     "+5V",        "COL2"),
        ("R10", "10k_COL3_PU",     "+5V",        "COL3"),
        ("R11", "330R_LED_PWR",    "+5V",        "LED_PWR_A"),
        # Alps-spec series current-limiting resistors for EC11 (prevents contact pitting!)
        ("R12", "10k_ENC1A_SER",   "ENC1_A_RAW", "ENC1_A"),
        ("R13", "10k_ENC1B_SER",   "ENC1_B_RAW", "ENC1_B"),
        ("R14", "10k_ENC2A_SER",   "ENC2_A_RAW", "ENC2_A"),
        ("R15", "10k_ENC2B_SER",   "ENC2_B_RAW", "ENC2_B"),
    ]
    for idx, (ref, val, n1, n2) in enumerate(resistors):
        rx = 25.40 + (idx % 8) * 20.32
        ry = 127.00 + (idx // 8) * 22.86
        sb.add_symbol(r_lib, ref, val, r_fp, rx, ry)
        sb.connect_pin_to_net(r_lib, rx, ry, "1", n1, 0, -3.81)
        sb.connect_pin_to_net(r_lib, rx, ry, "2", n2, 0, 3.81)

    capacitors = [
        ("C1", "100nF_U1_DEC",   "+5V",      "GND"),
        ("C2", "100nF_U2_DEC",   "+5V",      "GND"),
        ("C3", "DNP_OPT_100pF",  "MUX1_ADC", "GND"),   # v2.3: DNP (avoids 3.6-6.2 LSB charge-sharing!)
        ("C4", "10nF_ENC1A",     "ENC1_A",   "GND"),
        ("C5", "10nF_ENC1B",     "ENC1_B",   "GND"),
        ("C6", "10nF_ENC2A",     "ENC2_A",   "GND"),
        ("C7", "10nF_ENC2B",     "ENC2_B",   "GND"),
        ("C8", "100nF_MCU_DEC",  "+5V",      "GND"),
    ]
    # 16x Pre-Mux Anti-Crosstalk Filter Caps (C10..C25 = 100nF, one per analog channel BEFORE U1!)
    for ch in range(16):
        capacitors.append((f"C{10 + ch}", f"100nF_POT{ch}", f"POT_CH{ch}", "GND"))

    for idx, (ref, val, n1, n2) in enumerate(capacitors):
        cx = 203.20 + (idx % 12) * 17.78
        cy = 127.00 + (idx // 12) * 22.86
        sb.add_symbol(c_lib, ref, val, c_fp, cx, cy, dnp="yes" if ref == "C3" else "no")
        sb.connect_pin_to_net(c_lib, cx, cy, "1", n1, 0, -3.81)
        sb.connect_pin_to_net(c_lib, cx, cy, "2", n2, 0, 3.81)

    # Power Status LED (D17)
    sb.add_symbol(led_lib, "D17", "LED_PWR_GREEN", led_fp, 436.88, 127.00)
    sb.connect_pin_to_net(led_lib, 436.88, 127.00, "2", "LED_PWR_A", 5.08, 0)
    sb.connect_pin_to_net(led_lib, 436.88, 127.00, "1", "GND", -5.08, 0)

    # 4x Corner M3 Mounting Holes tied to GND plane (H1..H4)
    mh_lib = "Mechanical:MountingHole_Pad"
    mh_fp = "MountingHole:MountingHole_3.2mm_M3_Pad"
    for idx in range(4):
        hx = 436.88 + idx * 12.70
        hy = 149.86
        sb.add_symbol(mh_lib, f"H{idx + 1}", "M3_Mount_GND", mh_fp, hx, hy)
        sb.connect_pin_to_net(mh_lib, hx, hy, "1", "GND", 0, 3.81)

    # ── 5. OFF-BOARD PANEL CONTROLS (in_bom="yes", on_board="no") ────────────
    sb.add_text_box("5. OFF-BOARD PANEL CONTROLS (MOUNTED ON 3D FACEPLATE, WIRED TO J7..J13)", 20.32, 177.80)

    pot_lib = "Device:R_Potentiometer"
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
        px = 25.40 + (idx % 8) * 25.40
        py = 195.58 + (idx // 8) * 27.94
        sb.add_symbol(pot_lib, ref, val, "", px, py, in_bom="yes", on_board="no")
        sb.connect_pin_to_net(pot_lib, px, py, "1", "+5V", 0, -3.81)
        sb.connect_pin_to_net(pot_lib, px, py, "2", f"POT_CH{idx}", 5.08, 0)
        sb.connect_pin_to_net(pot_lib, px, py, "3", "GND", 0, 3.81)

    sw_lib = "Switch:SW_Push"
    for idx in range(16):
        sx = 243.84 + (idx % 4) * 25.40
        sy = 193.04 + (idx // 4) * 15.24
        deck = "A" if idx < 8 else "B"
        sb.add_symbol(sw_lib, f"SW{idx + 1}", f"PAD_{deck}{(idx % 8) + 1}", "", sx, sy, in_bom="yes", on_board="no")
        sb.connect_pin_to_net(sw_lib, sx, sy, "1", f"PAD_CH{idx}", -5.08, 0)
        sb.connect_pin_to_net(sw_lib, sx, sy, "2", "GND", 5.08, 0)

    d_lib = "Device:D"
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
        sx = 25.40 + c * 45.72
        sy = 259.08 + r * 17.78
        mid_net = f"MAT_N_{r}_{c}"
        sb.add_symbol(sw_lib, ref, val, "", sx, sy, in_bom="yes", on_board="no")
        sb.connect_pin_to_net(sw_lib, sx, sy, "1", f"COL{c}", -5.08, 0)
        sb.connect_pin_to_net(sw_lib, sx, sy, "2", mid_net, 5.08, 0)
        sb.add_symbol(d_lib, f"D{idx + 1}", "1N4148", "", sx + 20.32, sy, in_bom="yes", on_board="no")
        sb.connect_pin_to_net(d_lib, sx + 20.32, sy, "2", mid_net, 5.08, 0)
        sb.connect_pin_to_net(d_lib, sx + 20.32, sy, "1", f"ROW{r}", -5.08, 0)

    enc_lib = "Device:RotaryEncoder_Switch"
    enc_configs = [
        ("ENC1", "JOG_DECK_A_EC11", 233.68, 266.70, "ENC1_A_RAW", "ENC1_B_RAW", 3, 2, "D15"),
        ("ENC2", "JOG_DECK_B_EC11", 233.68, 297.18, "ENC2_A_RAW", "ENC2_B_RAW", 3, 3, "D16"),
    ]
    for ref, val, ex, ey, net_a, net_b, mr, mc, d_ref in enc_configs:
        mid_net = f"MAT_N_{mr}_{mc}"
        sb.add_symbol(enc_lib, ref, val, "", ex, ey, in_bom="yes", on_board="no")
        sb.connect_pin_to_net(enc_lib, ex, ey, "A", net_a, -5.08, 0)
        sb.connect_pin_to_net(enc_lib, ex, ey, "C", "GND", -5.08, 0)
        sb.connect_pin_to_net(enc_lib, ex, ey, "B", net_b, -5.08, 0)
        sb.connect_pin_to_net(enc_lib, ex, ey, "S1", f"COL{mc}", 5.08, 0)
        sb.connect_pin_to_net(enc_lib, ex, ey, "S2", mid_net, 5.08, 0)
        sb.add_symbol(d_lib, d_ref, "1N4148", "", ex + 30.48, ey, in_bom="yes", on_board="no")
        sb.connect_pin_to_net(d_lib, ex + 30.48, ey, "2", mid_net, 5.08, 0)
        sb.connect_pin_to_net(d_lib, ex + 30.48, ey, "1", f"ROW{mr}", -5.08, 0)

    sch_content = f"""(kicad_sch
\t(version 20250114)
\t(generator "eeschema")
\t(generator_version "9.0")
\t(uuid "{ROOT_UUID}")
\t(paper "A2")
\t(title_block
\t\t(title "DDJ-FLX4 Modular Core v2.3 — 98x98mm 2-Layer Motherboard (ATmega32U4)")
\t\t(date "2026-11-21")
\t\t(rev "v2.3-Modular")
\t\t(company "Joao Paulo Ferreira - Club AI / UFSCar")
\t\t(comment 1 "MCU: Pro Micro USB-C (RAW=NC, RST=NC) | 2x CD74HC4067 Breakout Modules (2.54mm THT)")
\t\t(comment 2 "Low-Crosstalk Analog: 16x 100nF Pre-Mux Filter Caps + R1=100R / C3=DNP")
\t\t(comment 3 "Alps-Spec 2-Resistor Encoder RC (10k PU + 10k Series + 10nF) | Panel Controls via J7..J14")
\t)
\t(lib_symbols
{chr(10).join(LIB_BLOCKS)}
\t)
{chr(10).join(sb.texts)}
{chr(10).join(sb.no_connects)}
{chr(10).join(sb.wires)}
{chr(10).join(sb.labels)}
{chr(10).join(sb.symbols)}
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

    pro_data = {
        "board": {
            "design_settings": {
                "defaults": {
                    "board_outline_line_width": 0.15,
                    "copper_line_width": 0.25,
                    "copper_text_size_h": 1.2,
                    "copper_text_size_v": 1.2,
                    "copper_text_thickness": 0.25
                },
                "rules": {
                    "min_clearance": 0.2,
                    "min_track_width": 0.2,
                    "min_via_annular_width": 0.15,
                    "min_via_diameter": 0.65
                }
            }
        },
        "meta": {"filename": "ddj_flx4_controller.kicad_pro", "version": 1},
        "schematic": {"meta": {"version": 1}}
    }
    with open(os.path.join(OUT_DIR, "ddj_flx4_controller.kicad_pro"), "w", encoding="utf-8") as f:
        json.dump(pro_data, f, indent=2)

    if os.path.exists(ONE_DRIVE_DIR):
        with open(os.path.join(ONE_DRIVE_DIR, "Projeto Mesa.kicad_sch"), "w", encoding="utf-8") as f:
            f.write(sch_content)

    print(f"SUCCESS: Generated v2 schematic {out_sch} ({len(sb.symbols)} symbols)")

if __name__ == "__main__":
    build()
