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


class ComponentPicker(QtWidgets.QDialog):
    """Modeless library browser: pick a device, click Add, repeat."""

    def __init__(self, doc, rail=None, plate=None, parent=None):
        super().__init__(parent)
        self.doc = doc
        self.rail = rail
        self.plate = plate
        self.setWindowTitle("Add component")
        self.resize(380, 480)
        lay = QtWidgets.QVBoxLayout(self)

        self.search = QtWidgets.QLineEdit()
        self.search.setPlaceholderText("Filter…")
        lay.addWidget(self.search)

        self.listw = QtWidgets.QListWidget()
        lay.addWidget(self.listw)

        target = "rail: %s" % rail.Label if rail else (
            "plate: %s" % plate.Label if plate else "no target selected")
        lay.addWidget(QtWidgets.QLabel("Placing on %s" % target))

        btns = QtWidgets.QHBoxLayout()
        self.add_btn = QtWidgets.QPushButton("Add")
        close_btn = QtWidgets.QPushButton("Close")
        btns.addWidget(self.add_btn)
        btns.addWidget(close_btn)
        lay.addLayout(btns)

        from freecad.panelwb.components import load_library
        self.lib = load_library()
        self._fill("")
        self.search.textChanged.connect(self._fill)
        self.add_btn.clicked.connect(self._add)
        self.listw.itemDoubleClicked.connect(lambda *_: self._add())
        close_btn.clicked.connect(self.close)

    def _fill(self, text):
        self.listw.clear()
        text = text.lower()
        for lib_id, meta in sorted(self.lib.items(),
                                   key=lambda kv: (kv[1]["category"],
                                                   kv[1]["label"])):
            line = "%s — %s (%s, %g mm)" % (
                meta["category"], meta["label"], meta["mount"],
                meta["width_mm"])
            if text and text not in line.lower():
                continue
            item = QtWidgets.QListWidgetItem(line)
            item.setData(32, lib_id)
            self.listw.addItem(item)

    def _add(self):
        item = self.listw.currentItem()
        if not item:
            return
        from freecad.panelwb.components import make_component
        make_component(self.doc, item.data(32),
                       rail=self.rail, plate=self.plate)
        self.doc.recompute()


class CutoutDialog(QtWidgets.QDialog):
    """Add standard device cutouts to an enclosure face."""

    def __init__(self, enclosure, parent=None):
        super().__init__(parent)
        self.enc = enclosure
        self.setWindowTitle("Add device / cutout")
        form = QtWidgets.QFormLayout(self)

        from freecad.panelwb.cutouts import DEVICE_PRESETS
        self.preset = QtWidgets.QComboBox()
        self.preset.addItems(list(DEVICE_PRESETS))
        form.addRow("Device", self.preset)

        from freecad.panelwb.enclosure import CUTOUT_FACES
        self.face = QtWidgets.QComboBox()
        self.face.addItems(list(CUTOUT_FACES))
        form.addRow("Face", self.face)

        self.u = QtWidgets.QDoubleSpinBox()
        self.u.setRange(0, 4000)
        self.u.setValue(100)
        self.u.setSuffix(" mm")
        form.addRow("From left (u)", self.u)

        self.v = QtWidgets.QDoubleSpinBox()
        self.v.setRange(0, 4000)
        self.v.setValue(1200)
        self.v.setSuffix(" mm")
        form.addRow("From bottom (v)", self.v)

        add_btn = QtWidgets.QPushButton("Add")
        close_btn = QtWidgets.QPushButton("Close")
        row = QtWidgets.QHBoxLayout()
        row.addWidget(add_btn)
        row.addWidget(close_btn)
        form.addRow(row)

        def sync_face(name):
            self.face.setCurrentText(DEVICE_PRESETS[name][0])
        self.preset.currentTextChanged.connect(sync_face)
        sync_face(self.preset.currentText())

        add_btn.clicked.connect(self._add)
        close_btn.clicked.connect(self.close)

    def _add(self):
        from freecad.panelwb.cutouts import add_cutout
        add_cutout(self.enc, self.preset.currentText(),
                   self.u.value(), self.v.value(),
                   face=self.face.currentText())
        self.enc.Document.recompute()


def show_cutout_dialog(enclosure):
    dlg = CutoutDialog(enclosure,
                       Gui.getMainWindow() if hasattr(Gui, "getMainWindow")
                       else None)
    dlg.show()
    return dlg


def show_component_picker(doc, rail=None, plate=None):
    dlg = ComponentPicker(doc, rail, plate,
                          Gui.getMainWindow() if hasattr(Gui, "getMainWindow")
                          else None)
    dlg.show()
    return dlg
