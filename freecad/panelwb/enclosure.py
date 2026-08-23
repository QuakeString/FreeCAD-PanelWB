"""Parametric Rittal-style enclosure.

Two construction families:
  WallMount     - mono-body folded sheet box (Rittal AX style)
  FloorStanding - skeleton frame of 45 mm profile sections with 25 mm
                  pitch pre-holes (Rittal VX25 style), plinth, bolt-on panels

Height is the enclosure/frame height; the plinth adds below it.
"""

import os

import FreeCAD as App
import Part
from FreeCAD import Vector

ICONDIR = os.path.join(os.path.dirname(__file__), "resources", "icons")

DOOR_CONFIGS = ["FrontOnly", "FrontAndBack", "DoubleFront", "DoubleFrontAndBack"]
DOOR_SWINGS = ["HingeLeft", "HingeRight"]
IP_RATINGS = ["IP42", "IP54", "IP55", "IP65", "IP66"]
LOCK_TYPES = [
    "QuarterTurnDoubleBit3mm",
    "QuarterTurnDoubleBit5mm",
    "WingHandle",
    "SwingHandleKeyBarrel",
    "Padlockable",
]
PLINTHS = ["None", "100mm", "200mm"]
GLAND_PLATES = ["None", "Top", "Bottom", "Both"]

PROFILE = 45.0        # VX25 frame section size
DOOR_T = 2.0          # door sheet thickness
DOOR_GAP = 3.0        # door offset in front of face
PITCH_HOLE_D = 8.5    # VX25 system punching
FLOOR_ONLY_PROPS = ("Plinth", "SkeletonPitch", "ShowPitchHoles")


def make_enclosure(doc, name="Enclosure"):
    obj = doc.addObject("Part::FeaturePython", name)
    Enclosure(obj)
    if App.GuiUp:
        ViewProviderEnclosure(obj.ViewObject)
    return obj


