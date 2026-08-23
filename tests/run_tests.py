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


check("enclosure families", t_families)
check("bayed multi-bay", t_bays)
check("door swing", t_door_swing)
check("door styles + IP rule", t_door_styles)
check("cutouts", t_cutouts)
check("preset + inner door", t_preset_and_inner)
check("migration hook", t_migration)

print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
if FAIL:
    sys.exit(1)
