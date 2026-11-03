"""VFX (.vfb) PS3 -> PC, component-aware. Rules keyed by (component tag, version, flags, offset in component)."""
import re, struct, json, os, collections
TAGRE = re.compile(rb'\.[a-z0-9]{3}')
def tags(d):
    out = []
    for o in range(0, len(d) - 12, 4):
        w = d[o:o + 4]
        if TAGRE.fullmatch(w):
            v, s = struct.unpack('>II', d[o + 4:o + 12])
            if v < 64 and s < 256: out.append((o, w.decode(), v, s))
    return out
def hashruns(d):
    """aligned starts of '####' runs (string / asset-ref anchors)"""
    out = []; o = 0; n = len(d) & ~3
    while o < n:
        if d[o:o + 4] == b'####':
            out.append(o)
            while o < n and d[o:o + 4] == b'####': o += 4
        else: o += 4
    return out
def keys(d):
    """per word offset: list of keys, most specific first"""
    T = tags(d); H = hashruns(d); K = {}; ti = -1; hi = -1
    for o in range(0, len(d) & ~3, 4):
        while ti + 1 < len(T) and T[ti + 1][0] <= o: ti += 1
        while hi + 1 < len(H) and H[hi + 1] <= o: hi += 1
        if ti < 0:
            K[o] = [('hdr', o)] if o < 0x54 else [('hent', (o - 0x54) % 0x24), ('hdr', o)]; continue
        t0, tg, v, s = T[ti]; r = o - t0
        ks = []
        if hi >= 0 and H[hi] >= t0:
            na = sum(1 for x in H[:hi + 1] if x >= t0)
            # end of this '#' run (start of the string text / id)
            e = H[hi]
            while d[e:e + 4] == b'####': e += 4
            ks += [(tg, v, s, 'a%d' % na, o - e), (tg, v, 'a%d' % na, o - e), (tg, 'a%d' % na, o - e)]
        ks += [(tg, v, s, r), (tg, v, r)]
        K[o] = ks
    for h in H:
        e = h
        while d[e:e + 4] == b'####': e += 4
        w = [d[e + 4 * i:e + 4 * i + 4] for i in range(4)]
        if len(w[2]) == 4 and w[0] == w[1] == w[2] and w[0] != b'\0\0\0\0':
            for i in range(4):
                if e + 4 * i in K: K[e + 4 * i] = [('id', i)]
    return K
PERM = {'W': (3, 2, 1, 0), 'B': (0, 1, 2, 3), 'H': (1, 0, 3, 2), 'bbS': (0, 1, 3, 2), 'Sbb': (1, 0, 2, 3)}
def acts(p, q):
    return {c for c, pm in PERM.items() if bytes(p[i] for i in pm) == q}
def apply(p, c):
    return bytes(p[i] for i in PERM[c])
STR = re.compile(rb'#{4,}[\x20-\x7e]*\x00?|(?<![\x20-\x7e])[\x20-\x7e]{3,}\x00')
def strwords(d):
    S = set()
    for m in STR.finditer(d):
        s = m.group(0)
        if s.startswith(b'####') or re.search(rb'[a-z_]{2}|\d\.\d', s):
            for o in range(m.start() & ~3, m.end(), 4): S.add(o)
    return S
def guess(p):
    if p in (b'####',) or all(0x20 <= x < 0x7f for x in p) and sum(97 <= x < 123 for x in p) >= 3: return 'B'
    return 'W'
class Model:
    def __init__(self, R=None): self.R = R or {}
    def learn(self, pairs):
        C = collections.defaultdict(collections.Counter)
        for ps3, pc in pairs:
            K = keys(ps3)
            for o, ks in K.items():
                a = acts(ps3[o:o + 4], pc[o:o + 4])
                if not a:
                    for k in ks: C[repr(k)]['X'] += 1
                elif len(a) < len(PERM):
                    for k in ks: C[repr(k)][frozenset(a)] += 1
        self.R = {}
        for k, c in C.items():
            tot = sum(c.values())
            best = None
            for act in ('W', 'B', 'H', 'Sbb', 'bbS'):
                agree = sum(n for st, n in c.items() if st != 'X' and act in st)
                if agree >= 0.98 * tot and (best is None or agree > best[1]): best = (act, agree)
            if best: self.R[k] = best[0]
        self.C = C
        return self
    def convert(self, d):
        n = len(d) & ~3; out = bytearray(d); K = keys(d)
        for o in range(0, n, 4):
            p = d[o:o + 4]; c = None
            for k in K[o]:
                c = self.R.get(repr(k))
                if c: break
            if c is None: c = 'B' if o in strwords(d) else guess(p)
            out[o:o + 4] = apply(p, c)
        return bytes(out)
