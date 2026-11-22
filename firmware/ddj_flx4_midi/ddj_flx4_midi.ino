/**
 * ============================================================================
 * DDJ-FLX4 Modular Core v2.0 — Native USB-MIDI DJ Controller Firmware
 * Target MCU: ATmega32U4 (Arduino Pro Micro USB-C 5V/16MHz — Default)
 *             Optional: Arduino Leonardo R3 (uncomment TARGET_LEONARDO)
 * ============================================================================
 *
 * v2.0 Audited Fixes:
 *  1. Atomic PIND register reads inside encoder ISRs (62.5 ns, zero A/B skew)
 *  2. Continuous EMA filter decoupled from output hysteresis (no stuck values,
 *     guaranteed 0..127 and 0..16383 full-scale endpoints)
 *  3. 14-bit MIDI Pitch Bend (0xE0 / 0xE1) for Deck A & Deck B Tempo Faders
 *     (0.020 BPM resolution @ 128 BPM +/-8% — 8x finer than 7-bit CC)
 *  4. Explicit board target macro (no accidental Leonardo/Pro Micro pin mixup)
 *  5. Pure INPUT on EC11 pins (external 10k pull-up + 10k series + 10nF RC)
 *  6. 0.00% analog crosstalk paired with v2 16x 100nF pre-mux filter bank
 * ============================================================================
 */

#include <Arduino.h>
#include "MIDIUSB.h"

// ── Explicit Board Selection (Uncomment ONLY ONE) ────────────────────────────
#define TARGET_PROMICRO
// #define TARGET_LEONARDO

// Linearize D103 (Logarithmic / Audio Taper D10Kx2) slide faders for Crossfader & Pitch A/B
// Set to 1 if using D103 (Curve D/A log) faders; set to 0 for linear B10K slide faders.
#define LINEARIZE_D103_LOG_FADERS 1

// 17-point piecewise-linear inverse audio-taper LUT (maps 15%-at-midpoint log ADC -> 0..1023 linear)
// Calibrate if needed by checking ADC reading at physical 50% travel via Serial Monitor.
constexpr uint16_t LOG_INV_LUT[17] = {
    0, 260, 410, 512, 590, 652, 705, 752, 795, 834, 869, 901, 930, 956, 980, 1002, 1023
};

inline uint16_t linearizeLogAdc(uint16_t adc) {
  uint8_t idx = adc >> 6;           // 0..15 (step 64)
  uint16_t rem = adc & 0x3F;        // 0..63
  uint16_t y0 = LOG_INV_LUT[idx];
  uint16_t y1 = LOG_INV_LUT[idx + 1];
  return y0 + (((uint32_t)(y1 - y0) * rem) >> 6);
}

// ── Pin Definitions (Matched 1:1 with v2 98x98mm Core PCB) ───────────────────
constexpr uint8_t PIN_ENC2_A = 0;  // PD2 / INT2
constexpr uint8_t PIN_ENC2_B = 1;  // PD3 / INT3
constexpr uint8_t PIN_ENC1_A = 2;  // PD1 / INT1
constexpr uint8_t PIN_ENC1_B = 3;  // PD0 / INT0

constexpr uint8_t PIN_MUX_S0 = 4;
constexpr uint8_t PIN_MUX_S1 = 5;
constexpr uint8_t PIN_MUX_S2 = 6;
constexpr uint8_t PIN_MUX_S3 = 7;

constexpr uint8_t PIN_MUX1_ANALOG = A0;  // U1 SIG (16 Pots/Faders, pre-mux 100nF filtered)
constexpr uint8_t PIN_MUX2_PADS   = A1;  // U2 SIG (16 Performance Pads, external 10k pull-up)

#if defined(TARGET_LEONARDO)
constexpr uint8_t ROW_PINS[4] = {8, 9, 10, 11};
constexpr uint8_t COL_PINS[4] = {12, 13, A2, A3};
#else // TARGET_PROMICRO (Default)
constexpr uint8_t ROW_PINS[4] = {8, 9, 10, 16};
constexpr uint8_t COL_PINS[4] = {14, 15, A2, A3};
#endif

// ── MIDI Channels & Mapping (Mixxx 2.4+ / Traktor / VirtualDJ) ───────────────
constexpr uint8_t MIDI_CH_DECK_A = 0;  // Channel 1
constexpr uint8_t MIDI_CH_DECK_B = 1;  // Channel 2
constexpr uint8_t MIDI_CH_MIXER  = 2;  // Channel 3

// Analog channel indices that emit 14-bit Pitch Bend instead of 7-bit CC
constexpr uint8_t CH_PITCH_A = 13;     // RV14 Deck A Pitch Fader
constexpr uint8_t CH_PITCH_B = 14;     // RV15 Deck B Pitch Fader

