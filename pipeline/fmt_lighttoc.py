"""LightTOC (.lights.toc) PS3 -> PC: header {u16,u16, u32 off1, u32 off2, u16 n1, u16 n2}; n1 x 160-byte light records at off1,
n2 x 304-byte records at off2 (same first 160 bytes + 144 bytes of u32s). u32 words except +0x54 (2 bytes + u16),
+0x5C (4 bytes, colour) and +0x80..+0xA0 (name, as is)."""
import struct
def convert(d):
    out = bytearray(b''.join(d[i:i + 4][::-1] for i in range(0, len(d) & ~3, 4)) + d[len(d) & ~3:])
    for o in (0, 2, 12, 14): out[o:o + 2] = d[o:o + 2][::-1]
    o1, o2 = struct.unpack_from('>II', d, 4); n1, n2 = struct.unpack_from('>HH', d, 12)
    recs = [o1 + 160 * i for i in range(n1)] + ([o2 + 304 * i for i in range(n2)] if o2 else [])
    for r in recs:
        out[r + 0x54:r + 0x56] = d[r + 0x54:r + 0x56]; out[r + 0x56:r + 0x58] = d[r + 0x56:r + 0x58][::-1]
        out[r + 0x5C:r + 0x60] = d[r + 0x5C:r + 0x60]
        out[r + 0x80:r + 0xA0] = d[r + 0x80:r + 0xA0]
    return bytes(out)
