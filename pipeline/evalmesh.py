import os, sys, collections, importlib
mod = importlib.import_module(sys.argv[1]); D = 'pairs/' + sys.argv[2]; N = int(sys.argv[3]) if len(sys.argv) > 3 else 400
ok = szok = nf = 0; c = collections.Counter(); first = []
for i in range(N):
    if not os.path.exists('%s/%d.ps3' % (D, i)): break
    a = open('%s/%d.ps3' % (D, i), 'rb').read(); b = open('%s/%d.pc' % (D, i), 'rb').read(); nf += 1
    try: o = mod.convert(a)
    except Exception as e: c['err ' + repr(e)[:60]] += 1; continue
    if len(o) != len(b): c['size'] += 1; first.append((i, 'size', len(a), len(o), len(b))); continue
    szok += 1
    bad = [k for k in range(0, len(b) & ~3, 4) if o[k:k + 4] != b[k:k + 4]]
    if not bad: ok += 1
    else: first.append((i, len(bad), hex(bad[0])))
print(nf, 'files; size ok', szok, 'exact', ok, dict(c))
print(first[:15])
