#!/usr/bin/env python3
"""
NAM Player Bank (.npb) configuration tool.

A .npb file (as observed) is a gzipped tar archive containing:
  - config.json (preset + global settings)
  - one or more .nam neural model files
  - impulse responses (.ir) and other assets (state.bin, etc.)

This tool provides convenient read / modify / write operations on config.json
without disturbing other archive members.

Commands:
  show <bank.npb>                 : Print formatted config.json to stdout
  export <bank.npb> <out.json>    : Extract config.json to a separate file
  update <bank.npb> <in.json>     : Replace config.json in the archive using JSON from file
  set <bank.npb> <json-pointer> <value> : In-place modify a single value (string/number/bool)
  get <bank.npb> <json-pointer>   : Print value at JSON pointer

JSON Pointer: RFC6901 style, e.g.
  /presets/0/name
  /presets/2/potiGain

For convenience, a leading '#' is ignored (so shell users can write '#/presets/0/name').

Safety:
  - The original file is backed up to <bank.npb>.bak before destructive updates.
  - Archive rewrite is atomic-ish: writes to temp then moves into place.

Limitations / future ideas:
  - No schema enforcement yet.
  - Could add validation + diff output.

"""
from __future__ import annotations
import argparse
import json
import os
import sys
import tarfile
import tempfile
import shutil
from typing import Any, Tuple

CONFIG_NAME = "config.json"

class NPBBank:
    def __init__(self, path: str):
        self.path = path
        if not os.path.isfile(path):
            raise FileNotFoundError(path)
        if not tarfile.is_tarfile(path):
            # tarfile.is_tarfile only works on uncompressed? We'll open with mode 'r:gz'
            pass

    def read_config(self) -> Any:
        with tarfile.open(self.path, "r:gz") as tf:
            try:
                member = tf.getmember(f"./{CONFIG_NAME}")
            except KeyError:
                # fallback without leading ./
                try:
                    member = tf.getmember(CONFIG_NAME)
                except KeyError:
                    raise RuntimeError(f"{CONFIG_NAME} not found in archive")
            data = tf.extractfile(member).read().decode("utf-8")
            return json.loads(data)

    def replace_config(self, new_config: Any):
        # Create temp tar with all original members except config.json, then add new one.
        dir_name = os.path.dirname(self.path)
        base_name = os.path.basename(self.path)
        fd, tmp_path = tempfile.mkstemp(prefix=base_name+".", suffix=".tmp", dir=dir_name)
        os.close(fd)
        try:
            with tarfile.open(self.path, "r:gz") as tf_in, \
                 tarfile.open(tmp_path, "w:gz") as tf_out:
                for member in tf_in.getmembers():
                    name_norm = member.name.lstrip("./")
                    if name_norm == CONFIG_NAME:
                        continue  # skip old config
                    extracted = tf_in.extractfile(member) if member.isfile() else None
                    tf_out.addfile(member, extracted)
                # Add new config
                data = json.dumps(new_config, indent=4, sort_keys=False).encode("utf-8")
                info = tarfile.TarInfo(name=f"./{CONFIG_NAME}")
                info.size = len(data)
                tf_out.addfile(info, io_bytes(data))
            # Backup original
            backup = self.path + ".bak"
            if not os.path.exists(backup):
                shutil.copy2(self.path, backup)
            # Replace
            os.replace(tmp_path, self.path)
        finally:
            if os.path.exists(tmp_path):
                try: os.remove(tmp_path)
                except OSError: pass


def io_bytes(data: bytes):
    import io
    return io.BytesIO(data)

# JSON Pointer utilities

def json_pointer_get(doc: Any, pointer: str) -> Any:
    if pointer in ('', '/'): return doc
    if pointer.startswith('#'):
        pointer = pointer[1:]
    if not pointer.startswith('/'):
        raise ValueError("Pointer must start with '/' (after optional '#')")
    parts = [p.replace('~1','/').replace('~0','~') for p in pointer.split('/')[1:]]
    cur = doc
    for p in parts:
        if isinstance(cur, list):
            try:
                idx = int(p)
            except ValueError:
                raise KeyError(f"List index expected, got '{p}'")
            try:
                cur = cur[idx]
            except IndexError:
                raise KeyError(f"Index {idx} out of range")
        elif isinstance(cur, dict):
            if p not in cur: raise KeyError(f"Key '{p}' not found")
            cur = cur[p]
        else:
            raise KeyError(f"Cannot descend into non-container at '{p}'")
    return cur

