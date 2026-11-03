import json, os, sys, time, struct, hashlib
st = json.load(open('repack_state.json')); vf = 'verify_state.json'
v = json.load(open(vf)) if os.path.exists(vf) else {'next': 0, 'bad': []}
dest = sys.argv[1]; budget = float(sys.argv[2]); t0 = time.time()
with open(dest, 'rb') as d:
    if v['next'] == 0:
        h = d.read(16); n = struct.unpack('>I', h[8:12])[0]
        assert struct.unpack('<I', h[4:8])[0] == os.path.getsize(dest) and n == len(st['index'])
        for k, e in enumerate(st['index']):
            assert struct.unpack('>III', d.read(12)) == (e[0], e[1], e[2]), k
    srcs = {}
    while v['next'] < len(st['index']) and time.time() - t0 < budget:
        o, s, hh, kind, p, so = st['index'][v['next']]
        if kind not in srcs: pass
        f = srcs.get(p) or open(p, 'rb'); srcs[p] = f
        d.seek(o); f.seek(so if kind == 'dat' else 0)
        left = s; ok = True
        while left:
            c = min(left, 32 << 20)
            if d.read(c) != f.read(c): ok = False; break
            left -= c
        if not ok: v['bad'].append(v['next'])
        v['next'] += 1; json.dump(v, open(vf, 'w'))
print('verified %d/%d, bad %s' % (v['next'], len(st['index']), v['bad']))
