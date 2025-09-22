from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QFormLayout, QLineEdit, QDoubleSpinBox, QSpinBox, QCheckBox, QLabel, QColorDialog, QSlider
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

class PresetEditDialog(QDialog):
    def __init__(self, preset: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Preset")
        # Resize modal to 90% of parent width if possible
        if parent is not None and hasattr(parent, 'width'):
            parent_width = parent.width()
            self.resize(int(parent_width * 0.9), 0)
        self._original = preset
        self._working = preset.copy()  # Work on a copy, only apply on OK
        self._widgets = {}
        layout = QVBoxLayout()
        # Use a horizontal layout to split into two columns
        hbox = QHBoxLayout()
        form_left = QFormLayout()
        form_right = QFormLayout()


        # --- Left Column ---
        name_edit = QLineEdit(self._working.get('name', ''))
        form_left.addRow("Name", name_edit)
        self._widgets['name'] = name_edit

        nam_edit = QLineEdit(self._working.get('nam', ''))
        form_left.addRow("Main NAM File", nam_edit)
        self._widgets['nam'] = nam_edit

        ir_edit = QLineEdit(self._working.get('ir', ''))
        form_left.addRow("IR", ir_edit)
        self._widgets['ir'] = ir_edit

        # Noise Gate Threshold (slider + spinbox)
        ngate = QDoubleSpinBox()
        ngate.setRange(-80.0, -30.0)
        ngate.setDecimals(1)
        ngate.setValue(float(self._working.get('gateThreshold', -80)))
        self.ngate_slider = QSlider(Qt.Horizontal)
        self.ngate_slider.setRange(-800, -300)
        self.ngate_slider.setValue(int(ngate.value() * 10))
        def sync_ngate_spin(val):
            ngate.setValue(val / 10)
        def sync_ngate_slider(val):
            self.ngate_slider.setValue(int(val * 10))
        self.ngate_slider.valueChanged.connect(sync_ngate_spin)
        ngate.valueChanged.connect(sync_ngate_slider)
        ngate_row = QHBoxLayout()
        ngate_row.addWidget(ngate)
        ngate_row.addWidget(self.ngate_slider)
        form_left.addRow("Noise Gate Threshold (dB)", ngate_row)
        self._widgets['gateThreshold'] = ngate

        # Gain (slider + spinbox)
        gain_edit = QDoubleSpinBox()
        gain_edit.setRange(0.0, 10.0)
        gain_edit.setDecimals(2)
        gain_edit.setValue(float(self._working.get('potiGain', 0)))
        self.gain_slider = QSlider(Qt.Horizontal)
        self.gain_slider.setRange(0, 1000)
        self.gain_slider.setValue(int(gain_edit.value() * 100))
        def sync_gain_spin(val):
            gain_edit.setValue(val / 100)
        def sync_gain_slider(val):
            self.gain_slider.setValue(int(val * 100))
        self.gain_slider.valueChanged.connect(sync_gain_spin)
        gain_edit.valueChanged.connect(sync_gain_slider)
        gain_row = QHBoxLayout()
        gain_row.addWidget(gain_edit)
        gain_row.addWidget(self.gain_slider)
        form_left.addRow("Gain", gain_row)
        self._widgets['potiGain'] = gain_edit

        boost_enable = QCheckBox()
        boost_enable.setChecked(bool(self._working.get('boostEnable', False)))
        form_left.addRow("Boost/FX Enable", boost_enable)
        self._widgets['boostEnable'] = boost_enable

        boost_nam = QLineEdit(self._working.get('boostNam', ''))
        form_left.addRow("Boost NAM File", boost_nam)
        self._widgets['boostNam'] = boost_nam

        boost_gain = QDoubleSpinBox()
        boost_gain.setRange(0.0, 10.0)
        boost_gain.setDecimals(2)
        boost_gain.setValue(float(self._working.get('potiBoostGain', 0)))
        form_left.addRow("Boost Gain", boost_gain)
        self._widgets['potiBoostGain'] = boost_gain

        boost_bass = QDoubleSpinBox()
        boost_bass.setRange(-12.0, 12.0)
        boost_bass.setDecimals(2)
        boost_bass.setValue(float(self._working.get('potiBoostBass', 0)))
        form_left.addRow("Boost Bass", boost_bass)
        self._widgets['potiBoostBass'] = boost_bass

        boost_mids = QDoubleSpinBox()
        boost_mids.setRange(-12.0, 12.0)
        boost_mids.setDecimals(2)
        boost_mids.setValue(float(self._working.get('potiBoostMids', 0)))
        form_left.addRow("Boost Mids", boost_mids)
        self._widgets['potiBoostMids'] = boost_mids

        boost_treble = QDoubleSpinBox()
        boost_treble.setRange(-12.0, 12.0)
        boost_treble.setDecimals(2)
        boost_treble.setValue(float(self._working.get('potiBoostTreble', 0)))
        form_left.addRow("Boost Treble", boost_treble)
        self._widgets['potiBoostTreble'] = boost_treble

        # --- Right Column ---
        for band in range(1, 4):
            freq = QDoubleSpinBox()
            freq.setRange(20.0, 20000.0)
            freq.setDecimals(1)
            freq.setValue(float(self._working.get(f'eq{band}Freq', 1000)))
            form_right.addRow(f"EQ{band} Frequency (Hz)", freq)
            self._widgets[f'eq{band}Freq'] = freq

            q = QDoubleSpinBox()
            q.setRange(0.1, 10.0)
            q.setDecimals(2)
            q.setValue(float(self._working.get(f'eq{band}Q', 1.0)))
            form_right.addRow(f"EQ{band} Q", q)
            self._widgets[f'eq{band}Q'] = q

        volnorm_edit = QCheckBox()
        volnorm_edit.setChecked(bool(self._working.get('volNormalizeEnabled', False)))
        form_right.addRow("Volume Normalize", volnorm_edit)
        self._widgets['volNormalizeEnabled'] = volnorm_edit

        room_file = QLineEdit(self._working.get('roomReverbFile', ''))
        form_right.addRow("Room Reverb File", room_file)
        self._widgets['roomReverbFile'] = room_file

        room_mix = QDoubleSpinBox()
        room_mix.setRange(0.0, 1.0)
        room_mix.setDecimals(2)
        room_mix.setValue(float(self._working.get('roomMix', 0)))
        form_right.addRow("Room Mix", room_mix)
        self._widgets['roomMix'] = room_mix

        room_delay = QDoubleSpinBox()
        room_delay.setRange(0.0, 500.0)
        room_delay.setDecimals(1)
        room_delay.setValue(float(self._working.get('roomDelay', 0)))
        form_right.addRow("Room Delay (ms)", room_delay)
        self._widgets['roomDelay'] = room_delay

        room_trem = QDoubleSpinBox()
        room_trem.setRange(0.0, 1.0)
        room_trem.setDecimals(2)
        room_trem.setValue(float(self._working.get('roomTremolo', 0)))
        form_right.addRow("Room Tremolo", room_trem)
        self._widgets['roomTremolo'] = room_trem

        # LED Color: editable hex + color preview + picker
        led_color_val = self._working.get('ledColor', 0)
        if isinstance(led_color_val, int):
            led_hex = f"#{led_color_val:06X}"
        else:
            led_hex = "#FFA000"
        led_edit = QLineEdit(led_hex)
        led_edit.setMaxLength(7)
        led_edit.setFixedWidth(80)
        led_preview = QLabel()
        led_preview.setFixedSize(32, 18)
        def update_led_preview():
            text = led_edit.text()
            if text.startswith('#') and len(text) == 7:
                try:
                    color = QColor(text)
                    led_preview.setStyleSheet(f"background: {text}; border: 1px solid #888;")
                except Exception:
                    led_preview.setStyleSheet("")
            else:
                led_preview.setStyleSheet("")
        update_led_preview()
        led_edit.textChanged.connect(update_led_preview)
        pick_btn = QPushButton("Pick")
        def pick_color():
            col = QColor(led_edit.text()) if QColor(led_edit.text()).isValid() else QColor(255, 170, 0)
            dlg = QColorDialog(col, self)
            if dlg.exec():
                c = dlg.currentColor()
                led_edit.setText(c.name().upper())
        pick_btn.clicked.connect(pick_color)
        led_row = QHBoxLayout()
        led_row.addWidget(led_edit)
        led_row.addWidget(led_preview)
        led_row.addWidget(pick_btn)
        led_row.addStretch(1)
        form_right.addRow("LED Color", led_row)
        self._widgets['ledColor'] = led_edit

        hbox.addLayout(form_left)
        hbox.addLayout(form_right)
        layout.addLayout(hbox)

    # (Buttons remain at the bottom)
        btns = QHBoxLayout()
        ok_btn = QPushButton("OK")
        discard_btn = QPushButton("Discard")
        btns.addWidget(ok_btn)
        btns.addWidget(discard_btn)
        layout.addLayout(btns)
        self.setLayout(layout)

        ok_btn.clicked.connect(self.accept)
        discard_btn.clicked.connect(self.reject)

    def get_result(self):
        # Return a dict of updated values
        result = self._original.copy()
        result['name'] = self._widgets['name'].text()
        result['nam'] = self._widgets['nam'].text()
        result['ir'] = self._widgets['ir'].text()
        result['gateThreshold'] = self.ngate_slider.value() / 10
        result['potiGain'] = self.gain_slider.value() / 100
        result['boostEnable'] = self._widgets['boostEnable'].isChecked()
        result['boostNam'] = self._widgets['boostNam'].text()
        result['potiBoostGain'] = self._widgets['potiBoostGain'].value()
        result['potiBoostBass'] = self._widgets['potiBoostBass'].value()
        result['potiBoostMids'] = self._widgets['potiBoostMids'].value()
        result['potiBoostTreble'] = self._widgets['potiBoostTreble'].value()
        for band in range(1, 4):
            result[f'eq{band}Freq'] = self._widgets[f'eq{band}Freq'].value()
            result[f'eq{band}Q'] = self._widgets[f'eq{band}Q'].value()
        result['volNormalizeEnabled'] = self._widgets['volNormalizeEnabled'].isChecked()
        result['roomReverbFile'] = self._widgets['roomReverbFile'].text()
        result['roomMix'] = self._widgets['roomMix'].value()
        result['roomDelay'] = self._widgets['roomDelay'].value()
        result['roomTremolo'] = self._widgets['roomTremolo'].value()
        # LED color: convert #RRGGBB to int
        led_text = self._widgets['ledColor'].text()
        if led_text.startswith('#') and len(led_text) == 7:
            try:
                result['ledColor'] = int(led_text[1:], 16)
            except Exception:
                pass
        return result
