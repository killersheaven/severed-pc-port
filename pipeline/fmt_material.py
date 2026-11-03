"""Material (.mtlb, magic 0x0AA0DEED) PS3 -> PC.
0x00 magic, 0x04 2 x u16, 0x08..0x24 u32; 3 texture-slot entries at 0x24 {u32 hash, 4 bytes, u32 hash, 4 bytes};
0x54 2 x u16 (.., nParams); 0x58 (paramsOff, ?), 0x5C (valuesOff, valuesSize), 0x60 (stringsOff, stringsSize): u16 pairs;
params nParams x 12 B {u32 hash, u8, u8, u16, 2 x u16}; values: u32 words; strings as is."""
import struct
def convert(d):
    out = bytearray(d)
    def w(o): out[o:o + 4] = d[o:o + 4][::-1]
    def h(o): out[o:o + 2] = d[o:o + 2][::-1]
    w(0); h(4); h(6)
    for o in range(0x08, 0x20, 4): w(o)          # 0x20: 4 bytes, as is
    for e in range(3):
        o = 0x24 + 16 * e
        w(o); w(o + 8)
    for o in range(0x54, 0x70, 2): h(o)
    n = struct.unpack_from('>H', d, 0x56)[0]
    po = struct.unpack_from('>H', d, 0x58)[0]
    vo, vs = struct.unpack_from('>HH', d, 0x5C)
    for i in range(n):
        o = po + 12 * i
        w(o); h(o + 6); h(o + 8); h(o + 10)
    for o in range(vo, vo + vs, 4): w(o)
    return bytes(out)
