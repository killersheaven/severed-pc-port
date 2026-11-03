"""Replace base-game PC collision copies (pc-name, different size) with Severed's own converted HKX in the
streams of the installed DAT. Writes patched streams to patch_out/<rel> + patch.json."""
import os, sys, json, struct
sys.argv += ['x']
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import port_str, strfile, fmt_hkx, hkregions, hkfix, mopp2
from refpack import refpack_decompress
from bigh import x65599
G = os.path.expanduser('~/mnt/Dead Space 2'); W = os.path.expanduser('~/weller1')
DAT = G + '/DS2DAT3.DAT'
pc = port_str.PCAssets(G, os.path.join(G, 'pc_assets.csv'))
rows = [r for r in json.load(open('hkmod.json'))['rows'] if r[3] == 'pc-name' and r[6] == -1]
f = open(DAT, 'rb'); h = f.read(16); n = struct.unpack('>I', h[8:12])[0]
idx = {hh: (o, s) for o, s, hh in (struct.unpack('>III', f.read(12)) for _ in range(n))}

def fix_mopp(d):
    d = bytearray(d); ds, regs, fx, S = hkregions.regions(bytes(d), False); base = ds['start']; nj = 0
    for s, en, k in regs:
        if hkregions.kstr(k) == 'A[O:hkpMoppCode+32]':
            code = bytes(d[base + s:base + en])
            if 0x70 in code:
                new, j, errs, nb, nr = hkfix.relayout(code)
                assert not errs and nr == nb, errs[:3]
                d[base + s:base + en] = new; nj += j
    for s, en, k in regs:
        if hkregions.kstr(k) == 'A[O:hkpMoppCode+32]':
            b, t, n70, p = mopp2.walk(bytes(d[base + s:base + en])); assert not b and n70 == 0
    return bytes(d), nj

by_stream = {}
for r in rows: by_stream.setdefault(r[1], []).append(r[2])
report = []
for rel, names in sorted(by_stream.items()):
    hh = x65599(rel.replace('/', '\\'))
    o, s = idx[hh]; f.seek(o); sb = f.read(s)
    items = [(a['hdr_raw'], a['data']) for a in strfile.assets(sb, be=False, decode=True)]
    ps3 = {port_str.name_of(a): a for a in strfile.assets(open(os.path.join(W, rel), 'rb').read(), be=True, decode=False)}
    for nm in names:
        a = ps3[nm]
        d3 = b''.join(x if k == 'raw' else refpack_decompress(x) for k, x in a['parts'])[:a['shdr']['usize']]
        got = pc.get_by_name('HKX', nm)
        hits = [j for j, (hd, dd) in enumerate(items) if dd == got[1]]
        assert len(hits) >= 1, (rel, nm)
        new, nj = fix_mopp(fmt_hkx.convert(d3))
        for j in hits:
            hd = bytearray(items[j][0]); struct.pack_into('<I', hd, 40, len(new))
            items[j] = (bytes(hd), new)
        report.append([rel, nm, len(got[1]), len(new), nj, len(hits)])
    out = port_str.write_pc_str(items, sb[8:12])
    dst = os.path.join('patch_out', rel); os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, 'wb').write(out)
    # sanity: re-read
    chk = strfile.assets(out, be=False, decode=True)
    assert len(chk) == len(items) and all(c['data'] == it[1] for c, it in zip(chk, items))
json.dump(report, open('patch.json', 'w'), indent=0)
for r in report: print(r)
