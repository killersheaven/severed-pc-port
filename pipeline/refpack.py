"""EA RefPack (QFS) decoder, as used by Dead Space 2 PC 'Rpak' chunks."""


def refpack_decompress(d):
    flags = d[0]
    if d[1] != 0xFB:
        raise ValueError("not refpack")
    big = flags & 0x80
    n = 4 if big else 3
    p = 2
    if flags & 0x01:  # compressed-size field present
        p += n
    usize = int.from_bytes(d[p:p + n], 'big')
    p += n
    out = bytearray()
    while p < len(d):
        b0 = d[p]
        if b0 < 0x80:
            b1 = d[p + 1]; p += 2
            lit = b0 & 3
            ln = ((b0 >> 2) & 7) + 3
            off = ((b0 & 0x60) << 3) + b1 + 1
        elif b0 < 0xC0:
            b1, b2 = d[p + 1], d[p + 2]; p += 3
            lit = b1 >> 6
            ln = (b0 & 0x3F) + 4
            off = ((b1 & 0x3F) << 8) + b2 + 1
        elif b0 < 0xE0:
            b1, b2, b3 = d[p + 1], d[p + 2], d[p + 3]; p += 4
            lit = b0 & 3
            ln = ((b0 & 0x0C) << 6) + b3 + 5
            off = ((b0 & 0x10) << 12) + (b1 << 8) + b2 + 1
        elif b0 < 0xFC:
            p += 1
            lit = ((b0 & 0x1F) << 2) + 4
            ln = 0; off = 0
        else:
            p += 1
            lit = b0 & 3
            out += d[p:p + lit]; p += lit
            break
        out += d[p:p + lit]; p += lit
        for _ in range(ln):
            out.append(out[-off])
    if len(out) != usize:
        raise ValueError("size mismatch %d != %d" % (len(out), usize))
    return bytes(out)


# ---- fast path: C decoder (librefpack.so next to this file), same results
import ctypes as _ct, os as _os
_lib = None
_p = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'librefpack.so')
if _os.path.exists(_p):
    _lib = _ct.CDLL(_p)
    _lib.refpack_decode.restype = _ct.c_int
    _lib.refpack_decode.argtypes = [_ct.c_char_p, _ct.c_int, _ct.c_char_p, _ct.c_int]
    _py_refpack = refpack_decompress
    def refpack_decompress(d):
        d = bytes(d)
        big = d[0] & 0x80
        n = 4 if big else 3
        p = 2 + (n if d[0] & 1 else 0)
        usize = int.from_bytes(d[p:p + n], 'big')
        buf = _ct.create_string_buffer(usize)
        got = _lib.refpack_decode(d, len(d), buf, usize)
        if got != usize:
            return _py_refpack(d)
        return buf.raw
