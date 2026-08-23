"""BOM, thermal and fill reports.

Thermal model: first-order IEC 60890-style estimate.
  Ae = sum(area_i * b_i)  — effective cooling surface, b per face exposure
  dT = P / (k * Ae)       — k = 5.5 W/m2K painted sheet steel
This is an engineering estimate for cooling selection, not a type test.
"""

import csv
import os

import FreeCAD as App

K_STEEL = 5.5  # W/m2K


def _ptype(o):
    return getattr(getattr(o, "Proxy", None), "Type", "")


def collect(doc):
    objs = doc.Objects
    return {
        "enclosures": [o for o in objs
                       if _ptype(o).startswith("PanelEnclosure")],
        "plates": [o for o in objs if _ptype(o).startswith("PanelPlate")],
        "rails": [o for o in objs if _ptype(o).startswith("PanelDinRail")],
        "ducts": [o for o in objs if _ptype(o).startswith("PanelDuct")],
        "chassis": [o for o in objs
                    if _ptype(o).startswith("PanelChassisRail")],
        "components": [o for o in objs
                       if _ptype(o).startswith("PanelComponent")],
    }


def _sheet(doc, name):
    old = doc.getObject(name)
    if old is not None:
        doc.removeObject(name)
    return doc.addObject("Spreadsheet::Sheet", name)


def _csv_path(doc, suffix):
    base = doc.FileName
    if base:
        return os.path.splitext(base)[0] + "_%s.csv" % suffix
    return os.path.join(App.getUserAppDataDir(), "panelwb_%s.csv" % suffix)


# ------------------------------------------------------------------------ BOM
def make_bom(doc):
    from freecad.panelwb.cutouts import device_bom_entries
    data = collect(doc)
    rows = []  # (tag, part_no, description, qty, heat_w, weight_kg)

    for e in data["enclosures"]:
        fam = e.MountingType
        bays = int(e.BayCount) if fam == "Bayed" else 1
        desc = "%s enclosure %gx%gx%g %s" % (
            fam, e.Width.Value, e.Height.Value, e.Depth.Value, e.IPRating)
        rows.append((e.Label, "ENCL-" + fam.upper(), desc, bays, 0.0, 0.0))
        for label, qty in device_bom_entries(e):
            rows.append(("", "DOOR-DEV", label, qty, 0.0, 0.0))

    for p in data["plates"]:
        bb = p.Shape.BoundBox
        rows.append((p.Label, "PLATE",
                     "Mounting plate %.0fx%.0fx%g" % (bb.XLength, bb.ZLength,
                                                      p.Thickness.Value),
                     1, 0.0, 0.0))
    for r in data["rails"]:
        rows.append((r.Label, "RAIL-" + r.RailType,
                     "DIN rail %s L=%.0f" % (r.RailType,
                                             r.Proxy.rail_length(r)),
                     1, 0.0, 0.0))
    for d in data["ducts"]:
        rows.append((d.Label, "DUCT-" + d.Size,
                     "Wiring duct %s L=%.0f" % (d.Size,
                                                d.Proxy.duct_length(d)),
                     1, 0.0, 0.0))
    for c in data["chassis"]:
        rows.append((c.Label, "CHASSIS", "Chassis rail", 1, 0.0, 0.0))

    grouped = {}
    for comp in data["components"]:
        key = comp.PartNo
        if key not in grouped:
            lib_label = comp.LibId
            try:
                from freecad.panelwb.components import load_library
                lib_label = load_library()[comp.LibId]["label"]
            except Exception:
                pass
            grouped[key] = [comp.Tag or comp.Label, key, lib_label, 0,
                            0.0, 0.0]
        grouped[key][3] += 1
        grouped[key][4] += comp.HeatW
        grouped[key][5] += comp.WeightKg
    rows += [tuple(v) for v in grouped.values()]

    sheet = _sheet(doc, "BOM")
    headers = ("Tag", "PartNo", "Description", "Qty", "Heat W", "Weight kg")
    for col, head in enumerate(headers):
        sheet.set(chr(65 + col) + "1", head)
    for i, row in enumerate(rows, start=2):
        for col, val in enumerate(row):
            sheet.set(chr(65 + col) + str(i), str(val))
    total_heat = sum(r[4] for r in rows)
    total_weight = sum(r[5] for r in rows)
    sheet.set("A%d" % (len(rows) + 3), "TOTALS")
    sheet.set("E%d" % (len(rows) + 3), "%.1f" % total_heat)
    sheet.set("F%d" % (len(rows) + 3), "%.2f" % total_weight)
    doc.recompute()

    path = _csv_path(doc, "bom")
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(headers)
        writer.writerows(rows)
        writer.writerow(("TOTALS", "", "", "", "%.1f" % total_heat,
                         "%.2f" % total_weight))
    return rows, path


# -------------------------------------------------------------------- thermal
# face exposure factors, IEC 60890 flavor
B_FACTORS = {
    "WallMount":    {"top": 1.4, "front": 0.9, "sides": 0.9, "rear": 0.35},
    "SmallBox":     {"top": 1.4, "front": 0.9, "sides": 0.9, "rear": 0.35},
    "FreeStanding": {"top": 1.4, "front": 0.9, "sides": 0.9, "rear": 0.35},
    "Bayed":        {"top": 1.4, "front": 0.9, "sides": 0.9, "rear": 0.35},
}


