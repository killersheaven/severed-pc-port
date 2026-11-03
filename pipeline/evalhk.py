import sys, collections, fmt_hkx
D = 'pairs/HKX'; HOLD = '--holdout' in sys.argv
c = collections.Counter(); bad = collections.Counter()
for l in open(D + '/names.txt'):
    i, n = l.split(' ', 1); i = int(i)
    if HOLD and i % 5: continue
    a = open('%s/%d.ps3' % (D, i), 'rb').read(); b = open('%s/%d.pc' % (D, i), 'rb').read()
    if len(a) != len(b): c['sizediff'] += 1; continue
    try: o = fmt_hkx.convert(a)
    except Exception as e: c['err'] += 1; continue
    nb = sum(1 for k in range(0, len(b), 4) if o[k:k + 4] != b[k:k + 4])
    c['exact' if nb == 0 else 'diff'] += 1; bad['words'] += nb
print(dict(c), dict(bad))
