"""PanelWB workbench registration."""

import os

import FreeCADGui as Gui

ICONDIR = os.path.join(os.path.dirname(__file__), "resources", "icons")


class PanelWBWorkbench(Gui.Workbench):
    MenuText = "Panel"
    ToolTip = "Electrical control panel enclosure design (Rittal-style)"
    Icon = os.path.join(ICONDIR, "PanelWB.svg")

    def Initialize(self):
        from freecad.panelwb import commands
        self.appendToolbar("Panel", commands.command_names)
        self.appendMenu("&Panel", commands.command_names)

    def GetClassName(self):
        return "Gui::PythonWorkbench"


Gui.addWorkbench(PanelWBWorkbench())
