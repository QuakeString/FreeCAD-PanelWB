"""Power distribution objects: PE/N bars and busbar reserved zones."""

import FreeCAD as App
import Part
from FreeCAD import Vector

from freecad.panelwb.interior import SimpleViewProvider, plate_frame

BAR_TYPES = ["PE", "N", "PEN"]


def make_earth_bar(doc, plate, name="PEBar"):
    obj = doc.addObject("Part::FeaturePython", name)
    EarthBar(obj)
    obj.Plate = plate
    if App.GuiUp:
        SimpleViewProvider(obj.ViewObject, "Rail")
    return obj


class EarthBar:
    def __init__(self, obj):
        self.Type = "PanelEarthBar:1"
        obj.Proxy = self
        obj.addProperty("App::PropertyLink", "Plate", "Bar",
                        "Mounting plate")
        obj.addProperty("App::PropertyEnumeration", "BarType", "Bar",
                        "Conductor function")
        obj.BarType = BAR_TYPES
        obj.addProperty("App::PropertyLength", "PositionX", "Bar",
                        "From plate left edge").PositionX = 25.0
        obj.addProperty("App::PropertyLength", "PositionZ", "Bar",
                        "Height on plate").PositionZ = 60.0
        obj.addProperty("App::PropertyLength", "Length", "Bar",
                        "0 = auto").Length = 0.0
        obj.addProperty("App::PropertyInteger", "Terminals", "Bar",
                        "Number of terminal holes").Terminals = 12

    def dumps(self):
        return None

    def loads(self, state):
        return None

    def execute(self, obj):
        length = obj.Length.Value or (
            plate_frame(obj.Plate)[3] - 2 * obj.PositionX.Value
            if obj.Plate is not None else 300.0)
        if obj.Plate is not None:
            x0, yf, z0, _, _ = plate_frame(obj.Plate)
            bx = x0 + obj.PositionX.Value
            bz = z0 + obj.PositionZ.Value - 7.5
            by = yf - 18.0
        else:
            bx, by, bz = 0.0, 0.0, 0.0
        bar = Part.makeBox(length, 10.0, 15.0, Vector(bx, by, bz))
        n = max(int(obj.Terminals), 1)
        pitch = length / (n + 1)
        holes = [Part.makeCylinder(
            2.5, 12.0, Vector(bx + pitch * (i + 1), by - 1.0, bz + 7.5),
            Vector(0, 1, 0)) for i in range(n)]
        obj.Shape = bar.cut(Part.makeCompound(holes))


def make_busbar_zone(doc, plate, name="BusbarZone"):
    obj = doc.addObject("Part::FeaturePython", name)
    BusbarZone(obj)
    obj.Plate = plate
    if App.GuiUp:
        SimpleViewProvider(obj.ViewObject, "Bus")
        try:
            obj.ViewObject.Transparency = 60
        except Exception:
            pass
    return obj


class BusbarZone:
    """Reserved space for a busbar system (RiLine-style module)."""

    def __init__(self, obj):
        self.Type = "PanelBusbarZone:1"
        obj.Proxy = self
        obj.addProperty("App::PropertyLink", "Plate", "Busbar",
                        "Mounting plate")
        obj.addProperty("App::PropertyLength", "PositionX", "Busbar",
                        "From plate left edge").PositionX = 25.0
        obj.addProperty("App::PropertyLength", "PositionZ", "Busbar",
                        "From plate bottom edge").PositionZ = 100.0
        obj.addProperty("App::PropertyLength", "Length", "Busbar",
                        "0 = auto").Length = 0.0
        obj.addProperty("App::PropertyLength", "ZoneHeight", "Busbar",
                        "Reserved height (60mm-module = 200)")
        obj.ZoneHeight = 200.0
        obj.addProperty("App::PropertyLength", "ZoneDepth", "Busbar",
                        "Reserved depth off the plate").ZoneDepth = 110.0
        obj.addProperty("App::PropertyInteger", "RatedAmps", "Busbar",
                        "Rated current (BOM/report data)").RatedAmps = 250

    def dumps(self):
        return None

    def loads(self, state):
        return None

    def execute(self, obj):
        length = obj.Length.Value or (
            plate_frame(obj.Plate)[3] - 2 * obj.PositionX.Value
            if obj.Plate is not None else 400.0)
        if obj.Plate is not None:
            x0, yf, z0, _, _ = plate_frame(obj.Plate)
            bx = x0 + obj.PositionX.Value
            bz = z0 + obj.PositionZ.Value
            by = yf - obj.ZoneDepth.Value
        else:
            bx, by, bz = 0.0, 0.0, 0.0
        obj.Shape = Part.makeBox(length, obj.ZoneDepth.Value,
                                 obj.ZoneHeight.Value, Vector(bx, by, bz))
