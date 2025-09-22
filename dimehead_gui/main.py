from __future__ import annotations
import sys
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QMessageBox, QTableView, QStatusBar, QToolBar, QSplitter, QWidget, QColorDialog
)
from PySide6.QtGui import QAction, QColor
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, Signal

import dimehead_bank as db
from .global_panel import GlobalSettingsPanel

class PresetTableModel(QAbstractTableModel):
    HEADERS = ["#", "Name", "Model (nam)", "IR", "Gain", "VolNorm", "LED"]
    dirtyChanged = Signal(bool)

    def __init__(self, bank: db.Bank | None = None):
        super().__init__()
        self.bank = bank

    def set_bank(self, bank: db.Bank):
        self.beginResetModel()
        self.bank = bank
        self.endResetModel()

    # Basic model implementation
    def rowCount(self, parent=QModelIndex()):
        if not self.bank: return 0
        return len(self.bank.config.get('presets', []))

    def columnCount(self, parent=QModelIndex()):
        return len(self.HEADERS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.HEADERS[section]
        return None

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid() or not self.bank:
            return None
        presets = self.bank.config.get('presets', [])
        if index.row() >= len(presets):
            return None
        preset = presets[index.row()]
        col = index.column()
        if role == Qt.DisplayRole:
            if col == 0:
                return index.row()
            if col == 1:
                return preset.get('name', '')
            if col == 2:
                return preset.get('nam', '')
            if col == 3:
                return preset.get('ir', '')
            if col == 4:
                return f"{preset.get('potiGain', 0):.2f}"
            if col == 5:
                return 'Y' if preset.get('volNormalizeEnabled') else ''
            if col == 6:
                # Show hex RGB
                val = preset.get('ledColor')
                if isinstance(val, int):
                    return f"#{val:06X}"
                return ''
        if role == Qt.BackgroundRole and col == 6:
            val = preset.get('ledColor')
            if isinstance(val, int):
                r = (val >> 16) & 0xFF
                g = (val >> 8) & 0xFF
                b = val & 0xFF
                return QColor(r, g, b)
        return None

    # Combined flags: selection, edit (Name), drag for all rows, drop on first column
    def flags(self, index: QModelIndex):  # merged editing + dnd
        if not index.isValid():
            return Qt.ItemIsEnabled | Qt.ItemIsDropEnabled
        base = Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsDragEnabled
        if index.column() == 1:
            base |= Qt.ItemIsEditable
        if index.column() == 0:
            base |= Qt.ItemIsDropEnabled
        return base

    def setData(self, index: QModelIndex, value, role=Qt.EditRole):
        if not self.bank or role != Qt.EditRole or index.column() != 1:
            return False
        presets = self.bank.config.get('presets', [])
        if index.row() >= len(presets):
            return False
        new_name = str(value).strip()
        if not new_name:
            return False
        preset = presets[index.row()]
        old_name = preset.get('name', '')
        if new_name == old_name:
            return False
        preset['name'] = new_name
        self.dataChanged.emit(index, index, [Qt.DisplayRole])
        self.dirtyChanged.emit(True)
        return True

    # Reordering support
    def move_row(self, src_row: int, dst_row: int) -> bool:
        """Move a single row to dst_row (after adjustment) using beginMoveRows.
        dst_row is the *target index after removal* semantics expected by Qt.
        """
        if not self.bank:
            return False
        presets = self.bank.config.get('presets', [])
        count = len(presets)
        if src_row < 0 or src_row >= count or dst_row < 0 or dst_row >= count:
            return False
        if src_row == dst_row:
            return False
        # Qt beginMoveRows requires parent indexes
        parent = QModelIndex()
        # Adjust destination for removal if moving downward
        if dst_row > src_row:
            adj_dst = dst_row + 1  # because removal shifts indices up
        else:
            adj_dst = dst_row
        if not self.beginMoveRows(parent, src_row, src_row, parent, adj_dst):
            return False
        item = presets.pop(src_row)
        # Insert at the final intended index. When moving downward we intentionally
        # do NOT decrement dst_row; the desired final index remains dst_row because
        # items after the source shifted left by one after the pop.
        presets.insert(dst_row, item)
        self.endMoveRows()
        self.dirtyChanged.emit(True)
        return True

    # ---- Drag & Drop Reordering API ----
    def supportedDropActions(self):
        return Qt.MoveAction

    def mimeTypes(self):
        return ["application/x-dimehead-preset-index"]

    def mimeData(self, indexes):
        from PySide6.QtCore import QMimeData
        mime = QMimeData()
        # Use first row index only (row-based move)
        rows = sorted({i.row() for i in indexes})
        if rows:
            mime.setData("application/x-dimehead-preset-index", str(rows[0]).encode('utf-8'))
        return mime

    def dropMimeData(self, data, action, row, column, parent):
        if action != Qt.MoveAction:
            return False
        if not data.hasFormat("application/x-dimehead-preset-index"):
            return False
        try:
            src_row = int(bytes(data.data("application/x-dimehead-preset-index")).decode('utf-8'))
        except Exception:
            return False
        # Determine destination row: Qt supplies 'row' or parent.row()
        if row == -1:
            if parent and parent.isValid():
                dst_row = parent.row()
            else:
                # Dropped at empty space -> treat as append (end)
                dst_row = self.rowCount() - 1
        else:
            dst_row = row
        # If dropping below original when intending to move after, adjust
        if dst_row != src_row:
            return self.move_row(src_row, dst_row)
        return False

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NAM Player Manager")
        self.table = QTableView()
        self.model = PresetTableModel()
        self.model.dirtyChanged.connect(self.notify_dirty)
        self.table.setModel(self.model)
        self.table.doubleClicked.connect(self._maybe_edit)
        # Update move buttons when selection changes
        self.table.selectionModel().selectionChanged.connect(lambda *_: self._update_move_actions())
        # Enable internal drag & drop row reordering
        self.table.setDragDropMode(QTableView.InternalMove)
        self.table.setDragEnabled(True)
        self.table.setAcceptDrops(True)
        self.table.setDefaultDropAction(Qt.MoveAction)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        # Global settings panel
        self.global_panel = GlobalSettingsPanel()
        self.global_panel.changed.connect(self._on_global_changed)
        splitter = QSplitter()
        splitter.addWidget(self.table)
        splitter.addWidget(self.global_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        self.setCentralWidget(splitter)
        self._dirty = False
        self._save_act = None
        self._create_actions()
        self.setStatusBar(QStatusBar())

    def _create_actions(self):
        tb = QToolBar("Main")
        self.addToolBar(tb)
        open_act = QAction("Open Bank", self)
        open_act.triggered.connect(self.open_bank)
        tb.addAction(open_act)
        tb.addSeparator()
        version_act = QAction("Save New Version", self)
        version_act.triggered.connect(self.save_new_version)
        version_act.setEnabled(False)
        tb.addAction(version_act)
        self._save_act = version_act

        overwrite_act = QAction("Overwrite", self)
        overwrite_act.triggered.connect(self.overwrite_bank)
        overwrite_act.setEnabled(False)
        # Mark visually (Qt doesn't have native color on QAction text, so rely on confirmation)
        tb.addAction(overwrite_act)
        self._overwrite_act = overwrite_act
        tb.addSeparator()
        up_act = QAction("Move Up", self)
        up_act.triggered.connect(self.move_up)
        tb.addAction(up_act)
        down_act = QAction("Move Down", self)
        down_act.triggered.connect(self.move_down)
        tb.addAction(down_act)
        self._move_up_act = up_act
        self._move_down_act = down_act

    def open_bank(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open .npb Bank", str(Path.cwd()), "NAM Banks (*.npb *.tar.gz)")
        if not path:
            return
        try:
            bank = db.load_bank(path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load bank:\n{e}")
            return
        self.model.set_bank(bank)
        self.statusBar().showMessage(f"Loaded {Path(path).name} ({len(bank.config.get('presets', []))} presets)")
        # Load global settings
        if bank and bank.config:
            self.global_panel.load_config(bank.config)
        else:
            self.global_panel.clear()
        self._update_move_actions()

    def _current_path(self) -> Path | None:
        if self.model.bank:
            return Path(self.model.bank.path)
        return None

    def save_new_version(self):
        bank = self.model.bank
        if not bank:
            QMessageBox.information(self, "No Bank", "No bank loaded")
            return
        base_path = Path(bank.path)
        new_path = self._next_version_path(base_path)
        try:
            db.save_bank_as(bank, str(new_path))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save new version:\n{e}")
            return
        # Update bank path to new version for subsequent overwrites / increments
        bank.path = str(new_path)
        self.statusBar().showMessage(f"Saved new version: {new_path.name}")
        self.notify_dirty(False)

    def overwrite_bank(self):
        bank = self.model.bank
        if not bank:
            QMessageBox.information(self, "No Bank", "No bank loaded")
            return
        resp = QMessageBox.warning(
            self,
            "Confirm Overwrite",
            "This will OVERWRITE the existing bank file in place.\nA .bak may already exist from previous operations. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if resp != QMessageBox.StandardButton.Yes:
            return
        try:
            db.save_bank(bank)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to overwrite bank:\n{e}")
            return
        self.statusBar().showMessage("Overwrote existing bank")
        self.notify_dirty(False)

    def _next_version_path(self, path: Path) -> Path:
        """Generate next versioned filename by inserting _v### before extension.
        Example: mybank.npb -> mybank_v001.npb, mybank_v002.npb, etc.
        If file already has _vNNN, increment.
        """
        stem = path.stem
        suffix = path.suffix  # .npb
        import re
        m = re.search(r"^(.*)_v(\d{3})$", stem)
        if m:
            base = m.group(1)
            num = int(m.group(2))
        else:
            base = stem
            num = 0
        while True:
            num += 1
            candidate = path.with_name(f"{base}_v{num:03d}{suffix}")
            if not candidate.exists():
                return candidate

    def notify_dirty(self, dirty: bool):
        self._dirty = dirty
        if self._save_act:
            self._save_act.setEnabled(dirty)
        if hasattr(self, '_overwrite_act') and self._overwrite_act:
            self._overwrite_act.setEnabled(dirty)
        if dirty:
            self.setWindowTitle("* NAM Player Manager")
        else:
            self.setWindowTitle("NAM Player Manager")
        self._update_move_actions()

    def _on_global_changed(self, key: str, value):
        # Mark dirty if a global setting changed
        if not self._dirty:
            self.notify_dirty(True)

    def _maybe_edit(self, index: QModelIndex):
        if index.column() == 1:
            self.table.edit(index)
        elif index.column() == 6:  # LED color picker
            self._edit_led_color(index.row())

    def _edit_led_color(self, row: int):
        if not self.model.bank:
            return
        presets = self.model.bank.config.get('presets', [])
        if row < 0 or row >= len(presets):
            return
        preset = presets[row]
        current = preset.get('ledColor')
        if isinstance(current, int):
            r = (current >> 16) & 0xFF
            g = (current >> 8) & 0xFF
            b = current & 0xFF
            initial = QColor(r, g, b)
        else:
            initial = QColor(255, 170, 0)
        color = QColorDialog.getColor(initial, self, "Select LED Color")
        if not color.isValid():
            return
        new_val = (color.red() << 16) | (color.green() << 8) | color.blue()
        if new_val == current:
            return
        preset['ledColor'] = new_val
        # Emit dataChanged for that cell
        idx = self.model.index(row, self.model.HEADERS.index("LED"))
        self.model.dataChanged.emit(idx, idx, [Qt.DisplayRole, Qt.BackgroundRole])
        self.notify_dirty(True)

    def _selected_row(self) -> int:
        sel = self.table.selectionModel()
        if not sel:
            return -1
        indexes = sel.selectedRows()
        if not indexes:
            return -1
        return indexes[0].row()

    def move_up(self):
        row = self._selected_row()
        if row <= 0:
            return
        if self.model.move_row(row, row - 1):
            self.table.selectRow(row - 1)

    def move_down(self):
        row = self._selected_row()
        if row < 0:
            return
        last = self.model.rowCount() - 1
        if row >= last:
            return
        if self.model.move_row(row, row + 1):
            self.table.selectRow(row + 1)

    def _update_move_actions(self):
        if not hasattr(self, '_move_up_act'):
            return
        row = self._selected_row()
        count = self.model.rowCount()
        if row < 0:
            self._move_up_act.setEnabled(False)
            self._move_down_act.setEnabled(False)
            return
        self._move_up_act.setEnabled(row > 0)
        self._move_down_act.setEnabled(row < count - 1)


def run():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.resize(1000, 500)
    win.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    run()
