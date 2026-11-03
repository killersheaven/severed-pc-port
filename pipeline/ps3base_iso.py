"""PS3 base game (decrypted ISO) archive access: BIGFILE0-2.VIV are BIGH archives with the PC naming."""
import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from iso import ISO
from bigh import x65599
ISO_PATH = os.path.expanduser('~/mnt/Dead Space 2 (USA) (EnFrEs)/Dead Space 2 (USA) (En,Fr,Es).iso')

class PS3Base:
    def __init__(self, path=ISO_PATH):
        self.iso = ISO(path)
        files = dict(self.iso.walk())
        self.vivs = {}
        self.index = {}                      # hash -> (viv, offset, size); lowest VIV wins
        for n in range(3):
            ext = files['PS3_GAME/USRDIR/BIGFILE%d.VIV' % n]
            self.vivs[n] = ext
            h = self._read(ext, 0, 16)
            cnt, hsz = struct.unpack('>II', h[8:16])
            raw = self._read(ext, 16, 12 * cnt)
            for i in range(cnt):
                o, s, hh = struct.unpack_from('>III', raw, 12 * i)
                self.index.setdefault(hh, (n, o, s))
    def _read(self, ext, off, n):
        out = bytearray(); pos = 0
        for lba, size in ext:
            if off < pos + size and n > 0:
                a = max(off, pos); take = min(pos + size, off + n) - a
                self.iso.f.seek(lba * 2048 + (a - pos)); out += self.iso.f.read(take)
                n -= take; off = a + take
            pos += size
        return bytes(out)
    def has(self, name):
        return x65599(name) in self.index
    def read(self, name):
        h = x65599(name) if isinstance(name, str) else name
        n, o, s = self.index[h]
        return self._read(self.vivs[n], o, s)
if __name__ == '__main__':
    b = PS3Base()
    print('entries', len(b.index))
    for nm in sys.argv[1:]:
        print(nm, b.has(nm), b.index.get(x65599(nm)))
