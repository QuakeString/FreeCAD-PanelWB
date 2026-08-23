"""Standard device cutout presets and helpers.

A cutout spec is a string on Enclosure.Cutouts (see enclosure.py).
Device presets add a `dev=` field so the device renders a visual on the
door and shows up in the BOM.
"""

# metric gland clearance drill sizes (EN 62444 practice)
GLAND_DRILL = {
    "M12": 12.5, "M16": 16.5, "M20": 20.5, "M25": 25.5,
    "M32": 32.5, "M40": 40.5, "M50": 50.5, "M63": 63.5,
}

# preset -> (face default, spec template, BOM label)
DEVICE_PRESETS = {
    "PushButton22": ("FrontDoor", "type=circle;d=22.3;dev=button",
                     "Push button Ø22.5"),
    "EStop22": ("FrontDoor", "type=circle;d=22.3;dev=estop",
                "Emergency stop Ø22.5"),
    "PilotLamp22": ("FrontDoor", "type=circle;d=22.3;dev=lamp",
                    "Pilot lamp Ø22.5"),
    "SelectorSwitch22": ("FrontDoor", "type=circle;d=22.3;dev=button",
                         "Selector switch Ø22.5"),
    "Meter48": ("FrontDoor", "type=rect;w=45;h=45;dev=meter",
                "Panel meter 48x48 (DIN 43700)"),
    "Meter96": ("FrontDoor", "type=rect;w=92;h=92;dev=meter",
                "Panel meter 96x96 (DIN 43700)"),
    "HMI_4in": ("FrontDoor", "type=rect;w=119;h=93;dev=hmi",
                'HMI 4.3"'),
    "HMI_7in": ("FrontDoor", "type=rect;w=192;h=138;dev=hmi",
                'HMI 7"'),
    "HMI_10in": ("FrontDoor", "type=rect;w=259;h=201;dev=hmi",
                 'HMI 10"'),
}
for _size, _d in GLAND_DRILL.items():
    DEVICE_PRESETS["Gland" + _size] = (
        "GlandPlate", "type=circle;d=%g;dev=gland%s" % (_d, _size),
        "Cable gland %s" % _size)


def add_cutout(enclosure, preset, u, v, face=None):
    """Append a preset cutout at (u, v) on a face; returns the spec."""
    default_face, template, _label = DEVICE_PRESETS[preset]
    spec = "face=%s;%s;u=%g;v=%g" % (face or default_face, template, u, v)
    enclosure.Cutouts = list(enclosure.Cutouts) + [spec]
    return spec


def device_bom_entries(enclosure):
    """[(label, qty)] for devices implied by cutout specs."""
    from freecad.panelwb.enclosure import parse_cutout
    counts = {}
    labels = {template.split("dev=")[-1]: label
              for _f, template, label in DEVICE_PRESETS.values()
              if "dev=" in template}
    for spec in enclosure.Cutouts:
        dev = parse_cutout(spec).get("dev")
        if dev:
            label = labels.get(dev, "Device (%s)" % dev)
            counts[label] = counts.get(label, 0) + 1
    return sorted(counts.items())
