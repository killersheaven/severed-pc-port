import os, re, collections, struct, json
from crack import x65599
import fmt_metamodel
D = 'pairs/MetaModel'
stat = collections.defaultdict(collections.Counter)
import sys
HOLD = '--holdout' in sys.argv
for f in [f for f in os.listdir(D) if f.endswith('.ps3') and not (HOLD and int(f[:-4]) % 5 == 0)]:
    a = open(D + '/' + f, 'rb').read(); b = open(D + '/' + f[:-4] + '.pc', 'rb').read()
    A = fmt_metamodel.anchors_of(a); last = None
    ss, se = fmt_metamodel.string_range(a)
    secs = sorted((struct.unpack_from('>I', a, h_)[0], h_) for h_ in range(0x34, 0x58, 4) if 0 < struct.unpack_from('>I', a, h_)[0] < len(a))
    def sect_of(o):
        cur = (0x68, 0x34)
        for v, h_ in secs:
            if v <= o: cur = (v, h_)
        return (cur[1], o - cur[0])
    for o in range(0x68, len(a) & ~3, 4):
        if ss <= o < se: continue
        w = a[o:o + 4]
        if w in A: last = (A[w], o); continue
        p, q = w, b[o:o + 4]
        W = p[::-1]; H = p[1::-1] + p[:1:-1]
        ks = [k for k, v in (('W', W), ('H', H), ('S', p)) if v == q]
        if len(ks) == 1:
            k = ('%s+%d' % (last[0], o - last[1])) if last else 'sec%x+%d' % sect_of(o)
            stat[k][ks[0]] += 1; stat[k + '|' + fmt_metamodel.shape(p)][ks[0]] += 1
rules = {}
amb = 0
for k, v in stat.items():
    tot = sum(v.values()); best, n = v.most_common(1)[0]
    if n >= 0.97 * tot and n >= 2: rules[k] = best
    elif best != 'W' or len(v) > 1: amb += 1
json.dump(rules, open('mm_rules.json', 'w'))
print('rules', len(rules), collections.Counter(rules.values()), 'ambiguous keys', amb)
