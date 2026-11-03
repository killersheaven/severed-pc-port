"""Walk the structured part of an EA animation bank (BNK, PS3 big-endian): regions reached through 16-byte-aligned
pointers, each ending at '____' padding or at the next region; returns {start: (end, path)}."""
import struct
PAD = b'____'
def walk(d):
    n = len(d)
    U = lambda o: struct.unpack_from('>I', d, o)[0]
    regions = {}
    todo = [(0, 'root')]
    while todo:
        st, path = todo.pop()
        if st in regions or st >= n: continue
        o = st; ptrs = []
        while o + 4 <= n and d[o:o + 4] != PAD and (o == st or o not in regions):
            if o - st > 0x400: break
            v = U(o)
            if v >= 0x40 and v % 16 == 0 and v < n and v != st: ptrs.append((v, '%s>%d' % (path, o - st)))
            o += 4
        regions[st] = (o, path)
        for v, p in ptrs:
            # a pointer to printable text = name string, not a structure
            if 32 <= d[v] < 127 and 32 <= d[v + 1] < 127 and 32 <= d[v + 2] < 127: regions.setdefault(v, (v, 'str')); continue
            todo.append((v, p))
    return regions
