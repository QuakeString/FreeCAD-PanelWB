"""Interior installation objects: mounting plate, DIN rails, ducts, chassis.

Coordinate convention: the mounting plate is vertical, facing -Y (the door).
Rails/ducts/components position themselves in PLATE coordinates:
  PositionX  - mm from the plate's left edge
  PositionZ  - mm from the plate's bottom edge
The plate publishes its world frame in hidden properties (OriginX/Y/Z,
PlateWidth/PlateHeight) so children only need a Link to it.
"""

import os

import FreeCAD as App
import Part
from FreeCAD import Vector

ICONDIR = os.path.join(os.path.dirname(__file__), "resources", "icons")

RAIL_TYPES = ["TS35x7.5", "TS35x15"]
DUCT_SIZES = ["25x40", "40x40", "60x40", "60x60", "80x60", "100x60", "120x80"]
DUCT_ORIENTATIONS = ["Horizontal", "Vertical"]


def _viewprovider(obj, icon):
    if App.GuiUp:
        SimpleViewProvider(obj.ViewObject, icon)


def _proxy_type(o):
    return getattr(getattr(o, "Proxy", None), "Type", "")


def find_plate(doc, explicit=None):
    if explicit is not None:
        return explicit
    plates = [o for o in doc.Objects
              if _proxy_type(o).startswith("PanelPlate")]
    return plates[0] if plates else None


# --------------------------------------------------------------- mounting plate
def make_mounting_plate(doc, enclosure, name="MountingPlate"):
    obj = doc.addObject("Part::FeaturePython", name)
    MountingPlate(obj)
    obj.Enclosure = enclosure
    if hasattr(enclosure, "MountingPlate"):
        enclosure.MountingPlate = False  # supersede the built-in slab
    _viewprovider(obj, "Plate")
    return obj


class MountingPlate:
    def __init__(self, obj):
        self.Type = "PanelPlate:1"
        obj.Proxy = self
        obj.addProperty("App::PropertyLink", "Enclosure", "Plate",
                        "Enclosure this plate belongs to")
        obj.addProperty("App::PropertyBool", "AutoSize", "Plate",
                        "Size the plate from the enclosure").AutoSize = True
        obj.addProperty("App::PropertyLength", "PlateWidth", "Plate",
                        "Manual width (AutoSize off)").PlateWidth = 549.0
        obj.addProperty("App::PropertyLength", "PlateHeight", "Plate",
                        "Manual height (AutoSize off)").PlateHeight = 745.0
        obj.addProperty("App::PropertyLength", "Thickness", "Plate",
                        "Plate thickness").Thickness = 3.0
        obj.addProperty("App::PropertyLength", "Setback", "Plate",
                        "Distance from enclosure rear").Setback = 20.0
        for name in ("OriginX", "OriginY", "OriginZ"):
            obj.addProperty("App::PropertyFloat", name, "Frame",
                            "Plate world frame (computed)")
            obj.setEditorMode(name, 1)

    def dumps(self):
        return None

    def loads(self, state):
        return None

    def execute(self, obj):
        enc = obj.Enclosure
        t = obj.Thickness.Value
        if enc is not None and obj.AutoSize:
            from freecad.panelwb.enclosure import PLINTH_MM, PROFILE
            fam = enc.MountingType
            w = enc.Width.Value * (int(enc.BayCount)
                                   if fam == "Bayed" else 1)
            h = enc.Height.Value
            d = enc.Depth.Value
            ph = PLINTH_MM[enc.Plinth] if fam in ("FreeStanding",
                                                  "Bayed") else 0.0
            margin = 50.0 if fam == "Bayed" else 25.0
            frame = PROFILE if fam == "Bayed" else enc.WallThickness.Value
            pw = w - 2 * margin
            phh = h - 2 * margin
            px, pz = margin, ph + margin
            py = d - frame - obj.Setback.Value
        else:
            pw = obj.PlateWidth.Value
            phh = obj.PlateHeight.Value
            px, py, pz = 0.0, 0.0, 0.0
        obj.OriginX, obj.OriginY, obj.OriginZ = px, py, pz
        obj.Shape = Part.makeBox(pw, t, phh, Vector(px, py, pz))


