def shape(p):
    hi, lo = int.from_bytes(p[:2], 'big'), int.from_bytes(p[2:], 'big')
    if p[1:] == b'\0\0\0': return 'b'
    if lo == 0: return 'l0'
    if hi == 0: return 'h0'
    if hi < 0x1000 and lo < 0x1000: return 'bs'
    return 'o'
