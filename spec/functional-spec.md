# Functional Spec for the NAM Player Manager

## General Goals

- The project aims to be a simple GUI editor for Dimehead NAM Player `.npb` bank files.
- Users export the .npb file from the NAM Player, edit it in this tool, then re-import it back to the device using a USB stick.
- Users are generally guitarists or audio techs, not programmers, so we need to aim for a GUI which makes sense for them.

## Features to implement

- Full preset parameter editing (gain / tone / boost / ambience / gate)
- Undo / redo (QUndoStack)
- Drag & drop preset reordering + asset import (.nam / .ir)
- Diff panel (original vs edited)
- Validation (frequency & range checks)
- Bulk operations (copy EQ, normalize loudness)
- JSON schema + validate command
- Preset extraction / cloning / multi‑select edits


---
