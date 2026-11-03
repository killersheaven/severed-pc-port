import os, sys, collections, struct, fmt_metamodel as M
D = 'pairs/MetaModel'; c = collections.Counter(); ex = {}
for f in sorted(os.listdir(D)):
    if not f.endswith('.ps3'): continue
    a = open(D + '/' + f, 'rb').read(); b = open(D + '/' + f[:-4] + '.pc', 'rb').read(); o_ = M.convert(a)
    A = M.anchors_of(a); last = None; ss, se = M.string_range(a)
    for o in range(0x68, len(a) & ~3, 4):
        w = a[o:o + 4]
        if w in A and not (ss <= o < se): last = (A[w], o)
        if o_[o:o + 4] == b[o:o + 4]: continue
        p, q = w, b[o:o + 4]
        k = 'needW' if p[::-1] == q else 'needH' if p[1::-1] + p[:1:-1] == q else 'needS' if p == q else None
        if not k: continue
        inS = ss <= o < se
        key = (k, 'instr' if inS else ('%s+%d' % (last[0], o - last[1]) if last else 'nolast'), )
        c[key] += 1
        ex.setdefault(key, (f, hex(o), p.hex(), hex(ss), hex(se)))
for k, v in c.most_common(40): print(v, k, ex[k])
