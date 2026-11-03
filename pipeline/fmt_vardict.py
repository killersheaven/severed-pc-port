"""VariableDictionary (.vardict.bin) PS3 -> PC: u32 version, u32 count, count x {hash, type, value, nameOffset} u32s; then names (as is)."""
import struct
def convert(d):
    n = struct.unpack_from('>I', d, 4)[0]
    end = 8 + 16 * n
    return b''.join(d[i:i + 4][::-1] for i in range(0, end, 4)) + d[end:]
