# PanelWB — Domain Study & Implementation Plan

Status: living document. Phases 1-8 implemented (v0.2.0); the Roadmap
section of README.md tracks post-0.2 refinements.

---

## Part 1 — Domain study: what a control panel is made of

### 1.1 Enclosure families (Rittal mapping)

| Family | Rittal line | Construction | Typical envelope |
|---|---|---|---|
| Small terminal box | **KX** | Folded sheet, lid or small door | ≤ ~400×400×200 |
| Compact wall-mount | **AX** | Mono-body sheet box, single door, mounting plate | ≤ ~1000×760×300 |
| Free-standing mono-body | **VX SE** | One-piece body (no skeleton), floor-standing, W ≤ 1800 | 300–800 deep |
| Baying skeleton system | **VX25** | 45 mm frame profile, 25 mm pitch grid, bolt-on panels, bays join side-by-side | up to 2200 H |
| Switchgear | VX25 **Ri4Power** | VX25 + busbar/form separation | up to 6300 A |

Variants that cut across families: stainless (hygienic design with sloped
roof), outdoor (double wall, higher IK), ATEX.

**Modeling consequence:** `MountingType` becomes a 4-value family enum
(`SmallBox`, `WallMount`, `FreeStanding`, `Bayed`), and `Bayed` supports N
bays with shared frame members. All families share the 25 mm system pitch for
interior mounting.

### 1.2 Enclosure structure and options

- **Doors:** single / double (vertically split); glazed (viewing window);
  vented; **inner door** (hinged panel behind the main door carrying
  low-voltage devices); **swing frame** (19" or component frame that swings
  out). Hinge side reversible; opening angle 130°/180°.
- **Locks:** quarter-turn insert — double-bit 3 mm / 5 mm, square 7/8 mm,
  slotted; wing handle; comfort/swing handle with key barrel or semi-cylinder;
  padlockable hasp. One enum + insert sub-type.
- **Removable panels:** side panels, rear panel (or rear door), roof plate,
  **gland plates** in the floor (multi-piece, solid / slotted / with brush).
- **Plinth/base:** 100 / 200 mm, with removable trim panels and cable entry
  from below; levelling feet or castors as alternatives.
- **Baying:** enclosures bolt side-to-side (also back-to-back); shared
  side = open or partition panel; corner baying exists but is out of scope.
- **19" mounting:** fixed 482.6 mm angles or swing frame, U-numbered.

### 1.3 Ratings and standards (what the model must know, not certify)

- **IP (IEC 60529):** IP42/54/55/65/66. Drives: gasket presence, vented door
  legality (louvres kill anything above IP54 unless filtered), gland plate
  style, fan/filter choice.
- **IK (IEC 62262):** impact rating — metadata only.
- **NEMA:** 12 / 4 / 4X mapping for UL-flavored projects — metadata + label.
- **IEC 61439-1/-2** (assemblies) and **UL 508A** (US industrial control
  panels): the workbench never certifies, but exports the data an inspector
  asks for: fill, heat, SCCR placeholder, torque/label lists.
- **IEC 60890:** temperature-rise calculation method — the basis of the
  thermal report in Phase 6 (installed heat loss W vs. effective cooling
  surface Ae by mounting arrangement).

### 1.4 Interior installation

- **Mounting plate:** full-height zinc plated 2.5–3 mm; partial plates;
  depth-adjustable on the pitch grid. Everything mounts to it.
- **Chassis/support rails:** C-profile and VX punched-section rails on the
  25 mm grid for heavy gear (drives, transformers).
- **DIN rail (EN 60715):** TS35×7.5 and TS35×15. Devices occupy rail width in
  **modules (1 M = 18 mm / 17.5 mm eu convention)**.
- **Component families** (each = footprint + width + heat loss + weight):
  MCB/RCD/MCCB, contactors/overloads, relays/interface, PSUs, PLC/RTU racks,
  network switches, routers (Robustel!), energy meters, SPDs, terminal
  blocks (with end brackets, separators, jumpers, markers), motor drives
  (plate-mount), transformers/UPS (chassis-mount).
- **Earthing:** PE bar/rail, mounting-plate bonding straps, door bonding.

### 1.5 Power distribution

Main switch/isolator (door-interlocked handle), busbar systems (RiLine
40/60 mm module), distribution blocks, N/PE bars. Geometry-light in early
phases (reserved zones + BOM entries), real busbar modeling deferred.

### 1.6 Cable management

