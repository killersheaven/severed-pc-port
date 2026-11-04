# Builds an index of every asset inside the PC game's level streams.
# Read-only: it only reads the small asset headers inside DS2DAT*.DAT, never writes to them.
# Run from the Dead Space 2 game folder:
#   powershell -ExecutionPolicy Bypass -File .\index_pc_assets.ps1
# Output: pc_asset_index.csv (then zip it if it is large). Takes a few minutes.

$out = Join-Path $PWD "pc_asset_index.csv"
$sw = New-Object IO.StreamWriter($out, $false, [Text.Encoding]::UTF8)
$sw.WriteLine("dat,entry_offset,entry_size,entry_hash,asset_offset,type_hash,usize,name,ext")

function BE32($b, $o) { return ([uint32]$b[$o] -shl 24) -bor ([uint32]$b[$o+1] -shl 16) -bor ([uint32]$b[$o+2] -shl 8) -bor [uint32]$b[$o+3] }
function LE32($b, $o) { return [BitConverter]::ToUInt32($b, $o) }

$enc = [Text.Encoding]::ASCII
$total = 0
foreach ($datFile in Get-ChildItem -Path $PWD -Filter "DS2DAT*.DAT" | Sort-Object Name) {
    $dat = $datFile.BaseName.Substring(6)
    $fs = [IO.File]::OpenRead($datFile.FullName)
    $br = New-Object IO.BinaryReader($fs)
    try {
        $h = $br.ReadBytes(16)
        if ($enc.GetString($h, 0, 4) -ne "BIGH") { continue }
        $count = BE32 $h 8
        $idx = $br.ReadBytes([int]($count * 12))
        Write-Host ("{0}: {1} entries" -f $datFile.Name, $count)
        for ($i = 0; $i -lt $count; $i++) {
            $eoff = BE32 $idx ($i*12); $esz = BE32 $idx ($i*12+4); $ehash = BE32 $idx ($i*12+8)
            $fs.Position = [int64]$eoff
            $magic = $br.ReadBytes(4)
            if ($magic.Length -lt 4 -or $enc.GetString($magic) -ne "3slo") { continue }
            $pos = [int64]12
            while ($pos + 16 -le $esz) {
                $fs.Position = [int64]$eoff + $pos
                $ch = $br.ReadBytes(16)
                if ($ch.Length -lt 16) { break }
                $tag = $enc.GetString($ch, 0, 4)
                $csz = LE32 $ch 4
                if ($csz -eq 0) { break }
                if ($tag -eq "COHS" -and $enc.GetString($ch, 8, 4) -eq "RDHS" -and $csz -le 4096) {
                    $fs.Position = [int64]$eoff + $pos
                    $raw = $br.ReadBytes([int]$csz)
                    $typeHash = LE32 $raw 20
                    $usize = LE32 $raw 40
                    $strs = $enc.GetString($raw, 44, $raw.Length - 44).Split([char]0)
                    $name = $strs[0]; $ext = ""
                    if ($strs.Length -gt 2) { $ext = $strs[2] }
                    $sw.WriteLine(('{0},{1},{2},{3:x8},{4},{5:x8},{6},"{7}","{8}"' -f $dat, $eoff, $esz, $ehash, $pos, $typeHash, $usize, $name.Replace('"',''), $ext.Replace('"','')))
                    $total++
                }
                $pos += $csz
            }
        }
    } finally { $br.Close(); $fs.Close() }
}
$sw.Close()
Write-Host ("Done: {0} assets indexed in pc_asset_index.csv" -f $total)
