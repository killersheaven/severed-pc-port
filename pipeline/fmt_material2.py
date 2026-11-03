"""Material (.mtlb) PS3 -> PC with the PC-only technique entry (2026-10-16).
PS3 materials repeat one technique in all 3 slots; PC replaces slot 1 for some techniques (e.g. 3e8bbbf9/8890d2c1 ->
0e155d33/2e222315) and appends copies of the params that technique uses (same hash/type/strings, new value offset,
value copied). Table learned from base-game pairs (mat_rules.json: PS3 slot-1 entry hex -> [PC entry hex, [param hashes]]).
Also rewrites the embedded build path ps3\\ntsc_en_es_fr -> win\\ntsc_en_fr (string offsets shifted)."""
import os, json, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fmt_material
_R = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mat_rules.json')
RULES = json.load(open(_R)) if os.path.exists(_R) else {}
PATHS = [(b'\\build\\ps3\\ntsc_en_es_fr\\', b'\\build\\win\\ntsc_en_fr\\')]
def convert(d, rules=None):
    rules = RULES if rules is None else rules
    base = fmt_material.convert(d)                          # PS3 layout, little-endian
    u16 = lambda o: struct.unpack_from('<H', base, o)[0]
    n, po, ps, vo, vs, so, ss = u16(0x56), u16(0x58), u16(0x5A), u16(0x5C), u16(0x5E), u16(0x60), u16(0x62)
    hdr = bytearray(base[:po]); params = [bytearray(base[po + 12 * i:po + 12 * i + 12]) for i in range(n)]
    gap = base[po + ps:vo]; vals = bytearray(base[vo:vo + vs]); strs = base[so:so + ss]; tail = base[so + ss:]
    key = d[0x34:0x44].hex()                               # PS3 slot-1 entry (big-endian bytes)
    r = rules.get(key)
    if r:
        hdr[0x34:0x44] = bytes.fromhex(r[0])
        want = set(r[1])
        for p in list(params):
            h = struct.unpack_from('<I', p, 0)[0]
            if h in want:
                q = bytearray(p); voff = struct.unpack_from('<H', p, 6)[0]
                struct.pack_into('<H', q, 6, len(vals)); vals += vals[voff:voff + 4]; params.append(q)
    for old, new in PATHS:                                  # build path string
        i = strs.find(old)
        if i >= 0:
            strs = strs[:i] + new + strs[i + len(old):]; delta = len(new) - len(old)
            for p in params:
                for f in (8, 10):
                    x = struct.unpack_from('<H', p, f)[0]
                    if x > i: struct.pack_into('<H', p, f, x + delta)
    n2 = len(params); ps2 = 12 * n2
    vo2 = (po + ps2 + 15) & ~15; so2 = vo2 + len(vals)
    struct.pack_into('<H', hdr, 0x56, n2); struct.pack_into('<HHHHH', hdr, 0x5A, ps2, vo2, len(vals), so2, len(strs))
    return bytes(hdr) + b''.join(params) + b'\0' * (vo2 - po - ps2) + bytes(vals) + strs + tail
