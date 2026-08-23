# PanelWB — Control Panel Enclosure Workbench for FreeCAD

Parametric design of electrical control panel enclosures, modeled around the
Rittal system:

- **Wall-mount** (AX style): mono-body sheet box, front door, mounting plate
- **Floor-standing** (VX25 style): skeleton frame of 45 mm profile sections
  with 25 mm pitch pre-holes, plinth (100/200 mm), bolt-on panels

## Enclosure parameters

| Parameter | Options |
|---|---|
| MountingType | WallMount / FloorStanding |
| Width / Height / Depth | free (Height excludes plinth) |
| DoorConfig | FrontOnly / FrontAndBack / DoubleFront / DoubleFrontAndBack — double is forced above 800 mm width |
| DoorSwing | HingeLeft / HingeRight |
| IPRating | IP42 / IP54 / IP55 / IP65 / IP66 |
| LockType | quarter-turn double-bit 3/5 mm, wing handle, swing handle w/ key barrel, padlockable |
| MountingPlate | on/off + rear setback |
| GlandPlate | None / Top / Bottom / Both |
| Plinth | None / 100 mm / 200 mm (floor-standing only) |
| SkeletonPitch / ShowPitchHoles | frame pre-hole grid (floor-standing only) |

## Install

Symlink (or copy) this folder into your FreeCAD `Mod` directory:

```
ln -s /path/to/PanelWB ~/.local/share/FreeCAD/v1-1/Mod/PanelWB
```

Restart FreeCAD and select the **Panel** workbench.

## Roadmap

- [ ] DIN rail (TS35) and cable duct placement on the mounting plate
- [ ] Device cutout tool (Ø22 push buttons, HMIs, cable glands) with IP-aware rules
- [ ] Component library (MCBs, contactors, PSUs, PLCs, terminal blocks)
- [ ] BOM / rail-fill / duct-fill export
- [ ] Heat dissipation estimate
- [ ] TechDraw fabrication drawing generation

## License

LGPL-2.1-or-later
