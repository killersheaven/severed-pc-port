"""Dead Space 2 .str (ols3) reader for 360 (big-endian) and PC (little-endian)."""
import struct
from lzx import xmem_decompress
from refpack import refpack_decompress

def chunks(b, be):
    E = '>' if be else '<'
    i = 12; out = []
    while i + 8 <= len(b):
        tag = b[i:i+4] if be else b[i:i+4][::-1]
        sz = struct.unpack(E+'I', b[i+4:i+8])[0]
        if sz == 0:
            break
        if tag == b'FILL':   # padding to a block boundary; more chunks may follow
            i += sz
            continue
        sub = (b[i+8:i+12] if be else b[i+8:i+12][::-1]).decode()
        out.append((i, sub, b[i:i+sz]))
        i += sz
    return out

def read_shdr(raw, be):
    E = '>' if be else '<'
    f = list(struct.unpack(E+'I', raw[12:16]))          # type/version word
    h0, h1 = struct.unpack(E+'HH', raw[16:20])           # two u16
    rest = list(struct.unpack(E+'6I', raw[20:44]))       # type hash, 3x id, ?, usize
    name = raw[44:]
    return {'w0': f[0], 'h': (h0, h1), 'f': rest, 'usize': rest[5], 'name': name}

def data_of(sub, raw, be):
    E = '>' if be else '<'
    if sub == 'SDAT':
        return 'raw', raw[12:]
    n = struct.unpack(E+'I', raw[12:16])[0]
    return sub, raw[16:16+n]

def assets(b, be, decode=True):
    res = []; cur = None
    for i, sub, raw in chunks(b, be):
        if sub == 'SHDR':
            cur = {'off': i, 'shdr': read_shdr(raw, be), 'hdr_raw': raw, 'parts': []}
            res.append(cur)
        else:
            cur['parts'].append(data_of(sub, raw, be))
    if decode:
        for a in res:
            out = b''
            for kind, d in a['parts']:
                if kind == 'raw':
                    out += d
                elif kind == 'Rpak':
                    out += refpack_decompress(d)
                elif kind == 'LZXD':
                    out += xmem_decompress(d, a['shdr']['usize'] - len(out))
                else:
                    raise ValueError(kind)
            a['data'] = out[:a['shdr']['usize']]
            a['complete'] = len(out) >= a['shdr']['usize']
    return res
