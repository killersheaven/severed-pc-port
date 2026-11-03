"""SBK sound bank PS3 ('knbs', BE) -> PC ('sbnk', LE).  Audio payload (EALayer3, codec 7) is identical on both: copied.
File: 0x18-byte header {magic, ver, metaSize, dataSize, sdatOff, dataSize}; section offsets in the header are relative to 0x18.
  hdr 0x18..rec0       u32
  REC (N x 0x50)       u32, except byte arrays at +0x04, +0x1C
  A (N x 8), B (N x 4) u32            (B = offsets of the C blocks)
  C, D                 u32 float curves; block-start words {u16 n, u16 0} (0x000N0000) are 2 x u16
  E                    op stream of 8-byte entries {u16, u8, u8 | u32}; float header blocks [1.0,0,0,0.01,0,n] are u32
  F (N x 0x18)         u32
  G (N x 0x18)         u32, byte array (reversed hash) at +0x14
  sdat                 'tads' -> 'sdat', count, N x {idx, 0x0313BABE, off, 0xFEEDFEED} u32; sample data copied as is.
"""
import struct
B0 = 0x18

def sections(a):
    h = struct.unpack_from('>20I', a, 0)
    rec0 = struct.unpack_from('>I', a, 0x60)[0] + B0
    meta_end = h[2] + B0
    fixed = [('hdr', 0x18, rec0), ('REC', rec0, h[9] + B0), ('A', h[9] + B0, h[11] + B0), ('B', h[11] + B0, h[12] + B0)]
    lo_ok = h[11] + B0
    var = sorted([(h[12] + B0, 'C'), (h[13] + B0, 'D'), (h[14] + B0, 'E'), (h[16] + B0, 'F'), (h[17] + B0, 'G')])
    var = [(st, nm) for st, nm in var if st >= lo_ok]          # a section pointing back into earlier data is empty
    out = list(fixed)
    for k, (st, nm) in enumerate(var):
        en = var[k + 1][0] if k + 1 < len(var) else meta_end
        out.append((nm, st, en))
    # B ends at the first variable section actually present
    if var: out[3] = ('B', h[11] + B0, var[0][0])
    return h, out

def _is_pair16(w):
    return w[0] == 0 and w[1] != 0 and w[2] == 0 and w[3] == 0

def convert(a):
    if a[:4] != b'knbs':
        raise ValueError('not a PS3 SBK')
    h, secs = sections(a)
    meta_end, sdat = h[2] + B0, h[4]
    out = bytearray(a)
    def sw(o): out[o:o + 4] = a[o:o + 4][::-1]
    def u16(o): out[o:o + 2] = a[o:o + 2][::-1]
    def p16(o): out[o:o + 2] = a[o:o + 2][::-1]; out[o + 2:o + 4] = a[o + 2:o + 4][::-1]
    out[0:4] = b'sbnk'
    for o in range(4, 0x18, 4): sw(o)
    for nm, lo, hi in secs:
        if not (0x18 <= lo <= hi <= meta_end):
            raise ValueError('bad section %s %x..%x' % (nm, lo, hi))
        if nm == 'REC':
            for o in range(lo, hi, 4):
                if (o - lo) % 0x50 not in (4, 0x1C): sw(o)
        elif nm == 'G':
            for o in range(lo, hi, 4):
                if (o - lo) % 0x18 != 0x14: sw(o)
        elif nm in ('C', 'D'):
            for o in range(lo, hi, 4):
                if _is_pair16(a[o:o + 4]): p16(o)
                else: sw(o)
        elif nm == 'E':
            o = lo
            while o + 8 <= hi:
                w = a[o:o + 4]
                if w == b'\x3f\x80\x00\x00' and o + 24 <= hi and a[o + 12:o + 16] == b'\x3c\x23\xd7\x0a':
                    for k in range(0, 24, 4): sw(o + k)
                    o += 24; continue
                u16(o); sw(o + 4); o += 8
            for k in range(o, hi, 4): sw(k)
        else:
            for o in range(lo, hi, 4): sw(o)
    # padding between metadata and sdat stays as is; sdat table
    if a[sdat:sdat + 4] != b'tads':
        raise ValueError('no tads at %x' % sdat)
    out[sdat:sdat + 4] = b'sdat'
    n = struct.unpack_from('>I', a, sdat + 4)[0]
    for o in range(sdat + 4, sdat + 8 + 16 * n, 4): sw(o)
    return bytes(out)

if __name__ == '__main__':
    import sys, os, collections
    P = os.path.expanduser('~/port/pairs/SBK/')
    tot = collections.Counter(); per = []
    for i in range(81):
        a = open(P + '%d.ps3' % i, 'rb').read(); b = open(P + '%d.pc' % i, 'rb').read()
        h, secs = sections(a)
        if struct.unpack_from('<I', b, 0x10)[0] != h[4]: tot['skip(layout differs)'] += 1; continue
        c = convert(a)
        bad = [o for o in range(0, h[4], 4) if c[o:o + 4] != b[o:o + 4] and o not in (0xC, 0x14)]
        tot['pairs'] += 1; tot['badwords'] += len(bad)
        if not bad: tot['exact'] += 1
        else: per.append((i, len(bad), [hex(x) for x in bad[:5]]))
    print(dict(tot)); print(per)
