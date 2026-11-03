import os, sys, json, collections
import hkregions
D = 'pairs/HKX'
HOLD = '--holdout' in sys.argv
stat = collections.defaultdict(collections.Counter); kst = collections.defaultdict(collections.Counter); per = collections.defaultdict(collections.Counter)
names = [l.split(' ', 1) for l in open(D + '/names.txt')]
for i, n in names:
    i = int(i)
    if HOLD and i % 5 == 0: continue
    a = open('%s/%d.ps3' % (D, i), 'rb').read(); b = open('%s/%d.pc' % (D, i), 'rb').read()
    if len(a) != len(b): continue
    try: ds, regs, fx, S = hkregions.regions(a, True)
    except Exception as e: continue
    base = ds['start']
    for st, en, k in regs:
        ks = hkregions.kstr(k)
        for o in range(st, en, 4):
            p, q = a[base + o:base + o + 4], b[base + o:base + o + 4]
            if len(p) < 4: break
            W = p[::-1]; H = p[1::-1] + p[:1:-1]
            cands = [('W', W), ('H', H), ('S', p), ('BH', p[:2] + p[3:1:-1]), ('HB', p[1::-1] + p[2:])]
            p8, q8 = a[base + o:base + o + 8], b[base + o:base + o + 8]
            if (o - st) % 8 == 0 and len(p8) == 8 and o + 8 <= en and p8[::-1] == q8 and p8[::-1] != p8[:4][::-1] + p8[4:][::-1]:
                cl = ['Q0']
            elif (o - st) % 8 == 4 and a[base + o - 4:base + o + 4][::-1] == b[base + o - 4:base + o + 4] and a[base+o-4:base+o+4][::-1] != a[base+o-4:base+o][::-1] + p[::-1]:
                cl = ['Q1']
            else:
                cl = list({c for c, v in cands if v == q})
                if len(cl) > 1: cl = [] if not ({'W','H','S'} & set(cl)) or len({c for c, v in cands if v == q} & {'W','H','S'}) != 1 else [c for c in cl if c in ('W','H','S')]
            if len(cl) != 1: continue
            stat[ks + '@%d' % (o - st)][cl[0]] += 1; kst[ks][cl[0]] += 1
            if k and k[0] == 'A':
                for P in range(4, 68, 4): per[(ks, P, (o - st) % P)][cl[0]] += 1
rules = {}
for k, v in stat.items():
    best, n = v.most_common(1)[0]
    if n >= 0.95 * sum(v.values()): rules[k] = best
kmaj = {k: v.most_common(1)[0][0] for k, v in kst.items()}
period = {}
for ks in {k[0] for k in per}:
    if len(kst[ks]) == 1: continue
    for P in range(4, 68, 4):
        tot = good = 0; pat = []
        for r in range(0, P, 4):
            v = per.get((ks, P, r))
            if not v: pat.append('W'); continue
            b_, n_ = v.most_common(1)[0]; tot += sum(v.values()); good += n_; pat.append(b_)
        if tot and good >= 0.995 * tot:
            period[ks] = ''.join(pat); break
json.dump({'pos': rules, 'key': kmaj, 'period': period}, open('hk_rules.json', 'w'))
print('periods', period)
print('rules', len(rules), collections.Counter(rules.values()), 'keys', len(kmaj))
mixed = sorted(((k, dict(v)) for k, v in kst.items() if len(v) > 1), key=lambda x: -sum(x[1].values()))[:25]
for m in mixed: print(m)
