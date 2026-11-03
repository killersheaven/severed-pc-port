import sys, collections, fmt_vfx
D = 'pairs/VFX'; HOLD = '--holdout' in sys.argv; c = collections.Counter()
for l in open(D + '/names.txt'):
    i, n = l.split(' ', 1); i = int(i)
    if HOLD and i % 5: continue
    a = open('%s/%d.ps3' % (D, i), 'rb').read(); b = open('%s/%d.pc' % (D, i), 'rb').read()
    o = fmt_vfx.convert(a)
    bad = [k for k in range(0, len(b), 4) if o[k:k + 4] != b[k:k + 4] and (a[k:k+4][::-1] == b[k:k+4] or a[k:k+4][1::-1]+a[k:k+4][:1:-1] == b[k:k+4] or a[k:k+4] == b[k:k+4])]
    c['exact' if not bad else 'diff'] += 1; c['words'] += len(bad)
print(dict(c))
