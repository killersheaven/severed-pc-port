import os, sys, collections
T = sys.argv[1]; D = 'pairs/' + T
def cat(p):
    hi, lo = int.from_bytes(p[:2], 'big'), int.from_bytes(p[2:], 'big')
    if hi == 0 and lo == 0: return 'z'
    if hi == 0 and lo < 0x1000: return 'h0'
    if lo == 0 and hi < 0x1000: return 'l0'
    if hi < 0x1000 and lo < 0x1000: return 'b'
    if p == b'\xff\xff\xff\xff': return 'f'
    return 'o'
c = collections.defaultdict(collections.Counter)
for f in os.listdir(D):
    if not f.endswith('.ps3'): continue
    a = open(D + '/' + f, 'rb').read(); b = open(D + '/' + f[:-4] + '.pc', 'rb').read()
    n = len(a) & ~3
    for o in range(4, n - 4, 4):
        p, q = a[o:o + 4], b[o:o + 4]
        if cat(p) != 'h0': continue
        W = p[::-1]; H = p[1::-1] + p[:1:-1]
        k = 'W' if W == q else 'H' if H == q else 'o'
        c[(cat(a[o - 4:o]), cat(a[o + 4:o + 8]))][k] += 1
for k, v in sorted(c.items(), key=lambda x: -sum(x[1].values())): print(k, dict(v))
