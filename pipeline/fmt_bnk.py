"""EA animation bank (BNK) PS3 -> PC.
Layout: u32[0] = offset of the fixup list (= content size), u32[4] = 9. The fixup list (to the end of the file) holds
the offsets of every pointer field, newest first, 0-terminated. The compressed animation data is identical on both
platforms. Converted: the header (0..0x40), the fixup list, every pointer field, and every region a pointer points at
(up to '____' padding or the next region); inside regions, words are u32 except byte fields (b0 small and the rest
0xFFFFFF, or two small bytes + 0x0000) and type/index words (b0 0x10-0x3F, b1 0, u16). Pointed-to strings stay as is."""
import struct
PAD = b'____'
def kind(p):
    if p[0] <= 0x10 and p[1:] == b'\xff\xff\xff': return 'S'
    if p[0] <= 0x10 and p[2:] == b'\0\0' and 0 < p[1] <= 0x10: return 'S'
    if p[0] <= 0x10 and p[1] <= 0x10 and p[2] <= 0x10 and p[3] == 0xff: return 'S'
    if 0 < p[0] < 0x40 and p[1] <= 0x40 and p[2] == 0 and p[3] != 0 and not (p[0] <= 0x10 and p[1] == 0 and p[3] < 0x10 and False): return 'BH'
    return 'W'
def convert(d):
    n = len(d); out = bytearray(d)
    U = lambda o: struct.unpack_from('>I', d, o)[0]
    W = lambda o: out.__setitem__(slice(o, o + 4), d[o:o + 4][::-1])
    fx = U(0)
    if not (0x40 <= fx < n): raise ValueError('no fixup list')
    for o in range(0, 0x40, 4): W(o)
    ptrs = []
    for o in range(fx, n - 3, 4):
        W(o); v = U(o)
        if v == 0: break
        if v + 4 <= fx: ptrs.append(v)
    targets = set()
    for p in ptrs:
        W(p); t = U(p)
        if 0 < t < fx: targets.add(t)
    starts = sorted(targets | {0x40})
    for i, st in enumerate(starts):
        if st % 4: continue                                # unaligned target: a string
        run = 0
        while st + run < fx and 32 <= d[st + run] < 127: run += 1
        if run >= 4 and st + run + 1 < fx and d[st + run] == 0 and (run >= 5 or d[st + run + 1] != 0): continue   # a string
        end = starts[i + 1] if i + 1 < len(starts) else fx
        if d[st + 4:st + 8] == b'\0\0\0\x09' and st + 0x30 <= fx:      # animation header (0x30 bytes) + compressed data
            for k, c in enumerate('WSWWWWWSWSWW'):
                o = st + 4 * k
                if c == 'W' and o not in ptrs: W(o)
            continue
        o = st
        while o < end and o + 4 <= fx and d[o:o + 4] != PAD:
            if o not in ptrs:
                k = kind(d[o:o + 4])
                if k == 'W': W(o)
                elif k == 'BH': out[o + 2:o + 4] = d[o + 2:o + 4][::-1]
            o += 4
    return bytes(out)
