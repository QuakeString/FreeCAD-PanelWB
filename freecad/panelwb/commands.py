"""Toolbar/menu commands for PanelWB."""

import os

import FreeCAD as App
import FreeCADGui as Gui

ICONDIR = os.path.join(os.path.dirname(__file__), "resources", "icons")


def _icon(name):
    path = os.path.join(ICONDIR, name + ".svg")
    return path if os.path.exists(path) else os.path.join(ICONDIR,
                                                          "PanelWB.svg")


def selected_enclosure():
    """Selected enclosure, else the document's only enclosure, else None."""
    sel = [o for o in Gui.Selection.getSelection()
           if getattr(getattr(o, "Proxy", None), "Type",
                      "").startswith("PanelEnclosure")]
    if sel:
        return sel[0]
    doc = App.ActiveDocument
    if not doc:
        return None
    encs = [o for o in doc.Objects
            if getattr(getattr(o, "Proxy", None), "Type",
                       "").startswith("PanelEnclosure")]
    return encs[0] if len(encs) == 1 else None


class _Command:
    MENU = "?"
    TIP = ""
    ICON = "PanelWB"

    def GetResources(self):
        return {"Pixmap": _icon(self.ICON), "MenuText": self.MENU,
                "ToolTip": self.TIP or self.MENU}

    def IsActive(self):
        return True


class AddEnclosureCommand(_Command):
    MENU = "Add enclosure"
    TIP = "Create a parametric Rittal-style enclosure"
    ICON = "Enclosure"

    def Activated(self):
        from freecad.panelwb.enclosure import make_enclosure
        doc = App.ActiveDocument or App.newDocument("Panel")
        obj = make_enclosure(doc)
        doc.recompute()
        Gui.SendMsgToActiveView("ViewFit")
        try:
            from freecad.panelwb.ui import show_enclosure_dialog
            show_enclosure_dialog(obj)
        except Exception:
            pass


class EditEnclosureCommand(_Command):
    MENU = "Edit enclosure…"
    TIP = "Open the enclosure quick editor"
    ICON = "Enclosure"

    def IsActive(self):
        return selected_enclosure() is not None

    def Activated(self):
        from freecad.panelwb.ui import show_enclosure_dialog
        show_enclosure_dialog(selected_enclosure())


class ToggleFrontDoorCommand(_Command):
    MENU = "Open/close front door"
    TIP = "Toggle the front door swing"
    ICON = "Door"

    def IsActive(self):
        return selected_enclosure() is not None

    def Activated(self):
        from freecad.panelwb.enclosure import _toggle
        _toggle(selected_enclosure(), "FrontDoorAngle")


class OpenAllDoorsCommand(_Command):
    MENU = "Open all doors"
    ICON = "Door"

    def IsActive(self):
        return selected_enclosure() is not None

    def Activated(self):
        from freecad.panelwb.enclosure import _set_doors
        _set_doors(selected_enclosure(), 120.0)


class CloseAllDoorsCommand(_Command):
    MENU = "Close all doors"
    ICON = "Door"

    def IsActive(self):
        return selected_enclosure() is not None

    def Activated(self):
        from freecad.panelwb.enclosure import _set_doors
        _set_doors(selected_enclosure(), 0.0)


class ViewServiceCommand(_Command):
    MENU = "Service view"
    TIP = "Doors open, side panels off"
    ICON = "PanelWB"

    def IsActive(self):
        return selected_enclosure() is not None

    def Activated(self):
        from freecad.panelwb.enclosure import _set_doors
        obj = selected_enclosure()
        obj.SidePanels = False
        _set_doors(obj, 130.0)


class ViewClosedCommand(_Command):
    MENU = "Closed view"
    TIP = "Doors closed, all panels fitted"
    ICON = "PanelWB"

    def IsActive(self):
        return selected_enclosure() is not None

    def Activated(self):
        from freecad.panelwb.enclosure import _set_doors
        obj = selected_enclosure()
        obj.SidePanels = True
        _set_doors(obj, 0.0)


def _selected_of(prefix):
    for o in Gui.Selection.getSelection():
        if getattr(getattr(o, "Proxy", None), "Type", "").startswith(prefix):
            return o
    return None


class AddMountingPlateCommand(_Command):
    MENU = "Add mounting plate"
    TIP = "Add an auto-sized mounting plate to the enclosure"
    ICON = "Plate"

    def IsActive(self):
        return selected_enclosure() is not None

    def Activated(self):
        from freecad.panelwb import interior
        enc = selected_enclosure()
        interior.make_mounting_plate(enc.Document, enc)
        enc.Document.recompute()


class _AddInteriorCommand(_Command):
    FACTORY = None

    def IsActive(self):
        doc = App.ActiveDocument
        if not doc:
            return False
        from freecad.panelwb.interior import find_plate
        return find_plate(doc, _selected_of("PanelPlate")) is not None

    def Activated(self):
        from freecad.panelwb import interior
        doc = App.ActiveDocument
        plate = interior.find_plate(doc, _selected_of("PanelPlate"))
        getattr(interior, self.FACTORY)(doc, plate)
        doc.recompute()


class AddDinRailCommand(_AddInteriorCommand):
    MENU = "Add DIN rail"
    TIP = "TS35 rail on the mounting plate"
    ICON = "Rail"
    FACTORY = "make_din_rail"