class Enclosure:
    def __init__(self, obj):
        self.Type = "PanelEnclosure"
        obj.Proxy = self

        obj.addProperty("App::PropertyEnumeration", "MountingType", "Enclosure",
                        "Construction family: mono-body box or skeleton frame")
        obj.MountingType = ["WallMount", "FloorStanding"]

        obj.addProperty("App::PropertyLength", "Width", "Enclosure",
                        "Overall width").Width = 600.0
        obj.addProperty("App::PropertyLength", "Height", "Enclosure",
                        "Enclosure height (plinth adds below)").Height = 800.0
        obj.addProperty("App::PropertyLength", "Depth", "Enclosure",
                        "Overall depth").Depth = 300.0
        obj.addProperty("App::PropertyLength", "WallThickness", "Enclosure",
                        "Sheet thickness").WallThickness = 1.5

        obj.addProperty("App::PropertyEnumeration", "IPRating", "Enclosure",
                        "Ingress protection rating (drives gasket/gland/vent rules)")
        obj.IPRating = IP_RATINGS
        obj.IPRating = "IP55"

        obj.addProperty("App::PropertyEnumeration", "DoorConfig", "Doors",
                        "Door arrangement")
        obj.DoorConfig = DOOR_CONFIGS
        obj.addProperty("App::PropertyEnumeration", "DoorSwing", "Doors",
                        "Hinge side (single doors)")
        obj.DoorSwing = DOOR_SWINGS
        obj.addProperty("App::PropertyEnumeration", "LockType", "Doors",
                        "Door lock / handle type")
        obj.LockType = LOCK_TYPES

        obj.addProperty("App::PropertyBool", "MountingPlate", "Interior",
                        "Include mounting plate").MountingPlate = True
        obj.addProperty("App::PropertyLength", "PlateSetback", "Interior",
                        "Mounting plate distance from rear wall").PlateSetback = 20.0

        obj.addProperty("App::PropertyEnumeration", "GlandPlate", "Enclosure",
                        "Cable gland plate location")
        obj.GlandPlate = GLAND_PLATES
        obj.GlandPlate = "Bottom"

        obj.addProperty("App::PropertyEnumeration", "Plinth", "FloorStanding",
                        "Plinth/base height under the frame")
        obj.Plinth = PLINTHS
        obj.Plinth = "100mm"
        obj.addProperty("App::PropertyLength", "SkeletonPitch", "FloorStanding",
                        "Frame pre-hole pitch").SkeletonPitch = 25.0
        obj.addProperty("App::PropertyBool", "ShowPitchHoles", "FloorStanding",
                        "Model the frame pitch holes (slower recompute)").ShowPitchHoles = False

        self._update_modes(obj)

    # -- persistence (FeaturePython proxies must be picklable) --------------
    def dumps(self):
        return None

    def loads(self, state):
        return None

    # -- property visibility ------------------------------------------------
    def _update_modes(self, obj):
        if not all(hasattr(obj, p) for p in FLOOR_ONLY_PROPS):
            return  # still constructing
        floor = obj.MountingType == "FloorStanding"
        for prop in FLOOR_ONLY_PROPS:
            obj.setEditorMode(prop, 0 if floor else 2)

    def onChanged(self, obj, prop):
        if prop == "MountingType":
            self._update_modes(obj)

    def onDocumentRestored(self, obj):
        self._update_modes(obj)

    # -- geometry -----------------------------------------------------------
    def execute(self, obj):
        if obj.MountingType == "FloorStanding":
            solids = self._build_floorstanding(obj)
        else:
            solids = self._build_wallmount(obj)
        obj.Shape = Part.makeCompound(solids)

    def _build_wallmount(self, obj):
        w = obj.Width.Value
        h = obj.Height.Value
        d = obj.Depth.Value
        t = obj.WallThickness.Value

        outer = Part.makeBox(w, d, h)
        inner = Part.makeBox(w - 2 * t, d - 2 * t, h - 2 * t, Vector(t, t, t))
        front = Part.makeBox(w - 2 * t, 2 * t, h - 2 * t, Vector(t, -t, t))
        body = outer.cut(inner).cut(front)

        solids = [body]
        solids += self._doors(obj, w, h, z0=0.0, front_y=0.0, back_y=None)

        if obj.MountingPlate:
            margin = 25.0
            py = d - t - obj.PlateSetback.Value
            solids.append(Part.makeBox(
                w - 2 * margin, 2.0, h - 2 * margin,
                Vector(margin, py, margin)))
        return solids

    def _build_floorstanding(self, obj):
        w = obj.Width.Value
        h = obj.Height.Value
        d = obj.Depth.Value
        s = PROFILE
        ph = {"None": 0.0, "100mm": 100.0, "200mm": 200.0}[obj.Plinth]

        solids = []

        if ph:
            p_outer = Part.makeBox(w, d, ph)
            p_inner = Part.makeBox(w - 6, d - 6, ph + 2, Vector(3, 3, -1))
            solids.append(p_outer.cut(p_inner))

        posts = []
        for px, py in ((0, 0), (w - s, 0), (0, d - s), (w - s, d - s)):
            posts.append(Part.makeBox(s, s, h, Vector(px, py, ph)))
        if obj.ShowPitchHoles:
            posts = [self._drill_pitch_holes(obj, p, s, ph, h) for p in posts]
        solids += posts

        for z in (ph, ph + h - s):
            for y in (0, d - s):  # members along X, front and back
                solids.append(Part.makeBox(w - 2 * s, s, s, Vector(s, y, z)))
            for x in (0, w - s):  # members along Y, left and right
                solids.append(Part.makeBox(s, d - 2 * s, s, Vector(x, s, z)))

        # top cover and side panels
        solids.append(Part.makeBox(w, d, 2.0, Vector(0, 0, ph + h)))
        solids.append(Part.makeBox(1.5, d, h, Vector(-1.5, 0, ph)))
        solids.append(Part.makeBox(1.5, d, h, Vector(w, 0, ph)))

        has_back_door = "Back" in obj.DoorConfig
        if not has_back_door:
            solids.append(Part.makeBox(w, 1.5, h, Vector(0, d, ph)))

        solids += self._doors(obj, w, h, z0=ph, front_y=0.0,
                              back_y=d if has_back_door else None)

        if obj.MountingPlate:
            margin = 50.0
            py = d - s - obj.PlateSetback.Value
            solids.append(Part.makeBox(
                w - 2 * margin, 3.0, h - 2 * margin,
                Vector(margin, py, ph + margin)))
        return solids

    def _drill_pitch_holes(self, obj, post, s, z0, h):
        pitch = max(obj.SkeletonPitch.Value, 5.0)
        r = PITCH_HOLE_D / 2.0
        origin = post.BoundBox
        cyls = []
        z = z0 + pitch / 2.0
        while z < z0 + h - pitch / 2.0:
            cyls.append(Part.makeCylinder(
                r, s + 2.0,
                Vector(origin.XMin + s / 2.0, origin.YMin - 1.0, z),
                Vector(0, 1, 0)))
            z += pitch
        return post.cut(Part.makeCompound(cyls)) if cyls else post

    def _doors(self, obj, w, h, z0, front_y, back_y):
        solids = []
        double = obj.DoorConfig.startswith("Double") or w > 800.0

        def leaves(y, outward):
            # outward: -1 for the front face, +1 for the back face
            y_door = y + outward * DOOR_GAP - (DOOR_T if outward < 0 else 0)
            if double:
                half = w / 2.0 - 1.0
                solids.append(Part.makeBox(half, DOOR_T, h, Vector(0, y_door, z0)))
                solids.append(Part.makeBox(half, DOOR_T, h, Vector(w / 2.0 + 1.0, y_door, z0)))
                for hx in (w / 2.0 - 40.0, w / 2.0 + 40.0):
                    solids.append(self._handle(obj, hx, y_door, z0 + h / 2.0, outward))
            else:
                solids.append(Part.makeBox(w, DOOR_T, h, Vector(0, y_door, z0)))
                hx = w - 60.0 if obj.DoorSwing == "HingeLeft" else 60.0
                solids.append(self._handle(obj, hx, y_door, z0 + h / 2.0, outward))

        leaves(front_y, -1)
        if back_y is not None:
            leaves(back_y, +1)
        return solids

    def _handle(self, obj, hx, y_door, hz, outward):
        lock = obj.LockType
        y_face = y_door + (DOOR_T if outward > 0 else 0)
        if lock.startswith("QuarterTurn"):
            return Part.makeCylinder(
                11.0, 6.0, Vector(hx, y_face, hz), Vector(0, outward, 0))
        if lock == "WingHandle":
            size = (24.0, 6.0, 90.0)
        elif lock == "SwingHandleKeyBarrel":
            size = (30.0, 8.0, 150.0)
        else:  # Padlockable
            size = (20.0, 10.0, 40.0)
        sx, sy, sz = size
        y0 = y_face if outward > 0 else y_face - sy
        return Part.makeBox(sx, sy, sz, Vector(hx - sx / 2.0, y0, hz - sz / 2.0))


class ViewProviderEnclosure:
    def __init__(self, vobj):
        vobj.Proxy = self

    def getIcon(self):
        return os.path.join(ICONDIR, "Enclosure.svg")

    def attach(self, vobj):
        pass

    def dumps(self):
        return None

    def loads(self, state):
        return None
