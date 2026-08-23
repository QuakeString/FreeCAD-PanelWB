"""Headless test suite. Run:  freecadcmd tests/run_tests.py"""

import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import FreeCAD as App  # noqa: E402

PASS = []
FAIL = []


def check(name, fn):
    try:
        fn()
        PASS.append(name)
        print("PASS %s" % name)
    except Exception:
        FAIL.append(name)
        print("FAIL %s" % name)
        traceback.print_exc()


# ---------------------------------------------------------------- enclosure
def t_families():
    from freecad.panelwb.enclosure import make_enclosure
    doc = App.newDocument("TFam")
    e = make_enclosure(doc)
    for fam, w, h, d in (("SmallBox", 300, 400, 155),
                         ("WallMount", 600, 800, 300),
                         ("FreeStanding", 800, 2000, 600),
                         ("Bayed", 800, 2000, 600)):
        e.MountingType = fam
        e.Width, e.Height, e.Depth = w, h, d
        doc.recompute()
        assert e.Shape.isValid(), fam
        assert len(e.Shape.Solids) > 2, fam
    App.closeDocument("TFam")


def t_bays():
    from freecad.panelwb.enclosure import make_enclosure
    doc = App.newDocument("TBay")
    e = make_enclosure(doc)
    e.MountingType = "Bayed"
    e.Width, e.Height, e.Depth = 800, 2000, 600
    e.BayCount = 3
    doc.recompute()
    assert e.Shape.isValid()
    assert e.Shape.BoundBox.XLength > 2350  # 3 bays + side panels
    App.closeDocument("TBay")


def t_door_swing():
    from freecad.panelwb.enclosure import make_enclosure
    doc = App.newDocument("TDoor")
    e = make_enclosure(doc)
    doc.recompute()
    y_closed = e.Shape.BoundBox.YMin
    e.FrontDoorAngle = 120.0
    doc.recompute()
    assert e.Shape.isValid()
    assert e.Shape.BoundBox.YMin < y_closed - 100  # door swings out
    e.FrontDoorAngle = 0.0
    e.DoorConfig = "DoubleFrontAndBack"
    e.RearStyle = "Door"
    e.BackDoorAngle = 90.0
    doc.recompute()
    assert e.Shape.isValid()
    App.closeDocument("TDoor")


def t_door_styles():
    from freecad.panelwb.enclosure import make_enclosure
    doc = App.newDocument("TStyle")
    e = make_enclosure(doc)
    for style in ("Glazed", "Vented", "Solid"):
        e.DoorStyle = style
        doc.recompute()
        assert e.Shape.isValid(), style
    e.DoorStyle = "Vented"
    e.IPRating = "IP65"
    doc.recompute()
    assert any("Vented" in w for w in e.Warnings)
    App.closeDocument("TStyle")


def t_cutouts():
    from freecad.panelwb.enclosure import make_enclosure
    doc = App.newDocument("TCut")
    e = make_enclosure(doc)
    e.Cutouts = [
        "face=FrontDoor;type=circle;u=100;v=600;d=22.3",
        "face=FrontDoor;type=rect;u=300;v=500;w=96;h=96",
        "face=Roof;type=rect;u=300;v=150;w=80;h=80",
        "face=GlandPlate;type=circle;u=60;v=40;d=20",
    ]
    doc.recompute()
    assert e.Shape.isValid()
    App.closeDocument("TCut")


def t_preset_and_inner():
    from freecad.panelwb.enclosure import make_enclosure
    doc = App.newDocument("TPre")
    e = make_enclosure(doc)
    e.Preset = "VX25 800x2000x600"
    doc.recompute()
    assert e.MountingType == "Bayed"
    assert abs(e.Height.Value - 2000) < 0.1
    e.InnerDoor = True
    e.InnerDoorAngle = 45.0
    doc.recompute()
    assert e.Shape.isValid()
    App.closeDocument("TPre")


def t_migration():
    """Old files: onDocumentRestored must add missing properties."""
    from freecad.panelwb.enclosure import Enclosure, make_enclosure
    doc = App.newDocument("TMig")
    e = make_enclosure(doc)
    e.Proxy.onDocumentRestored(e)
    doc.recompute()
    assert e.Shape.isValid()
    App.closeDocument("TMig")


