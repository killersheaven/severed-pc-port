"""Learn u16-pair (H) vs u32 (W) word positions relative to anchor words (frequent type hashes) over all pairs of a type."""
import os, sys, struct, collections, json
T = sys.argv[1]; D = 'pairs/' + T
files = sorted(int(f[:-4]) for f in os.listdir(D) if f.endswith('.ps3'))
def cls(p, q):
    if p == q: return 'S'
    if p[::-1] == q: return 'W'
    if p[1::-1] + p[:1:-1] == q: return 'H'
    return 'X'
freq = collections.Counter()
data = []
for i in files:
    a = open('%s/%d.ps3' % (D, i), 'rb').read(); b = open('%s/%d.pc' % (D, i), 'rb').read()
    ws = [a[o:o + 4] for o in range(0, len(a) & ~3, 4)]
    for w in set(ws):
        v = int.from_bytes(w, 'big')
        if v > 0x01000000 and w.count(0) == 0: freq[w] += 1
    data.append((a, b))
anchors = {w for w, c in freq.items() if c >= 40}
print('anchors', len(anchors), [w.hex() for w, c in freq.most_common(25)])
stat = collections.defaultdict(collections.Counter)
for a, b in data:
    last = None
    for o in range(0, len(a) & ~3, 4):
        w = a[o:o + 4]
        if w in anchors: last = (w, o); continue
        c = cls(w, b[o:o + 4])
        if c in ('H', 'W') and last and o - last[1] <= 0x60:
            stat[(last[0].hex(), o - last[1])][c] += 1
rules = {}
for k, v in sorted(stat.items()):
    if v['H'] and v['W'] == 0 and v['H'] >= 5: rules['%s+%x' % k] = v['H']
    elif v['H'] and v['W']: print('mixed', k, dict(v))
print('H rules', len(rules)); print(rules)
json.dump(sorted(rules), open('hrules_%s.json' % T, 'w'))
