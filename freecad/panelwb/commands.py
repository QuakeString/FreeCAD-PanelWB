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
command_names = list(toolbar_panel)
