# Dead Space 2: Severed (PC port) — v0.2-wip install guide

> ⚠️ **Highly work in progress.** Expect crashes, placeholder effects and a large debug log. Back up your saves.

This package installs the **SeveredLoader plugin**: it adds "Dead Space 2: Severed" to the episode list, handles
New Game / Continue for Severed and works around known crashes. **The Severed level data is not included** (it can't be
shared): you build it once from your own PS3 copy of Severed, see `BUILDING_DATA.md`. Without the data the plugin
installs with the Severed episode hidden.

## Requirements
- Dead Space 2 for PC, current Steam / EA App version.
- **MarkerPatch** installed in the game folder (it provides `dinput8.dll`, which loads plugins from `plugins\`).
  Optional: `EnableSeveredDLC = 1` in `MarkerPatch.ini` makes Severed's Patrol Suit and Seeker Rifle appear in the shop.
- For the Severed episode: `DS2DAT3.DAT` built from your own PS3 Severed (see `BUILDING_DATA.md`).

## Install — Windows
1. Unzip this folder anywhere.
2. Double-click **`install-windows.bat`**. It finds the game (Steam or EA App) or asks for the folder
   (the one with `deadspace2.exe`), backs up any previous plugin files and copies the new ones into `plugins\`.
   Command line: `powershell -ExecutionPolicy Bypass -File install-windows.ps1 -GameDir "D:\...\Dead Space 2"`
3. Start the game normally → **New Game** → pick **Dead Space 2: Severed**.

## Install — Linux (Steam + Proton)
1. Unzip, then `./install-linux.sh` (or `./install-linux.sh --game-dir "/path/to/Dead Space 2"`).
2. In Steam → Dead Space 2 → Properties → Launch options:
   `WINEDLLOVERRIDES="dinput8=n,b" %command%`
3. Start the game → **New Game** → pick **Dead Space 2: Severed**.

## Uninstall
`uninstall-windows.bat` / `./uninstall-linux.sh`: moves the plugin files to `plugins\SeveredLoader.removed-<date>`.
To remove Severed completely, also delete `DS2DAT3.DAT` from the game folder.

## Settings (`plugins\SeveredLoader.ini`)
| Key | Default | Meaning |
|---|---|---|
| `[Launch] Trigger` | `menu` | New Game follows the episode you pick |
| `[Launch] Checkpoint` | `XONTREALPR_CB22182_E50854D_v3` | Severed starts at the very beginning (intro). `XMARINELLO_CB806AB_62AC82F_v3` skips the intro |
| `[Launch] SaveRouting` | `1` | Continue/Load of a Severed save goes to Severed |
| `[Menu] AddEpisode` | `1` | Show Severed in the episode list (installers set 0 when no data is found) |
| `[Debug] StaleGuard` | `1` | Safety net for released graphics objects (keep on) |
| `[Debug] LockGuard` | `0` | Diagnostics only; `1` causes stutter |

## Known issues
- Many visual effects are placeholders (grey grid / missing effects).
- A few textures (9) and two menu icons are not converted yet.
- Continue/Load routing for Severed saves is new; if Continue starts Isaac's chapter 1, send `plugins\SeveredLoader.log`.
- The plugin writes a detailed log (`plugins\SeveredLoader.log`, can grow to several MB).

## Reporting problems
Open an issue with what you did, where it happened, and `plugins\SeveredLoader.log`.
