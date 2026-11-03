"""New BIGH from an existing one, replacing entries by name with files from patch_out/. Resumable.
usage: repack_dat.py SRC DEST [budget]"""
import os, sys, struct, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bigh import x65599
src, dest = sys.argv[1], sys.argv[2]; budget = float(sys.argv[3]) if len(sys.argv) > 3 else 140
part = dest + '.part'; sf = 'repack_state.json'
if not os.path.exists(sf):
    f = open(src, 'rb'); h = f.read(16); n, hsz = struct.unpack('>II', h[8:16])
    old = [struct.unpack('>III', f.read(12)) for _ in range(n)]
    foot = f.read(8)
    rep = {}
    for dp, dn, fn in os.walk('patch_out'):
        for x in fn:
            p = os.path.join(dp, x); rep[x65599(os.path.relpath(p, 'patch_out').replace('/', '\\'))] = p
    assert all(hh in {e[2] for e in old} for hh in rep), 'patched name not in DAT'
    off = (16 + 12 * n + 8 + 0x7FF) & ~0x7FF; index = []
    for o, s, hh in sorted(old, key=lambda e: e[2]):
        if hh in rep: s2 = os.path.getsize(rep[hh]); index.append([off, s2, hh, 'file', rep[hh], 0])
        else: s2 = s; index.append([off, s2, hh, 'dat', src, o])
        off = (off + s2 + 0x7FF) & ~0x7FF
    hdr = bytearray(b'BIGH' + struct.pack('<I', off) + struct.pack('>II', n, hsz))
    for e in index: hdr += struct.pack('>III', e[0], e[1], e[2])
    hdr += foot; hdr += b'\0' * (index[0][0] - len(hdr))
    open(part, 'wb').write(hdr)
    json.dump({'index': index, 'next': 0, 'total': off}, open(sf, 'w'))
st = json.load(open(sf)); t0 = time.time()
with open(part, 'r+b') as f, open(src, 'rb') as g:
    while st['next'] < len(st['index']) and time.time() - t0 < budget:
        o, s, hh, kind, p, so = st['index'][st['next']]
        if kind == 'file': data = open(p, 'rb').read()
        else: g.seek(so); data = g.read(s)
        assert len(data) == s
        nxt = st['index'][st['next'] + 1][0] if st['next'] + 1 < len(st['index']) else st['total']
        f.seek(o); f.write(data + b'\0' * (nxt - o - s))
        st['next'] += 1; json.dump(st, open(sf, 'w'))
done = st['next'] == len(st['index'])
if done:
    assert os.path.getsize(part) == st['total']; os.replace(part, dest)
print('entries %d/%d %s' % (st['next'], len(st['index']), 'COMPLETE' if done else 'in progress'))
