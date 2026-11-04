# Dead Space 2: Severed PC port - installer for Windows (v0.2-wip)
# Usage:  right-click install-windows.bat -> Run, or
#         powershell -ExecutionPolicy Bypass -File install-windows.ps1 [-GameDir "D:\...\Dead Space 2"] [-Uninstall]
param([string]$GameDir = "", [switch]$Uninstall)
$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path

function Find-GameDir {
    $cands = @()
    foreach ($k in @("HKCU:\Software\Valve\Steam", "HKLM:\SOFTWARE\WOW6432Node\Valve\Steam")) {
        try {
            $p = (Get-ItemProperty -Path $k -ErrorAction Stop)
            $steam = if ($p.SteamPath) { $p.SteamPath } else { $p.InstallPath }
            if ($steam) {
                $steam = $steam -replace '/', '\'
                $cands += Join-Path $steam "steamapps\common\Dead Space 2"
                $vdf = Join-Path $steam "steamapps\libraryfolders.vdf"
                if (Test-Path $vdf) {
                    foreach ($m in [regex]::Matches((Get-Content $vdf -Raw), '"path"\s+"([^"]+)"')) {
                        $cands += Join-Path ($m.Groups[1].Value -replace '\\\\', '\') "steamapps\common\Dead Space 2"
                    }
                }
            }
        } catch {}
    }
    $cands += "C:\Program Files\EA Games\Dead Space 2", "C:\Program Files (x86)\EA Games\Dead Space 2",
              "C:\Program Files (x86)\Origin Games\Dead Space 2"
    foreach ($c in $cands) { if (Test-Path (Join-Path $c "deadspace2.exe")) { return $c } }
    return ""
}

if (-not $GameDir) { $GameDir = Find-GameDir }
if (-not $GameDir -or -not (Test-Path (Join-Path $GameDir "deadspace2.exe"))) {
    Write-Host "Could not find Dead Space 2 automatically."
    $GameDir = Read-Host "Paste the Dead Space 2 game folder (the one with deadspace2.exe)"
    $GameDir = $GameDir.Trim('"')
}
if (-not (Test-Path (Join-Path $GameDir "deadspace2.exe"))) { Write-Host "deadspace2.exe not found in '$GameDir'. Nothing changed." -ForegroundColor Red; exit 1 }
Write-Host "Game folder: $GameDir"
$Plugins = Join-Path $GameDir "plugins"
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"

if ($Uninstall) {
    $bak = Join-Path $Plugins "SeveredLoader.removed-$Stamp"
    New-Item -ItemType Directory -Force -Path $bak | Out-Null
    foreach ($f in @("SeveredLoader.asi", "SeveredLoader.ini")) {
        $p = Join-Path $Plugins $f; if (Test-Path $p) { Move-Item $p $bak }
    }
    Write-Host "Plugin removed (moved to $bak)." -ForegroundColor Green
    Write-Host "Severed data, if you built it, is DS2DAT3.DAT in the game folder: delete it yourself to remove Severed completely."
    exit 0
}

# MarkerPatch provides the plugin loader (dinput8.dll + plugins folder)
if (-not (Test-Path (Join-Path $GameDir "dinput8.dll"))) {
    Write-Host "WARNING: MarkerPatch (dinput8.dll) is not installed in the game folder." -ForegroundColor Yellow
    Write-Host "         The Severed plugin is loaded by MarkerPatch. Install MarkerPatch first, then run this again." -ForegroundColor Yellow
}

New-Item -ItemType Directory -Force -Path $Plugins | Out-Null
$existing = @("SeveredLoader.asi", "SeveredLoader.ini") | Where-Object { Test-Path (Join-Path $Plugins $_) }
if ($existing) {
    $bak = Join-Path $Plugins "SeveredLoader.backup-$Stamp"
    New-Item -ItemType Directory -Force -Path $bak | Out-Null
    foreach ($f in $existing) { Copy-Item (Join-Path $Plugins $f) $bak }
    Write-Host "Previous plugin files backed up to $bak"
}
Copy-Item (Join-Path $Here "plugins\SeveredLoader.asi") $Plugins -Force
Copy-Item (Join-Path $Here "plugins\SeveredLoader.ini") $Plugins -Force

# Severed data check: DS2DAT3.DAT is built from your own PS3 copy of Severed (see BUILDING_DATA.md)
$dat = Join-Path $GameDir "DS2DAT3.DAT"
$ini = Join-Path $Plugins "SeveredLoader.ini"
if ((Test-Path $dat) -and ((Get-Item $dat).Length -gt 1GB)) {
    Write-Host "Severed data found (DS2DAT3.DAT). 'Dead Space 2: Severed' will appear in the episode list." -ForegroundColor Green
} else {
    (Get-Content $ini) -replace '^AddEpisode=1', 'AddEpisode=0' | Set-Content $ini
    Write-Host "No Severed data yet (DS2DAT3.DAT missing). The plugin is installed but the Severed episode is hidden" -ForegroundColor Yellow
    Write-Host "until you build the data (BUILDING_DATA.md), then set AddEpisode=1 in plugins\SeveredLoader.ini." -ForegroundColor Yellow
}
Write-Host "Done. Start the game normally. New Game -> pick 'Dead Space 2: Severed'." -ForegroundColor Green
Write-Host "Log: plugins\SeveredLoader.log (attach it when reporting a problem)."
