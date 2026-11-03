"""Validate a PS3->PC converter on every base-game pair of one asset type.
usage: validate.py TYPE module [max_streams]"""
import os, sys, csv, collections, importlib, struct, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import strfile, port_str
from ps3base import PS3Base
T, mod = sys.argv[1], importlib.import_module(sys.argv[2]); maxs = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3].isdigit() else 10**9
IGNORE = [int(x, 16) for x in os.environ.get('IGNORE', '').split(',') if x]
G = os.path.expanduser('~/mnt/Dead Space 2')
streams = collections.OrderedDict()
for r in csv.DictReader(open(os.path.join(G, 'pc_asset_index.csv'), encoding='utf-8-sig')):
    if r['ext'] == T:
        streams.setdefault((r['dat'], int(r['entry_offset']), int(r['entry_size']), int(r['entry_hash'], 16)), 0)
        streams[(r['dat'], int(r['entry_offset']), int(r['entry_size']), int(r['entry_hash'], 16))] += 1
b = PS3Base(); ok = bad = miss = 0; badlist = []; t0 = time.time(); seen = set()
for k, (dat, off, size, h) in enumerate(list(streams)[:maxs]):
    if h not in b.index: miss += 1; continue
    f = open(os.path.join(G, 'DS2DAT%s.DAT' % dat), 'rb'); f.seek(off); pc = f.read(size)
    ps3 = b.read(h)
    P = {(port_str.name_of(a)).replace('.ps3', '.win'): a['data'] for a in strfile.assets(ps3, be=True, decode=True) if port_str.type_of(a) == T}
    for a in strfile.assets(pc, be=False, decode=True):
        if port_str.type_of(a) != T: continue
        nm = port_str.name_of(a)
        if nm not in P or nm in seen: continue
        seen.add(nm)
        try:
            o = mod.convert(P[nm])
        except Exception as e:
            o = repr(e)
        if isinstance(o, bytes) and IGNORE and len(o) == len(a['data']):
            o = bytearray(o); [o.__setitem__(slice(i, i + 4), a['data'][i:i + 4]) for i in IGNORE]; o = bytes(o)
        if os.environ.get('SAMESIZE') and len(P[nm]) != len(a['data']): diffsize = globals().get('diffsize', 0) + 1; globals()['diffsize'] = diffsize; continue  # SAMESIZE
        if o == a['data']: ok += 1
        else:
            bad += 1
            if bad <= 3 and isinstance(o, bytes):
                open('bad%d.ps3' % bad, 'wb').write(P[nm]); open('bad%d.pc' % bad, 'wb').write(a['data'])  # DUMPBAD
            if len(badlist) < 8:
                first = next((i for i in range(min(len(o), len(a['data']))) if o[i] != a['data'][i]), None) if isinstance(o, bytes) else o
                badlist.append((nm, len(P[nm]), len(a['data']), first))
print('size-differs', globals().get('diffsize', 0)); print('%s: %d identical, %d different, %d streams missing on PS3 (%.0fs)' % (T, ok, bad, miss, time.time() - t0))
for x in badlist: print('  BAD', x)
