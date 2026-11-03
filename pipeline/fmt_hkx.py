"""Havok 6.5 packfile (HKX/.hka collision) PS3 -> PC.
Header and section headers: u32 words (magic, names as is); layout rules set to PC (4, little endian, no padding reuse, 1).
__classnames__: {u32 signature, 0x09, name} entries. __data__: split into objects (virtual fixups) and the arrays they
point to (local/global fixups); each word converted by rules learned from base-game pairs (learnhk.py -> hk_rules.json):
per class + offset for objects, per owner field + repeating element pattern for arrays. Fixup tables: u32 words."""
import struct, json, os
import hkregions
_r = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hk_rules.json')
R = json.load(open(_r)) if os.path.exists(_r) else {'pos': {}, 'key': {}, 'period': {}}
def convert(d):
    out = bytearray(d)
    def W(o): out[o:o + 4] = d[o:o + 4][::-1]
    def H(o): out[o:o + 2] = d[o:o + 2][::-1]; out[o + 2:o + 4] = d[o + 2:o + 4][::-1]
    for o in (0x08, 0x0C, 0x14, 0x18, 0x1C, 0x20, 0x24): W(o)
    out[0x10:0x14] = bytes([4, 1, 0, 1])
    ds, regs, fx, S = hkregions.regions(d, True)
    for s in S:
        for k in range(7): W(s['hdr'] + 20 + 4 * k)
    for s in S:
        base = s['start']
        if s['name'] == '__classnames__':
            o = base
            while o + 5 <= base + s['lf'] and d[o:o + 4] != b'\xff\xff\xff\xff':
                W(o); e = d.index(b'\0', o + 5); o = e + 1
        elif s['name'] == '__data__':
            for st, en, k in regs:
                ks = hkregions.kstr(k)
                per = R['period'].get(ks); dflt = R['key'].get(ks, 'W')
                for o in range(st, en, 4):
                    if base + o + 4 > len(d): break
                    c = R['pos'].get(ks + '@%d' % (o - st))
                    if c is None: c = per[((o - st) // 4) % len(per)] if per else dflt
                    if c == 'W': W(base + o)
                    elif c == 'H': H(base + o)
                    elif c == 'BH': out[base + o + 2:base + o + 4] = d[base + o + 2:base + o + 4][::-1]
                    elif c == 'HB': out[base + o:base + o + 2] = d[base + o:base + o + 2][::-1]
                    elif c == 'Q0': out[base + o:base + o + 8] = d[base + o:base + o + 8][::-1]
                    elif c == 'Q1': pass
            for o in range(base + s['lf'], base + s['ex'], 4): W(o)
    return bytes(out)
