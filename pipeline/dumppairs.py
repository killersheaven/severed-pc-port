"""dump all base-game PS3/PC pairs of a type into pairs/TYPE/N.ps3|.pc (same size only). usage: dumppairs.py TYPE [max]"""
import os, sys, csv
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import strfile, port_str
from ps3base import PS3Base
T = sys.argv[1]; mx = int(sys.argv[2]) if len(sys.argv) > 2 else 10**9
G = os.path.expanduser('~/mnt/Dead Space 2'); out = 'pairs/' + T; os.makedirs(out, exist_ok=True)
streams = []
for r in csv.DictReader(open(os.path.join(G, 'pc_asset_index.csv'), encoding='utf-8-sig')):
    if r['ext'] == T:
        k = (r['dat'], int(r['entry_offset']), int(r['entry_size']), int(r['entry_hash'], 16))
        if k not in streams: streams.append(k)
b = PS3Base(); n = 0; seen = set(); names = open(out + '/names.txt', 'w')
for dat, off, size, h in streams:
    if h not in b.index or n >= mx: continue
    f = open(os.path.join(G, 'DS2DAT%s.DAT' % dat), 'rb'); f.seek(off); pc = f.read(size)
    P = {port_str.name_of(a).replace('.ps3', '.win'): a['data'] for a in strfile.assets(b.read(h), be=True, decode=True) if port_str.type_of(a) == T}
    for a in strfile.assets(pc, be=False, decode=True):
        nm = port_str.name_of(a)
        if port_str.type_of(a) != T or nm not in P or nm in seen: continue
        seen.add(nm)
        if len(P[nm]) != len(a['data']) and '--all' not in sys.argv: continue
        open('%s/%d.ps3' % (out, n), 'wb').write(P[nm]); open('%s/%d.pc' % (out, n), 'wb').write(a['data'])
        names.write('%d %s\n' % (n, nm)); n += 1
print(T, n, 'pairs')
