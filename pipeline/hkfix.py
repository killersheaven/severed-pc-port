"""Re-lay out PS3 chunked MOPP code for the PC MOPP machine (no chunk opcode 0x70, forward jumps only).
Blocks = code split at every chunk-jump target; DFS pre-order from block 0 (parent before children); every 0x70
<u32 BE absolute> becomes 0x07 <u24 BE forward relative> + 1 spare byte. Same size. usage: hkfix.py DAT [--write]"""
import json, collections, os, sys, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hkregions, mopp2
L = mopp2.L

def chunk_jumps(code, start, end):
    """walk one block; returns list of (pos, target) chunk jumps, and errors (relative moves leaving the block)"""
    jumps = []; errs = []; seen = set(); stack = [start]
    while stack:
        i = stack.pop()
        while True:
            if not (start <= i < end): errs.append(('leave', i)); break
            if i in seen: break
            seen.add(i); op = code[i]
            if op not in L: errs.append(('op', op, i)); break
            if op == 0: break
            if op == 0x70: jumps.append((i, int.from_bytes(code[i+1:i+5], 'big'))); break
            if op == 0x05: i += 2 + code[i+1]; continue
            if op == 0x06: i += 3 + (code[i+1] << 8 | code[i+2]); continue
            if op == 0x07: i += 4 + (code[i+1] << 16 | code[i+2] << 8 | code[i+3]); continue
            if 0x10 <= op <= 0x1c: stack.append(i + 4 + code[i+3]); i += 4; continue
            if 0x20 <= op <= 0x22: stack.append(i + 3 + code[i+2]); i += 3; continue
            if 0x23 <= op <= 0x25:
                stack.append(i + 7 + (code[i+5] << 8 | code[i+6])); i = i + 7 + (code[i+3] << 8 | code[i+4]); continue
            if 0x30 <= op <= 0x53: break
            i += L[op]
    return jumps, errs

def relayout(code):
    n = len(code)
    # discover blocks iteratively
    starts = {0}; changed = True
    while changed:
        changed = False
        ss = sorted(starts)
        for k, s in enumerate(ss):
            e = ss[k + 1] if k + 1 < len(ss) else n
            for p, t in chunk_jumps(code, s, e)[0]:
                if 0 <= t < n and t not in starts: starts.add(t); changed = True
    ss = sorted(starts); ends = {s: (ss[k + 1] if k + 1 < len(ss) else n) for k, s in enumerate(ss)}
    info = {s: chunk_jumps(code, s, ends[s]) for s in ss}
    errs = [e for s in ss for e in info[s][1]]
    order = []; placed = set(); stack = [0]
    while stack:                                     # DFS pre-order
        s = stack.pop()
        if s in placed: errs.append(('dag', s)); continue
        placed.add(s); order.append(s)
        for p, t in reversed(info[s][0]): stack.append(t)
    order += [s for s in ss if s not in placed]     # unreachable blocks keep their bytes, appended
    new = bytearray(); pos = {}
    for s in order: pos[s] = len(new); new += code[s:ends[s]]
    nj = 0
    for s in order:
        for p, t in info[s][0]:
            q = pos[s] + p - s; rel = pos[t] - (q + 4)
            if not (0 <= rel < 1 << 24): errs.append(('back', q, pos[t])); continue
            new[q:q + 4] = bytes([0x07]) + rel.to_bytes(3, 'big'); nj += 1
    assert len(new) == n
    return bytes(new), nj, errs, len(ss), len(placed)

if __name__ == '__main__':
    DAT, WRITE = sys.argv[1], '--write' in sys.argv
    ms = json.load(open('hkx.json')); cmp = json.load(open('cmp_hkx.json'))
    f = open(DAT, 'r+b' if WRITE else 'rb'); st = collections.Counter(); bad = []
    for i, m in enumerate(ms):
        if cmp.get(str(i)) == 'identical': continue
        d = b''
        for o, n in m['pieces']: f.seek(o); d += f.read(n)
        d = bytearray(d[:m['usize']])
        ds, regs, fx, S = hkregions.regions(bytes(d), False); base = ds['start']; ch = False
        for s_, en, k in regs:
            if hkregions.kstr(k) != 'A[O:hkpMoppCode+32]': continue
            code = bytes(d[base + s_:base + en])
            if 0x70 not in code: continue
            b0, t0, n70, _ = mopp2.walk(code)
            new, nj, errs, nb, nr = relayout(code)
            if not nj: continue
            b1, t1, n71, p1 = mopp2.walk(new)
            ok = not errs and not b1 and n71 == 0 and nr == nb
            st['mopp-ok' if ok else 'mopp-err'] += 1; st['jumps'] += nj
            if not ok and len(bad) < 5: bad.append((m['name'][-30:], errs[:3], dict(b1), n71, nb, nr))
            if ok:
                d[base + s_:base + en] = new; ch = True
        if ch:
            st['assets'] += 1
            if WRITE:
                pos = 0
                for o, n in m['pieces']:
                    take = min(n, len(d) - pos)
                    if take <= 0: break
                    f.seek(o); f.write(d[pos:pos + take]); pos += take
    print(dict(st)); print(bad)
