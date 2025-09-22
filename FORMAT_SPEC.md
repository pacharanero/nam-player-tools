# Dimehead NAM Player Bank Format (Reverse Engineered Reference)

> This document captures the technical details of the `.npb` bank format and `config.json` schema as observed. It is separate from the main README which focuses on the GUI tooling. The format remains the intellectual property of Dimehead.

## 1. Container Overview

A Dimehead bank (`.npb`) is a **gzip-compressed POSIX tar archive**. It can be renamed to `.tar.gz` and manipulated with standard tools.

### Typical Contents

```
./
./config.json
./state.bin
./<Amp Model>.nam
./<Pedal Model>.nam
./<Impulse>.ir
```

Other files (reverb impulses, etc.) may appear.

### Key Files

| File          | Purpose                                                    |
| ------------- | ---------------------------------------------------------- |
| `config.json` | Global settings + ordered preset list                      |
| `state.bin`   | Undocumented binary (likely runtime / calibration / cache) |
| `*.nam`       | Neural Amp Modeler model captures (amps, pedals, boosts)   |
| `*.ir`        | Impulse responses for cabinets or ambience                 |
| `*.reverb`    | Convolution reverb impulse (if used)                       |

## 2. `config.json` Schema (Observed v1)

Global config field

|JSON Field (data type    | NAM UI Label    |   Notes     |
|------------------------|-----------------|-------------|
|`configVersion` (int, observed: 1) | n/a | |
| `lineoutPosition` (int) (options are: Boost) | Lineout/FX tap after ... | Enum options: Boost, EQ, Room, HP/LP, IR (0) || 
| `lineoutVolume` (float 0–1) | Lineout Master Volume | 0.0 - 10.0 |
| `lcdBrightness` (int) | LCD Brightness | 0 - 10 |
| `ledBrightness` (int) | LED Brightness | 0 - 10 |
| `footswitchModeIndex` (int) | Footswitch Mode | Enum options: 1-4, Bank |
| `footswitchLongpress` (int) | Footswitch Long Press Mode | Enum options: Nothing, Tuner, Bypass |
| `enableRotateBack` (bool) | Press-Rotate-Release to Close | Enum options: No (0), Yes (1) |
| `enableStagemodeEncoder` (bool) | Enable Encoder in Stage Mode | Enum options: No (0), Yes (1) |
| `midiChannelIndex` (int) | MIDI Channel | Enum options: Omni (0), 1-16 |

### GLOBAL CONFIGS TO ADD:

?JSON key (?float) | Tuner Pitch Reference | 430.0 - 450.0 Hz  
Recall Last Preset (on power up?) (bool) | n/a | Enum options: No (0), Yes (1)

### 2.1 Preset Object Fields

These are contained in an array under the `presets` key. Each preset object has many fields, some optional.

| Category      | Fields                                                                                                                                                                                                                                                                                         |
| ------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Identity      | `name`, `nam`                                                                                                                                                                                                                                                                                  |
| Boost         | `boostEnable`, `boostNam`, `potiBoostGain`, `potiBoostBass`, `potiBoostMids`, `potiBoostTreble`                                                                                                                                                                                                |
| EQ            | `eqBassFreq`, `eqBassQ`, `eqMidsFreq`, `eqMidsQ`, `eqTrebleFreq`, `eqTrebleQ`                                                                                                                                                                                                                  |
| Filters       | `hpFreq`, `lpFreq`                                                                                                                                                                                                                                                                             |
| Core Pots     | `potiGain`, `potiBass`, `potiMids`, `potiTreble`, `potiVol`                                                                                                                                                                                                                                    |
| Gate          | `ngThreshold` (extremely low value disables)                                                                                                                                                                                                                                                   |
| Phase         | `phaseInvert`                                                                                                                                                                                                                                                                                  |
| Cabinet       | `ir`                                                                                                                                                                                                                                                                                           |
| Normalization | `volNormalizeEnabled`                                                                                                                                                                                                                                                                          |
| LED/UI        | `ledColor` (24-bit RGB int)                                                                                                                                                                                                                                                                    |
| Ambience      | `roomBind`, `roomConvolutionEnable`, `roomConvolutionFile`, `roomConvolutionMix`, `roomDelayEnable`, `roomDelayTime`, `roomDelayMix`, `roomDelayFeedback`, `roomDelayHP`, `roomDelayLP`, `roomDelayLFODepth`, `roomDelayLFOSpeed`, `roomTremoloEnable`, `roomTremoloDepth`, `roomTremoloSpeed` |

Notes:

- All numerical pot values stored as floats (0–1 normalized) even if conceptually discrete.
- `lpFreq` can be 0.0 meaning effectively disabled (full bandwidth).
- `ledColor` examples show values like `16718080` (`0xFFAA00`).

### 2.2 Inferred Semantics

| Field                    | Inference                                                                    |
| ------------------------ | ---------------------------------------------------------------------------- |
| `hpFreq` / `lpFreq`      | Global/input filtering or cab pre/post relative – exact stage not confirmed. |
| Parametric bands (`eq*`) | Appear to be wide tone-stack style filters; Q ~0.7 common.                   |
| `ngThreshold`            | Negative threshold; large negative sentinel indicates disabled gate.         |
| `room*` set              | Unified ambience pipeline (convolution + delay + optional tremolo).          |
| `volNormalizeEnabled`    | Loudness normalization per preset.                                           |

## 3. Diff & Change Considerations

- Order of presets matters (index used for recall ordering).
- Renaming does not alter other preset parameters; diffing by name changes only.
- Adding/removing entries requires careful index handling by consumers.

## 4. Archive Manipulation Notes

- `config.json` can be replaced by rebuilding the tar with all other members copied intact.
- A backup (`.bak`) strategy is recommended prior to destructive overwrite operations.
- Extracting / injecting large `.nam` models unchanged preserves their binary integrity (no recompression beyond tar+gzip layer).

## 5. Risks & Unknowns

| Topic                | Status      | Notes                                                         |
| -------------------- | ----------- | ------------------------------------------------------------- |
| EQ Topology          | Unconfirmed | Could be pre or post amp model; empirical measurement needed. |
| Gate Threshold Scale | Unknown     | Need calibration vs actual UI units.                          |
| `roomBind` Meaning   | Unknown     | Possibly a shared pool or grouping key.                       |
| `state.bin`          | Unexplored  | Binary format unspecified.                                    |
| Future Versions      | Unknown     | Should treat unknown `configVersion` as read-only safe mode.  |

## 6. Suggested Validation Rules

- 0 ≤ all `poti*` ≤ 1
- Frequencies within 20–20000 Hz (except sentinel 0.0 for `lpFreq`)
- `ngThreshold` within plausible negative range (guard against accidental large positive)
- `ledColor` within 0x000000–0xFFFFFF

## 7. Example Minimal Preset Snippet

```json
{
  "name": "CRUNCH",
  "nam": "Factory/Plexi100 1966.nam",
  "boostEnable": false,
  "potiGain": 0.72,
  "potiBass": 0.5,
  "potiMids": 0.48,
  "potiTreble": 0.49,
  "potiVol": 0.62,
  "eqBassFreq": 90.0,
  "eqBassQ": 0.7,
  "eqMidsFreq": 650.0,
  "eqMidsQ": 0.45,
  "eqTrebleFreq": 3500.0,
  "eqTrebleQ": 0.7,
  "ir": "Factory/4x12_1960_G12M_SM57.ir",
  "hpFreq": 60.0,
  "lpFreq": 11200.0,
  "volNormalizeEnabled": true
}
```

## 8. License & Attribution

The `.npb` format remains the IP of Dimehead. This document is based on observation only and is provided under the repository MIT license for interoperability.

---

_Updates to this spec should remain additive and note new `configVersion` values when encountered._