def plate_frame(plate):
    """(x0, y_front, z0, width, height) of a plate in world coords."""
    bb = plate.Shape.BoundBox
    return (plate.OriginX, plate.OriginY, plate.OriginZ,
            bb.XLength, bb.ZLength)


# --------------------------------------------------------------------- DIN rail
def make_din_rail(doc, plate, name="DinRail"):
    obj = doc.addObject("Part::FeaturePython", name)
    DinRail(obj)
    obj.Plate = plate
    _viewprovider(obj, "Rail")
    return obj


class DinRail:
    def __init__(self, obj):
        self.Type = "PanelDinRail:1"
        obj.Proxy = self
        obj.addProperty("App::PropertyLink", "Plate", "Rail",
                        "Mounting plate")
        obj.addProperty("App::PropertyEnumeration", "RailType", "Rail",
                        "EN 60715 profile")
        obj.RailType = RAIL_TYPES
        obj.addProperty("App::PropertyLength", "PositionX", "Rail",
                        "From plate left edge (rail start)").PositionX = 25.0
        obj.addProperty("App::PropertyLength", "PositionZ", "Rail",
                        "Rail centerline height on plate").PositionZ = 200.0
        obj.addProperty("App::PropertyLength", "Length", "Rail",
                        "0 = auto (plate width minus margins)").Length = 0.0

    def dumps(self):
        return None

    def loads(self, state):
        return None

    def rail_length(self, obj):
        if obj.Length.Value > 0:
            return obj.Length.Value
        if obj.Plate is None:
            return 400.0
        return plate_frame(obj.Plate)[3] - 2 * obj.PositionX.Value

    def execute(self, obj):
        if obj.Plate is None:
            obj.Shape = Part.makeBox(400, 7.5, 35)
            return
        x0, yf, z0, _, _ = plate_frame(obj.Plate)
        depth = 7.5 if obj.RailType == "TS35x7.5" else 15.0
        length = self.rail_length(obj)
        rx = x0 + obj.PositionX.Value
        rz = z0 + obj.PositionZ.Value - 17.5
        y = yf - depth
        base = Part.makeBox(length, depth - 1.0, 27.0,
                            Vector(rx, y + 1.0, rz + 4.0))
        lip_t = Part.makeBox(length, depth, 4.0, Vector(rx, y, rz + 31.0))
        lip_b = Part.makeBox(length, depth, 4.0, Vector(rx, y, rz))
        obj.Shape = Part.makeCompound([base, lip_t, lip_b])


# ------------------------------------------------------------------------ duct
def make_duct(doc, plate, name="Duct"):
    obj = doc.addObject("Part::FeaturePython", name)
    Duct(obj)
    obj.Plate = plate
    _viewprovider(obj, "Duct")
    return obj


