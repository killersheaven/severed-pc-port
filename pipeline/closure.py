"""Find the PC asset closure (by ID references) of a PC asset given type|name."""
import os, sys, csv, json, struct, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import port_str
G = os.path.expanduser('~/mnt/Dead Space 2')
pc = port_str.PCAssets(G, os.path.join(G, 'pc_assets.csv'))
byid = {}
for r in csv.DictReader(open(os.path.join(G, 'pc_assets.csv'), encoding='utf-8-sig')):
    if r['id1'] != '00000000':
        byid.setdefault(int(r['id1'], 16), []).append((r['source'], int(r['entry_offset']), int(r['asset_offset']), r['ext'], r['name']))
SCAN = {'MetaModel', 'Mesh', 'Material', 'MeshVolatile_hdr'}
def closure(t, name):
    idx = json.load(open('pc_fullnames.json'))
    loc = idx[t + '|' + name.lower()]
    todo = [('DS2DAT%s' % loc[0], loc[1], loc[2], t, name)]; seen = set(); out = []
    while todo:
        src, eo, ao, tt, nm = todo.pop()
        if (src, eo, ao) in seen: continue
        seen.add((src, eo, ao))
        a = pc.stream(src, eo).get(ao)
        if not a: print('missing', nm); continue
        out.append((tt, port_str.name_of(a), len(a['data'])))
        if tt in SCAN:
            d = a['data']
            for o in range(0, len(d) - 3, 4):
                v = struct.unpack_from('<I', d, o)[0]
                for e in byid.get(v, []):
                    if e[3] in ('Mesh', 'MeshVolatile', 'Material', 'tg4h', 'tg4d', 'MetaModel', 'HKX', 'VFX'):
                        todo.append(e)
    return out
if __name__ == '__main__':
    res = closure(sys.argv[1], sys.argv[2])
    c = collections.Counter(t for t, n, s in res)
    print(len(res), dict(c), sum(s for t, n, s in res))
    for r in res[:40]: print(r)
