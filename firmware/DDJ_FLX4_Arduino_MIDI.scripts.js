// ============================================================================
// Mixxx 2.4+ Controller Script for DDJ-FLX4 Modular Core v2.0 (ATmega32U4)
// Handles:
//   - 14-bit MIDI Pitch Bend (0xE0 / 0xE1) for smooth Tempo/Rate Faders
//   - Relative Binary Offset (64 +/- delta) EC11 Jog Wheel Nudge & Scratch
//   - EC11 Push Switch (ENC1_SW / ENC2_SW) to engage Scratch Mode while held
// ============================================================================

var DDJFLX4 = {};

DDJFLX4.JOG_NUDGE_SENSITIVITY = 1.5;   // Pitch-bend / nudge scaling per EC11 tick
DDJFLX4.SCRATCH_INTERVALS_PER_REV = 80; // EC11 20 PPR * 4x quadrature = 80 ticks/rev
DDJFLX4.SCRATCH_RPM = 33.3333;
DDJFLX4.SCRATCH_ALPHA = 1.0 / 8.0;
DDJFLX4.SCRATCH_BETA = DDJFLX4.SCRATCH_ALPHA / 32.0;

DDJFLX4.init = function(id, debugging) {
    print("DDJ-FLX4 Modular Core v2.0 initialized: " + id);
};

DDJFLX4.shutdown = function() {
    engine.scratchDisable(1);
    engine.scratchDisable(2);
};

// 14-bit Pitch Bend (LSB in control, MSB in value) -> Mixxx rate [-1.0 .. +1.0]
DDJFLX4.pitchFader = function(channel, control, value, status, group) {
    var val14 = (value << 7) | control; // 0 .. 16383
    var normalized = (val14 / 8191.5) - 1.0;
    // Invert if fader DOWN means faster tempo (Pioneer standard: down = +BPM)
    engine.setValue(group, "rate", -normalized);
};

// Hold EC11 push switch to engage Vinyl Scratch mode; release to return to Nudge
DDJFLX4.jogPush = function(channel, control, value, status, group) {
    var deck = script.deckFromGroup(group);
    var pressed = ((status & 0xF0) === 0x90) && (value > 0);
    if (pressed) {
        engine.scratchEnable(
            deck,
            DDJFLX4.SCRATCH_INTERVALS_PER_REV,
            DDJFLX4.SCRATCH_RPM,
            DDJFLX4.SCRATCH_ALPHA,
            DDJFLX4.SCRATCH_BETA
        );
    } else {
        engine.scratchDisable(deck);
    }
};

// Relative Binary Offset (64 +/- delta) on CC 0x22
DDJFLX4.jogWheel = function(channel, control, value, status, group) {
    var delta = value - 64;
    if (delta === 0) {
        return;
    }
    var deck = script.deckFromGroup(group);
    if (engine.isScratching(deck)) {
        engine.scratchTick(deck, delta);
    } else {
        engine.setValue(group, "jog", delta * DDJFLX4.JOG_NUDGE_SENSITIVITY);
    }
};