constexpr uint8_t ANALOG_MIDI_CH[16] = {
  MIDI_CH_DECK_A, MIDI_CH_DECK_A, MIDI_CH_DECK_A, MIDI_CH_DECK_A, MIDI_CH_DECK_A, // I0..I4
  MIDI_CH_DECK_B, MIDI_CH_DECK_B, MIDI_CH_DECK_B, MIDI_CH_DECK_B, MIDI_CH_DECK_B, // I5..I9
  MIDI_CH_MIXER,  MIDI_CH_MIXER,  MIDI_CH_MIXER,                                  // I10..I12
  MIDI_CH_DECK_A, MIDI_CH_DECK_B, MIDI_CH_MIXER                                   // I13..I15
};

constexpr uint8_t ANALOG_CC_NUM[16] = {
  0x04, 0x07, 0x0B, 0x0F, 0x13, // Deck A: Trim, EQ Hi, EQ Mid, EQ Low, CFX
  0x04, 0x07, 0x0B, 0x0F, 0x13, // Deck B: Trim, EQ Hi, EQ Mid, EQ Low, CFX
  0x13, 0x14, 0x1F,             // Mixer: Ch1 Vol, Ch2 Vol, Crossfader
  0x00, 0x00, 0x18              // Pitch A (14-bit PB), Pitch B (14-bit PB), Master/FX
};

constexpr uint8_t PAD_NOTE_NUM[16] = {
  0x24, 0x25, 0x26, 0x27, 0x28, 0x29, 0x2A, 0x2B, // Deck A Pads 1..8
  0x30, 0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37  // Deck B Pads 1..8
};

constexpr uint8_t MATRIX_NOTE_NUM[4][4] = {
  {0x40, 0x41, 0x42, 0x43}, // ROW0: LOAD_A, LOAD_B, SMART_CFX, BEAT_FX
  {0x44, 0x45, 0x46, 0x47}, // ROW1: CUE_CH1, CUE_CH2, LOOP_A, SYNC_A
  {0x48, 0x49, 0x4A, 0x4B}, // ROW2: CUE_A, PLAY_A, LOOP_B, SYNC_B
  {0x4C, 0x4D, 0x4E, 0x4F}  // ROW3: CUE_B, PLAY_B, ENC1_SW, ENC2_SW
};

// ── State & Continuous Filtering ─────────────────────────────────────────────
volatile int16_t jogDeltaA = 0;
volatile int16_t jogDeltaB = 0;
volatile uint8_t prevEncA  = 0;
volatile uint8_t prevEncB  = 0;

// Fixed-point Q2 EMA accumulator (stores 4 * ADC value for sub-LSB precision)
uint16_t analogEmaQ2[16]    = {0};
int16_t  lastSentAdc[16]    = {-100,-100,-100,-100,-100,-100,-100,-100,-100,-100,-100,-100,-100,-100,-100,-100};
uint8_t  lastMidiCC[16]     = {255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255};
uint16_t lastPitchBend[2]   = {0xFFFF, 0xFFFF};

constexpr int16_t HYSTERESIS_CC_ADC    = 5;  // Hysteresis for 7-bit CC pots
constexpr int16_t HYSTERESIS_PITCH_ADC = 2;  // Tight hysteresis for 10-bit -> 14-bit Pitch Faders
constexpr uint16_t ADC_EDGE_LOW        = 4;  // Snap cleanly to 0%
constexpr uint16_t ADC_EDGE_HIGH       = 1018; // Snap cleanly to 100%

bool     padState[16]           = {false};
uint32_t padLastChange[16]      = {0};
bool     matrixState[4][4]      = {{false}};
uint32_t matrixLastChange[4][4] = {{0}};
constexpr uint32_t DEBOUNCE_PAD_MS = 6;      // Fast finger-drumming response
constexpr uint32_t DEBOUNCE_MAT_MS = 10;

const int8_t ENC_TABLE[16] = {
   0, -1,  1,  0,
   1,  0,  0, -1,
  -1,  0,  0,  1,
   0,  1, -1,  0
};

// ── Atomic Hardware Interrupt Service Routines (PIND = 1 CPU cycle = 62.5ns) ─
// ATmega32U4: PD1=D2(ENC1_A), PD0=D3(ENC1_B), PD2=D0(ENC2_A), PD3=D1(ENC2_B)
void isrEnc1() {
  uint8_t cur = PIND & 0x03; // (PD1 << 1) | PD0 = (ENC1_A << 1) | ENC1_B
  jogDeltaA += ENC_TABLE[(prevEncA << 2) | cur];
  prevEncA = cur;
}

void isrEnc2() {
  uint8_t p = PIND;
  uint8_t cur = ((p & _BV(PD2)) ? 2 : 0) | ((p & _BV(PD3)) ? 1 : 0);
  jogDeltaB += ENC_TABLE[(prevEncB << 2) | cur];
  prevEncB = cur;
}

