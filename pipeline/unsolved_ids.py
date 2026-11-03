import os, json, collections, strfile, port_str
W = os.path.expanduser('~/mnt/weller1')
m = json.load(open('idmap_state.json'))['map']
c = collections.Counter(); bts = collections.Counter(); names = {}
for dp, dn, fn in os.walk(W):
    if 'clod' in dp: continue
    for f in fn:
        if not f.endswith('.str'): continue
        for a in strfile.assets(open(os.path.join(dp, f), 'rb').read(), be=True, decode=False):
            t = port_str.type_of(a)
            if t not in ('Mesh', 'MeshVolatile', 'MetaModel', 'Material', 'HKX', 'VFX', 'SBK', 'BNK', 'RCB'): continue
            ids = a['shdr']['f'][1:5]
            k = 'mapped' if '%08x' % ids[0] in m else 'unique'
            c[(t, k)] += 1
for k, v in sorted(c.items()): print(k, v)
