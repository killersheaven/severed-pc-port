import struct, collections, os
def load_names(d):
    m = {}
    for l in open(d + '/names.txt'):
        i, n = l.rstrip('\n').split(' ', 1); m[n] = int(i)
    return m
MN = load_names('pairs/Mesh'); VN = load_names('pairs/MeshVolatile')
def pairs_iter(limit=10**9):
    for n, i in list(MN.items())[:limit]:
        a = open('pairs/Mesh/%d.ps3' % i, 'rb').read(); b = open('pairs/Mesh/%d.pc' % i, 'rb').read()
        va = vb = b''
        if n in VN:
            j = VN[n]; va = open('pairs/MeshVolatile/%d.ps3' % j, 'rb').read(); vb = open('pairs/MeshVolatile/%d.pc' % j, 'rb').read()
        yield n, a, b, va, vb
def streams(m, vol, be):
    e = '>' if be else '<'
    U = lambda o: struct.unpack_from(e + 'I', m, o)[0]
    s0, s1 = U(0x68), U(0x6C); out = []
    for o in range(s0, s1, 16):
        size, cnt, off = U(o), U(o + 4), U(o + 12)
        stride = struct.unpack_from(e + 'H', m, o + 8)[0]; A, B = m[o + 10], m[o + 11]
        src = m if off < len(m) else vol; base = 0 if off < len(m) else len(m)
        out.append(dict(size=size, cnt=cnt, stride=stride, A=A, B=B, data=src[off - base:off - base + size], where='mesh' if off < len(m) else 'vol'))
    return out