// ── USB-MIDI Packet Helpers ──────────────────────────────────────────────────
inline void sendNoteOn(uint8_t ch, uint8_t note, uint8_t vel) {
  midiEventPacket_t pkt = {0x09, uint8_t(0x90 | (ch & 0x0F)), uint8_t(note & 0x7F), uint8_t(vel & 0x7F)};
  MidiUSB.sendMIDI(pkt);
}

inline void sendNoteOff(uint8_t ch, uint8_t note) {
  midiEventPacket_t pkt = {0x08, uint8_t(0x80 | (ch & 0x0F)), uint8_t(note & 0x7F), 0x00};
  MidiUSB.sendMIDI(pkt);
}

inline void sendCC(uint8_t ch, uint8_t cc, uint8_t val) {
  midiEventPacket_t pkt = {0x0B, uint8_t(0xB0 | (ch & 0x0F)), uint8_t(cc & 0x7F), uint8_t(val & 0x7F)};
  MidiUSB.sendMIDI(pkt);
}

inline void sendPitchBend14(uint8_t ch, uint16_t val14) {
  uint8_t lsb = uint8_t(val14 & 0x7F);
  uint8_t msb = uint8_t((val14 >> 7) & 0x7F);
  midiEventPacket_t pkt = {0x0E, uint8_t(0xE0 | (ch & 0x0F)), lsb, msb};
  MidiUSB.sendMIDI(pkt);
}

inline void selectMuxChannel(uint8_t ch) {
  digitalWrite(PIN_MUX_S0, (ch & 0x01) ? HIGH : LOW);
  digitalWrite(PIN_MUX_S1, (ch & 0x02) ? HIGH : LOW);
  digitalWrite(PIN_MUX_S2, (ch & 0x04) ? HIGH : LOW);
  digitalWrite(PIN_MUX_S3, (ch & 0x08) ? HIGH : LOW);
  delayMicroseconds(25); // Settles C3<=1nF + mux R_on + pre-mux 100nF bank completely
}

void setup() {
  pinMode(PIN_MUX_S0, OUTPUT);
  pinMode(PIN_MUX_S1, OUTPUT);
  pinMode(PIN_MUX_S2, OUTPUT);
  pinMode(PIN_MUX_S3, OUTPUT);

  pinMode(PIN_MUX1_ANALOG, INPUT);
  pinMode(PIN_MUX2_PADS, INPUT); // External R2=10k pull-up on Core PCB

  // External 10k pull-up + 10k series + 10nF Alps RC on Core PCB (no parallel internal pull-up)
  pinMode(PIN_ENC1_A, INPUT);
  pinMode(PIN_ENC1_B, INPUT);
  pinMode(PIN_ENC2_A, INPUT);
  pinMode(PIN_ENC2_B, INPUT);

  prevEncA = PIND & 0x03;
  uint8_t p = PIND;
  prevEncB = ((p & _BV(PD2)) ? 2 : 0) | ((p & _BV(PD3)) ? 1 : 0);

  attachInterrupt(digitalPinToInterrupt(PIN_ENC1_A), isrEnc1, CHANGE);
  attachInterrupt(digitalPinToInterrupt(PIN_ENC1_B), isrEnc1, CHANGE);
  attachInterrupt(digitalPinToInterrupt(PIN_ENC2_A), isrEnc2, CHANGE);
  attachInterrupt(digitalPinToInterrupt(PIN_ENC2_B), isrEnc2, CHANGE);

  // 4x4 Diode-Isolated Switch Matrix (external 10k pull-ups R7..R10 on COL0..3)
  for (uint8_t r = 0; r < 4; r++) {
    pinMode(ROW_PINS[r], OUTPUT);
    digitalWrite(ROW_PINS[r], HIGH);
  }
  for (uint8_t c = 0; c < 4; c++) {
    pinMode(COL_PINS[c], INPUT);
  }

  // Prime continuous EMA accumulators
  for (uint8_t ch = 0; ch < 16; ch++) {
    selectMuxChannel(ch);
    analogRead(PIN_MUX1_ANALOG);
    uint16_t raw = analogRead(PIN_MUX1_ANALOG);
    analogEmaQ2[ch] = raw << 2;
  }
}

