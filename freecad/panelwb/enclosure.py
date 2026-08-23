"""Parametric Rittal-style enclosure.

Four construction families:
  SmallBox     - small terminal box (Rittal KX style)
  WallMount    - compact mono-body wall box (Rittal AX style)
  FreeStanding - floor-standing mono-body, no skeleton (Rittal VX SE style)
  Bayed        - skeleton frame system, 45 mm profiles, 25 mm pitch,
                 1..N bays side by side (Rittal VX25 style)

Height is the enclosure/frame height; the plinth adds below it.
Doors carry a live OpenAngle so the cabinet can be "opened" with one click.

Geometry carries per-solid colors (SolidColors property, applied by the
view provider) so the model reads like a real cabinet: RAL 7035 body,
black plinth/handles, zinc plate, colored operator devices.
"""

import os

import FreeCAD as App
import Part
from FreeCAD import Vector

ICONDIR = os.path.join(os.path.dirname(__file__), "resources", "icons")

FAMILIES = ["SmallBox", "WallMount", "FreeStanding", "Bayed"]
DOOR_CONFIGS = ["FrontOnly", "FrontAndBack", "DoubleFront", "DoubleFrontAndBack"]
DOOR_SWINGS = ["HingeLeft", "HingeRight"]
DOOR_STYLES = ["Solid", "Glazed", "Vented"]
REAR_STYLES = ["Panel", "Door", "None"]
IP_RATINGS = ["IP42", "IP54", "IP55", "IP65", "IP66"]
LOCK_TYPES = [
    "QuarterTurnDoubleBit3mm",
    "QuarterTurnDoubleBit5mm",
    "WingHandle",
    "SwingHandleKeyBarrel",
    "Padlockable",
]
PLINTHS = ["None", "100mm", "200mm"]

PRESETS = {
    "Custom": None,
    "KX 200x300x120": ("SmallBox", 200, 300, 120, "None"),
    "KX 300x400x155": ("SmallBox", 300, 400, 155, "None"),
    "AX 400x500x210": ("WallMount", 400, 500, 210, "None"),
    "AX 600x760x350": ("WallMount", 600, 760, 350, "None"),
    "AX 800x1000x300": ("WallMount", 800, 1000, 300, "None"),
    "VX SE 600x1800x500": ("FreeStanding", 600, 1800, 500, "100mm"),
    "VX SE 800x2000x600": ("FreeStanding", 800, 2000, 600, "100mm"),
    "VX25 800x2000x600": ("Bayed", 800, 2000, 600, "100mm"),
    "VX25 1200x2200x800": ("Bayed", 1200, 2200, 800, "200mm"),
}

PROFILE = 45.0        # VX25 frame section size
DOOR_T = 18.0         # door depth (folded pan construction)
DOOR_SKIN = 4.0       # outer skin the recess leaves standing
DOOR_GAP = 4.0        # door offset in front of face
PITCH_HOLE_D = 8.5    # VX25 system punching
PLINTH_MM = {"None": 0.0, "100mm": 100.0, "200mm": 200.0}

# palette (RGB 0..1)
RAL7035 = (0.784, 0.800, 0.792)   # light grey body
RAL7035_D = (0.706, 0.722, 0.714)  # slightly darker: frame, inner door
BLACK = (0.110, 0.110, 0.118)      # plinth, handles
ZINC = (0.718, 0.749, 0.769)       # mounting/gland plate
GLASS = (0.588, 0.735, 0.828)
DEV_RED = (0.769, 0.118, 0.118)
DEV_YELLOW = (0.939, 0.788, 0.118)
DEV_GREEN = (0.318, 0.639, 0.318)
DEV_AMBER = (0.918, 0.639, 0.180)
DEV_DARK = (0.149, 0.157, 0.176)

FLOOR_ONLY_PROPS = ("Plinth",)
BAYED_ONLY_PROPS = ("BayCount", "SkeletonPitch", "ShowPitchHoles")

CUTOUT_FACES = ("FrontDoor", "BackDoor", "Roof", "GlandPlate")


def make_enclosure(doc, name="Enclosure"):
    obj = doc.addObject("Part::FeaturePython", name)
    Enclosure(obj)
    if App.GuiUp:
        ViewProviderEnclosure(obj.ViewObject)
    return obj


def parse_cutout(spec):
    out = {}
    for chunk in spec.split(";"):
        if "=" in chunk:
            k, _, v = chunk.partition("=")
            out[k.strip()] = v.strip()
    for key in ("u", "v", "d", "w", "h"):
        if key in out:
            out[key] = float(out[key])
    return out


