import mopp
L = dict(mopp.LEN); L[0x70] = 5
def walk(code, fix=None):
    """walk with terminal tracking. 0x70 = chunk jump (u32 BE absolute target). If fix is a bytearray, rewrite
    each reachable 0x70 as 0x07 (24-bit forward relative jump). Returns (bad ops, terminal ids set, n70, problems)."""
    import collections
    bad = collections.Counter(); terms = set(); n70 = 0; probs = []
    seen = set(); stack = [(0, 0)]
    while stack:
        i, t = stack.pop()
        while 0 <= i < len(code) and (i, t) not in seen:
            seen.add((i, t)); op = code[i]
            if op not in L: bad[op] += 1; break
            if op == 0x00: break
            if op == 0x70:
                tgt = int.from_bytes(code[i+1:i+5], 'big'); n70 += 1
                rel = tgt - (i + 4)
                if not (0 <= rel < 1 << 24) or tgt >= len(code): probs.append((i, tgt)); break
                if fix is not None: fix[i:i+4] = bytes([0x07]) + rel.to_bytes(3, 'big')
                i = tgt; continue
            if op == 0x05: i += 2 + code[i+1]; continue
            if op == 0x06: i += 3 + (code[i+1] << 8 | code[i+2]); continue
            if op == 0x07: i += 4 + (code[i+1] << 16 | code[i+2] << 8 | code[i+3]); continue
            if op == 0x09: t += code[i+1]; i += 2; continue
            if op == 0x0a: t += code[i+1] << 8 | code[i+2]; i += 3; continue
            if op == 0x0b: t = int.from_bytes(code[i+1:i+5], 'big'); i += 5; continue
            if 0x10 <= op <= 0x1c: stack.append((i + 4 + code[i+3], t)); i += 4; continue
            if 0x20 <= op <= 0x22: stack.append((i + 3 + code[i+2], t)); i += 3; continue
            if 0x23 <= op <= 0x25:
                stack.append((i + 7 + (code[i+5] << 8 | code[i+6]), t)); i = i + 7 + (code[i+3] << 8 | code[i+4]); continue
            if 0x30 <= op <= 0x4f: terms.add(t + op - 0x30); break
            if op == 0x50: terms.add(t + code[i+1]); break
            if op == 0x51: terms.add(t + (code[i+1] << 8 | code[i+2])); break
            if op == 0x52: terms.add(t + int.from_bytes(code[i+1:i+4], 'big')); break
            if op == 0x53: terms.add(t + int.from_bytes(code[i+1:i+5], 'big')); break
            i += L[op]
    return bad, terms, n70, probs