class AddDuctCommand(_AddInteriorCommand):
    MENU = "Add cable duct"
    TIP = "Wiring duct on the mounting plate"
    ICON = "Duct"
    FACTORY = "make_duct"


class AddChassisRailCommand(_AddInteriorCommand):
    MENU = "Add chassis rail"
    TIP = "C-profile support rail for heavy gear"
    ICON = "Rail"
    FACTORY = "make_chassis_rail"


class AddComponentCommand(_Command):
    MENU = "Add component…"
    TIP = "Pick a device from the library and drop it on the " \
          "selected rail or plate"
    ICON = "Component"

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        from freecad.panelwb.ui import show_component_picker
        doc = App.ActiveDocument
        rail = _selected_of("PanelDinRail")
        plate = None
        if rail is None:
            from freecad.panelwb.interior import find_plate
            plate = find_plate(doc, _selected_of("PanelPlate"))
            rails = [o for o in doc.Objects
                     if getattr(getattr(o, "Proxy", None), "Type",
                                "").startswith("PanelDinRail")]
            if len(rails) == 1:
                rail = rails[0]
        self._dlg = show_component_picker(doc, rail=rail, plate=plate)


class AddCutoutCommand(_Command):
    MENU = "Add device / cutout…"
    TIP = "Punch a standard device cutout (buttons, HMI, glands)"
    ICON = "Cutout"

    def IsActive(self):
        return selected_enclosure() is not None

    def Activated(self):
        from freecad.panelwb.ui import show_cutout_dialog
        self._dlg = show_cutout_dialog(selected_enclosure())


class _ReportCommand(_Command):
    ICON = "Report"

    def IsActive(self):
        return App.ActiveDocument is not None

    def _notify(self, title, text):
        try:
            from PySide import QtWidgets
            QtWidgets.QMessageBox.information(Gui.getMainWindow(), title,
                                              text)
        except Exception:
            App.Console.PrintMessage("%s\n%s\n" % (title, text))


class GenerateBOMCommand(_ReportCommand):
    MENU = "Generate BOM"
    TIP = "Bill of materials -> spreadsheet + CSV"

    def Activated(self):
        from freecad.panelwb.reports import make_bom
        rows, path = make_bom(App.ActiveDocument)
        self._notify("BOM", "%d line items.\nCSV: %s" % (len(rows), path))


class ThermalReportCommand(_ReportCommand):
    MENU = "Thermal report"
    TIP = "IEC 60890-style temperature rise estimate"

    def Activated(self):
        from freecad.panelwb.reports import thermal_report
        r = thermal_report(App.ActiveDocument)
        self._notify("Thermal", "P=%.0f W, Ae=%.2f m2, dT=%.1f K "
                     "-> %.1f C\n%s" % (r["heat_w"], r["ae_m2"],
                                         r["delta_t"], r["internal_c"],
                                         r["advice"]))


class FillReportCommand(_ReportCommand):
    MENU = "Fill / collision report"
    TIP = "Rail and duct fill, clearance collisions"

    def Activated(self):
        from freecad.panelwb.reports import fill_report
        entries, warnings = fill_report(App.ActiveDocument)
        text = "\n".join("%s: %s" % e for e in entries)
        if warnings:
            text += "\n\nWARNINGS:\n" + "\n".join(warnings)
        self._notify("Fill report", text or "Nothing to report.")


Gui.addCommand("PanelWB_GenerateBOM", GenerateBOMCommand())
Gui.addCommand("PanelWB_ThermalReport", ThermalReportCommand())
Gui.addCommand("PanelWB_FillReport", FillReportCommand())
Gui.addCommand("PanelWB_AddCutout", AddCutoutCommand())
Gui.addCommand("PanelWB_AddComponent", AddComponentCommand())
Gui.addCommand("PanelWB_AddMountingPlate", AddMountingPlateCommand())
Gui.addCommand("PanelWB_AddDinRail", AddDinRailCommand())
Gui.addCommand("PanelWB_AddDuct", AddDuctCommand())
Gui.addCommand("PanelWB_AddChassisRail", AddChassisRailCommand())
Gui.addCommand("PanelWB_AddEnclosure", AddEnclosureCommand())
Gui.addCommand("PanelWB_EditEnclosure", EditEnclosureCommand())
Gui.addCommand("PanelWB_ToggleFrontDoor", ToggleFrontDoorCommand())
Gui.addCommand("PanelWB_OpenAllDoors", OpenAllDoorsCommand())
Gui.addCommand("PanelWB_CloseAllDoors", CloseAllDoorsCommand())
Gui.addCommand("PanelWB_ViewService", ViewServiceCommand())
Gui.addCommand("PanelWB_ViewClosed", ViewClosedCommand())

toolbar_panel = [
    "PanelWB_AddEnclosure",
    "PanelWB_EditEnclosure",
    "PanelWB_ToggleFrontDoor",
    "PanelWB_OpenAllDoors",
    "PanelWB_CloseAllDoors",
    "PanelWB_ViewService",
    "PanelWB_ViewClosed",
]
toolbar_interior = [
    "PanelWB_AddMountingPlate",
    "PanelWB_AddDinRail",
    "PanelWB_AddDuct",
    "PanelWB_AddChassisRail",
    "PanelWB_AddComponent",
    "PanelWB_AddCutout",
]
toolbar_outputs = [
    "PanelWB_GenerateBOM",
    "PanelWB_ThermalReport",
    "PanelWB_FillReport",
]
command_names = toolbar_panel + toolbar_interior + toolbar_outputs
