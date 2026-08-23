"""Component library and placement.

Library entries live in parts/library.json (generic devices) — vendor parts
can be added as more JSON entries (and later: real geometry files).

DIN-rail components snap onto a DinRail: OffsetMM from the rail start;
a fresh component auto-appends after the last one (5 mm gap).
Plate components place free on the plate (PositionX/PositionZ, 25 mm grid
rounding applied by the placement command, not enforced here).
"""

import json
import os

import FreeCAD as App
import Part
from FreeCAD import Vector

from freecad.panelwb.interior import SimpleViewProvider, plate_frame

CATEGORY_COLORS = {
    "breaker": (0.910, 0.910, 0.890),
    "contactor": (0.230, 0.240, 0.270),
    "relay": (0.900, 0.550, 0.150),
    "psu": (0.740, 0.760, 0.780),
    "plc": (0.840, 0.850, 0.820),
    "network": (0.290, 0.430, 0.620),
    "terminal": (0.550, 0.570, 0.620),
    "protection": (0.700, 0.250, 0.250),
    "metering": (0.180, 0.190, 0.210),
    "drive": (0.350, 0.370, 0.400),
    "power": (0.480, 0.400, 0.320),
}

LIBRARY_PATH = os.path.normpath(os.path.join(
    os.path.dirname(__file__), "..", "..", "parts", "library.json"))

_cache = None


def load_library():
    global _cache
    if _cache is None:
        with open(LIBRARY_PATH, encoding="utf-8") as fh:
            _cache = json.load(fh)
    return _cache


def _proxy_type(o):
    return getattr(getattr(o, "Proxy", None), "Type", "")


def components_on_rail(rail):
    comps = [o for o in rail.InList
              if _proxy_type(o).startswith("PanelComponent")
              and getattr(o, "Rail", None) is rail]
    return sorted(comps, key=lambda c: c.OffsetMM.Value)


def rail_fill(rail):
    """(used_mm, length_mm, fill_ratio) of a DIN rail."""
    used = sum(c.WidthMM.Value for c in components_on_rail(rail))
    length = rail.Proxy.rail_length(rail)
    return used, length, (used / length if length else 0.0)


def next_offset(rail, gap=5.0):
    comps = components_on_rail(rail)
    if not comps:
        return 10.0
    return max(c.OffsetMM.Value + c.WidthMM.Value for c in comps) + gap


def make_component(doc, lib_id, rail=None, plate=None, name=None):
    lib = load_library()
    meta = lib[lib_id]
    obj = doc.addObject("Part::FeaturePython",
                        name or lib_id.replace(".", "_"))
    PanelComponent(obj, lib_id, meta)
    if meta["mount"] == "din35" and rail is not None:
        obj.Rail = rail
        obj.OffsetMM = next_offset(rail)
    elif plate is not None:
        obj.Plate = plate
    if App.GuiUp:
        SimpleViewProvider(obj.ViewObject, "Component",
                           CATEGORY_COLORS.get(meta.get("category"),
                                               (0.7, 0.7, 0.7)))
    return obj


class PanelComponent:
    def __init__(self, obj, lib_id, meta):
        self.Type = "PanelComponent:1"
        obj.Proxy = self

        obj.addProperty("App::PropertyString", "LibId", "Component",
                        "Library id").LibId = lib_id
        obj.addProperty("App::PropertyString", "PartNo", "Component",
                        "Part number").PartNo = meta.get("part_no", lib_id)
        obj.addProperty("App::PropertyString", "Vendor", "Component",
                        "Vendor").Vendor = meta.get("vendor", "generic")
        obj.addProperty("App::PropertyString", "Category", "Component",
                        "Category").Category = meta.get("category", "misc")
        obj.addProperty("App::PropertyString", "Tag", "Component",
                        "Device tag (e.g. -K1, -F2)")
        obj.addProperty("App::PropertyEnumeration", "Mount", "Component",
                        "Mounting style")
        obj.Mount = ["din35", "plate"]
        obj.Mount = meta.get("mount", "din35")

        obj.addProperty("App::PropertyLength", "WidthMM", "Component",
                        "Width").WidthMM = meta.get("width_mm", 45.0)
        obj.addProperty("App::PropertyLength", "HeightMM", "Component",
                        "Height").HeightMM = meta.get("height_mm", 90.0)
        obj.addProperty("App::PropertyLength", "DepthMM", "Component",
                        "Depth").DepthMM = meta.get("depth_mm", 80.0)
        obj.addProperty("App::PropertyFloat", "HeatW", "Component",
                        "Heat dissipation (W)")
        obj.HeatW = float(meta.get("heat_w", 0.0))
        obj.addProperty("App::PropertyFloat", "WeightKg", "Component",
                        "Weight (kg)")
        obj.WeightKg = float(meta.get("weight_kg", 0.0))
        obj.addProperty("App::PropertyLength", "ClearanceTop", "Component",
                        "Required clearance above").ClearanceTop = 20.0
        obj.addProperty("App::PropertyLength", "ClearanceBottom", "Component",
                        "Required clearance below").ClearanceBottom = 20.0

        obj.addProperty("App::PropertyLink", "Rail", "Placement2",
                        "DIN rail (din35 mount)")
        obj.addProperty("App::PropertyLength", "OffsetMM", "Placement2",
                        "Offset from rail start").OffsetMM = 10.0
        obj.addProperty("App::PropertyLink", "Plate", "Placement2",
                        "Mounting plate (plate mount)")
        obj.addProperty("App::PropertyLength", "PositionX", "Placement2",
                        "Plate X (plate mount)").PositionX = 50.0
        obj.addProperty("App::PropertyLength", "PositionZ", "Placement2",
                        "Plate Z (plate mount)").PositionZ = 50.0

    def dumps(self):
        return None

    def loads(self, state):
        return None

    def execute(self, obj):
        w = obj.WidthMM.Value
        h = obj.HeightMM.Value
        d = obj.DepthMM.Value

        if obj.Mount == "din35" and obj.Rail is not None:
            rail = obj.Rail
            rbb = rail.Shape.BoundBox
            x = rbb.XMin + obj.OffsetMM.Value
            z = rbb.ZMin + rbb.ZLength / 2.0 - h / 2.0  # centered on rail
            y = rbb.YMin - d  # device front sticks toward the door
            body = Part.makeBox(w, d, h, Vector(x, y, z))
        elif obj.Plate is not None:
            x0, yf, z0, _, _ = plate_frame(obj.Plate)
            body = Part.makeBox(
                w, d, h,
                Vector(x0 + obj.PositionX.Value, yf - d,
                       z0 + obj.PositionZ.Value))
        else:
            body = Part.makeBox(w, d, h)
        obj.Shape = body


def all_components(doc):
    return [o for o in doc.Objects
            if _proxy_type(o).startswith("PanelComponent")]
