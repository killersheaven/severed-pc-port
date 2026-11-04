# Lists every asset (name, type, ID, size) in either:
#   - the PC game's DS2DAT*.DAT files:   -Mode pc   (run in the Dead Space 2 game folder)
#   - a folder of console .str files:    -Mode ps3  -Folder "<path to ...\USRDIR\weller1>"
# Read-only: only reads small asset headers.
#   powershell -ExecutionPolicy Bypass -File .\index_assets.ps1 -Mode pc
#   powershell -ExecutionPolicy Bypass -File .\index_assets.ps1 -Mode ps3 -Folder "C:\...\USRDIR\weller1"
# Output: pc_assets.csv or ps3_assets.csv in the current folder.
param([Parameter(Mandatory=$true)][ValidateSet('pc','ps3')][string]$Mode, [string]$Folder = "")

$enc = [Text.Encoding]::ASCII
function U32([byte[]]$b, [int]$o, [bool]$be) {
    if ($be) { return ([uint32]$b[$o] -shl 24) -bor ([uint32]$b[$o+1] -shl 16) -bor ([uint32]$b[$o+2] -shl 8) -bor [uint32]$b[$o+3] }
    return [BitConverter]::ToUInt32($b, $o)
}

$outName = if ($Mode -eq 'pc') { "pc_assets.csv" } else { "ps3_assets.csv" }
$sw = New-Object IO.StreamWriter((Join-Path $PWD $outName), $false, [Text.Encoding]::UTF8)
$sw.WriteLine("source,entry_offset,asset_offset,type_hash,id1,id2,id3,id4,usize,name,ext")
$script:total = 0

# Walks one ols3 stream that starts at $base inside $fs, $size bytes long.
function Walk($fs, $br, [int64]$base, [int64]$size, [string]$source, [bool]$be) {
    $pos = [int64]12
    while ($pos + 16 -le $size) {
        $fs.Position = $base + $pos
        $ch = $br.ReadBytes(16)
        if ($ch.Length -lt 16) { break }
        $tag = $enc.GetString($ch, 0, 4); $sub = $enc.GetString($ch, 8, 4)
        $csz = U32 $ch 4 $be
        if ($csz -eq 0) { break }
        $isHdr = ($be -and $tag -eq "SHOC" -and $sub -eq "SHDR") -or ((-not $be) -and $tag -eq "COHS" -and $sub -eq "RDHS")
        if ($isHdr -and $csz -le 4096) {
            $fs.Position = $base + $pos
            $raw = $br.ReadBytes([int]$csz)
            $t = U32 $raw 20 $be; $i1 = U32 $raw 24 $be; $i2 = U32 $raw 28 $be; $i3 = U32 $raw 32 $be; $i4 = U32 $raw 36 $be
            $us = U32 $raw 40 $be
            $strs = $enc.GetString($raw, 44, $raw.Length - 44).Split([char]0)
            $name = $strs[0]; $ext = ""; if ($strs.Length -gt 2) { $ext = $strs[2] }
            $sw.WriteLine(('"{0}",{1},{2},{3:x8},{4:x8},{5:x8},{6:x8},{7:x8},{8},"{9}","{10}"' -f $source, $base, $pos, $t, $i1, $i2, $i3, $i4, $us, $name.Replace('"',''), $ext.Replace('"','')))
            $script:total++
        }
        $pos += $csz
    }
}

if ($Mode -eq 'pc') {
    foreach ($datFile in Get-ChildItem -Path $PWD -Filter "DS2DAT*.DAT" | Sort-Object Name) {
        $fs = [IO.File]::OpenRead($datFile.FullName); $br = New-Object IO.BinaryReader($fs)
        try {
            $h = $br.ReadBytes(16)
            if ($enc.GetString($h, 0, 4) -ne "BIGH") { continue }
            $count = U32 $h 8 $true
            $idx = $br.ReadBytes([int]($count * 12))
            Write-Host ("{0}: {1} entries" -f $datFile.Name, $count)
            for ($i = 0; $i -lt $count; $i++) {
                $eoff = U32 $idx ($i*12) $true; $esz = U32 $idx ($i*12+4) $true
                $fs.Position = [int64]$eoff
                $m = $br.ReadBytes(4)
                if ($m.Length -eq 4 -and $enc.GetString($m) -eq "3slo") { Walk $fs $br ([int64]$eoff) ([int64]$esz) $datFile.BaseName $false }
            }
        } finally { $br.Close(); $fs.Close() }
    }
} else {
    if (-not (Test-Path $Folder)) { Write-Host "Folder not found: $Folder"; exit 1 }
    $files = Get-ChildItem -Path $Folder -Recurse -Filter "*.str"
    Write-Host ("{0} .str files" -f $files.Count)
    foreach ($f in $files) {
        $fs = [IO.File]::OpenRead($f.FullName); $br = New-Object IO.BinaryReader($fs)
        try {
            $m = $br.ReadBytes(4)
            if ($m.Length -eq 4 -and $enc.GetString($m) -eq "ols3") {
                $rel = $f.FullName.Substring($Folder.TrimEnd('\').Length + 1)
                Walk $fs $br ([int64]0) ([int64]$f.Length) $rel $true
            }
        } finally { $br.Close(); $fs.Close() }
    }
}
$sw.Close()
Write-Host ("Done: {0} assets in {1}" -f $script:total, $outName)
