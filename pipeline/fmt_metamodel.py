"""MetaModel (.mm, 'MMdl') PS3 -> PC.  u32 words except u16 pairs; strings as is; asset IDs remapped (idmap_util).
u16-pair positions: header 0x58..0x64, plus positions learned from all 2,767 base-game pairs, keyed by the nearest preceding
part-type hash (x65599 of a lower-case name in the file's own string table, or the tags UMTR/IN01/APMM) and the distance to it
(mm_hrules.json). Where the learned table is ambiguous, a word whose two halves are both small numbers with a non-zero high half
is treated as a u16 pair."""
import struct, re, json, os
from idmap_util import remap_words_le
from bigh import x65599
_r = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mm_rules.json')
RULES = json.load(open(_r)) if os.path.exists(_r) else {}     # 'anchor+delta' -> 'H' (u16 pair) or 'S' (bytes as is)
def string_range(d):
    se = struct.unpack_from('>I', d, 0x50)[0]
    if not (0 < se <= len(d)): return (len(d), len(d))
    o = se
    while o > 0x68 and (32 <= d[o - 1] < 127 or d[o - 1] == 0): o -= 1
    o = (o + 3) & ~3
    while o < se and d[o:o + 2] == b'\0\0': o += 4      # pointers/zero words just before the strings
    return (o, se)
def shape(p):
    hi, lo = int.from_bytes(p[:2], 'big'), int.from_bytes(p[2:], 'big')
    if p[1:] == b'\0\0\0': return 'b'
    if lo == 0: return 'l0'
    if hi == 0: return 'h0'
    if hi < 0x1000 and lo < 0x1000: return 'bs'
    return 'o'
_GLOBAL = {}
for _k in RULES:
    _n = _k.split('+', 1)[0]
    if _n and not _n.startswith('sec') and _n not in ('UMTR', 'IN01', 'APMM'):
        _GLOBAL[struct.pack('>I', x65599(_n))] = _n
def anchors_of(d):
    A = dict(_GLOBAL)
    for s in set(re.findall(rb'[A-Za-z_][A-Za-z0-9_]{1,60}', d)):
        A[struct.pack('>I', x65599(s.lower().decode('latin1')))] = s.lower().decode('latin1')
    for tag in (b'UMTR', b'IN01', b'APMM'): A[tag] = tag.decode()
    return A
def convert(d):
    n = len(d) & ~3
    out = bytearray(b''.join(d[i:i + 4][::-1] for i in range(0, n, 4)) + d[n:])
    def h(o): out[o:o + 2] = d[o:o + 2][::-1]; out[o + 2:o + 4] = d[o + 2:o + 4][::-1]
    for o in (0x58, 0x5C, 0x60, 0x64): h(o)
    A = anchors_of(d); last = None
    ss, se = string_range(d)
    secs = sorted((struct.unpack_from('>I', d, h_)[0], h_) for h_ in range(0x34, 0x58, 4) if 0 < struct.unpack_from('>I', d, h_)[0] < len(d))
    def sect_of(o):
        cur = (0x68, 0x34)
        for v, h_ in secs:
            if v <= o: cur = (v, h_)
        return (cur[1], o - cur[0])
    for o in range(0x68, n, 4):
        if ss <= o < se: continue
        w = d[o:o + 4]
        if w in A: last = (A[w], o); continue
        k = ('%s+%d' % (last[0], o - last[1])) if last else 'sec%x+%d' % sect_of(o)
        r = RULES.get(k + '|' + shape(w)) or RULES.get(k)
        if r == 'H': h(o); continue
        if r == 'S': out[o:o + 4] = d[o:o + 4]; continue
        if r == 'W': continue
        hi, lo = struct.unpack_from('>HH', d, o)
        if 0 < hi < 0x1000 and lo < 0x1000:
            h(o)
    out[ss:se] = d[ss:se]
    remap_words_le(out)
    return bytes(out)
