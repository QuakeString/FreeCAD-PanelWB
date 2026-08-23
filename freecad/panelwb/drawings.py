"""TechDraw fabrication drawing generation.

make_drawings(doc) creates:
  Page 'GA'     - general arrangement: front / side / top / iso of the
                  enclosure (doors closed as modeled)
  Page 'Layout' - mounting plate with rails, ducts and components,
                  plus a device schedule annotation keyed to the BOM
"""

import os

import FreeCAD as App


def _template_path():
    tdir = os.path.join(App.getResourceDir(), "Mod", "TechDraw", "Templates")
    for name in ("A3_Landscape_blank.svg", "A3_Landscape_ISO7200TD.svg",
                 "A3_Landscape.svg"):
        path = os.path.join(tdir, name)
        if os.path.exists(path):
            return path
    for name in sorted(os.listdir(tdir)):
        if name.endswith(".svg"):
            return os.path.join(tdir, name)
    raise RuntimeError("No TechDraw template found in %s" % tdir)


def _new_page(doc, name):
    old = doc.getObject(name)
    if old is not None:
        for v in list(getattr(old, "Views", [])):
            doc.removeObject(v.Name)
        doc.removeObject(name)
        tmpl = doc.getObject(name + "Template")
        if tmpl is not None:
            doc.removeObject(tmpl.Name)
    page = doc.addObject("TechDraw::DrawPage", name)
    template = doc.addObject("TechDraw::DrawSVGTemplate",
                             name + "Template")
    template.Template = _template_path()
    page.Template = template
    return page


def _add_view(doc, page, sources, name, direction, x, y, scale,
              rotation=0.0):
    view = doc.addObject("TechDraw::DrawViewPart", name)
    view.Source = sources
    view.Direction = direction
    view.ScaleType = "Custom"
    view.Scale = scale
    view.X = x
    view.Y = y
    if rotation:
        view.Rotation = rotation
    page.addView(view)
    return view


def make_drawings(doc):
    from freecad.panelwb.reports import collect
    data = collect(doc)
    if not data["enclosures"]:
        raise ValueError("No enclosure in document")
    enc = data["enclosures"][0]

    bays = int(enc.BayCount) if enc.MountingType == "Bayed" else 1
    w = enc.Width.Value * bays
    h = enc.Height.Value + 250.0  # plinth allowance
    d = enc.Depth.Value
    # fit views into an A3 quadrant (~180x120 mm each)
    scale = min(150.0 / max(w, d), 100.0 / h, 0.25)

    ga = _new_page(doc, "GA")
    _add_view(doc, ga, [enc], "GA_Front", App.Vector(0, -1, 0),
              80, 180, scale)
    _add_view(doc, ga, [enc], "GA_Side", App.Vector(-1, 0, 0),
              200, 180, scale)
    _add_view(doc, ga, [enc], "GA_Top", App.Vector(0, 0, 1),
              80, 70, scale)
    _add_view(doc, ga, [enc], "GA_Iso", App.Vector(1, -1, 1),
              300, 100, scale * 0.8)

    pages = [ga]
    if data["plates"]:
        layout_sources = (data["plates"] + data["rails"] + data["ducts"] +
                          data["chassis"] + data["components"])
        layout = _new_page(doc, "Layout")
        _add_view(doc, layout, layout_sources, "Layout_Front",
                  App.Vector(0, -1, 0), 140, 150, scale)

        # device schedule annotation
        lines = ["DEVICE SCHEDULE"]
        for comp in data["components"]:
            tag = comp.Tag or comp.Label
            lines.append("%s  %s" % (tag, comp.PartNo))
        note = doc.addObject("TechDraw::DrawViewAnnotation", "Schedule")
        note.Text = lines[:30]
        note.X = 330
        note.Y = 220
        layout.addView(note)
        pages.append(layout)

    doc.recompute()
    return pages
