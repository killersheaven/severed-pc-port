import os, re, collections, struct, json, sys
from crack import x65599
D = 'pairs/MetaModel'
def anchors_of(a):
    A = {}
    for s in set(re.findall(rb'[A-Za-z_][A-Za-z0-9_]{1,60}', a)):
        A[struct.pack('>I', x65599(s.lower()))] = s.lower().decode()
    for tag in (b'UMTR', b'IN01', b'APMM'): A[tag] = tag.decode()
    return A
def cls(p, q):
    W = p[::-1]; H = p[1::-1] + p[:1:-1]
    if W == H: return None
    return 'W' if W == q else 'H' if H == q else 'S' if p == q else 'X'
stat = collections.defaultdict(collections.Counter); anyH = collections.Counter()
for f in [f for f in os.listdir(D) if f.endswith('.ps3')]:
    a = open(D + '/' + f, 'rb').read(); b = open(D + '/' + f[:-4] + '.pc', 'rb').read()
    A = anchors_of(a); last = None
    for o in range(0x68, len(a) & ~3, 4):
        w = a[o:o + 4]
        if w in A: last = (A[w], o); continue
        c = cls(w, b[o:o + 4])
        if c in ('H', 'W') and last:
            stat[(last[0], o - last[1])][c] += 1
            if c == 'H': anyH[last[0]] += 1
good = {k: v['H'] for k, v in stat.items() if v['H'] and not v['W']}
mixed = {k: dict(v) for k, v in stat.items() if v['H'] and v['W']}
print('H-anchors', anyH.most_common(40))
print('pure', len(good), sum(good.values()), 'mixed', len(mixed), sum(v['H'] for v in mixed.values()))
for k, v in sorted(mixed.items(), key=lambda x: -x[1]['H'])[:40]: print(k, v)
json.dump({'%s+%d' % k: v for k, v in good.items()}, open('mm_hrules.json', 'w'))