- **Wiring duct:** slotted PVC, standard widths 25–125 mm, heights 40–100 mm,
  with lid; fill % target ≤ 50 %.
- **Cable entry:** metric glands **M12–M63 (EN 62444)**, gland plates,
  membrane/brush entry systems for pre-terminated cables, EMC glands.
- **Strain relief rails** below the gland area; C-rail with clamps.

### 1.7 Climate control

Passive louvres → filter fans (with exhaust filter) → air/air heat
exchanger → air/water heat exchanger → compressor cooling unit → and, for
condensation, **anti-condensation heater + thermostat/hygrostat**. Selection
is an output of the IEC 60890 calc: ΔT from installed W and Ae. Door-operated
switch, enclosure LED light, document pocket as minor accessories.

### 1.8 Door / operator devices

- **Ø22.5 devices** (pushbuttons, selector switches, pilot lights, e-stops):
  standard **22.3 mm punched hole**, on a spacing grid.
- **HMI / panel meters:** rectangular cutouts per DIN 43700 (48×48, 96×96,
  138×138…) plus vendor-specific HMI cutouts with corner radii and stud holes.
- Signal towers (roof), key switches, USB/RJ45 bulkhead feed-throughs.

### 1.9 What engineers need out of the tool

1. **GA drawing** — outside views, dimensions, door swing, cutout positions.
2. **Layout drawing** — mounting plate with placed components, labeled.
3. **BOM** — part numbers, quantities, per-device heat/weight rolled up.
4. **Thermal report** — installed W, Ae, predicted ΔT, suggested cooling.
5. **Fill reports** — rail fill %, duct fill %, plate utilization %.
6. Labels/wire lists later (EPLAN does wiring; we don't compete there).

---

## Part 2 — Workbench architecture

### 2.1 Document object model

```
PanelProject (App::Part)
├── Enclosure            (FeaturePython — family, doors, IP, locks, plinth…)
│   └── Cutouts          (list of cutout features bound to faces: glands, Ø22.5, HMI)
├── Interior
│   ├── MountingPlate    (auto-sized from Enclosure, overridable)
│   ├── DinRail[]        (TS35, position on plate, length, fill state)
│   ├── Duct[]           (width/height, routed as polyline on the plate)
│   └── ChassisRail[]
├── Components[]         (App::Link to library parts + placement metadata)
└── Reports              (spreadsheet objects: BOM, thermal, fill)
```

Parent/child via `App::Part` groups; placements expressed relative to the
mounting-plate coordinate system so a resized enclosure re-flows sensibly.

### 2.2 Component library

`parts/<category>/<vendor>_<partno>/`:
- `geometry.FCStd` (or `.step`) — visual model, simplified
- `meta.json` — schema:

```json
{
  "part_no": "3RT2015-1BB41", "vendor": "Siemens", "category": "contactor",
  "mount": "din35", "width_mm": 45, "height_mm": 85, "depth_mm": 80,
  "heat_w": 4.2, "weight_kg": 0.28, "voltage": "24VDC",
  "clearance_mm": {"top": 30, "bottom": 30}
}
```

Insertion = `App::Link` to a shared instance (cheap, library-editable).
A generic parametric "brick" renders any meta.json without geometry file.

### 2.3 Placement engine

- DIN devices snap to a rail: rail keeps an ordered occupancy list; insert =
  append or drop at offset; auto-shove; fill % = Σ width / rail length.
- Ducts: fill % from wire estimate property (manual at first).
- Plate-mount devices: free XY on plate grid (default 25 mm snap), collision
  check against bounding boxes + clearances.

### 2.4 Rules engine (advisory, never blocking)

Rules emit warnings on the object (report view + a `Warnings` property):
IP ≥ 55 with plain louvres; double doors required (W > 800); duct/rail fill
> 80 %; thermal ΔT > 15 K without active cooling; gland plate absent while
cable entries exist; e-stop cutout below reachable height, etc.

### 2.5 Exports

BOM → FreeCAD Spreadsheet + CSV. Thermal → IEC 60890 sheet. Drawings →
TechDraw page templates (GA, plate layout) with auto-placed views and a
dimension starter set.

### 2.6 Interaction & UX — "one click, not ten"

Working with the panel must feel like handling the real cabinet, not editing
a property sheet. Concretely:

- **Door angle as first-class state:** each door gets an `OpenAngle`
  (0–180°) rendered as a real swing. Toolbar/context toggles set it —
  no property digging.
- **Right-click context menu** on the enclosure (ViewProvider
  `setupContextMenu`): *Open/close front door*, *Open all doors*,
  *Remove/replace side panels*, *Show interior only*.
- **Double-click** opens a task dialog with the everyday controls (size,
  family, doors, IP) laid out in one panel with live preview — the full
  property editor stays for the long tail.
- **View presets** as toolbar buttons: **Closed** (as shipped), **Service**
  (doors open, panels off), **Interior** (shell hidden, plate front and
  center), **Transparent doors** for screenshots.
- Placement tools work by clicking in the 3D view (pick rail, pick position)
  with snap preview — not by typing coordinates.

These land starting in Phase 2 (door state + context menu + presets) and are
an acceptance criterion for every GUI feature after it: *the common action
takes one click; only the rare action opens a dialog.*

### 2.7 Engineering notes

- All geometry in `Part::FeaturePython.execute()`; keep booleans shallow
  (compound of solids, cut only where needed) for recompute speed.
- Property migration: bump `self.Type` version string; `onDocumentRestored`
  adds missing properties so old files keep opening.
- Icons SVG; toolbar grows per phase; unit-test via `freecadcmd` scripts in
  `tests/` (`make_*`, flip properties, assert `Shape.isValid()`).

---

## Part 3 — Phases

### Phase 1 — Scaffold (DONE)
Workbench + parametric Enclosure (WallMount / FloorStanding), doors, locks,
IP enum, plinth, pitch holes, mounting plate slab.

### Phase 2 — Enclosure families & realism (DONE)
- 4-family enum: SmallBox (KX), WallMount (AX), FreeStanding (VX SE),
  Bayed (VX25, `BayCount` + per-bay width).
- Standard-size presets (pick a catalog size, still freely editable).
- Door realism: reveal gap, gasket line, vented/glazed door options gated by
  IP rules; inner door option.
- Gland plate as real cutout + removable plate solids in the floor.
- Rear door vs rear panel; side panel on/off (bayed shared sides).
- UX: `OpenAngle` door swing, right-click menu (open/close doors, show
  interior), view preset buttons, double-click task dialog.
- **Accept:** every family recomputes valid at 3 sizes; IP rule warnings
  fire; opening the front door is a single click.

### Phase 3 — Interior infrastructure (DONE)
- MountingPlate object auto-sized from enclosure; partial plates.
- `Add DIN rail` (TS35×7.5/15) placed on plate; `Add duct` from polyline;
  chassis rails.
- Plate coordinate system + 25 mm snap.
- **Accept:** resize enclosure → plate and rails re-flow; fill props exist.

### Phase 4 — Component library & placement (DONE)
- meta.json schema + generic parametric brick renderer; App::Link insertion.
- Rail snap/shove/occupancy; plate placement with collision + clearances.
- Seed library: ~20 generic devices (MCB 1/3P, contactor S00/S0, PSU, PLC,
  terminal 2.5/4/6 mm², switch, router) — generic first, vendor parts grow.
- **Accept:** populate a 600×800 AX demo panel start-to-finish in GUI.

### Phase 5 — Door devices & cutout engine (DONE)
- Cutout feature bound to a face: Ø22.3, DIN 43700 rects, custom rect/circle
  with radius + stud holes, gland cutouts M12–M63 on gland plates.
- Device visual on the outside, legend plate text property.
- **Accept:** door with e-stop + 4 buttons + HMI cutout, all in BOM.

### Phase 6 — Calculations & BOM (DONE)
- BOM spreadsheet + CSV (roll-up heat/weight).
- IEC 60890 thermal sheet (mounting-arrangement Ae factors, ΔT curve),
  cooling suggestion; rail/duct/plate fill report.
- **Accept:** demo panel report matches hand calc within tolerance.

### Phase 7 — Drawings (DONE)
- TechDraw templates: GA sheet, plate layout sheet with balloons keyed to
  BOM rows.
- **Accept:** two-sheet PDF of the demo panel generated by one command.

### Phase 8 — Power distribution, baying polish, release (DONE except Addon Manager submission)
- Busbar reserved zones + RiLine-style geometry; PE bar object.
- Bayed suites: shared panels, cross-bay plate; weight per bay.
- package.xml finalization, screenshots, submission to the FreeCAD Addon
  Manager registry.

---

## Sources / further reading

- Rittal VX25 / AX-KX / VX SE system documentation (rittal.com)
- IEC 60529 (IP), IEC 62262 (IK), IEC 61439-1/-2, IEC 60890, UL 508A
- EN 60715 (DIN rail), EN 62444 (cable glands), DIN 43700 (panel cutouts)
