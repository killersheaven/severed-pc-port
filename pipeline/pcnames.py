"""Index all PC assets by (type, full name): pc_fullnames.json {type|name: [dat, entry_off, entry_size, ids...]}. Resumable."""
import os, sys, csv, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import strfile, port_str
G = os.path.expanduser('~/mnt/Dead Space 2'); budget = float(sys.argv[1]) if len(sys.argv) > 1 else 150
st = json.load(open('pcnames_state.json')) if os.path.exists('pcnames_state.json') else {'k': 0, 'idx': {}}
ents = []; seen = set()
for r in csv.DictReader(open(os.path.join(G, 'pc_asset_index.csv'), encoding='utf-8-sig')):
    k = (r['dat'], int(r['entry_offset']), int(r['entry_size']))
    if k not in seen: seen.add(k); ents.append(k)
t0 = time.time(); k = st['k']
while k < len(ents) and time.time() - t0 < budget:
    dat, off, size = ents[k]; k += 1
    f = open(os.path.join(G, 'DS2DAT%s.DAT' % dat), 'rb'); f.seek(off); pc = f.read(size)
    for a in strfile.assets(pc, be=False, decode=False):
        key = port_str.type_of(a) + '|' + port_str.name_of(a).lower()
        st['idx'].setdefault(key, [dat, off, a['off']] + ['%08x' % x for x in a['shdr']['f'][1:5]])
st['k'] = k; json.dump(st, open('pcnames_state.json', 'w'))
print('%d/%d streams, %d names, %.0fs' % (k, len(ents), len(st['idx']), time.time() - t0))
