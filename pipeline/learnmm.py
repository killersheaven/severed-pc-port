import os, re, collections, struct, json
from crack import x65599
D = 'pairs/MetaModel'
TYPES = ['modelpart','model','mesh','xform','vfx','dismemberstate','vfxpart','navmodel','state','collisionmodel','visibilitymask',
 'collisionhavok4part','hkx','generatenav','navpart','visibility','metamodelpart','dismembervfxpart','destructiblestate','clientspace',
 'health','transform','attachpointtransform','ragdollmodel','tkpart','scriptableprop','genericcollisionpart','ragdollpart','geometry',
 'damageableprop','attackpartnpc','script_predicate','textvfxpart','velocityhavok4part','necrovfx','destructible','weakmetamodelpart',
 'singlecollision','necrovisionvfxpart','gundrop_predicate']
A = {struct.pack('>I', x65599(t.encode())): t for t in TYPES}
for tag in (b'UMTR', b'IN01', b'APMM'): A[tag] = tag.decode()
def cls(p, q):
    W = p[::-1]; H = p[1::-1] + p[:1:-1]
    if W == H: return None
    return 'W' if W == q else 'H' if H == q else 'S' if p == q else 'X'
stat = collections.defaultdict(collections.Counter)
files = [f for f in os.listdir(D) if f.endswith('.ps3')]
for f in files:
    a = open(D + '/' + f, 'rb').read(); b = open(D + '/' + f[:-4] + '.pc', 'rb').read()
    last = None
    for o in range(0x68, len(a) & ~3, 4):
        w = a[o:o + 4]
        if w in A: last = (A[w], o); continue
        c = cls(w, b[o:o + 4])
        if c in ('H', 'W') and last:
            stat[(last[0], o - last[1])][c] += 1
good = {}; bad = []
for k, v in sorted(stat.items()):
    if v['H'] and v['W'] == 0: good[k] = v['H']
    elif v['H'] and v['W']: bad.append((k, dict(v)))
print('pure H', len(good)); print(good)
print('mixed', len(bad));
for x in bad: print(x)
