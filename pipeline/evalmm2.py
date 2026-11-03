"""exact-match rate ignoring X words (ID/hash values that differ per platform)"""
import os, sys, collections, importlib
mod = importlib.import_module(sys.argv[1]); D = 'pairs/' + sys.argv[2]
ok = nf = 0; c = collections.Counter(); badf = []
for f in sorted(os.listdir(D), key=lambda x: (len(x), x)):
    if not f.endswith('.ps3'): continue
    if '--holdout' in sys.argv and int(f[:-4]) % 5: continue
    a = open(D + '/' + f, 'rb').read(); b = open(D + '/' + f[:-4] + '.pc', 'rb').read(); o_ = mod.convert(a); nf += 1
    bad = 0
    for o in range(0, len(a) & ~3, 4):
        if o_[o:o + 4] == b[o:o + 4]: continue
        p, q = a[o:o + 4], b[o:o + 4]
        k = 'needW' if p[::-1] == q else 'needH' if p[1::-1] + p[:1:-1] == q else 'needS' if p == q else None
        if k: c[k] += 1; bad += 1
    ok += bad == 0
    if bad: badf.append((f, bad))
print(nf, 'files', ok, 'exact (ignoring ID words);', dict(c))
print(sorted(badf, key=lambda x: -x[1])[:10])
