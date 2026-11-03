"""Havok 6.5 packfile reader (PS3 big-endian or PC little-endian)."""
import struct
def parse(d, be):
    e = '>' if be else '<'
    U = lambda o: struct.unpack_from(e + 'I', d, o)[0]
    nsec = U(0x14); csi = U(0x18)
    secs = []
    for i in range(nsec):
        o = 0x40 + 0x30 * i
        name = d[o:o + 20].split(b'\0')[0].decode('latin1')
        start, lf, gf, vf, ex, im, end = struct.unpack_from(e + '7I', d, o + 20)
        secs.append(dict(hdr=o, name=name, start=start, lf=lf, gf=gf, vf=vf, ex=ex, im=im, end=end))
    return secs
def fixups(d, be, s):
    e = '>' if be else '<'
    base = s['start']
    loc = []; glo = []; vir = []
    for o in range(base + s['lf'], base + s['gf'] - 7, 8):
        a, b = struct.unpack_from(e + '2I', d, o)
        if a != 0xFFFFFFFF: loc.append((a, b))
    for o in range(base + s['gf'], base + s['vf'] - 11, 12):
        a, sec, b = struct.unpack_from(e + '3I', d, o)
        if a != 0xFFFFFFFF: glo.append((a, sec, b))
    for o in range(base + s['vf'], base + s['ex'] - 11, 12):
        a, sec, b = struct.unpack_from(e + '3I', d, o)
        if a != 0xFFFFFFFF: vir.append((a, sec, b))
    return loc, glo, vir
def classname(d, secs, sec, off):
    s = secs[sec]; p = s['start'] + off
    return d[p:d.index(b'\0', p)].decode('latin1')
