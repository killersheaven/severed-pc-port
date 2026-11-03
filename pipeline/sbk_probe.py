import struct, collections, sys
P = '/sessions/' + __import__('os').environ.get('USER', '') + '/port/pairs/SBK/'
import os; P = os.path.expanduser('~/port/pairs/SBK/')
def cls(w, v):
    if w == v and w == w[::-1]: return '='
    if v == w[::-1]: return 'S'
    if v == w: return 'K'
    if v == w[1::-1] + w[3:1:-1]: return '2'
    if v[:2] == w[1::-1] and v[2:] == w[2:]: return 'U'
    return 'X'
def sections(a):
    h = struct.unpack_from('>20I', a, 0)
    B = 0x18
    rec0 = struct.unpack_from('>I', a, 0x60)[0] + B
    s = {'hdr': (0x18, rec0), 'REC': (rec0, h[9] + B), 'A': (h[9] + B, h[11] + B), 'B': (h[11] + B, h[12] + B),
         'C': (h[12] + B, h[13] + B), 'D': (h[13] + B, h[14] + B), 'E': (h[14] + B, h[16] + B), 'F': (h[16] + B, h[17] + B),
         'G': (h[17] + B, h[2] + B)}
    return h, s
if __name__ == '__main__':
    stride = {'REC': 0x50, 'A': 8, 'B': 4, 'F': 0x18, 'G': 0x18}
    st = collections.defaultdict(collections.Counter)
    for i in range(81):
        a = open(P + '%d.ps3' % i, 'rb').read(); b = open(P + '%d.pc' % i, 'rb').read()
        h, s = sections(a)
        if struct.unpack_from('<I', b, 0x10)[0] != h[4]: continue
        for nm, (lo, hi) in s.items():
            for o in range(lo, hi, 4):
                c = cls(a[o:o+4], b[o:o+4])
                if c == '=': continue
                key = (nm, (o - lo) % stride[nm]) if nm in stride else (nm, (o - lo) if nm == 'hdr' else -1)
                st[key][c] += 1
    for k in sorted(st, key=lambda k: (k[0], k[1])): print(k, dict(st[k]))
