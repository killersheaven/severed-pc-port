"""NAV (navcollection.xml.ps3 -> .win) PS3 -> PC.  u32 words, except:
 - a constant 128-byte raw block (starts bf14d67e 2ddc8e66 ...) is copied as is, wherever it occurs;
 - the runtime pointer slot 0xC8 bytes before each such block, and the one at 0x28, are 0xFFFFFFFF on PS3 and 0 on PC;
 - u32 at 0x34 is a platform-specific checksum (function unknown): kept from PS3 (HASHMAP if learned)."""
SIG = bytes.fromhex('bf14d67e2ddc8e6683ef574961ff698f')
FF = b'\xff\xff\xff\xff'
def convert(d):
    out = bytearray(b''.join(d[i:i + 4][::-1] for i in range(0, len(d) & ~3, 4)) + d[len(d) & ~3:])
    if d[0x28:0x2C] == FF: out[0x28:0x2C] = bytes(4)
    p = d.find(SIG)
    while p >= 0:
        out[p:p + 128] = d[p:p + 128]
        q = p - 0xC8
        if q >= 0 and d[q:q + 4] == FF: out[q:q + 4] = bytes(4)
        p = d.find(SIG, p + 128)
    return bytes(out)
