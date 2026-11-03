import sys, collections, importlib
T = sys.argv[1]; mod = importlib.import_module(sys.argv[2]); HOLD = '--holdout' in sys.argv
c = collections.Counter()
for l in open('pairs/%s/names.txt' % T):
    i, n = l.split(' ', 1); i = int(i)
    if HOLD and i % 5: continue
    a = open('pairs/%s/%d.ps3' % (T, i), 'rb').read(); b = open('pairs/%s/%d.pc' % (T, i), 'rb').read()
    if len(a) != len(b): continue
    o = mod.convert(a); nb = sum(1 for k in range(0, len(b), 4) if o[k:k + 4] != b[k:k + 4])
    c['exact' if nb == 0 else 'diff'] += 1; c['words'] += nb
print(dict(c))
