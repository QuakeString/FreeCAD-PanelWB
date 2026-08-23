"""Custom task-panel UI for PanelWB (GUI only)."""

import FreeCAD as App
import FreeCADGui as Gui

from PySide import QtWidgets  # FreeCAD ships a PySide alias package

from freecad.panelwb import enclosure as enc


class EnclosureTaskPanel:
    """Quick editor with the everyday parameters, applied live."""

    def __init__(self, obj):
        self.obj = obj
        w = QtWidgets.QWidget()
        w.setWindowTitle("Enclosure")
        form = QtWidgets.QFormLayout(w)

        self.preset = QtWidgets.QComboBox()
        self.preset.addItems(list(enc.PRESETS))
        self.preset.setCurrentText(obj.Preset)
        form.addRow("Preset", self.preset)

        self.family = QtWidgets.QComboBox()
        self.family.addItems(enc.FAMILIES)
        self.family.setCurrentText(obj.MountingType)
        form.addRow("Family", self.family)

        self.dims = {}
        for name in ("Width", "Height", "Depth"):
            spin = QtWidgets.QDoubleSpinBox()
            spin.setRange(50, 4000)
            spin.setSuffix(" mm")
            spin.setValue(getattr(obj, name).Value)
            form.addRow(name, spin)
            self.dims[name] = spin

        self.bays = QtWidgets.QSpinBox()
        self.bays.setRange(1, 12)
        self.bays.setValue(int(obj.BayCount))
        form.addRow("Bays", self.bays)

        self.doorcfg = QtWidgets.QComboBox()
        self.doorcfg.addItems(enc.DOOR_CONFIGS)
        self.doorcfg.setCurrentText(obj.DoorConfig)
        form.addRow("Doors", self.doorcfg)

        self.doorstyle = QtWidgets.QComboBox()
        self.doorstyle.addItems(enc.DOOR_STYLES)
        self.doorstyle.setCurrentText(obj.DoorStyle)
        form.addRow("Door style", self.doorstyle)

        self.lock = QtWidgets.QComboBox()
        self.lock.addItems(enc.LOCK_TYPES)
        self.lock.setCurrentText(obj.LockType)
        form.addRow("Lock", self.lock)

        self.ip = QtWidgets.QComboBox()
        self.ip.addItems(enc.IP_RATINGS)
        self.ip.setCurrentText(obj.IPRating)
        form.addRow("IP rating", self.ip)

        self.plinth = QtWidgets.QComboBox()
        self.plinth.addItems(enc.PLINTHS)
        self.plinth.setCurrentText(obj.Plinth)
        form.addRow("Plinth", self.plinth)

        self.inner = QtWidgets.QCheckBox("Inner door")
        self.inner.setChecked(obj.InnerDoor)
        form.addRow(self.inner)

        self.door_btn = QtWidgets.QPushButton("Open / close front door")
        form.addRow(self.door_btn)

        self.warn = QtWidgets.QLabel()
        self.warn.setWordWrap(True)
        self.warn.setStyleSheet("color: #b05000;")
        form.addRow(self.warn)

        self.form = w

        self.preset.currentTextChanged.connect(self._apply)
        self.family.currentTextChanged.connect(self._apply)
        for spin in self.dims.values():
            spin.valueChanged.connect(self._apply)
        self.bays.valueChanged.connect(self._apply)
        for combo in (self.doorcfg, self.doorstyle, self.lock,
                      self.ip, self.plinth):
            combo.currentTextChanged.connect(self._apply)
        self.inner.toggled.connect(self._apply)
        self.door_btn.clicked.connect(
            lambda: enc._toggle(self.obj, "FrontDoorAngle"))
        self._refresh_warnings()

    def _apply(self, *_):
        obj = self.obj
        if obj.Preset != self.preset.currentText():
            obj.Preset = self.preset.currentText()
            # preset changed family/dims: sync widgets back
            self.family.blockSignals(True)
            self.family.setCurrentText(obj.MountingType)
            self.family.blockSignals(False)
            for name, spin in self.dims.items():
                spin.blockSignals(True)
                spin.setValue(getattr(obj, name).Value)
                spin.blockSignals(False)
        else:
            obj.MountingType = self.family.currentText()
            for name, spin in self.dims.items():
                setattr(obj, name, spin.value())
        obj.BayCount = self.bays.value()
        obj.DoorConfig = self.doorcfg.currentText()
        obj.DoorStyle = self.doorstyle.currentText()
        obj.LockType = self.lock.currentText()
        obj.IPRating = self.ip.currentText()
        obj.Plinth = self.plinth.currentText()
        obj.InnerDoor = self.inner.isChecked()
        obj.Document.recompute()
        self._refresh_warnings()

    def _refresh_warnings(self):
        self.warn.setText("\n".join(self.obj.Warnings))

    def accept(self):
        Gui.Control.closeDialog()
        return True

    def reject(self):
        Gui.Control.closeDialog()
        return True


def show_enclosure_dialog(obj):
    if Gui.Control.activeDialog():
        Gui.Control.closeDialog()
    Gui.Control.showDialog(EnclosureTaskPanel(obj))
