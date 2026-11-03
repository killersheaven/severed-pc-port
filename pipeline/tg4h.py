"""PS3 (big-endian) tg4h texture header -> PC tg4h.
Learned from 24 PS3/PC pairs (all exact). Header versions 3 and 4 differ only in
ID length (3 vs 4 u32 words at 0x30)."""
def _s32(b, o): return b[o:o+4][::-1]
def convert(p):
    p = bytes(p); out = bytearray(p)
    ver = p[0x27]
    if ver not in (3, 4):
        raise NotImplementedError('tg4h version %d' % ver)
    idwords = 3 if ver == 3 else 4
    for o in (0x00, 0x08, 0x0C, 0x10, 0x14, 0x18, 0x1C, 0x28, 0x2C):
        out[o:o+4] = _s32(p, o)
    for k in range(idwords):
        o = 0x30 + 4*k; out[o:o+4] = _s32(p, o)
    out[0x05] = 0x00                      # platform/endian flag: 1 on PS3, 0 on PC
    out[0x06:0x08] = p[0x06:0x08][::-1]
    out[0x20:0x22] = p[0x20:0x22][::-1]   # width
    out[0x22:0x24] = p[0x22:0x24][::-1]   # height
    g = 0x30 + 4*idwords                  # start of packed string-offset block
    i = p.find(b'DXT', g)
    if i < 0:
        raise NotImplementedError('non-DXT texture')
    f = i - 5                             # flag byte, then u32 data size, then FourCC
    out[g:f] = p[g+3:f] + b'\0\0\0'       # 3 pad bytes move from the front to the back
    out[f+1:i] = _s32(p, f+1)
    return bytes(out)
