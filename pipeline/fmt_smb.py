"""SMB (streamed-audio list, type hash 0x390E1228) PS3/360 big-endian -> PC.  Validated on all 167 base-game pairs.
Layout (offsets inside a record are relative to the record):
  header: 6 x u32 (0, 0, 0xC, 0x10, count, tableOffset); table: count x u32 record offsets
  record: u16, u16 type, u32 fields up to S = u32 at +0x40 (string offset), T = u32 at +0x44 (0 = plain record)
          names (NUL-terminated, 4-byte padded, unchanged) from S up to E = u32 at T+12, or to the record end if T == 0
          extended records: from E to the record end everything is u32 (entries of 8 u32, then the table at T:
          count, 0, hash, E)."""
import struct

def convert(d):
    out = bytearray(d)
    def sw32(o): out[o:o + 4] = d[o:o + 4][::-1]
    for o in range(0, 24, 4): sw32(o)
    n, tab = struct.unpack_from('>II', d, 16)
    offs = [struct.unpack_from('>I', d, tab + 4 * i)[0] for i in range(n)]
    for i in range(n): sw32(tab + 4 * i)
    so = sorted(offs)
    end_of = dict(zip(so, so[1:] + [len(d)]))
    for a in offs:
        b = end_of[a]
        out[a:a + 2] = d[a:a + 2][::-1]; out[a + 2:a + 4] = d[a + 2:a + 4][::-1]
        s, t = struct.unpack_from('>II', d, a + 0x40)
        for o in range(a + 4, a + s, 4): sw32(o)
        if t:
            e = struct.unpack_from('>I', d, a + t + 12)[0]
            for o in range(a + e, b, 4): sw32(o)
    return bytes(out)
