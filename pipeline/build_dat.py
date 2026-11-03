"""Resumable BIGH writer for the Severed test package. usage: build_dat.py DEST [budget_s]"""
import os, sys, struct, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import toc
from bigh import x65599
W = os.path.expanduser('~/weller1'); dest = sys.argv[1]; budget = float(sys.argv[2]) if len(sys.argv) > 2 else 150
part = dest + '.part'; state_f = 'build_state.json'
if not os.path.exists(state_f):
    # entries: (dat name, source file)
    os.makedirs('toc', exist_ok=True)
    ents = []
    for nm in ('pdlc1_ch01_mng.toc', 'pdlc1_ch01_mng_global.toc'):
        d = open(os.path.join(W, 'pdlc1_ch01_mng', nm), 'rb').read()
        pc = toc.to_pc(d); ok, bad = toc.check(pc); assert ok, bad
        open(os.path.join('toc', nm), 'wb').write(pc)
        ents.append(('pdlc1_ch01_mng\\' + nm, os.path.join('toc', nm)))
    for dp, dn, fn in os.walk('out'):
        for f in fn:
            rel = os.path.relpath(os.path.join(dp, f), 'out')
            name = rel.replace('/', '\\')
            if name.lower().startswith('global_assets\\'):
                continue                      # keep the PC game's own global_assets_global.str
            ents.append((name, os.path.join(dp, f)))
    items = sorted(((x65599(n), n, p, os.path.getsize(p)) for n, p in ents), key=lambda t: t[0])
    assert len({h for h, *_ in items}) == len(items), 'hash collision'
    hsz = 16 + 12 * len(items) + 8
    off = (hsz + 0x7FF) & ~0x7FF
    index = []
    for h, n, p, sz in items:
        index.append([off, sz, h, n, p]); off = (off + sz + 0x7FF) & ~0x7FF
    total = off
    hdr = bytearray(b'BIGH' + struct.pack('<I', total) + struct.pack('>II', len(items), hsz))
    for o, s, h, n, p in index: hdr += struct.pack('>III', o, s, h)
    hdr += bytes.fromhex('4c32383315050000')
    hdr += b'\0' * (index[0][0] - len(hdr))
    with open(part, 'wb') as f: f.write(hdr)
    json.dump({'index': index, 'next': 0, 'total': total}, open(state_f, 'w'))
    with open('manifest.txt', 'w') as m:
        for o, s, h, n, p in index: m.write('0x%08X %10d %10d %s\n' % (h, o, s, n))
st = json.load(open(state_f)); t0 = time.time()
with open(part, 'r+b') as f:
    while st['next'] < len(st['index']) and time.time() - t0 < budget:
        o, s, h, n, p = st['index'][st['next']]
        f.seek(o); f.write(open(p, 'rb').read())
        nxt = st['index'][st['next'] + 1][0] if st['next'] + 1 < len(st['index']) else st['total']
        pad = nxt - (o + s)
        if pad: f.write(b'\0' * pad)
        st['next'] += 1
        json.dump(st, open(state_f, 'w'))
done = st['next'] == len(st['index'])
if done:
    assert os.path.getsize(part) == st['total'], (os.path.getsize(part), st['total'])
    os.replace(part, dest)
print('entries %d/%d, %.0f MB written, %s' % (st['next'], len(st['index']), os.path.getsize(dest if done else part) / 1e6, 'COMPLETE' if done else 'in progress'))
