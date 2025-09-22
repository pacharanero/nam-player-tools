# Unofficial NAM Player Manager (GUI + CLI)

Python tooling to open, inspect, edit, version, and manipulate **Dimehead NAM Player** preset bank files (`.npb`).

A NAM Player backup file is obtained using the Export to USB feature in the NAM Player Settings menu (3rd Page). The files use a custom .npb format, however internally they are tar.gz archives containing a `config.json` and various preset assets.

## Components

1. **NAM Player Manager GUI** for preset management.
2. **CLI utility** (`nam_config_tool.py`) for scripting / automation.
3. **Backup file format reference** for reverse‑engineering and development **[`FORMAT_SPEC.md`](FORMAT_SPEC.md)**.

> IP Notice: The `.npb` format remains the intellectual property of Dimehead. This project exists for convenience, education, interoperability and to enhance the ecosystem around the Dimehead NAM Player .

## Quick Start (GUI)

Install dependencies (Python 3.10+ suggested):

```
pip install -e .
```

Run the NAM Player Manager GUI:

```
python -m dimehead_gui.main
```

Open a `.npb` file via 'Open Bank' button in the toolbar.

### Current NAM Player Manager GUI Capabilities

- Open & parse bank (`.npb`)
- Display presets in a table (index + name)
- Inline rename (editable Name column)
- Reorder presets (Move Up / Move Down)
- Drag & drop preset reordering
- Global settings panel (brightness, line out, MIDI, footswitch, etc.)
- LED color column with picker (hex + swatch)
- Dirty tracking (save buttons enable only when changes exist)
- Versioned save (auto `_vNNN` numbering)
- In‑place overwrite (confirmation + existing backup respect)

### Coming Soon

- Full preset parameter editing (gain / tone / boost / ambience / gate)
- Undo / redo (QUndoStack)
- Drag & drop preset reordering + asset import (.nam / .ir)
- Diff panel (original vs edited)
- Validation (frequency & range checks)
- Bulk operations (copy EQ, normalize loudness)
- JSON schema + validate command
- Preset extraction / cloning / multi‑select edits

Progress is incremental—expect frequent small improvements instead of a big monolith release.

## Format Details?

They're now housed in [`FORMAT_SPEC.md`](FORMAT_SPEC.md) to keep this README focused on usage. That document covers:

- Archive layout & member roles
- Full observed `config.json` schema
- Field semantics & inferences
- Risks / unknowns / validation suggestions
- Change & diff considerations

## CLI Tool: `nam_config_tool.py`

A Python CLI that operates directly on `.npb` archives without manual extraction.

### Features

- Show formatted `config.json`
- Export `config.json` to standalone file
- Update (replace) `config.json` from an edited JSON file
- Get a single value using JSON Pointer
- Set a single value using JSON Pointer (auto type coercion for bool/int/float/null)
- Automatic `.bak` backup (only created once) before first destructive write
- Preserves ordering & all non-config archive members

### Usage Examples (CLI)

Print entire config:

```
python3 nam_config_tool.py show namplayer0.npb
```

Export config:

```
python3 nam_config_tool.py export namplayer0.npb current_config.json
```

Modify locally then write back:

```
# (edit current_config.json in an editor)
python3 nam_config_tool.py update namplayer0.npb current_config.json
```

Read a single field:

```
python3 nam_config_tool.py get namplayer0.npb /presets/0/name
```

Change a field:

```
python3 nam_config_tool.py set namplayer0.npb /presets/0/potiGain 0.65
```

Enable boost on preset 1:

```
python3 nam_config_tool.py set namplayer0.npb /presets/1/boostEnable true
```

### JSON Pointer Notes

- Standard RFC6901, with list indices numeric: `/presets/3/name`
- You may prefix with `#` (ignored): `#/presets/0/name`
- Escape rules: `~0` = `~`, `~1` = `/`

### Safety Considerations

- Always keeps a first-write backup `<file>.bak`
- Rebuilds archive rather than editing in-place (prevents structural corruption)
- Does not (yet) validate schema — malformed changes could confuse the device

## Architecture (High Level)

Layered design keeps the GUI optional:

