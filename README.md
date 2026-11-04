# Dead Space 2: Severed — PC port (early, private, v0.1)

> ⚠️ **HIGHLY WORK IN PROGRESS.** Expect crashes, missing effects, placeholder VFX and debug logging. Not ready for play-throughs or sharing.

Work-in-progress port of the console-exclusive **Severed** DLC (Gabe Weller, 2 chapters) to the PC version of
Dead Space 2 (current Steam / EA App build, exe dated Feb 24 2011).

**This repository contains no game data.** It holds the converter pipeline that turns the PS3 Severed package
into PC format, the in-place patch scripts used since build 19, and the `SeveredLoader.asi` plugin. You need your
own copies of: PS3 Severed (`USRDIR\weller1`, e.g. from RPCS3), the PS3 base game (for reference pairs), and the PC game.

## Quick start (v0.2-wip)
1. Install **MarkerPatch** in your Dead Space 2 folder.
2. Download `SeveredPC-v0.2-wip.zip` from Releases (or use `release/SeveredPC/` in this repo).
3. **Windows:** double-click `install-windows.bat`. **Linux (Proton):** `./install-linux.sh`, then set the launch option
   `WINEDLLOVERRIDES="dinput8=n,b" %command%`.
4. Build the Severed data from your own PS3 copy once: [`docs/BUILDING_DATA.md`](docs/BUILDING_DATA.md)
   (expert path today; a one-command builder is next).
5. New Game → **Dead Space 2: Severed**.

Details: [`release/SeveredPC/README-INSTALL.md`](release/SeveredPC/README-INSTALL.md).

## Status (2026-11-04, v0.2-wip: build 21 + plugin stage 17)
| Area | State |
|---|---|
| Severed in the episode/DLC menu ("Dead Space 2: Severed") | works (plugin) |
| New Game | confirmed 2026-11-04 (Severed episode → native StartLevel index 1, `initial` checkpoint). Follows the episode picked in the menu: main campaign → main game, Severed → Severed from its very start (`initial`, with intro) (`Trigger=menu`) |
| Continue / Load of a Severed save | routed to Severed when the save's checkpoint is one of Severed's 25 (`SaveRouting=1`); reported working by the tester, not yet confirmed in a log |
| Respawn after death | works |
| Level geometry, collision, characters, animation | converted; plays through drill tunnels, bomb run, quarry, elevator |
| Quarry door crash | fixed by the plugin's D3D argument guard (engine passes SetTexture stage 417); data source not yet fixed |
| Sound banks (SBK) | converted (1,461 banks; Gabe's voice/foley/ambience) |
| Streamed audio, video calls | converted |
| VFX | mostly placeholders (converter exists, disabled after a crash) |
| Open | tg4h v2 textures (9), menu icons (2), ANIM (1), proper Continue/Load routing, lean release plugin, Windows installer |

## Layout
- `plugin/` — `SeveredLoader.asi` source (loaded by MarkerPatch from `<game>\plugins\`), all diagnostic stages up to 16,
  offline build kit (`build_shim/`), sample ini.
- `pipeline/` — PS3 → PC converters (`fmt_*.py`), stream converter `port_str.py`, batch `port_all.py`/`runall.sh`,
  DAT writer `build_dat.py`, reference-pair tools (`dumppairs.py`, `validate.py`, `ps3base.py`), learned rule tables
  (`*_rules.json`, SimGroup maps, ID maps). `fmt_sbk.py` + `patch_sbk.py` = sound banks.
- `patches/` — in-place DAT fixes applied after the last full build (b19 mesh/IB descriptor fixes, `repack_dat.py`), SBK report.
- `docs/` — latest handoff notes (formats, crash analyses, addresses), `BUILDING_DATA.md`.
- `release/SeveredPC/` — the install package: prebuilt plugin, ini, Windows/Linux install + uninstall scripts.
- `pipeline/indexers/` — PowerShell indexers that list the PC game's assets (needed by the pipeline).

## Building the plugin (Linux, no Windows SDK needed)
```
cd plugin
for l in kernel32 user32 ucrtbase; do llvm-dlltool -m i386 -k -d build_shim/$l.def -l lib$l.a; done
clang++ -target i686-w64-windows-gnu -O2 -std=c++17 -fno-exceptions -fno-rtti -fno-asynchronous-unwind-tables -fno-unwind-tables \
        -nostdinc -isystem $(clang -print-resource-dir)/include -isystem build_shim -c SeveredLoader.cpp -o sl.o
ld.lld -m i386pe --shared -e _DllMain@12 --image-base=0x10000000 --dynamicbase --nxcompat -s --subsystem windows \
       -o SeveredLoader.asi sl.o libkernel32.a libuser32.a libucrtbase.a
```
Requires MarkerPatch (`dinput8.dll`, `EnableSeveredDLC = 1`). Copy `SeveredLoader.asi` + `SeveredLoader.ini` (from `SeveredLoader.ini.sample`) to `<game>\plugins\`.
Key ini settings: `[Launch] Trigger=menu`, `Checkpoint=` (Severed episode start point), `SaveRouting=1`; `[Debug] StaleGuard`, `LockGuard` (diagnostics; `LockGuard=0` removes most stutter).

## Building the data (current workflow, Linux VM)
1. `port_all.py` / `runall.sh` converts each PS3 Severed stream (`weller1\**\*.str`) to PC (`out/`), using base-game PS3/PC
   pairs and learned rules; `build_dat.py` writes `DS2DAT3.DAT` (165 entries: 163 streams + 2 TOCs). The game mounts any
   `DS2DAT0..12.DAT` automatically.
2. Apply the post-build patches (`patches/b19/fixdesc*.py`, b20 mesh fixes, `pipeline/patch_sbk.py`) and repack with
   `repack_dat.py`. Folding these into `port_str.py` for a clean one-shot build is still TODO.

Key facts: DAT = BIGH archive, entries keyed by x65599 of the path; `.str` = `ols3` chunk stream (PS3 BE + RefPack,
PC LE uncompressed); textures copy as is (PS3 DXT already PC order); audio is EALayer3 on both platforms.

## Legal
Fan project for personal use. No game files are included or distributed. Dead Space 2 and Severed are © Electronic Arts.
