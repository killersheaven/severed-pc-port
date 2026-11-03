"""Dead Space 2 level TOC (.toc) reader and console -> PC converter.

Layout (all u32 unless noted; PC little-endian, PS3/360 big-endian; strings never swapped):
  0x00 magic 0x287BBA9C (PC bytes 28 7B BA 9C, console 9C BA 7B 28)
  0x04 version (0x0A)
  0x08 u16 nRecords   0x0A u16 nNames
  0x0C u16 nList  0x0E u16 (0)   0x10 namesOffset (hash table)   0x14 unknown (swap)
  0x18 4 flag bytes (not swapped)
  0x1C (nRecords-1) records of 20 bytes: u32 a, u32 listPtr, u32 namePtr, u32 size, 4 flag bytes
       then 2 u32
  namesOffset: nNames x (u32 id, u32 stringOffset). Entry 0 = the package's own _global stream (id 0), then the
               package's streams sorted by id, then streams of other packages (id 0, e.g. global_assets_global). The id is NOT x65599/CRC32/FNV/djb2 of the name and not a content checksum
               (PS3 and 360 .add files list the same ids for differently compressed streams); the .add file lists the
               same id per stream. Conversion keeps it unchanged (byte-swapped only).
  record listPtr -> into the offset list region, namePtr -> a names-table entry, size = memory size (not file size)
  then nList x u32 offsets
  then NUL-terminated names (stream paths without ".str") and zero padding.
Structure verified on PC ds_2.toc, ds_2_global.toc, frontend.toc, ch01_hos.toc and PS3 pdlc1_ch01_mng.toc.
"""
import struct
import sys

MAGIC_PC = b'\x28\x7B\xBA\x9C'
MAGIC_CONSOLE = b'\x9C\xBA\x7B\x28'


def x65599(s):
    h = 0
    for c in s.encode('latin1'):
        h = (h * 65599 + c) & 0xFFFFFFFF
    return h


def layout(d):
    """Return (endian, header dict, list of (offset, kind)) where kind is 'u32', 'u16', 'raw4'."""
    if d[:4] == MAGIC_PC:
        E = '<'
    elif d[:4] == MAGIC_CONSOLE:
        E = '>'
    else:
        raise ValueError('not a TOC (magic %r)' % d[:4])
    ver, n_rec, n_names, n_list, pad, names_off, unk = struct.unpack_from(E + 'IHHHHII', d, 4)
    fields = [(0x04, 'u32'), (0x08, 'u16'), (0x0A, 'u16'), (0x0C, 'u16'), (0x0E, 'u16'), (0x10, 'u32'), (0x14, 'u32'), (0x18, 'raw4')]
    p = 0x1C
    for _ in range(n_rec - 1):
        fields += [(p, 'u32'), (p + 4, 'u32'), (p + 8, 'u32'), (p + 12, 'u32'), (p + 16, 'raw4')]
        p += 20
    fields += [(p, 'u32'), (p + 4, 'u32')]
    p += 8
    if p != names_off:
        raise ValueError('records end at 0x%X but names table is at 0x%X' % (p, names_off))
    for _ in range(n_names):
        fields += [(p, 'u32'), (p + 4, 'u32')]
        p += 8
    list_off = p
    for _ in range(n_list):
        fields += [(p, 'u32')]
        p += 4
    hdr = dict(endian=E, version=ver, records=n_rec, names=n_names, list=n_list,
               names_off=names_off, list_off=list_off, strings_off=p, unknown=unk)
    return hdr, fields


def names(d):
    hdr, _ = layout(d)
    E = hdr['endian']
    out = []
    for i in range(hdr['names']):
        h, off = struct.unpack_from(E + 'II', d, hdr['names_off'] + 8 * i)
        s = d[off:d.index(b'\0', off)].decode('latin1')
        out.append((h, off, s))
    return hdr, out


def check(d):
    """Structural check: every pointer lands where it should. Returns (ok, problems)."""
    hdr, ns = names(d)
    E = hdr['endian']
    bad = []
    so = hdr['strings_off']
    for i, (h, off, s) in enumerate(ns):
        if not (so <= off < len(d)) or (off > so and d[off - 1] != 0) or not s:
            bad.append('name %d offset 0x%X not a string start' % (i, off))
    ids = [h for h, _, _ in ns if h]
    if ids != sorted(ids):
        bad.append('non-zero ids not sorted')
    lo, hi = hdr['list_off'], hdr['strings_off']
    for k in range(hdr['list']):
        v = struct.unpack_from(E + 'I', d, lo + 4 * k)[0]
        if not (v < len(d)):
            bad.append('list entry %d -> 0x%X out of file' % (k, v))
    p = 0x1C
    for r in range(hdr['records'] - 1):
        a, lp, np_, size = struct.unpack_from(E + 'IIII', d, p)
        if not (lo <= lp <= hi):
            bad.append('record %d listPtr 0x%X outside list 0x%X-0x%X' % (r, lp, lo, hi))
        if not (hdr['names_off'] <= np_ < lo and (np_ - hdr['names_off']) % 8 == 0):
            bad.append('record %d namePtr 0x%X not a names entry' % (r, np_))
        p += 20
    return not bad, bad


def to_pc(d):
    if d[:4] == MAGIC_PC:
        return bytes(d)
    _, fields = layout(d)
    out = bytearray(d)
    out[0:4] = MAGIC_PC
    for off, kind in fields:
        if kind == 'u32':
            out[off:off + 4] = d[off:off + 4][::-1]
        elif kind == 'u16':
            out[off:off + 2] = d[off:off + 2][::-1]
    return bytes(out)


if __name__ == '__main__':
    for path in sys.argv[1:]:
        d = open(path, 'rb').read()
        hdr, ns = names(d)
        ok, bad = check(d)
        print('%s: %s, %d records, %d names, %d list, names@0x%X strings@0x%X, structure %s'
              % (path, 'PC' if hdr['endian'] == '<' else 'console', hdr['records'], hdr['names'], hdr['list'],
                 hdr['names_off'], hdr['strings_off'], 'OK' if ok else 'FAILED %s' % bad[:3]))
