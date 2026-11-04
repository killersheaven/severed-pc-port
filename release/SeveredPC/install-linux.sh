#!/usr/bin/env bash
# Dead Space 2: Severed PC port - installer for Linux (Steam / Proton) (v0.2-wip)
# Usage:  ./install-linux.sh [--game-dir "/path/to/Dead Space 2"] [--uninstall]
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GAME=""; UNINSTALL=0
while [ $# -gt 0 ]; do
  case "$1" in
    --game-dir) GAME="$2"; shift 2 ;;
    --uninstall) UNINSTALL=1; shift ;;
    -h|--help) sed -n '2,3p' "$0"; exit 0 ;;
    *) GAME="$1"; shift ;;
  esac
done

find_game() {
  local roots=("$HOME/.steam/steam" "$HOME/.local/share/Steam" "$HOME/.var/app/com.valvesoftware.Steam/.local/share/Steam")
  local libs=()
  for r in "${roots[@]}"; do
    [ -d "$r" ] || continue
    libs+=("$r")
    local vdf="$r/steamapps/libraryfolders.vdf"
    if [ -f "$vdf" ]; then
      while IFS= read -r p; do libs+=("$p"); done < <(grep -oP '"path"\s+"\K[^"]+' "$vdf" || true)
    fi
  done
  for l in "${libs[@]}"; do
    local d="$l/steamapps/common/Dead Space 2"
    if [ -f "$d/deadspace2.exe" ]; then echo "$d"; return 0; fi
  done
  return 1
}

if [ -z "$GAME" ]; then GAME="$(find_game || true)"; fi
if [ -z "$GAME" ] || [ ! -f "$GAME/deadspace2.exe" ]; then
  read -r -p "Dead Space 2 game folder (the one with deadspace2.exe): " GAME
fi
if [ ! -f "$GAME/deadspace2.exe" ]; then echo "deadspace2.exe not found in '$GAME'. Nothing changed." >&2; exit 1; fi
echo "Game folder: $GAME"
PLUG="$GAME/plugins"; STAMP="$(date +%Y%m%d-%H%M%S)"

if [ "$UNINSTALL" = 1 ]; then
  BAK="$PLUG/SeveredLoader.removed-$STAMP"; mkdir -p "$BAK"
  for f in SeveredLoader.asi SeveredLoader.ini; do [ -f "$PLUG/$f" ] && mv "$PLUG/$f" "$BAK/"; done
  echo "Plugin removed (moved to $BAK)."
  echo "Severed data, if you built it, is DS2DAT3.DAT in the game folder: delete it yourself to remove Severed completely."
  exit 0
fi

if [ ! -f "$GAME/dinput8.dll" ]; then
  echo "WARNING: MarkerPatch (dinput8.dll) is not installed in the game folder."
  echo "         The Severed plugin is loaded by MarkerPatch. Install MarkerPatch first, then run this again."
fi

mkdir -p "$PLUG"
if [ -f "$PLUG/SeveredLoader.asi" ] || [ -f "$PLUG/SeveredLoader.ini" ]; then
  BAK="$PLUG/SeveredLoader.backup-$STAMP"; mkdir -p "$BAK"
  for f in SeveredLoader.asi SeveredLoader.ini; do [ -f "$PLUG/$f" ] && cp "$PLUG/$f" "$BAK/"; done
  echo "Previous plugin files backed up to $BAK"
fi
cp "$HERE/plugins/SeveredLoader.asi" "$HERE/plugins/SeveredLoader.ini" "$PLUG/"

DAT="$GAME/DS2DAT3.DAT"
if [ -f "$DAT" ] && [ "$(stat -c%s "$DAT")" -gt 1073741824 ]; then
  echo "Severed data found (DS2DAT3.DAT). 'Dead Space 2: Severed' will appear in the episode list."
else
  sed -i 's/^AddEpisode=1/AddEpisode=0/' "$PLUG/SeveredLoader.ini"
  echo "No Severed data yet (DS2DAT3.DAT missing). The plugin is installed but the Severed episode is hidden"
  echo "until you build the data (BUILDING_DATA.md), then set AddEpisode=1 in plugins/SeveredLoader.ini."
fi
echo
echo "Done. IMPORTANT for Proton: set the game's Steam launch options to"
echo '    WINEDLLOVERRIDES="dinput8=n,b" %command%'
echo "so MarkerPatch (and with it this plugin) is loaded. Then New Game -> pick 'Dead Space 2: Severed'."
echo "Log: plugins/SeveredLoader.log (attach it when reporting a problem)."
