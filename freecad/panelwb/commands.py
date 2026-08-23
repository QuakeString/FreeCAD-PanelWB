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
]
command_names = toolbar_panel + toolbar_interior