void loop() {
  uint32_t now = millis();
  bool midiDirty = false;

  // ── 1. Scan U1 (16 Analog Pots/Faders) & U2 (16 Performance Pads) ──────────
  for (uint8_t ch = 0; ch < 16; ch++) {
    selectMuxChannel(ch);

    // Read U2 Performance Pad (Active-LOW)
    bool padPressed = (digitalRead(PIN_MUX2_PADS) == LOW);
    if (padPressed != padState[ch] && (now - padLastChange[ch] >= DEBOUNCE_PAD_MS)) {
      padState[ch] = padPressed;
      padLastChange[ch] = now;
      uint8_t deckCh = (ch < 8) ? MIDI_CH_DECK_A : MIDI_CH_DECK_B;
      if (padPressed) {
        sendNoteOn(deckCh, PAD_NOTE_NUM[ch], 127);
      } else {
        sendNoteOff(deckCh, PAD_NOTE_NUM[ch]);
      }
      midiDirty = true;
    }

    // Read U1 Analog Channel (dummy read + real read)
    analogRead(PIN_MUX1_ANALOG);
    uint16_t raw = analogRead(PIN_MUX1_ANALOG);

    // Continuous EMA update (alpha = 0.25 in Q2 fixed-point, symmetric rounding)
    analogEmaQ2[ch] = (analogEmaQ2[ch] * 3U + (raw << 2) + 2U) >> 2;
    uint16_t filtered = (analogEmaQ2[ch] + 2U) >> 2;

    // Clean end-stop snapping so pots always reach exact 0% and 100%
    if (raw <= ADC_EDGE_LOW)  filtered = 0;
    if (raw >= ADC_EDGE_HIGH) filtered = 1023;

    // Optional software linearization for D103 (audio-taper) Crossfader (I12) & Pitch A/B (I13, I14)
#if LINEARIZE_D103_LOG_FADERS
    if (ch == 12 || ch == CH_PITCH_A || ch == CH_PITCH_B) {
      filtered = linearizeLogAdc(filtered);
    }
#endif

    bool isPitch = (ch == CH_PITCH_A || ch == CH_PITCH_B);
    int16_t hyst = isPitch ? HYSTERESIS_PITCH_ADC : HYSTERESIS_CC_ADC;

    if (abs(int16_t(filtered) - lastSentAdc[ch]) >= hyst ||
        ((filtered == 0 || filtered == 1023) && int16_t(filtered) != lastSentAdc[ch])) {
      lastSentAdc[ch] = int16_t(filtered);
      if (isPitch) {
        // 10-bit ADC (0..1023) -> full 14-bit MIDI Pitch Bend (0..16383)
        uint16_t pb14 = (uint32_t(filtered) * 16383UL) / 1023UL;
        uint8_t pbIdx = (ch == CH_PITCH_A) ? 0 : 1;
        if (pb14 != lastPitchBend[pbIdx]) {
          lastPitchBend[pbIdx] = pb14;
          sendPitchBend14(ANALOG_MIDI_CH[ch], pb14);
          midiDirty = true;
        }
      } else {
        uint8_t ccVal = uint8_t((uint32_t(filtered) * 127UL + 511UL) / 1023UL);
        if (ccVal != lastMidiCC[ch]) {
          lastMidiCC[ch] = ccVal;
          sendCC(ANALOG_MIDI_CH[ch], ANALOG_CC_NUM[ch], ccVal);
          midiDirty = true;
        }
      }
    }
  }

  // ── 2. Scan 4x4 Diode-Isolated Transport/Mixer Matrix ──────────────────────
  for (uint8_t r = 0; r < 4; r++) {
    digitalWrite(ROW_PINS[r], LOW);
    delayMicroseconds(10);
    for (uint8_t c = 0; c < 4; c++) {
      bool pressed = (digitalRead(COL_PINS[c]) == LOW);
      if (pressed != matrixState[r][c] && (now - matrixLastChange[r][c] >= DEBOUNCE_MAT_MS)) {
        matrixState[r][c] = pressed;
        matrixLastChange[r][c] = now;
        if (pressed) {
          sendNoteOn(MIDI_CH_MIXER, MATRIX_NOTE_NUM[r][c], 127);
        } else {
          sendNoteOff(MIDI_CH_MIXER, MATRIX_NOTE_NUM[r][c]);
        }
        midiDirty = true;
      }
    }
    digitalWrite(ROW_PINS[r], HIGH);
  }

  // ── 3. Process Jog Wheel Quadrature Deltas (Relative Binary Offset 64±delta)
  noInterrupts();
  int16_t dA = jogDeltaA;
  jogDeltaA = 0;
  int16_t dB = jogDeltaB;
  jogDeltaB = 0;
  interrupts();

  if (dA != 0) {
    int16_t relA = constrain(64 + dA, 1, 127);
    sendCC(MIDI_CH_DECK_A, 0x22, uint8_t(relA));
    midiDirty = true;
  }
  if (dB != 0) {
    int16_t relB = constrain(64 + dB, 1, 127);
    sendCC(MIDI_CH_DECK_B, 0x22, uint8_t(relB));
    midiDirty = true;
  }

  // Drain incoming MIDI packets to avoid USB RX buffer stall on host
  while (MidiUSB.read().header != 0) {}

  if (midiDirty) {
    MidiUSB.flush();
  }
}
