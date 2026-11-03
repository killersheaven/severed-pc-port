"""Severed assets that exist on PC under the same type+name but with other IDs: map Severed PS3 IDs -> PC IDs (sev_idmap.json)."""
import os, json, collections, strfile, port_str
W = os.path.expanduser('~/mnt/weller1')
idx = json.load(open('pc_fullnames.json'))
m = {}; c = collections.Counter(); conf = 0
for dp, dn, fn in os.walk(W):
    if 'clod' in dp: continue
    for f in fn:
        if not f.endswith('.str'): continue
        for a in strfile.assets(open(os.path.join(dp, f), 'rb').read(), be=True, decode=False):
            t = port_str.type_of(a); key = t + '|' + port_str.name_of(a).lower().replace('.ps3', '.win')
            if key not in idx: continue
            x = ['%08x' % v for v in a['shdr']['f'][1:5]]; y = idx[key][3:7]
            if x == y or not any(int(v, 16) for v in x): continue
            c[t] += 1
            for p, q in zip(x, y):
                if p in m and m[p] != q: conf += 1
                m[p] = q
json.dump(m, open('sev_idmap.json', 'w'))
print(len(m), 'ids, conflicts', conf, dict(c))