def _fillet_vertical(solid, radius):
    """Fillet the vertical edges of a box-like solid; best effort."""
    edges = []
    for e in solid.Edges:
        try:
            t = e.tangentAt(e.FirstParameter)
        except Exception:
            continue
        if abs(t.z) > 0.99:
            edges.append(e)
    try:
        return solid.makeFillet(radius, edges)
    except Exception:
        return solid


def _fillet_all(solid, radius):
    """Round every edge (sheet-metal folded look); best effort."""
    try:
        return solid.makeFillet(radius, solid.Edges)
    except Exception:
        return _fillet_vertical(solid, radius)


def _chamfer_vertical(solid, size):
    edges = []
    for e in solid.Edges:
        try:
            t = e.tangentAt(e.FirstParameter)
        except Exception:
            continue
        if abs(t.z) > 0.99:
            edges.append(e)
    try:
        return solid.makeChamfer(size, edges)
    except Exception:
        return solid


class Enclosure:
    def __init__(self, obj):
        self.Type = "PanelEnclosure:3"
        obj.Proxy = self
        self._add_properties(obj)
        self._update_modes(obj)

    def _add_properties(self, obj):
        def add(ptype, name, group, doc):
            if not hasattr(obj, name):
                obj.addProperty(ptype, name, group, doc)
                return True
            return False

        if add("App::PropertyEnumeration", "Preset", "Enclosure",
               "Catalog size preset (applies family + size, then editable)"):
            obj.Preset = list(PRESETS)
        if add("App::PropertyEnumeration", "MountingType", "Enclosure",
               "Construction family"):
            obj.MountingType = FAMILIES
            obj.MountingType = "WallMount"
        if add("App::PropertyLength", "Width", "Enclosure",
               "Width (per bay for Bayed)"):
            obj.Width = 600.0
        if add("App::PropertyLength", "Height", "Enclosure",
               "Enclosure height (plinth adds below)"):
            obj.Height = 800.0
        if add("App::PropertyLength", "Depth", "Enclosure", "Depth"):
            obj.Depth = 300.0
        if add("App::PropertyLength", "WallThickness", "Enclosure",
               "Sheet thickness"):
            obj.WallThickness = 1.5
        if add("App::PropertyEnumeration", "IPRating", "Enclosure",
               "Ingress protection rating"):
            obj.IPRating = IP_RATINGS
            obj.IPRating = "IP55"
        if add("App::PropertyIntegerConstraint", "BayCount", "Enclosure",
               "Number of bays (Bayed family)"):
            obj.BayCount = (1, 1, 12, 1)

        if add("App::PropertyEnumeration", "DoorConfig", "Doors",
               "Door arrangement"):
            obj.DoorConfig = DOOR_CONFIGS
        if add("App::PropertyEnumeration", "DoorSwing", "Doors",
               "Hinge side (single doors)"):
            obj.DoorSwing = DOOR_SWINGS
        if add("App::PropertyEnumeration", "DoorStyle", "Doors",
               "Front door style"):
            obj.DoorStyle = DOOR_STYLES
        if add("App::PropertyEnumeration", "LockType", "Doors",
               "Door lock / handle type"):
            obj.LockType = LOCK_TYPES
        if add("App::PropertyAngle", "FrontDoorAngle", "Doors",
               "Front door opening angle (0 = closed)"):
            obj.FrontDoorAngle = 0.0
        if add("App::PropertyAngle", "BackDoorAngle", "Doors",
               "Back door opening angle (0 = closed)"):
            obj.BackDoorAngle = 0.0
        if add("App::PropertyBool", "InnerDoor", "Doors",
               "Inner door behind the front door"):
            obj.InnerDoor = False
        if add("App::PropertyAngle", "InnerDoorAngle", "Doors",
               "Inner door opening angle"):
            obj.InnerDoorAngle = 0.0
        if add("App::PropertyEnumeration", "RearStyle", "Doors",
               "Rear: fixed panel, door, or open"):
            obj.RearStyle = REAR_STYLES
        if add("App::PropertyBool", "SidePanels", "Doors",
               "Fit side panels (Bayed/FreeStanding)"):
            obj.SidePanels = True

        if add("App::PropertyBool", "MountingPlate", "Interior",
               "Include simple built-in mounting plate "
               "(turned off when a MountingPlate object is added)"):
            obj.MountingPlate = True
        if add("App::PropertyLength", "PlateSetback", "Interior",
               "Mounting plate distance from rear"):
            obj.PlateSetback = 20.0

        if add("App::PropertyBool", "GlandPlateFitted", "CableEntry",
               "Fit bottom gland plate(s) over a floor cutout"):
            obj.GlandPlateFitted = True
        if add("App::PropertyStringList", "Cutouts", "CableEntry",
               "Cutout specs: face=..;type=circle|rect;u=..;v=..;d=..|w=..;h=.."):
            obj.Cutouts = []

        if add("App::PropertyEnumeration", "Plinth", "FloorStanding",
               "Plinth height under the body/frame"):
            obj.Plinth = PLINTHS
            obj.Plinth = "100mm"
        if add("App::PropertyLength", "SkeletonPitch", "FloorStanding",
               "Frame pre-hole pitch"):
            obj.SkeletonPitch = 25.0
        if add("App::PropertyBool", "ShowPitchHoles", "FloorStanding",
               "Model the frame pitch holes (slower recompute)"):
            obj.ShowPitchHoles = False

        if add("App::PropertyStringList", "Warnings", "Rules",
               "Advisory rule warnings (read-only)"):
            obj.setEditorMode("Warnings", 1)
        if add("App::PropertyStringList", "SolidColors", "Rules",
               "Per-solid display colors (computed)"):
            obj.setEditorMode("SolidColors", 2)

    # -- persistence --------------------------------------------------------
    def dumps(self):
        return None

    def loads(self, state):
        return None

    # -- property plumbing --------------------------------------------------
    def _update_modes(self, obj):
        needed = FLOOR_ONLY_PROPS + BAYED_ONLY_PROPS + ("MountingType",)
        if not all(hasattr(obj, p) for p in needed):
            return
        fam = obj.MountingType
        floor = fam in ("FreeStanding", "Bayed")
        for prop in FLOOR_ONLY_PROPS:
            obj.setEditorMode(prop, 0 if floor else 2)
        for prop in BAYED_ONLY_PROPS:
            obj.setEditorMode(prop, 0 if fam == "Bayed" else 2)
        if hasattr(obj, "SidePanels"):
            obj.setEditorMode("SidePanels", 0 if floor else 2)

    def onChanged(self, obj, prop):
        if prop == "MountingType":
            self._update_modes(obj)
        elif prop == "Preset":
            preset = PRESETS.get(obj.Preset)
            if preset:
                fam, w, h, d, plinth = preset
                obj.MountingType = fam
                obj.Width, obj.Height, obj.Depth = w, h, d
                obj.Plinth = plinth

    def onDocumentRestored(self, obj):
        self._add_properties(obj)
        self._update_modes(obj)

    # -- rule checks --------------------------------------------------------
    def _check_rules(self, obj):
        warnings = []
        ip_num = int(obj.IPRating[2:])
        if obj.DoorStyle == "Vented" and ip_num >= 55:
            warnings.append("Vented door is not achievable at %s — use a "
                            "filter fan or heat exchanger." % obj.IPRating)
        if obj.Width.Value > 800 and not obj.DoorConfig.startswith("Double"):
            warnings.append("Width > 800 mm: double door applied.")
        if obj.MountingType != "Bayed" and obj.BayCount > 1:
            warnings.append("BayCount ignored: family is not Bayed.")
        cut_specs = [parse_cutout(s) for s in obj.Cutouts]
        if any(c.get("face") == "GlandPlate" for c in cut_specs) \
                and not obj.GlandPlateFitted:
            warnings.append("Gland cutouts defined but no gland plate fitted.")
        if ip_num >= 65 and obj.DoorStyle == "Glazed":
            warnings.append("Check glazed door gasket rating for %s."
                            % obj.IPRating)
        return warnings

    # -- geometry -----------------------------------------------------------
    def execute(self, obj):
        parts = []  # list of (solid, color)
        fam = obj.MountingType
        if fam == "Bayed":
            self._build_bayed(obj, parts)
        else:
            self._build_monobody(obj, parts,
                                 floor=(fam == "FreeStanding"))
        obj.SolidColors = ["%.3f,%.3f,%.3f" % c for _s, c in parts]
        obj.Shape = Part.makeCompound([s for s, _c in parts])
        obj.Warnings = self._check_rules(obj)

    # .. mono-body families (KX / AX / VX SE) ...............................
    def _build_monobody(self, obj, parts, floor):
        w = obj.Width.Value
        h = obj.Height.Value
        d = obj.Depth.Value
        t = obj.WallThickness.Value
        ph = PLINTH_MM[obj.Plinth] if floor else 0.0

        if ph:
            parts.append((self._plinth(w, d, ph), BLACK))

        outer = Part.makeBox(w, d, h, Vector(0, 0, ph))
        outer = _fillet_all(outer, 5.0)
        inner = Part.makeBox(w - 2 * t, d - 2 * t, h - 2 * t,
                             Vector(t, t, ph + t))
        front = Part.makeBox(w - 2 * t, 2 * t, h - 2 * t,
                             Vector(t, -t, ph + t))
        body = outer.cut(inner).cut(front)
        body = self._roof_cutouts(obj, body, x0=0, w=w, d=d, ztop=ph + h)
        body, gland = self._floor_gland(obj, body, x0=0, w=w, d=d, zfloor=ph)
        parts.append((body, RAL7035))
        parts += gland

        self._doors(obj, parts, x0=0.0, w=w, h=h, z0=ph, front_y=0.0,
                    back_y=d if obj.RearStyle == "Door" else None)
        if obj.InnerDoor:
            parts.append((self._inner_door(obj, 0.0, w, h, ph, t),
                          RAL7035_D))

        if obj.MountingPlate:
            margin = 25.0
            py = d - t - obj.PlateSetback.Value
            parts.append((Part.makeBox(w - 2 * margin, 2.0, h - 2 * margin,
                                       Vector(margin, py, ph + margin)),
                          ZINC))

    # .. bayed skeleton family (VX25) .......................................
    def _build_bayed(self, obj, parts):
        w = obj.Width.Value
        h = obj.Height.Value
        d = obj.Depth.Value
        s = PROFILE
        ph = PLINTH_MM[obj.Plinth]
        bays = max(int(obj.BayCount), 1)
        total_w = w * bays

        if ph:
            parts.append((self._plinth(total_w, d, ph), BLACK))

        for b in range(bays):
            x0 = b * w
            for px, py in ((x0, 0), (x0 + w - s, 0),
                           (x0, d - s), (x0 + w - s, d - s)):
                post = Part.makeBox(s, s, h, Vector(px, py, ph))
                post = _chamfer_vertical(post, 6.0)
                if obj.ShowPitchHoles:
                    post = self._drill_pitch_holes(obj, post, s, ph, h)
                parts.append((post, RAL7035_D))
            for z in (ph, ph + h - s):
                for y in (0, d - s):
                    parts.append((Part.makeBox(w - 2 * s, s, s,
                                               Vector(x0 + s, y, z)),
                                  RAL7035_D))
                for x in (x0, x0 + w - s):
                    parts.append((Part.makeBox(s, d - 2 * s, s,
                                               Vector(x, s, z)),
                                  RAL7035_D))

            self._doors(obj, parts, x0=x0, w=w, h=h, z0=ph, front_y=0.0,
                        back_y=d if obj.RearStyle == "Door" else None)

        roof = Part.makeBox(total_w, d, 2.0, Vector(0, 0, ph + h))
        roof = self._roof_cutouts(obj, roof, 0, total_w, d, ph + h + 2.0)
        parts.append((roof, RAL7035))

        floor_sheet = Part.makeBox(total_w - 2 * s, d - 2 * s, 2.0,
                                   Vector(s, s, ph))
        floor_sheet, gland = self._floor_gland(
            obj, floor_sheet, x0=s, w=total_w - 2 * s, d=d, zfloor=ph)
        parts.append((floor_sheet, ZINC))
        parts += gland

        if obj.SidePanels:
            parts.append((Part.makeBox(1.5, d, h, Vector(-1.5, 0, ph)),
                          RAL7035))
            parts.append((Part.makeBox(1.5, d, h, Vector(total_w, 0, ph)),
                          RAL7035))
        if obj.RearStyle == "Panel":
            parts.append((Part.makeBox(total_w, 1.5, h, Vector(0, d, ph)),
                          RAL7035))

        if obj.MountingPlate:
            margin = 50.0
            py = d - s - obj.PlateSetback.Value
            parts.append((Part.makeBox(total_w - 2 * margin, 3.0,
                                       h - 2 * margin,
                                       Vector(margin, py, ph + margin)),
                          ZINC))
        if obj.InnerDoor:
            t = obj.WallThickness.Value
            parts.append((self._inner_door(obj, 0.0, w, h, ph, t),
                          RAL7035_D))

    # .. shared pieces ......................................................
    def _plinth(self, w, d, ph):
        p_outer = Part.makeBox(w, d, ph)
        p_inner = Part.makeBox(w - 6, d - 6, ph + 2, Vector(3, 3, -1))
        plinth = p_outer.cut(p_inner)
        # trim grooves front + back
        for z in (ph * 0.35, ph * 0.7):
            groove = Part.makeBox(w - 20, d + 4, 3.0, Vector(10, -2, z))
            plinth = plinth.cut(groove)
        return plinth

    def _drill_pitch_holes(self, obj, post, s, z0, h):
        pitch = max(obj.SkeletonPitch.Value, 5.0)
        r = PITCH_HOLE_D / 2.0
        bb = post.BoundBox
        cyls = []
        z = z0 + pitch / 2.0
        while z < z0 + h - pitch / 2.0:
            cyls.append(Part.makeCylinder(
                r, s + 2.0, Vector(bb.XMin + s / 2.0, bb.YMin - 1.0, z),
                Vector(0, 1, 0)))
            cyls.append(Part.makeCylinder(
                r, s + 2.0, Vector(bb.XMin - 1.0, bb.YMin + s / 2.0, z),
                Vector(1, 0, 0)))
            z += pitch
        return post.cut(Part.makeCompound(cyls)) if cyls else post

    def _face_cutout_solid(self, cut, x0, z0, y_from, y_to):
        if cut.get("type") == "circle":
            r = cut.get("d", 22.3) / 2.0
            return Part.makeCylinder(
                r, y_to - y_from,
                Vector(x0 + cut["u"], y_from, z0 + cut["v"]),
                Vector(0, 1, 0))
        cw, chh = cut.get("w", 50.0), cut.get("h", 50.0)
        return Part.makeBox(cw, y_to - y_from, chh,
                            Vector(x0 + cut["u"] - cw / 2.0, y_from,
                                   z0 + cut["v"] - chh / 2.0))

    def _roof_cutouts(self, obj, solid, x0, w, d, ztop):
        for spec in obj.Cutouts:
            cut = parse_cutout(spec)
            if cut.get("face") != "Roof":
                continue
            if cut.get("type") == "circle":
                r = cut.get("d", 22.3) / 2.0
                tool = Part.makeCylinder(
                    r, 20.0, Vector(x0 + cut["u"], cut["v"], ztop - 10.0))
            else:
                cw, cd = cut.get("w", 50.0), cut.get("h", 50.0)
                tool = Part.makeBox(cw, cd, 20.0,
                                    Vector(x0 + cut["u"] - cw / 2.0,
                                           cut["v"] - cd / 2.0, ztop - 10.0))
            solid = solid.cut(tool)
        return solid

    def _floor_gland(self, obj, floor_solid, x0, w, d, zfloor):
        if not obj.GlandPlateFitted:
            return floor_solid, []
        gw = max(w * 0.6, 60.0)
        gd = max(d * 0.4, 40.0)
        gx = x0 + (w - gw) / 2.0
        gy = (d - gd) / 2.0
        opening = Part.makeBox(gw, gd, 20.0, Vector(gx, gy, zfloor - 10.0))
        floor_solid = floor_solid.cut(opening)
        plate = Part.makeBox(gw + 20.0, gd + 20.0, 2.0,
                             Vector(gx - 10.0, gy - 10.0, zfloor - 2.0))
        for spec in obj.Cutouts:
            cut = parse_cutout(spec)
            if cut.get("face") != "GlandPlate":
                continue
            r = cut.get("d", 20.0) / 2.0
            plate = plate.cut(Part.makeCylinder(
                r, 10.0,
                Vector(gx - 10.0 + cut["u"], gy - 10.0 + cut["v"],
                       zfloor - 6.0)))
        return floor_solid, [(plate, ZINC)]

    def _inner_door(self, obj, x0, w, h, z0, t):
        border = 40.0
        panel = Part.makeBox(w - 2 * t - 4, 2.0, h - 2 * t - 4,
                             Vector(x0 + t + 2, t + 2, z0 + t + 2))
        opening = Part.makeBox(w - 2 * t - 4 - 2 * border, 4.0,
                               h - 2 * t - 4 - 2 * border,
                               Vector(x0 + t + 2 + border, t + 1,
                                      z0 + t + 2 + border))
        frame = panel.cut(opening)
        angle = float(obj.InnerDoorAngle)
        if angle:
            hx = x0 + t + 2 if obj.DoorSwing == "HingeLeft" else x0 + w - t - 2
            frame.rotate(Vector(hx, t + 2, 0), Vector(0, 0, 1),
                         -angle if obj.DoorSwing == "HingeLeft" else angle)
        return frame

    def _door_leaf(self, obj, lx, lw, y_door, z0, h, face, outward):
        """One door leaf: folded-pan look, rounded vertical edges,
        style + device cutouts. Returns (leaf, extras) where extras is
        a list of (solid, color) that swing with the leaf."""
        leaf = Part.makeBox(lw, DOOR_T, h, Vector(lx, y_door, z0))
        leaf = _fillet_all(leaf, 5.0)
        # pan recess from the inner side, leaving the outer skin
        m = 28.0
        if outward < 0:   # front door: outer face at y_door
            ry0 = y_door + DOOR_SKIN
        else:             # back door: outer face at y_door + DOOR_T
            ry0 = y_door - 1.0
        recess = Part.makeBox(lw - 2 * m, DOOR_T - DOOR_SKIN + 1.0,
                              h - 2 * m, Vector(lx + m, ry0, z0 + m))
        leaf = leaf.cut(recess)
        extras = []

        if face == "front" and obj.DoorStyle == "Glazed":
            gm = max(min(60.0, lw / 4.0), m + 4.0)
            win = Part.makeBox(lw - 2 * gm, DOOR_T + 2, h * 0.5,
                               Vector(lx + gm, y_door - 1, z0 + h * 0.35))
            leaf = leaf.cut(win)
            extras.append((Part.makeBox(
                lw - 2 * gm, 3.0, h * 0.5,
                Vector(lx + gm, y_door + 0.5, z0 + h * 0.35)), GLASS))
        elif face == "front" and obj.DoorStyle == "Vented":
            slot_w = lw * 0.5
            for i in range(6):
                slot = Part.makeBox(slot_w, DOOR_T + 2, 8.0,
                                    Vector(lx + (lw - slot_w) / 2.0,
                                           y_door - 1,
                                           z0 + h * 0.15 + i * 22.0))
                leaf = leaf.cut(slot)

        cface = "FrontDoor" if face == "front" else "BackDoor"
        y_out = y_door if outward < 0 else y_door + DOOR_T
        for spec in obj.Cutouts:
            cut = parse_cutout(spec)
            if cut.get("face") != cface:
                continue
            tool = self._face_cutout_solid(cut, lx, z0,
                                           y_door - 1, y_door + DOOR_T + 1)
            leaf = leaf.cut(tool)
            extras += self._device_visual(cut, lx, z0, y_out, outward)
        return leaf, extras

    def _device_visual(self, cut, lx, z0, y_out, outward):
        dev = cut.get("dev", "")
        if not dev:
            return []
        cx = lx + cut.get("u", 0.0)
        cz = z0 + cut.get("v", 0.0)
        n = Vector(0, outward, 0)
        p = Vector(cx, y_out, cz)
        if dev == "estop":
            base = Part.makeCylinder(30.0, 5.0, p, n)
            mushroom = Part.makeCylinder(
                20.0, 16.0, Vector(cx, y_out + 5.0 * outward, cz), n)
            return [(base, DEV_YELLOW), (mushroom, DEV_RED)]
        if dev == "button":
            bezel = Part.makeCylinder(15.0, 5.0, p, n)
            cap = Part.makeCylinder(
                11.0, 9.0, Vector(cx, y_out + 5.0 * outward, cz), n)
            return [(bezel, DEV_DARK), (cap, DEV_GREEN)]
        if dev == "lamp":
            bezel = Part.makeCylinder(15.0, 5.0, p, n)
            lens = Part.makeCylinder(
                11.0, 8.0, Vector(cx, y_out + 5.0 * outward, cz), n)
            return [(bezel, DEV_DARK), (lens, DEV_AMBER)]
        if dev in ("meter", "hmi"):
            w = cut.get("w", 92.0) + 14.0
            h = cut.get("h", 92.0) + 14.0
            y0 = y_out if outward > 0 else y_out - 6.0
            frame = Part.makeBox(w, 6.0, h,
                                 Vector(cx - w / 2.0, y0, cz - h / 2.0))
            screen = Part.makeBox(
                w - 14.0, 2.0, h - 14.0,
                Vector(cx - w / 2.0 + 7.0,
                       y0 + (6.0 if outward > 0 else -2.0),
                       cz - h / 2.0 + 7.0))
            return [(frame, DEV_DARK), (screen, GLASS)]
        return []

    def _doors(self, obj, parts, x0, w, h, z0, front_y, back_y):
        double = obj.DoorConfig.startswith("Double") or w > 800.0

        def build(face, y, outward, angle):
            y_door = y + outward * DOOR_GAP - (DOOR_T if outward < 0 else 0)
            pieces = []  # (solid, color, hinge_x, sign)
            if double:
                half = w / 2.0 - 1.0
                l1, ex1 = self._door_leaf(obj, x0, half, y_door, z0, h,
                                          face, outward)
                l2, ex2 = self._door_leaf(obj, x0 + w / 2.0 + 1.0, half,
                                          y_door, z0, h, face, outward)
                h1 = self._handle(obj, x0 + w / 2.0 - 45.0, y_door,
                                  z0 + h / 2.0, outward, z0, h)
                h2 = self._handle(obj, x0 + w / 2.0 + 45.0, y_door,
                                  z0 + h / 2.0, outward, z0, h)
                pieces += [(s, c, x0, -1) for s, c in [(l1, RAL7035)]
                           + ex1 + h1]
                pieces += [(s, c, x0 + w, +1) for s, c in [(l2, RAL7035)]
                           + ex2 + h2]
            else:
                leaf, extras = self._door_leaf(obj, x0, w, y_door, z0, h,
                                               face, outward)
                hinge_left = obj.DoorSwing == "HingeLeft"
                hx = x0 + (0.0 if hinge_left else w)
                sign = -1 if hinge_left else +1
                handle = self._handle(
                    obj, x0 + (w - 65.0 if hinge_left else 65.0),
                    y_door, z0 + h / 2.0, outward, z0, h)
                pieces += [(s, c, hx, sign)
                           for s, c in [(leaf, RAL7035)] + extras + handle]

            for solid, color, hx, sign in pieces:
                if angle:
                    solid.rotate(Vector(hx, y + outward * DOOR_GAP, 0),
                                 Vector(0, 0, 1), sign * angle * -outward)
                parts.append((solid, color))

            # hinge barrels (fixed halves, on the body side of the gap)
            if double:
                hinge_xs = (x0 + 2.0, x0 + w - 2.0)
            else:
                hinge_xs = (x0 + 2.0 if obj.DoorSwing == "HingeLeft"
                            else x0 + w - 2.0,)
            zs = [z0 + h * 0.12, z0 + h * 0.88]
            if h > 1200:
                zs.append(z0 + h * 0.5)
            hy = y + outward * (DOOR_GAP + DOOR_T / 2.0)
            for xh in hinge_xs:
                for zc in zs:
                    parts.append((Part.makeCylinder(
                        6.0, 64.0, Vector(xh, hy, zc - 32.0)), BLACK))

        build("front", front_y, -1, float(obj.FrontDoorAngle))
        if back_y is not None:
            build("back", back_y, +1, float(obj.BackDoorAngle))

    def _handle(self, obj, hx, y_door, hz, outward, z0=None, h=None):
        """Realistic handle assembly incl. 3-point locking:
        list of (solid, color)."""
        lock = obj.LockType
        y_face = y_door + (DOOR_T if outward > 0 else 0)
        n = Vector(0, outward, 0)
        out = []
        out += self._locking(hx, y_door, hz, outward, z0, h)

        if lock == "SwingHandleKeyBarrel":
            esc_h = 170.0
            esc = Part.makeBox(
                34.0, 6.0, esc_h,
                Vector(hx - 17.0,
                       y_face if outward > 0 else y_face - 6.0,
                       hz - esc_h / 2.0))
            esc = _fillet_vertical(esc, 8.0)
            out.append((esc, BLACK))
            lever = Part.makeBox(
                22.0, 14.0, 120.0,
                Vector(hx - 11.0,
                       y_face + 6.0 * outward if outward > 0
                       else y_face - 20.0,
                       hz - 66.0))
            lever = _fillet_vertical(lever, 6.0)
            out.append((lever, BLACK))
            barrel = Part.makeCylinder(
                7.0, 3.0, Vector(hx, y_face + (20.0 if outward > 0
                                               else -20.0) * 1.0, hz + 66.0),
                n)
            out.append((barrel, ZINC))
        elif lock == "WingHandle":
            knob = Part.makeCylinder(16.0, 9.0, Vector(hx, y_face, hz), n)
            out.append((knob, BLACK))
            wing = Part.makeBox(
                86.0, 9.0, 18.0,
                Vector(hx - 43.0,
                       y_face + 9.0 * outward if outward > 0
                       else y_face - 18.0,
                       hz - 9.0))
            out.append((wing, BLACK))
        elif lock == "Padlockable":
            base = Part.makeBox(
                26.0, 6.0, 44.0,
                Vector(hx - 13.0,
                       y_face if outward > 0 else y_face - 6.0,
                       hz - 22.0))
            out.append((base, BLACK))
            for dz in (-12.0, 12.0):
                lug = Part.makeBox(
                    5.0, 14.0, 16.0,
                    Vector(hx - 2.5,
                           y_face + 6.0 * outward if outward > 0
                           else y_face - 20.0,
                           hz + dz - 8.0))
                out.append((lug, ZINC))
        else:  # quarter-turn inserts
            esc = Part.makeCylinder(15.0, 4.0, Vector(hx, y_face, hz), n)
            out.append((esc, BLACK))
            insert = Part.makeCylinder(
                8.0, 8.0, Vector(hx, y_face + 4.0 * outward, hz), n)
            out.append((insert, ZINC))
            bit_r = 3.0 if "3mm" in lock else 5.0
            bit = Part.makeCylinder(
                bit_r, 4.0, Vector(hx, y_face + 12.0 * outward, hz), n)
            out.append((bit, DEV_DARK))
        return out

    def _locking(self, hx, y_door, hz, outward, z0, h):
        """3-point locking on the inner door face: cam box at the
        handle, vertical lock rods to top/bottom latch tongues."""
        if z0 is None or h is None:
            return []
        inner_y = y_door + DOOR_T + 2.0 if outward < 0 else y_door - 2.0
        rod_y = inner_y + 4.0 if outward < 0 else inner_y - 4.0
        out = []
        cam = Part.makeBox(
            28.0, 10.0, 18.0,
            Vector(hx - 14.0, inner_y if outward < 0 else inner_y - 10.0,
                   hz - 9.0))
        out.append((cam, ZINC))
        if h > 700:
            for za, zb in ((z0 + 28.0, hz - 12.0), (hz + 12.0, z0 + h - 28.0)):
                if zb - za > 50.0:
                    out.append((Part.makeCylinder(
                        3.0, zb - za, Vector(hx, rod_y, za)), ZINC))
            for ze in (z0 + 16.0, z0 + h - 40.0):
                out.append((Part.makeBox(
                    8.0, 6.0, 24.0,
                    Vector(hx - 4.0, rod_y - 3.0, ze)), ZINC))
        return out