1. Core I/O (`dimehead_bank.py`) – load / save / diff / version naming.
2. CLI (`nam_config_tool.py`) – surgical JSON pointer edits & scripting.
3. NAM Player Manager GUI (`dimehead_gui/`) – user friendly table + future editors.
4. Planned services – validation, diff view models, undo commands.

Undo/redo, diff visualization and validation will live above the pure data layer so headless automation remains possible.

### Roadmap Snapshot

| Stage | Focus                                    | Status  |
| ----- | ---------------------------------------- | ------- |
| 1     | Core load + table + rename               | Done    |
| 1.1   | Versioned save + overwrite safety        | Done    |
| 1.2   | Reorder presets (move up/down)           | Done    |
| 2     | Parameter editing panes + color picker   | Planned |
| 3     | Undo/redo + diff panel + validation      | Planned |
| 4     | Drag & drop assets + preset drag reorder | Planned |
| 5     | Bulk ops (EQ copy, normalize)            | Planned |
| 6     | Plugin hooks + export report             | Planned |
| 7     | Visualization (EQ curves, loudness)      | Planned |

### Dev Setup (Editable Install)

Clone + install editable for iterative hacking:

```
git clone <this repo>
cd nam-player-dimehead
pip install -e .[dev]
python -m dimehead_gui.main
```

### Saving Behavior

Two save actions are provided once edits are made (e.g. renaming a preset):

- **Save New Version**: Writes a new file alongside the original by inserting / incrementing a suffix of the form `_vNNN` before the `.npb` extension.
  - Examples: `mybank.npb` → `mybank_v001.npb`; next save → `mybank_v002.npb`.
  - If the original already ends with `_v007`, the next becomes `_v008`.
  - Original file remains untouched.
- **Overwrite**: Rewrites the currently loaded bank file in place (after a confirmation dialog). A `.bak` may already exist from earlier CLI or GUI saves; the overwrite respects existing backup creation logic.

Both actions are disabled until the session is marked dirty (after an edit). On successful save the dirty flag clears and buttons disable again.
For deeper reverse‑engineering notes, see `FORMAT_SPEC.md`.

## Features

- Load & parse `.npb` backup file
- Preset table (index + name)
- Rename presets inline
- Reorder presets (move up/down buttons)
- Drag & drop preset reordering
- Global settings panel (core device-wide parameters)
- LED color column + interactive picker
- Dirty tracking & toolbar state
- Versioned save (`_vNNN`) + overwrite with confirm
- CLI JSON pointer get/set/export/update with backup

## Future development ideas

- Parameter editing (knobs, filters, ambience, boost)
- LED color picker
- Undo/redo & diff visualization
- Validation & schema file
- Drag & drop asset import (.nam / .ir)
- Bulk ops & loudness normalize
- Preset extract / clone / multi-select
- Visualization (EQ curves, meters)
- Plugin / extension hooks
- Add bulk actions - multi select
- Compile to binary or executable
- Running on other platforms

## Firmware archive

For no reason other than future reference, I have also archived the firmware downloads from Dimehead's site https://www.dimehead.de/firmware/

These are in the [firmware_archive/](firmware_archive/) directory.
  
## Contributing

PRs welcome—small, focused improvements preferred (one feature or refactor at a time). For format discoveries, update `FORMAT_SPEC.md` and reference captured evidence (hashes / sample snippets) if possible.

## License & Intellectual Property

This tooling and accompanying documentation are released under the **MIT License** (see `LICENSE`).

**Acknowledgment & IP Notice**

- The `.npb` bank format, its structure, semantics, and any trademarks or distinctive product identifiers are the work and intellectual property of **Dimehead** (the creators / owners of the Dimehead NAM Player).
- This project is an independent, reverse-engineering and interoperability effort intended to assist legitimate owners/users of the hardware/software in managing their own preset data.
- No proprietary code from Dimehead is included; only observations of file layout and field behavior based on lawful inspection.
- Distribution of third‑party `.nam` model files, IRs (`.ir`), reverbs (`.reverb`), or other captured content may be subject to original authors' licensing. Do **not** redistribute commercial or copyrighted captures without explicit permission.

If Dimehead publishes an official specification or requests changes to attribution, this README should be updated accordingly.

---

_This documentation will evolve as we learn more about the Dimehead NAM Player internals. Feel free to request new sections or clarifications._
