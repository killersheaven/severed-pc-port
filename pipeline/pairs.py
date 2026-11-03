"""Collect PS3/PC pairs of shared assets of one type. usage: pairs.py TYPE MAXPAIRS"""
import os, sys, csv, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import port_str, strfile
T = sys.argv[1]; N = int(sys.argv[2])
G = os.path.expanduser('~/mnt/Dead Space 2'); W = os.path.expanduser('~/mnt/weller1')
rows = [r for r in csv.reader(open('report.csv')) if r[3] == T and r[4] == 'pc']
by_stream = collections.defaultdict(set)
for r in rows: by_stream[r[1]].add(r[2])
pc = port_str.PCAssets(G, os.path.join(G, 'pc_assets.csv'))
out = os.path.join('pairs', T); os.makedirs(out, exist_ok=True)
n = 0; seen = set()
for rel, names in sorted(by_stream.items(), key=lambda kv: -len(kv[1])):
    b = open(os.path.join(W, rel.replace('\\', '/')), 'rb').read()
    for a in strfile.assets(b, be=True, decode=True):
        if port_str.type_of(a) != T: continue
        k = port_str.key_of(a)
        if k in seen: continue
        first = a['shdr']['name'].split(b'\0')[0].decode('latin1', 'replace')
        got = pc.get(k, first)
        if not got: continue
        seen.add(k)
        open(os.path.join(out, '%03d_ps3.bin' % n), 'wb').write(a['data'])
        open(os.path.join(out, '%03d_pc.bin' % n), 'wb').write(got[1])
        open(os.path.join(out, '%03d_name.txt' % n), 'w').write(port_str.name_of(a))
        n += 1
        if n >= N: break
    if n >= N: break
print(T, 'pairs', n)
