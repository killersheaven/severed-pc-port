"""Split the __data__ section of a Havok packfile into regions (objects and the arrays they point to)."""
import hkpack, bisect
def regions(d, be):
    S = hkpack.parse(d, be)
    di = [i for i, s in enumerate(S) if s['name'] == '__data__'][0]; ds = S[di]
    loc, glo, vir = hkpack.fixups(d, be, ds)
    size = ds['lf']
    objs = {src: hkpack.classname(d, S, sec, c) for src, sec, c in vir}
    ptr_to = {}                                   # dst -> first src pointing at it
    for src, dst in loc: ptr_to.setdefault(dst, src)
    for src, sec, dst in glo:
        if sec == di: ptr_to.setdefault(dst, src)
    starts = sorted(set(objs) | {x for x in ptr_to if x < size})
    ends = starts[1:] + [size]
    reg = {}
    for st, en in zip(starts, ends): reg[st] = [en, None]
    for st in starts:
        if st in objs: reg[st][1] = ('O', objs[st])
    def key_of(st, depth=0):
        if reg[st][1] is not None or depth > 8: return reg[st][1]
        src = ptr_to.get(st)
        if src is None: return None
        i = bisect.bisect_right(starts, src) - 1
        if i < 0: return None
        ost = starts[i]; ok = key_of(ost, depth + 1)
        reg[st][1] = ('A', ok, src - ost) if ok else None
        return reg[st][1]
    for st in starts: key_of(st)
    return ds, [(st, reg[st][0], reg[st][1]) for st in starts], (loc, glo, vir), S
def kstr(k):
    if k is None: return 'none'
    if k[0] == 'O': return 'O:' + k[1]
    return 'A[' + kstr(k[1]) + '+%d]' % k[2]
