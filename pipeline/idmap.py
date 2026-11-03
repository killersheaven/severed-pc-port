"""Build PS3->PC asset ID map from all base-game streams (SHDR headers only). Resumable: idmap_state.json.
For each asset name present on both: PS3 (id1..id4) -> PC (id1..id4) when they differ."""
import os, sys, csv, json, time, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import strfile, port_str
from ps3base import PS3Base
G = os.path.expanduser('~/mnt/Dead Space 2'); budget = float(sys.argv[1]) if len(sys.argv) > 1 else 150
st = json.load(open('idmap_state.json')) if os.path.exists('idmap_state.json') else {'k': 0, 'map': {}, 'conf': 0, 'types': {}}
ents = []
seen = set()
for r in csv.DictReader(open(os.path.join(G, 'pc_asset_index.csv'), encoding='utf-8-sig')):
    k = (r['dat'], int(r['entry_offset']), int(r['entry_size']), int(r['entry_hash'], 16))
    if k not in seen: seen.add(k); ents.append(k)
b = PS3Base(); t0 = time.time(); k = st['k']; m = st['map']; types = collections.Counter(st['types'])
while k < len(ents) and time.time() - t0 < budget:
    dat, off, size, h = ents[k]; k += 1
    if h not in b.index: continue
    f = open(os.path.join(G, 'DS2DAT%s.DAT' % dat), 'rb'); f.seek(off); pc = f.read(size)
    try:
        ps3 = b.read(h)
        P = {}
        for a in strfile.assets(ps3, be=True, decode=False):
            P[(port_str.type_of(a), port_str.name_of(a).replace('.ps3', '.win'))] = a['shdr']['f']
        for a in strfile.assets(pc, be=False, decode=False):
            key = (port_str.type_of(a), port_str.name_of(a))
            if key in P:
                x, y = P[key][1:5], a['shdr']['f'][1:5]
                if x != y and any(x):
                    types[key[0]] += 1
                    for p, q in zip(x, y):
                        p, q = '%08x' % p, '%08x' % q
                        if p in m and m[p] != q: st['conf'] += 1
                        m[p] = q
    except Exception as e:
        print('err', k, repr(e)[:80])
st['k'] = k; st['map'] = m; st['types'] = dict(types)
json.dump(st, open('idmap_state.json', 'w'))
print('entries %d/%d map %d conflicts %d (%.0fs)' % (k, len(ents), len(m), st['conf'], time.time() - t0), dict(types))
