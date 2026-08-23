"""Toolbar/menu commands for PanelWB."""

import os

import FreeCAD as App
import FreeCADGui as Gui

ICONDIR = os.path.join(os.path.dirname(__file__), "resources", "icons")


class AddEnclosureCommand:
    def GetResources(self):
        return {
            "Pixmap": os.path.join(ICONDIR, "Enclosure.svg"),
            "MenuText": "Add enclosure",
            "ToolTip": "Create a parametric Rittal-style enclosure",
        }

    def IsActive(self):
        return True

    def Activated(self):
        from freecad.panelwb.enclosure import make_enclosure
        doc = App.ActiveDocument or App.newDocument("Panel")
        make_enclosure(doc)
        doc.recompute()
        Gui.SendMsgToActiveView("ViewFit")


Gui.addCommand("PanelWB_AddEnclosure", AddEnclosureCommand())

command_names = ["PanelWB_AddEnclosure"]
