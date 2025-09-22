from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget, QFormLayout, QSpinBox, QDoubleSpinBox, QCheckBox, QLabel, QHBoxLayout
)
from PySide6.QtCore import Signal, Qt

# Keys we expose and their widget types / ranges
# (Inferred ranges; adjust as more empirical data appears.)
_GLOBAL_SPECS = {
    "lcdBrightness": {"type": "int", "min": 0, "max": 10, "step": 1},
    "ledBrightness": {"type": "int", "min": 0, "max": 10, "step": 1},
    "lineoutVolume": {"type": "float", "min": 0.0, "max": 1.0, "step": 0.01, "decimals": 2},
    "lineoutPosition": {"type": "int", "min": 0, "max": 5, "step": 1},
    "midiChannelIndex": {"type": "int", "min": 0, "max": 15, "step": 1},  # 0-based (0..15) typical
    "footswitchModeIndex": {"type": "int", "min": 0, "max": 10, "step": 1},
    "footswitchLongpress": {"type": "int", "min": 0, "max": 5000, "step": 100},  # ms? guess
    "enableRotateBack": {"type": "bool"},
    "enableStagemodeEncoder": {"type": "bool"},
}

class GlobalSettingsPanel(QWidget):
    changed = Signal(str, object)  # key, new_value

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("GlobalSettingsPanel")
        self._widgets = {}
        self._suppress = False
        self._config_ref = None  # reference to live config dict (bank.config)

        form = QFormLayout()
        form.setContentsMargins(6, 6, 6, 6)
        form.setSpacing(4)

        for key, spec in _GLOBAL_SPECS.items():
            w = self._create_widget_for_spec(key, spec)
            self._widgets[key] = w
            label = key
            form.addRow(label, w)

        # Display-only configVersion
        self._config_version_label = QLabel("-")
        form.addRow("configVersion", self._config_version_label)

        self.setLayout(form)
        self.setDisabled(True)  # disabled until a bank loads

    # Public API -------------------------------------------------------------
    def load_config(self, config: dict):
        self._config_ref = config
        self._suppress = True
        for key, spec in _GLOBAL_SPECS.items():
            if key not in self._widgets:
                continue
            widget = self._widgets[key]
            value = config.get(key)
            self._apply_value(widget, spec, value)
        self._config_version_label.setText(str(config.get("configVersion", "-")))
        self._suppress = False
        self.setDisabled(False)

    def clear(self):
        self._config_ref = None
        self._suppress = True
        for key, spec in _GLOBAL_SPECS.items():
            w = self._widgets.get(key)
            if not w:
                continue
            if spec["type"] == "bool":
                w.setChecked(False)
            elif spec["type"] == "int":
                w.setValue(spec.get("min", 0))
            elif spec["type"] == "float":
                w.setValue(spec.get("min", 0.0))
        self._config_version_label.setText("-")
        self._suppress = False
        self.setDisabled(True)

    # Internal helpers -------------------------------------------------------
    def _create_widget_for_spec(self, key: str, spec: dict):
        t = spec["type"]
        if t == "bool":
            cb = QCheckBox()
            cb.stateChanged.connect(lambda _state, k=key: self._on_bool_changed(k))
            return cb
        if t == "int":
            sb = QSpinBox()
            sb.setRange(spec.get("min", 0), spec.get("max", 999999))
            sb.setSingleStep(spec.get("step", 1))
            sb.valueChanged.connect(lambda _val, k=key: self._on_number_changed(k))
            return sb
        if t == "float":
            dsb = QDoubleSpinBox()
            dsb.setRange(spec.get("min", 0.0), spec.get("max", 1.0))
            dsb.setSingleStep(spec.get("step", 0.01))
            dsb.setDecimals(spec.get("decimals", 3))
            dsb.valueChanged.connect(lambda _val, k=key: self._on_number_changed(k))
            return dsb
        # Fallback label if unknown
        return QLabel("(unsupported)")

    def _apply_value(self, widget, spec, value):
        if value is None:
            return
        t = spec["type"]
        if t == "bool":
            widget.setChecked(bool(value))
        elif t == "int":
            try:
                widget.setValue(int(value))
            except Exception:
                pass
        elif t == "float":
            try:
                widget.setValue(float(value))
            except Exception:
                pass

    # Change handlers --------------------------------------------------------
    def _on_bool_changed(self, key: str):
        if self._suppress or not self._config_ref:
            return
        w: QCheckBox = self._widgets[key]
        new_val = bool(w.isChecked())
        self._config_ref[key] = new_val
        self.changed.emit(key, new_val)

    def _on_number_changed(self, key: str):
        if self._suppress or not self._config_ref:
            return
        spec = _GLOBAL_SPECS[key]
        w = self._widgets[key]
        if spec["type"] == "int":
            new_val = int(w.value())
        else:
            new_val = float(w.value())
        self._config_ref[key] = new_val
        self.changed.emit(key, new_val)

__all__ = ["GlobalSettingsPanel"]