class ViewProviderEnclosure:
    def __init__(self, vobj):
        vobj.Proxy = self

    def getIcon(self):
        return os.path.join(ICONDIR, "Enclosure.svg")

    def attach(self, vobj):
        self.vobj = vobj

    def updateData(self, obj, prop):
        if prop == "Shape":
            apply_solid_colors(obj)

    def setupContextMenu(self, vobj, menu):
        try:
            obj = vobj.Object
            for label, fn in (
                ("Open/close front door", lambda: _toggle(obj,
                                                          "FrontDoorAngle")),
                ("Open/close back door", lambda: _toggle(obj,
                                                         "BackDoorAngle")),
                ("Open all doors", lambda: _set_doors(obj, 120.0)),
                ("Close all doors", lambda: _set_doors(obj, 0.0)),
            ):
                action = menu.addAction(label)
                action.triggered.connect(fn)
        except Exception:
            pass

    def doubleClicked(self, vobj):
        try:
            from freecad.panelwb.ui import show_enclosure_dialog
            show_enclosure_dialog(vobj.Object)
        except Exception:
            _toggle(vobj.Object, "FrontDoorAngle")
        return True

    def dumps(self):
        return None

    def loads(self, state):
        return None


def apply_solid_colors(obj):
    """Expand per-solid colors to per-face DiffuseColor."""
    try:
        vobj = obj.ViewObject
        solids = obj.Shape.Solids
        colors = [tuple(float(x) for x in c.split(","))
                  for c in obj.SolidColors]
        if not solids or len(colors) != len(solids):
            return
        faces = []
        for sol, col in zip(solids, colors):
            faces += [col + (1.0,)] * len(sol.Faces)
        if len(faces) == len(obj.Shape.Faces):
            vobj.DiffuseColor = faces
    except Exception:
        pass


def _toggle(obj, prop):
    setattr(obj, prop, 0.0 if float(getattr(obj, prop)) > 1.0 else 120.0)
    obj.Document.recompute()


def _set_doors(obj, angle):
    obj.FrontDoorAngle = angle
    obj.BackDoorAngle = angle
    if obj.InnerDoor:
        obj.InnerDoorAngle = angle
    obj.Document.recompute()
