"""Replace the SBK placeholders in the installed DS2DAT3 streams with Severed's own banks converted by fmt_sbk.
Resumable (state sbk_state.json). Patched streams -> patch_out/<rel>; report sbk_report.json.
usage: patch_sbk.py [--dry] [budget_seconds]"""
import os, sys, json, struct, time, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_argv = sys.argv[:]; sys.argv = [sys.argv[0], 'x']
import port_str, strfile, fmt_sbk
sys.argv = _argv
from bigh import x65599
G = os.path.expanduser('~/mnt/Dead Space 2'); W = os.path.expanduser('~/weller1')
DAT = G + '/DS2DAT3.DAT'
dry = '--dry' in sys.argv
budget = float([x for x in sys.argv[1:] if not x.startswith('--')][0]) if [x for x in sys.argv[1:] if not x.startswith('--')] else 150
SF = 'sbk_state.json'
f = open(DAT, 'rb'); h = f.read(16); n = struct.unpack('>I', h[8:12])[0]
idx = {hh: (o, s) for o, s, hh in (struct.unpack('>III', f.read(12)) for _ in range(n))}
if os.path.exists(SF): st = json.load(open(SF))
else:
    rels = sorted(os.path.relpath(p, W).replace('/', '\\') for p in glob.glob(W + '/**/*.str', recursive=True))
    st = {'rels': rels, 'next': 0, 'report': [], 'placeholder': None}
t0 = time.time()
while st['next'] < len(st['rels']) and time.time() - t0 < budget:
    rel = st['rels'][st['next']]; st['next'] += 1
    hh = x65599(rel)
    if hh not in idx: st['report'].append([rel, 'not-in-dat3', 0, 0, 0]); continue
    ps3raw = open(os.path.join(W, rel.replace('\\', '/')), 'rb').read()
    ps3 = [a for a in strfile.assets(ps3raw, be=True, decode=True) if port_str.type_of(a) == 'SBK']
    if not ps3: continue
    o, s = idx[hh]; f.seek(o); sb = f.read(s)
    pcs = strfile.assets(sb, be=False, decode=True)
    items = [(a['hdr_raw'], a['data']) for a in pcs]
    byname = {}
    for j, a in enumerate(pcs):
        if port_str.type_of(a) == 'SBK': byname.setdefault(port_str.name_of(a), []).append(j)
    nrep = nkeep = nfail = 0
    for a in ps3:
        nm = port_str.name_of(a)
        js = byname.get(nm) or byname.get(nm.replace('.ps3', '.win')) or []
        if not js: st['report'].append([rel, 'no-pc-item', nm, 0, 0]); continue
        cur = items[js[0]][1]
        if st['placeholder'] is None and len(cur) == 634: st['placeholder'] = cur.hex()
        if st['placeholder'] is None or cur.hex() != st['placeholder']:
            nkeep += 1; continue                      # not a placeholder (a real PC copy): leave it
        try:
            new = fmt_sbk.convert(a['data'])
        except Exception as e:
            nfail += 1; st['report'].append([rel, 'convert-fail', nm, str(e)[:80], 0]); continue
        for j in js:
            hd = bytearray(items[j][0]); struct.pack_into('<I', hd, 40, len(new)); items[j] = (bytes(hd), new)
        nrep += 1
    st['report'].append([rel, 'ok', nrep, nkeep, nfail])
    if nrep and not dry:
        out = port_str.write_pc_str(items, sb[8:12])
        chk = strfile.assets(out, be=False, decode=True)
        assert len(chk) == len(items) and all(c['data'] == it[1] for c, it in zip(chk, items)), rel
        dst = os.path.join('patch_out', rel.replace('\\', '/')); os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, 'wb').write(out)
    json.dump(st, open(SF, 'w'))
json.dump(st, open(SF, 'w'))
ok = [r for r in st['report'] if r[1] == 'ok']
print('streams %d/%d | with SBK %d | replaced %d kept %d failed %d | not in DAT3 %d | no pc item %d | %s' % (
    st['next'], len(st['rels']), len(ok), sum(r[2] for r in ok), sum(r[3] for r in ok), sum(r[4] for r in ok),
    sum(r[1] == 'not-in-dat3' for r in st['report']), sum(r[1] == 'no-pc-item' for r in st['report']),
    'COMPLETE' if st['next'] == len(st['rels']) else 'in progress'))
