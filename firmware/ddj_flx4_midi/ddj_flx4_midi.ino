/**
 * ============================================================================
 * DDJ-FLX4 Inspired Open-Source USB-MIDI DJ Controller Firmware
 * Target MCU: ATmega32U4 (Arduino Leonardo R3 / Arduino Pro Micro USB-C 5V 16MHz)
 * ============================================================================
 *
 * Hardware Architecture (Matched 1:1 with KiCad 9.0 Schematic & PCB):
 * ----------------------------------------------------------------------------
 * 1. Native USB-MIDI (Class-Compliant via MIDIUSB library)
 * 2. Quadrature Jog Wheels (Hardware External Interrupts - Zero Latency):
 *    - ENC1 (Deck A Jog): A -> D2 (INT1), B -> D3 (INT0)
 *    - ENC2 (Deck B Jog): A -> D0 (INT2), B -> D1 (INT3)
 * 3. Shared 4-Bit Multiplexer Address Bus:
 *    - MUX_S0 -> D4, MUX_S1 -> D5, MUX_S2 -> D6, MUX_S3 -> D7
 * 4. U1 (CD74HC4067M #1 - 16 Analog Channels -> A0 / MUX1_COM):
 *    - I0..I4   : Deck A Mixer (Trim, EQ High, EQ Mid, EQ Low, Smart CFX)
 *    - I5..I9   : Deck B Mixer (Trim, EQ High, EQ Mid, EQ Low, Smart CFX)
 *    - I10..I11 : Channel 1 & Channel 2 Volume Faders
 *    - I12      : Crossfader
 *    - I13..I14 : Deck A & Deck B Pitch/Tempo Sliders
 *    - I15      : Master / Beat FX Level Rotary Pot
 * 5. U2 (CD74HC4067M #2 - 16 Performance Pads -> A1 / MUX2_COM with 10k Pull-Up):
 *    - I0..I7   : Deck A Performance Pads (PAD_A1..PAD_A8)
 *    - I8..I15  : Deck B Performance Pads (PAD_B1..PAD_B8)
 * 6. 4x4 Diode-Isolated Switch Matrix (14 Transport/Mixer Buttons + 2 Jog Push SW):
 *    - Rows (Active-LOW Drive) : ROW0 -> D8, ROW1 -> D9, ROW2 -> D10, ROW3 -> D16 (or D11)
 *    - Cols (INPUT_PULLUP)     : COL0 -> D14 (or D12), COL1 -> D15 (or D13), COL2 -> A2, COL3 -> A3
 * ============================================================================
 */

#include <Arduino.h>
#include "MIDIUSB.h"

// ── Pin Definitions ──────────────────────────────────────────────────────────
constexpr uint8_t PIN_ENC2_A = 0;  // INT2
constexpr uint8_t PIN_ENC2_B = 1;  // INT3
constexpr uint8_t PIN_ENC1_A = 2;  // INT1
constexpr uint8_t PIN_ENC1_B = 3;  // INT0

constexpr uint8_t PIN_MUX_S0 = 4;
constexpr uint8_t PIN_MUX_S1 = 5;
constexpr uint8_t PIN_MUX_S2 = 6;
constexpr uint8_t PIN_MUX_S3 = 7;

constexpr uint8_t PIN_MUX1_ANALOG = A0;  // U1 COM (Analog Pots & Faders)
constexpr uint8_t PIN_MUX2_PADS   = A1;  // U2 COM (16 Performance Pads, Active LOW)

// Support both Leonardo R3 (D11..D13) and Pro Micro (D14..D16) seamlessly
#if defined(ARDUINO_AVR_PROMICRO)
constexpr uint8_t ROW_PINS[4] = {8, 9, 10, 16};
constexpr uint8_t COL_PINS[4] = {14, 15, A2, A3};
#else
constexpr uint8_t ROW_PINS[4] = {8, 9, 10, 11};
constexpr uint8_t COL_PINS[4] = {12, 13, A2, A3};
#endif

// ── MIDI Mapping Constants (Rekordbox / Mixxx / Serato Standard) ────────────
constexpr uint8_t MIDI_CH_DECK_A = 0;  // Channel 1
constexpr uint8_t MIDI_CH_DECK_B = 1;  // Channel 2
constexpr uint8_t MIDI_CH_MIXER  = 2;  // Channel 3

