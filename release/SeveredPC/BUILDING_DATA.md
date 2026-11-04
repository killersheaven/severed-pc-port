# Building the Severed data (DS2DAT3.DAT) — current state (v0.2-wip)

> This is the **expert path** as it stands today: several manual steps, Linux (or WSL on Windows), and a few hours of
> conversion. A one-command builder (`build_severed.py`, Windows + Linux) is planned for the next release.

## What you need
| Input | Where it comes from |
|---|---|
| PC Dead Space 2 (current Steam / EA App) | your install |
| PS3 Severed DLC folder `USRDIR\weller1` | your PS3 / RPCS3 install (`dev_hdd0\game\BLUS30624\USRDIR\weller1`), decrypted |
| PS3 Dead Space 2 base game (JB folder with `PS3_GAME\USRDIR\BIGFILE0-2.VIV`, or the decrypted .iso) | your disc; used for reference pairs and shared assets |
| Python 3.10+, gcc | Linux, or **WSL (Ubuntu)** on Windows |
| ~10 GB free space for intermediate files | |

## 1. Prepare (once)
```bash
# Windows users: open WSL (Ubuntu). Your C: drive is /mnt/c, D: is /mnt/d.
mkdir -p ~/mnt
ln -s "/path/to/steamapps/common/Dead Space 2" ~/mnt/"Dead Space 2"     # PC game
ln -s "/path/to/USRDIR/weller1" ~/weller1                                # PS3 Severed
export PS3_BASE="/path/to/Dead Space 2 (PS3 JB folder or .iso)"          # PS3 base game
git clone <this repo> ~/severed && ln -s ~/severed/pipeline ~/port
cd ~/port && gcc -O2 -shared -fPIC -o librefpack.so refpack_c.c          # fast RefPack decoder
```
Index the PC game's assets (PowerShell on Windows, or `pwsh` on Linux), **run inside the game folder**:
```
powershell -ExecutionPolicy Bypass -File <repo>\pipeline\indexers\index_pc_assets.ps1      -> pc_asset_index.csv
powershell -ExecutionPolicy Bypass -File <repo>\pipeline\indexers\index_assets.ps1 -Mode pc -> pc_assets.csv
```

## 2. Convert all streams and write the archive
```bash
cd ~/port
echo "-1,x" > report2.csv; ./runall.sh          # repeat until it prints ALLDONE (resumable)
python3 build_dat.py "$HOME/mnt/Dead Space 2/DS2DAT3.new" 150   # repeat until COMPLETE (resumable)
```
Then rename `DS2DAT3.new` to `DS2DAT3.DAT` in the game folder (keep any older one as a backup).

## 3. Post-build fixes (applied in this order; folding them into the converter is TODO)
| Step | Script | What it fixes |
|---|---|---|
| b19 | `patches/b19/b19_build.py` (+ `patches/b19/fmt_mesh_b19.py` as `fmt_mesh.py`) | mesh re-conversion with the fixed mesh converter |
| b19b | `patches/b19/fixdesc.py --apply` | extra index-buffer descriptors (strip kind) — invisible floors/walls |
| b19c | `patches/b19/fixdesc2.py --apply` | extra index-buffer descriptors (list kind) |
| b20 | `patches/b20/b20_build.py --write` → `patches/b19/repack_dat.py` | meshes in streams b19 never touched |
| b21 | `pipeline/patch_sbk.py` → `pipeline/repack_dat.py SRC DEST` | Severed's own sound banks (1,461) instead of placeholders |

`pipeline/verify_dat.py` checks a repacked archive entry by entry against its sources.
Scripts assume the paths from step 1 (`~/mnt/Dead Space 2`, `~/weller1`, `~/port`); some write `patch_out/` next to
them — point it at a disk with space (`ln -s /big/disk/patch_out patch_out`).

## 4. Streamed audio and video calls
Copy Severed's `audiostreams\` (header-swapped `.exa.snu`) next to `deadspace2.exe` and the two `movies\en\pdlc1_vt_*.vp6`
from `weller1\movies\en` into the game's `movies\en` (keep the PC placeholders as a backup). The converter scripts for
this step are not yet part of the repo — planned for the one-command builder.

## Formats and background
See `docs/` and the docstrings at the top of each `fmt_*.py` (every converter documents its layout and how it was
validated against base-game PS3/PC pairs).
