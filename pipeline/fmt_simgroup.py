"""SimGroup (type hash 0xCCB51828 in the file header) PS3 big-endian -> PC little-endian.
Layout (offsets from file start unless noted):
 0x00 header 0x3C: u32s, except 0x14 (u16 nHashes, u16 nRecords) and 0x18 (u16 nLayouts, u16).
 0x3C nHashes x u32 entry hashes; then nRecords x 68-byte records, transforms, layout ptr table, layouts: all u32.
 hdr[1]+8 = S (section 2): u32 hash, u32 size, u32 pairsOff, u16 nPairs, u16, u32 entOff, u32 nEnt, u32 propOff, u32 nProp
   pairs: (u32,u32); entries: {u32 hash, u16, u16 count, u32 indexOff}; props 12 B {u32 hash, u16 enum, u8 type, u8 idx, u32 value};
   index array u16; then the pool (strings + blobs). Prop values of blob types are self-relative pointers (from the value field).
Entry hashes are content hashes over raw (native-endian) blob bytes, so they change between platforms when an entry
holds a blob; HASHMAP (PS3 -> PC, learned from base-game pairs) is applied when known, else the PS3 value is kept."""
import struct, os, json
from idmap_util import IDMAP
BLOB = {12: 16, 13: 12, 14: 16, 15: 64}   # GUID, vec3, vec4, matrix4: all u32 words
HASHMAP = {}
_mp = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'simgroup_hashmap.json')
if os.path.exists(_mp):
    HASHMAP = {int(k, 16): int(v, 16) for k, v in json.load(open(_mp)).items()}

GUIDMAP = {}
_gp = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'simgroup_guidmap.json')
if os.path.exists(_gp):
    GUIDMAP = {bytes.fromhex(k): bytes.fromhex(v) for k, v in json.load(open(_gp)).items()}

def guid_blobs(d):
    """offsets of non-null type-12 (GUID) blobs"""
    U = lambda o: struct.unpack_from('>I', d, o)[0]
    S = (U(4) + 15) & ~15; prop, nprop = S + U(S + 24), U(S + 28)
    r = []
    for j in range(nprop):
        o = prop + 12 * j
        if d[o + 6] == 12 and U(o + 8): r.append((o + 8 + U(o + 8)) & 0xffffffff)
    return r

GUIDMAP_OK = {k: v for k, v in GUIDMAP.items() if v[:4] == v[4:8] == v[8:12]}   # 1,279 of 2,088 learned entries were misaligned garbage
_g2 = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'simgroup_guidmap_v2.json')
if os.path.exists(_g2): GUIDMAP_OK.update({bytes.fromhex(k): bytes.fromhex(v) for k, v in json.load(open(_g2)).items()})
HASHMAP_OK = {k: v for k, v in HASHMAP.items() if v >= 0x100000}   # old table: small values were mis-learned (offsets)
_h2 = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'simgroup_hashmap_v2.json')   # relearn_sg.py: same-size pairs, unanimous
if os.path.exists(_h2): HASHMAP_OK.update({int(k, 16): int(v, 16) for k, v in json.load(open(_h2)).items()})
def convert(d, hashmap=None, guidmap=None):
    hm = HASHMAP_OK if hashmap is None else hashmap
    gm = GUIDMAP_OK if guidmap is None else guidmap
    out = bytearray(d)
    def w(o): out[o:o + 4] = d[o:o + 4][::-1]
    def h(o): out[o:o + 2] = d[o:o + 2][::-1]
    def hh(o): h(o); h(o + 2)
    def wh(o):   # u32 hash, mapped
        v = struct.unpack_from('>I', d, o)[0]
        struct.pack_into('<I', out, o, hm.get(v, v))
    U = lambda o: struct.unpack_from('>I', d, o)[0]
    nh = struct.unpack_from('>H', d, 0x14)[0]
    S = (U(4) + 15) & ~15
    for o in range(0, 0x3C, 4): w(o)
    hh(0x14); hh(0x18)
    for i in range(nh): wh(0x3C + 4 * i)
    for o in range(0x3C + 4 * nh, S, 4): w(o)
    # layout hashes (layout table) may also be platform-specific: map them
    nl = struct.unpack_from('>H', d, 0x18)[0]; lt = U(0x10)
    for i in range(nl if lt else 0): wh(U(lt + 4 * i))
    # section 2
    w(S); w(S + 4); w(S + 8); hh(S + 12)
    for k in range(4): w(S + 16 + 4 * k)
    pairs, npairs = S + U(S + 8), struct.unpack_from('>H', d, S + 12)[0]
    ent, nent, prop, nprop = S + U(S + 16), U(S + 20), S + U(S + 24), U(S + 28)
    for o in range(pairs, pairs + 8 * npairs, 4): w(o)
    idx_lo, idx_hi = None, 0
    for i in range(nent):
        o = ent + 12 * i
        wh(o); h(o + 4); h(o + 6); w(o + 8)
        n, off = struct.unpack_from('>HI', d, o + 6)
        if n:
            idx_lo = S + off if idx_lo is None else min(idx_lo, S + off)
            idx_hi = max(idx_hi, S + off + 2 * n)
    for j in range(nprop):
        o = prop + 12 * j
        w(o); h(o + 4)
        t = d[o + 6]
        if t == 7 or (t == 5 and d[o + 9:o + 12] == b'\0\0\0'):
            pass            # bool / byte-sized enum: stored as a leading byte on both platforms
        else:
            w(o + 8)
        if t in BLOB and U(o + 8):
            x = (o + 8 + U(o + 8)) & 0xffffffff
            if t == 12 and d[x:x + 16] in gm:
                out[x:x + 16] = gm[d[x:x + 16]]
            else:
                for k in range(x, x + BLOB[t], 4): w(k)
                if t == 12:     # asset reference (h,h,h,k): remap IDs of assets replaced by PC versions
                    for k in range(x, x + 16, 4):
                        v = struct.unpack_from('<I', out, k)[0]
                        if v in IDMAP: struct.pack_into('<I', out, k, IDMAP[v])
    if idx_lo is not None:
        for o in range(idx_lo, idx_hi, 2): h(o)
    return bytes(out)