// CC Numbers for U1 (16 Analog Pots/Faders: I0..I15)
constexpr uint8_t ANALOG_CC_CH[16] = {
  MIDI_CH_DECK_A, MIDI_CH_DECK_A, MIDI_CH_DECK_A, MIDI_CH_DECK_A, MIDI_CH_DECK_A, // I0..I4
  MIDI_CH_DECK_B, MIDI_CH_DECK_B, MIDI_CH_DECK_B, MIDI_CH_DECK_B, MIDI_CH_DECK_B, // I5..I9
  MIDI_CH_MIXER,  MIDI_CH_MIXER,  MIDI_CH_MIXER,                                  // I10..I12
  MIDI_CH_DECK_A, MIDI_CH_DECK_B, MIDI_CH_MIXER                                   // I13..I15
};

constexpr uint8_t ANALOG_CC_NUM[16] = {
  0x04, 0x07, 0x0B, 0x0F, 0x13, // Deck A: Trim, EQ Hi, EQ Mid, EQ Low, CFX
  0x04, 0x07, 0x0B, 0x0F, 0x13, // Deck B: Trim, EQ Hi, EQ Mid, EQ Low, CFX
  0x13, 0x14, 0x1F,             // Mixer: Ch1 Vol, Ch2 Vol, Crossfader
  0x00, 0x00, 0x18              // Pitch A, Pitch B, Master/FX Level
};

// Note Numbers for U2 (16 Performance Pads: I0..I15)
constexpr uint8_t PAD_NOTE_NUM[16] = {
  0x24, 0x25, 0x26, 0x27, 0x28, 0x29, 0x2A, 0x2B, // Deck A Pads 1..8 (C2..G2)
  0x30, 0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37  // Deck B Pads 1..8 (C3..G3)
};

// Note Numbers for 4x4 Matrix (14 Transport/Mixer Buttons + 2 Jog Switches)
constexpr uint8_t MATRIX_NOTE_NUM[4][4] = {
  {0x40, 0x41, 0x42, 0x43}, // ROW0: LOAD_A, LOAD_B, SMART_CFX, BEAT_FX
  {0x44, 0x45, 0x46, 0x47}, // ROW1: CUE_CH1, CUE_CH2, LOOP_A, SYNC_A
  {0x48, 0x49, 0x4A, 0x4B}, // ROW2: CUE_A, PLAY_A, LOOP_B, SYNC_B
  {0x4C, 0x4D, 0x4E, 0x4F}  // ROW3: CUE_B, PLAY_B, ENC1_SW, ENC2_SW
};

// ── State & Filtering ────────────────────────────────────────────────────────
volatile int16_t jogDeltaA = 0;
volatile int16_t jogDeltaB = 0;
volatile uint8_t prevEncA  = 0;
volatile uint8_t prevEncB  = 0;

uint16_t analogFilter[16]  = {0};
uint8_t  lastMidiCC[16]    = {255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255};
constexpr uint16_t HYSTERESIS_ADC = 6; // Deadband on 10-bit ADC (0..1023) to prevent MIDI jitter

bool padState[16]          = {false};
uint32_t padLastChange[16] = {0};

bool matrixState[4][4]          = {{false}};
uint32_t matrixLastChange[4][4] = {{0}};
constexpr uint32_t DEBOUNCE_MS  = 12;

// Quadrature lookup table for glitch-free decoding
const int8_t ENC_TABLE[16] = {
   0, -1,  1,  0,
   1,  0,  0, -1,
  -1,  0,  0,  1,
   0,  1, -1,  0
};

// ── Hardware Interrupt Service Routines (ISRs) ───────────────────────────────
void isrEnc1() {
  uint8_t cur = ((digitalRead(PIN_ENC1_A) ? 1 : 0) << 1) | (digitalRead(PIN_ENC1_B) ? 1 : 0);
  jogDeltaA += ENC_TABLE[((prevEncA & 0x03) << 2) | cur];
  prevEncA = cur;
}

void isrEnc2() {
  uint8_t cur = ((digitalRead(PIN_ENC2_A) ? 1 : 0) << 1) | (digitalRead(PIN_ENC2_B) ? 1 : 0);
  jogDeltaB += ENC_TABLE[((prevEncB & 0x03) << 2) | cur];
  prevEncB = cur;
}

// ── USB-MIDI Helper Functions ────────────────────────────────────────────────
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

inline void selectMuxChannel(uint8_t ch) {
  digitalWrite(PIN_MUX_S0, (ch & 0x01) ? HIGH : LOW);
  digitalWrite(PIN_MUX_S1, (ch & 0x02) ? HIGH : LOW);
  digitalWrite(PIN_MUX_S2, (ch & 0x04) ? HIGH : LOW);
  digitalWrite(PIN_MUX_S3, (ch & 0x08) ? HIGH : LOW);
  delayMicroseconds(15); // Settling time for CD74HC4067 + 100nF RC filter
}

