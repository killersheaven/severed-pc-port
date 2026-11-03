import sys, json, collections, bnkwalk
D = 'pairs/BNK'; HOLD = '--holdout' in sys.argv
stat = collections.defaultdict(collections.Counter)
for l in open(D + '/names.txt'):
    i, n = l.split(' ', 1); i = int(i)
    if HOLD and i % 5 == 0: continue
    a = open('%s/%d.ps3' % (D, i), 'rb').read(); b = open('%s/%d.pc' % (D, i), 'rb').read()
    if len(a) != len(b): continue
    for st, (en, path) in bnkwalk.walk(a).items():
        for o in range(st, en, 4):
            p, q = a[o:o + 4], b[o:o + 4]
            c = {k for k, v in (('W', p[::-1]), ('H', p[1::-1] + p[:1:-1]), ('S', p), ('BH', p[:2] + p[3:1:-1])) if v == q}
            if len(c) == 1: stat['%s@%d' % (path, o - st)][c.pop()] += 1
rules = {k: v.most_common(1)[0][0] for k, v in stat.items() if v.most_common(1)[0][1] >= 0.95 * sum(v.values())}
json.dump(rules, open('bnk_rules.json', 'w')); print('rules', len(rules), collections.Counter(rules.values()))
