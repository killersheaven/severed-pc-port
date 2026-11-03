"""Which Severed HKX differ from the PC copy we ship? Convert Severed's PS3 HKX (fmt_hkx) and compare with the PC
asset found by key (port_str step 1) or by name (step 2). Resumable -> hkmod.json"""
import os, sys, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import port_str, strfile, fmt_hkx
from refpack import refpack_decompress
G = os.path.expanduser('~/mnt/Dead Space 2'); W = os.path.expanduser('~/weller1')
streams = sorted(os.path.relpath(os.path.join(dp, f), W) for dp, dn, fn in os.walk(W) if not dp.startswith(os.path.join(W, 'clod')) for f in fn if f.lower().endswith('.str'))
st = json.load(open('hkmod.json')) if os.path.exists('hkmod.json') else {'next': 0, 'rows': []}
pc = port_str.PCAssets(G, os.path.join(G, 'pc_assets.csv')); t0 = time.time()
while st['next'] < len(streams) and time.time() - t0 < 140:
    rel = streams[st['next']]; b = open(os.path.join(W, rel), 'rb').read()
    for a in strfile.assets(b, be=True, decode=False):
        if port_str.type_of(a) != 'HKX': continue
        d = b''.join(x if k == 'raw' else refpack_decompress(x) for k, x in a['parts'])[:a['shdr']['usize']]
        nm = port_str.name_of(a); first = a['shdr']['name'].split(b'\0')[0].decode('latin1', 'replace')
        got = pc.get(port_str.key_of(a), first); how = 'pc'
        if not got: got = pc.get_by_name('HKX', nm); how = 'pc-name'
        if not got: continue
        try: conv = fmt_hkx.convert(d)
        except Exception as e: conv = b''
        p = got[1]
        nd = sum(x != y for x, y in zip(conv, p)) if len(conv) == len(p) else -1
        st['rows'].append([st['next'], rel, nm, how, len(d), len(p), nd])
    st['next'] += 1
json.dump(st, open('hkmod.json', 'w'))
print('streams %d/%d rows %d' % (st['next'], len(streams), len(st['rows'])))