void setup() {
  // 1. Setup Multiplexer Address Bus
  pinMode(PIN_MUX_S0, OUTPUT);
  pinMode(PIN_MUX_S1, OUTPUT);
  pinMode(PIN_MUX_S2, OUTPUT);
  pinMode(PIN_MUX_S3, OUTPUT);

  pinMode(PIN_MUX1_ANALOG, INPUT);
  pinMode(PIN_MUX2_PADS, INPUT_PULLUP);

  // 2. Setup Quadrature Encoders with Internal Pull-ups
  pinMode(PIN_ENC1_A, INPUT_PULLUP);
  pinMode(PIN_ENC1_B, INPUT_PULLUP);
  pinMode(PIN_ENC2_A, INPUT_PULLUP);
  pinMode(PIN_ENC2_B, INPUT_PULLUP);

  prevEncA = ((digitalRead(PIN_ENC1_A) ? 1 : 0) << 1) | (digitalRead(PIN_ENC1_B) ? 1 : 0);
  prevEncB = ((digitalRead(PIN_ENC2_A) ? 1 : 0) << 1) | (digitalRead(PIN_ENC2_B) ? 1 : 0);

  attachInterrupt(digitalPinToInterrupt(PIN_ENC1_A), isrEnc1, CHANGE);
  attachInterrupt(digitalPinToInterrupt(PIN_ENC1_B), isrEnc1, CHANGE);
  attachInterrupt(digitalPinToInterrupt(PIN_ENC2_A), isrEnc2, CHANGE);
  attachInterrupt(digitalPinToInterrupt(PIN_ENC2_B), isrEnc2, CHANGE);

  // 3. Setup 4x4 Diode Switch Matrix
  for (uint8_t r = 0; r < 4; r++) {
    pinMode(ROW_PINS[r], OUTPUT);
    digitalWrite(ROW_PINS[r], HIGH);
  }
  for (uint8_t c = 0; c < 4; c++) {
    pinMode(COL_PINS[c], INPUT_PULLUP);
  }

  // 4. Enable Deck A & Deck B Status Indicator LEDs (D18 on A4, D19 on A5)
#if defined(A4) && defined(A5)
  pinMode(A4, OUTPUT);
  digitalWrite(A4, HIGH);
  pinMode(A5, OUTPUT);
  digitalWrite(A5, HIGH);
#endif

  // 5. Prime Analog Filter Bank
  for (uint8_t ch = 0; ch < 16; ch++) {
    selectMuxChannel(ch);
    analogRead(PIN_MUX1_ANALOG); // Dummy read for ADC S&H charge
    analogFilter[ch] = analogRead(PIN_MUX1_ANALOG);
  }
}

void loop() {
  uint32_t now = millis();
  bool midiDirty = false;

  // ── 1. Scan U1 (16 Analog Pots/Faders) & U2 (16 Performance Pads) ──────────
  for (uint8_t ch = 0; ch < 16; ch++) {
    selectMuxChannel(ch);

    // Read U2 Digital Performance Pad (Active-LOW)
    bool padPressed = (digitalRead(PIN_MUX2_PADS) == LOW);
    if (padPressed != padState[ch] && (now - padLastChange[ch] >= DEBOUNCE_MS)) {
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

    // Read U1 Analog Pot/Fader with Continuous EMA + Hysteresis Deadband
    analogRead(PIN_MUX1_ANALOG); // Dummy read after mux switch
    uint16_t raw = analogRead(PIN_MUX1_ANALOG);
    uint16_t smoothed = (analogFilter[ch] + raw) >> 1;
    if (abs(int16_t(raw) - int16_t(analogFilter[ch])) >= HYSTERESIS_ADC ||
        raw == 0 || raw >= 1020) {
      analogFilter[ch] = (raw == 0 || raw >= 1020) ? raw : smoothed;
      uint8_t ccVal = uint8_t(analogFilter[ch] >> 3); // 10-bit (0..1023) -> 7-bit MIDI (0..127)
      if (ccVal != lastMidiCC[ch]) {
        lastMidiCC[ch] = ccVal;
        sendCC(ANALOG_CC_CH[ch], ANALOG_CC_NUM[ch], ccVal);
        midiDirty = true;
      }
    }
  }

  // ── 2. Scan 4x4 Diode-Isolated Transport/Mixer Matrix ──────────────────────
  for (uint8_t r = 0; r < 4; r++) {
    digitalWrite(ROW_PINS[r], LOW);
    delayMicroseconds(10);
    for (uint8_t c = 0; c < 4; c++) {
      bool pressed = (digitalRead(COL_PINS[c]) == LOW);
      if (pressed != matrixState[r][c] && (now - matrixLastChange[r][c] >= DEBOUNCE_MS)) {
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

  if (midiDirty) {
    MidiUSB.flush();
  }
}
