import os, sys, collections, importlib, struct
mod = importlib.import_module(sys.argv[1]); D = 'pairs/Mesh'; N = int(sys.argv[2]) if len(sys.argv) > 2 else 300
c = collections.Counter(); ctx = collections.Counter(); ex = {}
for i in range(N):
    a = open('%s/%d.ps3' % (D, i), 'rb').read(); b = open('%s/%d.pc' % (D, i), 'rb').read()
    U = lambda o: struct.unpack_from('>I', a, o)[0]; V = lambda o: struct.unpack_from('<I', b, o)[0]
    try: o = mod.convert(a)
    except Exception as e: c['err'] += 1; ex.setdefault('err', (i, repr(e)[:80])); continue
    ibd = U(0x6C); ib_off = U(ibd + 12)
    W_ = lambda o_: struct.unpack_from('<I', o, o_)[0]
    myend = (W_(ibd + 12) + W_(ibd) + 15) & ~15; pcend = (V(ibd + 12) + V(ibd) + 15) & ~15
    ign = set()
    nd, dr = U(0x34), U(0x50)
    for k in range(nd):
        for f in (0x30, 0x34, 0x3C): ign.add(dr + 0xC0 * k + f)
    ign |= {0x0C, 0x9C, ibd, ibd + 4}
    bad = 0
    for k in range(0, ib_off, 4):
        if k in ign or o[k:k + 4] == b[k:k + 4]: continue
        bad += 1
        # classify relative to draw record
        if dr <= k < dr + 0xC0 * nd: key = 'rec+%x' % ((k - dr) % 0xC0)
        else: key = 'hdr+%x' % k if k < 0x200 else 'pre-ib'
        p, q = a[k:k + 4], b[k:k + 4]
        kind = 'W' if p[::-1] == q else 'H' if p[1::-1] + p[:1:-1] == q else 'S' if p == q else 'X'
        ctx[(key, kind)] += 1; ex.setdefault((key, kind), (i, hex(k), p.hex(), o[k:k+4].hex(), q.hex()))
    t1, t2 = o[myend:], b[pcend:]
    if len(t1) != len(t2): c['tail-size'] += 1; ex.setdefault('tail', (i, len(t1), len(t2)))
    else:
        tb = sum(1 for k in range(0, len(t1) & ~3, 4) if t1[k:k + 4] != t2[k:k + 4])
        if tb: c['tail-bad-files'] += 1; ex.setdefault('tailbad', (i, tb, hex(myend))); 
    c['files'] += 1; c['head-ok'] += bad == 0
print(dict(c)); print(ex.get('err'), ex.get('tail'), ex.get('tailbad'))
for k, v in ctx.most_common(25): print(v, k, ex[k])
