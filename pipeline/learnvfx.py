import sys, json, collections
from vfxcommon import anchors, names, shape
D = 'pairs/VFX'; HOLD = '--holdout' in sys.argv
stat = collections.defaultdict(collections.Counter)
for l in open(D + '/names.txt'):
    i, n = l.split(' ', 1); i = int(i)
    if HOLD and i % 5 == 0: continue
    a = open('%s/%d.ps3' % (D, i), 'rb').read(); b = open('%s/%d.pc' % (D, i), 'rb').read()
    A = anchors(a); Sx = names(a); last = ('start', 0)
    for o in range(0, len(a) & ~3, 4):
        for k in range(o - 3, o + 1):
            if k in A: last = (A[k], k)
        if o in Sx: continue
        p, q = a[o:o + 4], b[o:o + 4]
        cands = {c for c, v in (('W', p[::-1]), ('H', p[1::-1] + p[:1:-1]), ('S', p)) if v == q}
        if len(cands) != 1: continue
        c = cands.pop(); key = '%s+%d' % (last[0], o - last[1])
        stat[key][c] += 1; stat[key + '|' + shape(p)][c] += 1
rules = {}
for k, v in stat.items():
    b_, n_ = v.most_common(1)[0]
    if n_ >= 0.97 * sum(v.values()) and n_ >= 2: rules[k] = b_
json.dump(rules, open('vfx_rules.json', 'w'))
print('rules', len(rules), collections.Counter(rules.values()))
