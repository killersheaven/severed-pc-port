import os, re, collections, struct
from crack import x65599
D = 'pairs/MetaModel'
names = collections.Counter(); words = collections.Counter()
files = [f for f in os.listdir(D) if f.endswith('.ps3')]
for f in files:
    a = open(D + '/' + f, 'rb').read()
    for s in re.findall(rb'[A-Za-z_][A-Za-z0-9_]{2,40}', a): names[s.decode().lower()] += 1
    for o in range(0, len(a) & ~3, 4): words[a[o:o + 4]] += 1
hits = {}
for n in names:
    h = struct.pack('>I', x65599(n.encode()))
    if words[h]: hits[n] = (h.hex(), words[h])
for n, (h, c) in sorted(hits.items(), key=lambda x: -x[1][1])[:80]: print(n, h, c)