def thermal_report(doc, ambient_c=35.0, allowed_internal_c=50.0):
    data = collect(doc)
    if not data["enclosures"]:
        raise ValueError("No enclosure in document")
    e = data["enclosures"][0]
    fam = e.MountingType
    bays = int(e.BayCount) if fam == "Bayed" else 1
    w = e.Width.Value / 1000.0 * bays
    h = e.Height.Value / 1000.0
    d = e.Depth.Value / 1000.0
    b = B_FACTORS[fam]

    a_top = w * d
    a_front = w * h
    a_rear = w * h
    a_sides = 2 * d * h
    ae = (a_top * b["top"] + a_front * b["front"] +
          a_sides * b["sides"] + a_rear * b["rear"])

    p_total = sum(c.HeatW for c in data["components"])
    dt = p_total / (K_STEEL * ae) if ae else float("inf")
    t_internal = ambient_c + dt
    dt_allowed = allowed_internal_c - ambient_c

    if t_internal <= allowed_internal_c:
        advice = "Passive cooling sufficient."
    elif dt_allowed > 0:
        airflow = 3.1 * p_total / dt_allowed  # m3/h rule of thumb
        advice = ("Add filter fan ~%.0f m3/h (or heat exchanger)."
                  % airflow)
    else:
        advice = ("Ambient exceeds allowed internal temperature: "
                  "closed-loop cooling unit required (~%.0f W)." % p_total)

    result = {
        "heat_w": p_total, "ae_m2": ae, "delta_t": dt,
        "ambient_c": ambient_c, "internal_c": t_internal,
        "allowed_c": allowed_internal_c, "advice": advice,
    }

    sheet = _sheet(doc, "Thermal")
    lines = [
        ("Installed heat loss", "%.1f W" % p_total),
        ("Effective surface Ae", "%.2f m2" % ae),
        ("Ambient", "%.1f C" % ambient_c),
        ("Temperature rise", "%.1f K" % dt),
        ("Internal temperature", "%.1f C" % t_internal),
        ("Allowed internal", "%.1f C" % allowed_internal_c),
        ("Advice", advice),
        ("Method", "IEC 60890-style estimate, k=%.1f W/m2K" % K_STEEL),
    ]
    for i, (k, v) in enumerate(lines, start=1):
        sheet.set("A%d" % i, k)
        sheet.set("B%d" % i, v)
    doc.recompute()
    return result


# ----------------------------------------------------------------------- fill
def fill_report(doc):
    from freecad.panelwb.components import rail_fill, components_on_rail
    data = collect(doc)
    entries = []
    warnings = []

    for r in data["rails"]:
        used, length, ratio = rail_fill(r)
        entries.append(("Rail %s" % r.Label,
                        "%.0f / %.0f mm (%.0f%%)" % (used, length,
                                                     ratio * 100)))
        if ratio > 0.8:
            warnings.append("Rail %s over 80%% full." % r.Label)
        comps = components_on_rail(r)
        for a, bcomp in zip(comps, comps[1:]):
            if a.OffsetMM.Value + a.WidthMM.Value > bcomp.OffsetMM.Value + 0.01:
                warnings.append("Overlap on %s: %s / %s"
                                % (r.Label, a.Label, bcomp.Label))

    for dct in data["ducts"]:
        entries.append(("Duct %s" % dct.Label,
                        "wire fill %d%%" % dct.WireFill))
        if dct.WireFill > 50:
            warnings.append("Duct %s over 50%% wire fill." % dct.Label)

    for p in data["plates"]:
        bb = p.Shape.BoundBox
        area = bb.XLength * bb.ZLength
        used = sum(c.WidthMM.Value * c.HeightMM.Value
                   for c in data["components"])
        if area:
            entries.append(("Plate %s" % p.Label,
                            "device footprint %.0f%%"
                            % (100.0 * used / area)))

    # bounding-box collision among plate-mounted components
    plate_comps = [c for c in data["components"]
                   if c.Mount == "plate" and c.Shape.Solids]
    for i, a in enumerate(plate_comps):
        for bcomp in plate_comps[i + 1:]:
            ab, bb2 = a.Shape.BoundBox, bcomp.Shape.BoundBox
            if (ab.XMin < bb2.XMax and bb2.XMin < ab.XMax and
                    ab.ZMin < bb2.ZMax and bb2.ZMin < ab.ZMax and
                    ab.YMin < bb2.YMax and bb2.YMin < ab.YMax):
                warnings.append("Collision: %s and %s"
                                % (a.Label, bcomp.Label))

    sheet = _sheet(doc, "Fill")
    for i, (k, v) in enumerate(entries, start=1):
        sheet.set("A%d" % i, k)
        sheet.set("B%d" % i, v)
    for j, wtext in enumerate(warnings, start=len(entries) + 2):
        sheet.set("A%d" % j, "WARNING")
        sheet.set("B%d" % j, wtext)
    doc.recompute()
    return entries, warnings
