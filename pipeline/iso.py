"""Minimal ISO9660 reader (multi-extent aware) for decrypted PS3 disc images."""
import struct, sys
class ISO:
    def __init__(self, path):
        self.f = open(path, 'rb')
        pvd = self._sec(16)
        assert pvd[1:6] == b'CD001'
        self.root = self._rec(pvd[156:156 + 34])
    def _sec(self, lba, n=1):
        self.f.seek(lba * 2048); return self.f.read(2048 * n)
    def _rec(self, r):
        ln = r[0]; lba = struct.unpack('<I', r[2:6])[0]; size = struct.unpack('<I', r[10:14])[0]
        flags = r[25]; nl = r[32]; name = r[33:33 + nl]
        return dict(lba=lba, size=size, flags=flags, name=name)
    def listdir(self, d):
        out = []; data = self._sec(d['lba'], (d['size'] + 2047) // 2048); p = 0
        while p < len(data):
            ln = data[p]
            if ln == 0:
                p = (p // 2048 + 1) * 2048; continue
            r = self._rec(data[p:p + ln]); p += ln
            if r['name'] in (b'\x00', b'\x01'): continue
            nm = r['name'].decode('latin1').split(';')[0]
            if out and out[-1][0] == nm and (out[-1][2] & 0x80):   # multi-extent continuation
                prev = out[-1]; out[-1] = (nm, prev[1] + [(r['lba'], r['size'])], r['flags']); continue
            out.append((nm, [(r['lba'], r['size'])], r['flags']))
        return [(nm, ext, fl) for nm, ext, fl in out]
    def walk(self, d=None, prefix=''):
        d = d or self.root
        for nm, ext, fl in self.listdir(d):
            if fl & 2:
                yield from self.walk(dict(lba=ext[0][0], size=ext[0][1]), prefix + nm + '/')
            else:
                yield prefix + nm, ext
    def read(self, ext):
        out = bytearray()
        for lba, size in ext:
            self.f.seek(lba * 2048); out += self.f.read(size)
        return bytes(out)
if __name__ == '__main__':
    iso = ISO(sys.argv[1])
    for p, ext in iso.walk():
        print(sum(s for _, s in ext), p)
