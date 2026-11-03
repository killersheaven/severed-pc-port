import struct, collections
def strip_tris(idx):
    t = collections.Counter()
    for k in range(len(idx) - 2):
        a, b, c = idx[k], idx[k + 1], idx[k + 2]
        if a == b or b == c or a == c or 0xFFFF in (a, b, c): continue
        if k % 2: a, b = b, a
        m = min(range(3), key=lambda j: (a, b, c)[j]); tri = (a, b, c)[m:] + (a, b, c)[:m]
        t[tri] += 1
    return t
def ps3_tris(idx):   # strips with restart
    t = collections.Counter(); cur = []
    for i in list(idx) + [0xFFFF]:
        if i == 0xFFFF:
            t += strip_tris(cur); cur = []
        else: cur.append(i)
    return t
