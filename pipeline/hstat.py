import os, sys, collections
T = sys.argv[1]; D = 'pairs/' + T
c = collections.Counter()
for f in os.listdir(D):
    if not f.endswith('.ps3'): continue
    a = open(D + '/' + f, 'rb').read(); b = open(D + '/' + f[:-4] + '.pc', 'rb').read()
    for o in range(0, len(a) & ~3, 4):
        p, q = a[o:o + 4], b[o:o + 4]
        if p == q: continue
        k = 'W' if p[::-1] == q else 'H' if p[1::-1] + p[:1:-1] == q else 'X'
        hi, lo = int.from_bytes(p[:2], 'big'), int.from_bytes(p[2:], 'big')
        cat = 'hi0_lo_small' if hi == 0 and lo < 0x1000 else 'lo0_hi_small' if lo == 0 and hi < 0x1000 else 'both_small' if hi < 0x1000 and lo < 0x1000 else 'other'
        c[(cat, k)] += 1
for k, v in sorted(c.items()): print(k, v)
