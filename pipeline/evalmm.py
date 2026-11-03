import os, sys, collections, importlib, struct
mod = importlib.import_module(sys.argv[1]); D = 'pairs/' + sys.argv[2]
c = collections.Counter(); files_ok = 0; nf = 0; ctx = collections.Counter()
for f in sorted(os.listdir(D)):
    if not f.endswith('.ps3'): continue
    a = open(D + '/' + f, 'rb').read(); b = open(D + '/' + f[:-4] + '.pc', 'rb').read(); o_ = mod.convert(a); nf += 1
    bad = 0
    for o in range(0, len(a) & ~3, 4):
        if o_[o:o + 4] == b[o:o + 4]: continue
        p, q = a[o:o + 4], b[o:o + 4]
        k = 'needW' if p[::-1] == q else 'needH' if p[1::-1] + p[:1:-1] == q else 'needS' if p == q else 'X'
        c[k] += 1; bad += 1
        if k == 'needH': ctx[a[o - 4:o].hex()[:4] + '..|' + p.hex()] += 1
    files_ok += bad == 0
print(nf, 'files', files_ok, 'exact;', dict(c))
print(ctx.most_common(15))
