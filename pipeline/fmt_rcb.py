"""RCB (character rig/control blob) PS3 -> PC: all u32 words, except
- name strings starting on a 4-byte boundary (>= 4 chars, NUL-terminated, '_'-padded): as is;
- bit arrays: {u32 self-offset, u32 nBits, bytes...}: the ceil(nBits/32) words of bits stay as bytes."""
import re, struct
STR = re.compile(rb'[\x20-\x7e]{4,}\x00_*')
def convert(d):
    n = len(d) & ~3
    out = bytearray(b''.join(d[i:i + 4][::-1] for i in range(0, n, 4)) + d[n:])
    o = 0
    while o < n:
        m = STR.match(d, o)
        if m and re.search(rb'[a-z]{3}', m.group(0)):
            e = m.end(); out[o:e] = d[o:e]; o = (e + 3) & ~3; continue
        if o >= 8 and struct.unpack_from('>I', d, o - 8)[0] == o:
            nb = struct.unpack_from('>I', d, o - 4)[0]
            e = o + 4 * ((nb + 31) // 32); nbytes = (nb + 7) // 8
            if 0 < nb <= 256 and e <= n and d[o] != 0 and not any(d[o + nbytes:e]):
                out[o:e] = d[o:e]; o = e; continue
        o += 4
    return bytes(out)
