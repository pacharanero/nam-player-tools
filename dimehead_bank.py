"""Core library for loading and saving Dimehead NAM Player .npb banks.

This module factors out archive + config logic to be reused by both CLI and GUI.

Design goals:
- Pure functions / lightweight classes
- No PySide imports (keeps model layer UI-agnostic)
- Explicit errors for robust GUI error dialogs
"""
from __future__ import annotations
import tarfile
import json
import os
import io
import tempfile
import shutil
from dataclasses import dataclass, field
from typing import Any, List, Dict, Optional

CONFIG_NAME = "config.json"

class BankError(Exception):
    pass

@dataclass
class Asset:
    name: str
    size: int
    type: str  # 'file', 'dir', 'other'

@dataclass
class Bank:
    path: str
    config: Dict[str, Any]
    assets: List[Asset] = field(default_factory=list)
    original_config_json: str = ""  # for diffing

    def diff_config(self) -> Dict[str, Any]:
        """Return a naive diff structure {changed: {pointer: (old, new)}}."""
        try:
            old = json.loads(self.original_config_json)
        except Exception:
            return {"changed": {}, "added": {}, "removed": {}}
        new = self.config
        changed = {}
        added = {}
        removed = {}
        # Shallow pointer diff (top-level + presets list length + preset names). Extend later.
        for k in set(old.keys()) | set(new.keys()):
            if k not in old:
                added[f"/{k}"] = new[k]
            elif k not in new:
                removed[f"/{k}"] = old[k]
            else:
                if old[k] != new[k]:
                    # Special-case presets for name changes
                    if k == 'presets' and isinstance(old[k], list) and isinstance(new[k], list):
                        if len(old[k]) != len(new[k]):
                            changed['/presets'] = (len(old[k]), len(new[k]))
                        for i, (po, pn) in enumerate(zip(old[k], new[k])):
                            if isinstance(po, dict) and isinstance(pn, dict) and po.get('name') != pn.get('name'):
                                changed[f"/presets/{i}/name"] = (po.get('name'), pn.get('name'))
                    else:
                        changed[f"/{k}"] = (old[k], new[k])
        return {"changed": changed, "added": added, "removed": removed}


def _tar_members(path: str):
    with tarfile.open(path, "r:gz") as tf:
        for m in tf.getmembers():
            yield m

def load_bank(path: str) -> Bank:
    if not os.path.isfile(path):
        raise BankError(f"File not found: {path}")
    try:
        with tarfile.open(path, "r:gz") as tf:
            try:
                cfg_member = tf.getmember(f"./{CONFIG_NAME}")
            except KeyError:
                try:
                    cfg_member = tf.getmember(CONFIG_NAME)
                except KeyError:
                    raise BankError("config.json not found in archive")
            raw = tf.extractfile(cfg_member).read().decode('utf-8')
            config = json.loads(raw)
            assets = []
            for m in tf.getmembers():
                if m.name.lstrip('./') == CONFIG_NAME:
                    continue
                if m.isdir(): t = 'dir'
                elif m.isfile(): t = 'file'
                else: t = 'other'
                assets.append(Asset(name=m.name, size=getattr(m, 'size', 0), type=t))
    except tarfile.TarError as e:
        raise BankError(f"Failed to read archive: {e}")
    return Bank(path=path, config=config, assets=assets, original_config_json=raw)


def save_bank(bank: Bank, backup: bool = True):
    path = bank.path
    dir_name = os.path.dirname(path) or '.'
    fd, tmp_path = tempfile.mkstemp(prefix=os.path.basename(path)+'.', suffix='.tmp', dir=dir_name)
    os.close(fd)
    try:
        with tarfile.open(path, 'r:gz') as tf_in, tarfile.open(tmp_path, 'w:gz') as tf_out:
            for member in tf_in.getmembers():
                name_norm = member.name.lstrip('./')
                if name_norm == CONFIG_NAME:
                    continue
                extracted = tf_in.extractfile(member) if member.isfile() else None
                tf_out.addfile(member, extracted)
            data = json.dumps(bank.config, indent=4).encode('utf-8')
            info = tarfile.TarInfo(name=f'./{CONFIG_NAME}')
            info.size = len(data)
            tf_out.addfile(info, io.BytesIO(data))
        if backup and not os.path.exists(path + '.bak'):
            shutil.copy2(path, path + '.bak')
        os.replace(tmp_path, path)
        bank.original_config_json = json.dumps(bank.config)
    finally:
        if os.path.exists(tmp_path):
            try: os.remove(tmp_path)
            except OSError: pass


def save_bank_as(bank: Bank, dest_path: str, backup_source: bool = False):
    """Save bank config into a new archive at dest_path.

    Reads all non-config members from the original bank.path and writes them
    plus updated config.json to the new dest_path. Optionally create a .bak for
    the original (controlled by backup_source).
    """
    src_path = bank.path
    if not os.path.isfile(src_path):
        raise BankError(f"Source bank missing: {src_path}")
    dir_name = os.path.dirname(dest_path) or '.'
    fd, tmp_path = tempfile.mkstemp(prefix=os.path.basename(dest_path)+'.', suffix='.tmp', dir=dir_name)
    os.close(fd)
    try:
        with tarfile.open(src_path, 'r:gz') as tf_in, tarfile.open(tmp_path, 'w:gz') as tf_out:
            for member in tf_in.getmembers():
                name_norm = member.name.lstrip('./')
                if name_norm == CONFIG_NAME:
                    continue
                extracted = tf_in.extractfile(member) if member.isfile() else None
                tf_out.addfile(member, extracted)
            data = json.dumps(bank.config, indent=4).encode('utf-8')
            info = tarfile.TarInfo(name=f'./{CONFIG_NAME}')
            info.size = len(data)
            tf_out.addfile(info, io.BytesIO(data))
        os.replace(tmp_path, dest_path)
        if backup_source and not os.path.exists(src_path + '.bak'):
            shutil.copy2(src_path, src_path + '.bak')
    finally:
        if os.path.exists(tmp_path):
            try: os.remove(tmp_path)
            except OSError: pass
