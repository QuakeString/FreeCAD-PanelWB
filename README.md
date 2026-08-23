# PanelWB — Control Panel Enclosure Workbench for FreeCAD

Design electrical control panels the way you build them: pick an enclosure,
open its doors, populate the mounting plate, punch the door cutouts, and get
the BOM, thermal estimate and fabrication drawings out.

Modeled around the Rittal system: **KX** small boxes, **AX** compact
wall-mount, **VX SE** free-standing mono-body, **VX25** bayed skeleton
frames (45 mm profile, 25 mm pitch pre-holes, multi-bay suites).

## Features

**Enclosure** (`Add enclosure`, double-click to edit)
- 4 construction families + catalog size presets, plinth 100/200 mm
- Doors: single/double, front/back, hinge side, Solid/Glazed/Vented,
  inner door, 5 lock/handle types
- Live door swing: one click (toolbar/right-click) opens the cabinet;
  Service/Closed view presets
- IP rating with advisory rules (e.g. vented door vs IP55+)
- Gland plate with real floor opening and M12–M63 drillings

**Interior** (auto re-flows when the enclosure is resized)
- Auto-sized mounting plate, TS35×7.5/15 DIN rails, wiring ducts
  (catalog sizes, wire-fill tracking), chassis rails
- PE/N bars and reserved busbar zones (RiLine-style)

**Components**
- JSON library of 21 generic devices (breakers, contactors, relays, PSUs,
  PLC, cellular router, switch, terminals, SPD, meter, VFD, transformer) —
  extend by adding entries to `parts/library.json`
- DIN devices snap to rails with auto-append placement; plate devices
  place free; each carries part no, heat loss and weight

**Door devices & cutouts**
- Ø22.5 operators (push button, e-stop, pilot lamp, selector),
  DIN 43700 meters 48/96, HMI 4.3"/7"/10", metric glands
- Correct punched holes plus visual bezels that swing with the door

**Outputs**
- BOM: spreadsheet + CSV with heat/weight totals (door devices included)
- Thermal report: IEC 60890-style ΔT estimate with cooling advice
  (passive / filter fan airflow / closed-loop unit)
- Fill report: rail fill %, duct wire fill, plate utilization,
  collision detection
- TechDraw: GA page (front/side/top/iso) + plate layout page with
  device schedule

## Install

```
ln -s /path/to/PanelWB ~/.local/share/FreeCAD/v1-1/Mod/PanelWB
```

Restart FreeCAD, select the **Panel** workbench. Requires FreeCAD 1.0+.

## Quick start

1. **Add enclosure** → pick a preset in the dialog (e.g. `VX SE
   800x2000x600`).
2. **Add mounting plate**, then **Add DIN rail** (set `PositionZ`).
3. **Add component…** → double-click devices to drop them on the rail.
4. **Add device / cutout…** → e-stop and HMI on the front door.
5. **Generate BOM / Thermal report / Generate drawings.**

Run the test suite headless: `freecadcmd tests/run_tests.py`

## Roadmap (post-0.2)

- Click-in-3D placement with snap preview
- Vendor part geometry (STEP) in the library; App::Link instancing
- Baying refinements: shared side panels, per-bay widths, partition walls
- IEC 60890 full curve method; SCCR data fields (UL 508A)
- TechDraw balloons keyed to BOM rows; hole table for fabrication
- Addon Manager registry submission

## License

LGPL-2.1-or-later
