import re
def anchors(a):
    return {m.start(): m.group(1).decode('latin1') for m in re.finditer(rb'####(.{4})', a, re.S)}
def names(d):
    """word offsets of '#'-padded name fields and the name after them (bytes as is)"""
    S = set()
    for m in re.finditer(rb'#{4,}(?!\.[a-z]{3})[\x20-\x7e]*\x00', d):
        for o in range(m.start() & ~3, m.end() - 1, 4): S.add(o)
    for m in re.finditer(rb'(?<![\x20-\x7e])[\x20-\x7e]{6,}\x00', d):
        if re.search(rb'[a-z_]{3}', m.group(0)) and not m.group(0).startswith(b'#'):
            for o in range(m.start() & ~3, m.end() - 1, 4): S.add(o)
    return S
def shape(p):
    hi, lo = int.from_bytes(p[:2], 'big'), int.from_bytes(p[2:], 'big')
    if p[1:] == b'\0\0\0': return 'b'
    if lo == 0: return 'l0'
    if hi == 0: return 'h0'
    if hi < 0x1000 and lo < 0x1000: return 'bs'
    return 'o'