# ----------------------------------------------------------------- interior
def t_interior():
    from freecad.panelwb.enclosure import make_enclosure
    from freecad.panelwb import interior
    doc = App.newDocument("TInt")
    e = make_enclosure(doc)
    e.MountingType = "Bayed"
    e.Width, e.Height, e.Depth = 800, 2000, 600
    doc.recompute()
    plate = interior.make_mounting_plate(doc, e)
    doc.recompute()
    assert not e.MountingPlate  # built-in slab superseded
    assert plate.Shape.isValid()
    pw0 = plate.Shape.BoundBox.XLength

    rail = interior.make_din_rail(doc, plate)
    rail.PositionZ = 1500.0
    duct = interior.make_duct(doc, plate)
    duct.Orientation = "Vertical"
    chassis = interior.make_chassis_rail(doc, plate)
    doc.recompute()
    for o in (rail, duct, chassis):
        assert o.Shape.isValid(), o.Name
    rl0 = rail.Shape.BoundBox.XLength

    # resize the enclosure: plate and auto-length rail must follow
    e.Width = 1000
    doc.recompute()
    assert plate.Shape.BoundBox.XLength > pw0 + 150
    assert rail.Shape.BoundBox.XLength > rl0 + 150
    # rail sits proud of the plate face (towards the door, -Y)
    assert rail.Shape.BoundBox.YMin < plate.Shape.BoundBox.YMin
    App.closeDocument("TInt")


# --------------------------------------------------------------- components
def t_components():
    from freecad.panelwb.enclosure import make_enclosure
    from freecad.panelwb import interior, components
    doc = App.newDocument("TComp")
    e = make_enclosure(doc)
    e.Preset = "AX 600x760x350"
    doc.recompute()
    plate = interior.make_mounting_plate(doc, e)
    doc.recompute()
    rail = interior.make_din_rail(doc, plate)
    rail.PositionZ = 500.0
    doc.recompute()

    lib = components.load_library()
    assert len(lib) >= 20
    ids = ["mcb_3p", "contactor_s00", "psu_24v_5a", "plc_compact",
           "router_cell"] + ["terminal_2_5"] * 10
    for lib_id in ids:
        components.make_component(doc, lib_id, rail=rail)
    doc.recompute()

    comps = components.components_on_rail(rail)
    assert len(comps) == 15
    # no overlaps
    spans = sorted((c.OffsetMM.Value, c.OffsetMM.Value + c.WidthMM.Value)
                   for c in comps)
    for (a0, a1), (b0, b1) in zip(spans, spans[1:]):
        assert a1 <= b0 + 0.01, "overlap %s %s" % ((a0, a1), (b0, b1))
    used, length, fill = components.rail_fill(rail)
    assert 0 < fill < 1
    for c in comps:
        assert c.Shape.isValid()
    # plate-mount device
    vfd = components.make_component(doc, "vfd_2k2", plate=plate)
    vfd.PositionX, vfd.PositionZ = 350.0, 350.0
    doc.recompute()
    assert vfd.Shape.isValid()
    # devices stand proud of the plate towards the door
    assert vfd.Shape.BoundBox.YMin < plate.Shape.BoundBox.YMin
    App.closeDocument("TComp")


# ------------------------------------------------------------- door devices
def t_door_devices():
    from freecad.panelwb.enclosure import make_enclosure
    from freecad.panelwb import cutouts
    doc = App.newDocument("TDev")
    e = make_enclosure(doc)
    e.Preset = "VX SE 800x2000x600"
    doc.recompute()
    n0 = len(e.Shape.Solids)
    cutouts.add_cutout(e, "EStop22", 400, 1500)
    cutouts.add_cutout(e, "PushButton22", 150, 1500)
    cutouts.add_cutout(e, "PilotLamp22", 250, 1500)
    cutouts.add_cutout(e, "HMI_7in", 400, 1100)
    cutouts.add_cutout(e, "GlandM25", 80, 60)
    cutouts.add_cutout(e, "GlandM25", 140, 60)
    doc.recompute()
    assert e.Shape.isValid()
    assert len(e.Shape.Solids) > n0  # bezels/mushroom appeared
    bom = dict(cutouts.device_bom_entries(e))
    assert bom.get("Cable gland M25") == 2
    assert bom.get("Emergency stop Ø22.5", bom.get("Emergency stop Ø22.5")) == 1
    # devices must swing with the door
    e.FrontDoorAngle = 90.0
    doc.recompute()
    assert e.Shape.isValid()
    App.closeDocument("TDev")


check("enclosure families", t_families)
check("interior plate/rail/duct", t_interior)
check("component library + rail placement", t_components)
check("door devices + glands", t_door_devices)
check("bayed multi-bay", t_bays)
check("door swing", t_door_swing)
check("door styles + IP rule", t_door_styles)
check("cutouts", t_cutouts)
check("preset + inner door", t_preset_and_inner)
check("migration hook", t_migration)

print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
if FAIL:
    sys.exit(1)