def json_pointer_set(doc: Any, pointer: str, value: Any):
    if pointer in ('', '/'): raise ValueError("Refusing to overwrite root with scalar")
    if pointer.startswith('#'):
        pointer = pointer[1:]
    if not pointer.startswith('/'):
        raise ValueError("Pointer must start with '/' (after optional '#')")
    parts = [p.replace('~1','/').replace('~0','~') for p in pointer.split('/')[1:]]
    cur = doc
    for i, p in enumerate(parts):
        last = i == len(parts) - 1
        if isinstance(cur, list):
            try: idx = int(p)
            except ValueError: raise KeyError(f"List index expected, got '{p}'")
            if idx < 0 or idx >= len(cur):
                raise KeyError(f"Index {idx} out of range")
            if last:
                cur[idx] = value
            else:
                cur = cur[idx]
        elif isinstance(cur, dict):
            if p not in cur:
                raise KeyError(f"Key '{p}' not found")
            if last:
                cur[p] = value
            else:
                cur = cur[p]
        else:
            raise KeyError(f"Cannot descend into non-container at '{p}'")


def coerce_value(raw: str) -> Any:
    # Try bool, null, int, float, else string
    lowered = raw.lower()
    if lowered == 'true': return True
    if lowered == 'false': return False
    if lowered == 'null': return None
    try:
        if raw.startswith('0') and raw != '0' and not raw.startswith('0.'):
            # keep as string (avoid octal confusion)
            pass
        else:
            i = int(raw)
            return i
    except ValueError:
        pass
    try:
        f = float(raw)
        return f
    except ValueError:
        return raw


def cmd_show(args):
    bank = NPBBank(args.bank)
    cfg = bank.read_config()
    json.dump(cfg, sys.stdout, indent=4)
    print()


def cmd_export(args):
    bank = NPBBank(args.bank)
    cfg = bank.read_config()
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=4)
    print(f"Exported config to {args.output}")


def cmd_update(args):
    bank = NPBBank(args.bank)
    with open(args.input, 'r', encoding='utf-8') as f:
        new_cfg = json.load(f)
    bank.replace_config(new_cfg)
    print("Updated config.json inside bank (backup created if not already present).")


def cmd_get(args):
    bank = NPBBank(args.bank)
    cfg = bank.read_config()
    val = json_pointer_get(cfg, args.pointer)
    if isinstance(val, (dict, list)):
        json.dump(val, sys.stdout, indent=2)
        print()
    else:
        print(val)


def cmd_set(args):
    bank = NPBBank(args.bank)
    cfg = bank.read_config()
    value = coerce_value(args.value)
    json_pointer_set(cfg, args.pointer, value)
    bank.replace_config(cfg)
    print(f"Set {args.pointer} = {value!r}")


def build_parser():
    p = argparse.ArgumentParser(description="NAM .npb config tool")
    sub = p.add_subparsers(dest='cmd', required=True)

    s = sub.add_parser('show', help='Print config.json')
    s.add_argument('bank')
    s.set_defaults(func=cmd_show)

    s = sub.add_parser('export', help='Export config.json to a file')
    s.add_argument('bank')
    s.add_argument('output')
    s.set_defaults(func=cmd_export)

    s = sub.add_parser('update', help='Replace config.json from external JSON file')
    s.add_argument('bank')
    s.add_argument('input')
    s.set_defaults(func=cmd_update)

    s = sub.add_parser('get', help='Get value at JSON pointer')
    s.add_argument('bank')
    s.add_argument('pointer')
    s.set_defaults(func=cmd_get)

    s = sub.add_parser('set', help='Set value at JSON pointer')
    s.add_argument('bank')
    s.add_argument('pointer')
    s.add_argument('value')
    s.set_defaults(func=cmd_set)

    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main())