class Duct:
    def __init__(self, obj):
        self.Type = "PanelDuct:1"
        obj.Proxy = self
        obj.addProperty("App::PropertyLink", "Plate", "Duct",
                        "Mounting plate")
        obj.addProperty("App::PropertyEnumeration", "Orientation", "Duct",
                        "Run direction on the plate")
        obj.Orientation = DUCT_ORIENTATIONS
        obj.addProperty("App::PropertyEnumeration", "Size", "Duct",
                        "Width x depth (mm)")
        obj.Size = DUCT_SIZES
        obj.Size = "60x60"
        obj.addProperty("App::PropertyLength", "PositionX", "Duct",
                        "From plate left edge").PositionX = 25.0
        obj.addProperty("App::PropertyLength", "PositionZ", "Duct",
                        "From plate bottom edge").PositionZ = 25.0
        obj.addProperty("App::PropertyLength", "Length", "Duct",
                        "0 = auto (to plate edge)").Length = 0.0
        obj.addProperty("App::PropertyPercent", "WireFill", "Duct",
                        "Estimated wire fill").WireFill = 30

    def dumps(self):
        return None

    def loads(self, state):
        return None

    def duct_length(self, obj):
        if obj.Length.Value > 0:
            return obj.Length.Value
        if obj.Plate is None:
            return 400.0
        _, _, _, pw, phh = plate_frame(obj.Plate)
        if obj.Orientation == "Horizontal":
            return pw - 2 * obj.PositionX.Value
        return phh - 2 * obj.PositionZ.Value

    def execute(self, obj):
        wide, deep = (float(v) for v in obj.Size.split("x"))
        length = self.duct_length(obj)
        if obj.Plate is None:
            obj.Shape = Part.makeBox(length, deep, wide)
            return
        x0, yf, z0, _, _ = plate_frame(obj.Plate)
        dx = x0 + obj.PositionX.Value
        dz = z0 + obj.PositionZ.Value
        y = yf - deep
        if obj.Orientation == "Horizontal":
            outer = Part.makeBox(length, deep, wide, Vector(dx, y, dz))
            inner = Part.makeBox(length - 4, deep, wide - 4,
                                 Vector(dx + 2, y - 2, dz + 2))
        else:
            outer = Part.makeBox(wide, deep, length, Vector(dx, y, dz))
            inner = Part.makeBox(wide - 4, deep, length - 4,
                                 Vector(dx + 2, y - 2, dz + 2))
        obj.Shape = outer.cut(inner)


# ---------------------------------------------------------------- chassis rail
def make_chassis_rail(doc, plate, name="ChassisRail"):
    obj = doc.addObject("Part::FeaturePython", name)
    ChassisRail(obj)
    obj.Plate = plate
    _viewprovider(obj, "Rail")
    return obj


class ChassisRail:
    def __init__(self, obj):
        self.Type = "PanelChassisRail:1"
        obj.Proxy = self
        obj.addProperty("App::PropertyLink", "Plate", "Rail",
                        "Mounting plate")
        obj.addProperty("App::PropertyLength", "PositionX", "Rail",
                        "From plate left edge").PositionX = 25.0
        obj.addProperty("App::PropertyLength", "PositionZ", "Rail",
                        "Centerline height on plate").PositionZ = 400.0
        obj.addProperty("App::PropertyLength", "Length", "Rail",
                        "0 = auto").Length = 0.0

    def dumps(self):
        return None

    def loads(self, state):
        return None

    def execute(self, obj):
        length = obj.Length.Value or (
            plate_frame(obj.Plate)[3] - 2 * obj.PositionX.Value
            if obj.Plate is not None else 400.0)
        if obj.Plate is None:
            obj.Shape = Part.makeBox(length, 20, 40)
            return
        x0, yf, z0, _, _ = plate_frame(obj.Plate)
        rx = x0 + obj.PositionX.Value
        rz = z0 + obj.PositionZ.Value - 20.0
        outer = Part.makeBox(length, 20.0, 40.0, Vector(rx, yf - 20.0, rz))
        inner = Part.makeBox(length, 16.0, 32.0,
                             Vector(rx, yf - 22.0, rz + 4.0))
        obj.Shape = outer.cut(inner)


# ---------------------------------------------------------------- view provider
class SimpleViewProvider:
    def __init__(self, vobj, icon):
        vobj.Proxy = self
        self.icon = icon

    def getIcon(self):
        return os.path.join(ICONDIR, "%s.svg" % getattr(self, "icon",
                                                        "PanelWB"))

    def attach(self, vobj):
        pass

    def dumps(self):
        return getattr(self, "icon", "PanelWB")

    def loads(self, state):
        self.icon = state or "PanelWB"
