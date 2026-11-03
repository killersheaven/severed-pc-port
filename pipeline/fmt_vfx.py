"""VFX (.vfb) PS3 -> PC.  u32 words, except '#'-padded name fields (bytes as is) and u16 pairs / byte runs at
positions learned from all 2,504 base-game pairs (vfx_rules.json via learnvfx.py), keyed on the last '####xxxx'
marker + distance + value shape. Unknown positions: printable non-palindromic words stay bytes, others u32."""
import json, os
from vfxcommon import anchors, names, shape
_r = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vfx_rules.json')
R = json.load(open(_r)) if os.path.exists(_r) else {}
def convert(d):
    n = len(d) & ~3
    out = bytearray(d)
    A = anchors(d); Sx = names(d); last = ('start', 0)
    for o in range(0, n, 4):
        for k in range(o - 3, o + 1):
            if k in A: last = (A[k], k)
        if o in Sx: continue
        p = d[o:o + 4]; key = '%s+%d' % (last[0], o - last[1])
        c = R.get(key + '|' + shape(p)) or R.get(key)
        if c is None:
            c = 'S' if all(97 <= x < 123 or x in (0, 95) for x in p) and sum(97 <= x < 123 for x in p) >= 2 else 'W'
        if c == 'W': out[o:o + 4] = p[::-1]
        elif c == 'H': out[o:o + 2] = p[1::-1]; out[o + 2:o + 4] = p[:1:-1]
    return bytes(out)
