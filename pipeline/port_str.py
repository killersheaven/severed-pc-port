"""Port one Severed PS3 level stream (.str) to PC format.

For every asset (SHDR + payload) in the PS3 stream:
  1. shared with the PC game (same type + 4 SHDR IDs in pc_assets.csv)  -> PC's own header + payload, read from the DATs
  2. a solved type                                                   -> converted (container swap + payload rule)
  3. otherwise                                                       -> unsolved (reported; dropped or kept per --unsolved)
Output: a PC .str (little-endian ols3, 128 KB blocks, uncompressed SDAT) plus a per-asset report.

usage: port_str.py PS3.str OUT.str --game "<PC game dir>" [--index pc_assets.csv] [--unsolved drop|keep]
"""
import argparse
import collections
import csv
import os
import struct, json
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import strfile
import tg4h

BLOCK = 0x20000
TYPE_LH2 = 0x3596A436
TYPE_LUA = 0x35A3A798


# ------------------------------------------------------------------ payload rules (PS3 -> PC)
def lh2_to_pc(d):
    size, f2, ltab, kc, lc, z1, z2 = struct.unpack('>7I', d[4:32])
    n = kc + kc * lc
    out = bytearray(d[:4][::-1] + struct.pack('<7I', size, f2, ltab, kc, lc, z1, z2))
    out += struct.pack('<%dI' % n, *struct.unpack('>%dI' % n, d[32:32 + 4 * n]))
    out += d[32 + 4 * n:ltab]
    for q in range(ltab, size - 3, 4):
        w = d[q:q + 4]
        txt = 0x61 <= w[0] <= 0x7A and all(c == 0 or 0x61 <= c <= 0x7A for c in w)
        out += w if (txt or w == b'\0\0\0\0') else w[::-1]
    out += d[len(out):]
    return bytes(out)


import fmt_smb, fmt_simgroup, fmt_graph, fmt_nav, fmt_vardict, fmt_lighttoc, fmt_metamodel, fmt_material, fmt_mesh, fmt_hkx, fmt_vfx, fmt_bnk, fmt_rcb
RULES = {
    'tg4d': lambda d: d,          # pixel data identical PS3/PC (24/24 + 421 pairs)
    'tg4h': tg4h.convert,         # 170/170 headers, 24/24 exact vs PC
    'LUA': lambda d: d,           # bytecode identical
    'LH2': lh2_to_pc,
    'SMB': fmt_smb.convert,            # 167/167 base-game pairs identical
    'Graph': fmt_graph.convert,        # 122/122 identical
    'TOB': lambda d: b''.join(d[i:i + 4][::-1] for i in range(0, len(d) & ~3, 4)) + d[len(d) & ~3:],  # 501/501
    'NAV': fmt_nav.convert,            # 764/770 (+ checksum @0x34 kept)
    'VariableDictionary': fmt_vardict.convert,  # 128/128
    'LightTOC': fmt_lighttoc.convert,  # 554/554
    # 'VFX': fmt_vfx.convert,  # disabled for crash isolation (2026-10-12 19:45)
    'VFX_disabled': fmt_vfx.convert,              # learned layout: 294/501 held-out pairs exact, ~2 words off in the rest
    'BNK': fmt_bnk.convert,              # animation banks: 373/399 base pairs identical
    'RCB': fmt_rcb.convert,              # rigs: 283/300 identical
    'HKX': fmt_hkx.convert,              # Havok 6.5 packfile, learned layouts: 223/241 held-out pairs exact
    'Mesh': fmt_mesh.convert,            # constructive (indices re-stripped, packed normals expanded)
    'MetaModel': fmt_metamodel.convert,  # learned layout: 90% of held-out base pairs exact
    'Material': fmt_material.convert,    # 746/776 same-layout pairs
    'SimGroup': fmt_simgroup.convert,  # 1293/1310 identical (rest: genuine content/generated-GUID differences)
}


def type_of(a):
    parts = a['shdr']['name'].split(b'\0')
    return parts[2].decode('latin1') if len(parts) > 2 and parts[2] else '?'


def name_of(a):
    parts = a['shdr']['name'].split(b'\0')
    return (parts[1] or parts[0]).decode('latin1', 'replace')


def key_of(a):
    f = a['shdr']['f']
    return '%08x:%08x:%08x:%08x:%08x' % (f[0], f[1], f[2], f[3], f[4])


def x65599(bs, h=0):
    for c in bs: h = (h * 65599 + c) & 0xffffffff
    return h


def pc_rename(raw):
    """console asset names ending '.ps3' are '.win' on PC (NAV, TOB). NAV IDs = x65599(full name), last ID word +7 on PC."""
    raw = bytearray(raw)
    if b'.ps3\0' not in bytes(raw[44:]):
        return bytes(raw)
    raw[44:] = bytes(raw[44:]).replace(b'.ps3\0', b'.win\0')
    parts = bytes(raw[44:]).split(b'\0')
    full = parts[1] or parts[0]
    if len(parts) > 2 and parts[2] == b'NAV':
        rest = list(struct.unpack('>6I', raw[20:44]))
        h = x65599(full)
        rest[1] = rest[2] = rest[3] = h
        rest[4] = (rest[4] + 7) & 0xffffffff
        raw[20:44] = struct.pack('>6I', *rest)
    return bytes(raw)


def swap_shdr(raw, usize=None):
    """Big-endian SHOC/SHDR chunk -> little-endian; optionally replace usize."""
    sz = struct.unpack('>I', raw[4:8])[0]
    w0 = struct.unpack('>I', raw[12:16])
    h = struct.unpack('>HH', raw[16:20])
    rest = list(struct.unpack('>6I', raw[20:44]))
    if usize is not None:
        rest[5] = usize
    return (b'COHS' + struct.pack('<I', sz) + b'RDHS' + struct.pack('<I', *w0) + struct.pack('<HH', *h)
            + struct.pack('<6I', *rest) + raw[44:])


# ------------------------------------------------------------------ PC side
class PCAssets:
    def __init__(self, game, index_csv):
        self.game = game
        self.by_key = {}
        with open(index_csv, newline='', encoding='utf-8-sig') as f:
            for r in csv.DictReader(f):
                k = '%s:%s:%s:%s:%s' % (r['type_hash'], r['id1'], r['id2'], r['id3'], r['id4'])
                self.by_key.setdefault(k.lower(), (r['source'], int(r['entry_offset']), int(r['asset_offset']), r['name'].lower()))
        self.sizes = {}
        self.cache = collections.OrderedDict()

    def _entry_size(self, dat, off):
        if dat not in self.sizes:
            path = os.path.join(self.game, dat + '.DAT')
            with open(path, 'rb') as f:
                hdr = f.read(16)
                n = struct.unpack('>I', hdr[8:12])[0]
                raw = f.read(12 * n)
            self.sizes[dat] = {struct.unpack_from('>I', raw, i)[0]: struct.unpack_from('>I', raw, i + 4)[0]
                               for i in range(0, 12 * n, 12)}
        return self.sizes[dat][off]

    def stream(self, dat, off):
        ck = (dat, off)
        if ck in self.cache:
            self.cache.move_to_end(ck)
            return self.cache[ck]
        size = self._entry_size(dat, off)
        with open(os.path.join(self.game, dat + '.DAT'), 'rb') as f:
            f.seek(off)
            b = f.read(size)
        res = {a['off']: a for a in strfile.assets(b, be=False, decode=True)}
        self.cache[ck] = res
        while len(self.cache) > 24:
            self.cache.popitem(last=False)
        return res

    def get_by_name(self, t, name):
        """same type + full name on PC (Severed re-exports of base assets, different IDs)"""
        if not hasattr(self, 'names'):
            p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pc_fullnames.json')
            self.names = json.load(open(p)) if os.path.exists(p) else {}
        loc = self.names.get(t + '|' + name.lower().replace('.ps3', '.win'))
        if not loc:
            return None
        a = self.stream('DS2DAT%s' % loc[0], loc[1]).get(loc[2])
        if not a or not a['complete']:
            return None
        return a['hdr_raw'], a['data']

    def get(self, key, name=None):
        loc = self.by_key.get(key)
        if not loc:
            return None
        dat, eoff, aoff, pcname = loc
        if key.split(':', 1)[1] == '00000000:00000000:00000000:00000000':
            return None            # no real ID (SimGroups etc. all share zero IDs and a zero-GUID name)
        if name is not None and pcname != name.lower():
            return None            # same IDs but a different asset (e.g. all-zero IDs): not shared
        a = self.stream(dat, eoff).get(aoff)
        if not a or not a['complete']:
            return None
        return a['hdr_raw'], a['data']


# ------------------------------------------------------------------ writer
def write_pc_str(items, version_bytes=b'\x02\x00\x03\x01'):
    """items: list of (pc_shdr_chunk_bytes, payload). Returns PC .str bytes."""
    out = bytearray(b'3slo' + struct.pack('<I', 12) + version_bytes)

    def fill():
        left = BLOCK - len(out) % BLOCK
        if left != BLOCK:
            out.extend(b'LLIF' + struct.pack('<I', left) + b'\0' * (left - 8))

    for sh, data in items:
        if BLOCK - len(out) % BLOCK < len(sh) + 32:   # keep >= 32 bytes after the header
            fill()
        out += sh
        while data:
            space = BLOCK - len(out) % BLOCK
            if space < 32:
                fill()
                continue
            maxbody = space - 12
            if len(data) <= maxbody:
                body = data + b'\0' * ((-len(data)) % 4)
                data = b''
                rem = space - 12 - len(body)
                if 0 < rem < 32:                      # never leave a gap too small for a FILL chunk
                    body += b'\0' * rem
            else:
                body, data = data[:maxbody], data[maxbody:]
            out += b'COHS' + struct.pack('<I', 12 + len(body)) + b'TADS' + body
    fill()
    return bytes(out)


# Assets Severed modified relative to the PS3 base game (audit_pc.py -> modified_vs_base.json): never copy the PC
# base-game version for these; convert Severed's own and give it the PC ID so references and overriding still work.
import json as _json
_MODP = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'modified_vs_base.json')
MODIFIED = {k for k in (_json.load(open(_MODP)) if os.path.exists(_MODP) else {}) if not k.startswith(('VFX|', 'HKX|'))}   # HKX: keep PC copies (converted-mod collision crashed in physics, build 10)
def swap_shdr_mapped(raw, usize=None):
    from idmap_util import IDMAP
    out = bytearray(swap_shdr(raw, usize))
    for o in (24, 28, 32):                               # id1..id3 (little-endian after swap)
        v = struct.unpack_from('<I', out, o)[0]
        if v in IDMAP: struct.pack_into('<I', out, o, IDMAP[v])
    return bytes(out)

_SBKP = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sbk_placeholder.bin')
_VFXP = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vfx_placeholder.bin')
VFX_PLACEHOLDER = open(_VFXP, 'rb').read() if os.path.exists(_VFXP) and os.environ.get('VFX_PLACEHOLDER', '1') != '0' else b''
SBK_PLACEHOLDER = open(_SBKP, 'rb').read() if os.path.exists(_SBKP) and os.environ.get('SBK_PLACEHOLDER', '1') != '0' else b''

def port(src_bytes, pc, unsolved='drop'):
    assets = strfile.assets(src_bytes, be=True, decode=True)
    items, report = [], []
    meshes = {}
    for a in assets:
        t, k, nm = type_of(a), key_of(a), name_of(a)
        if not a['complete']:
            report.append((nm, t, 'error', len(a['data']), 'payload did not decode'))
            continue
        first = a['shdr']['name'].split(b'\0')[0].decode('latin1', 'replace')
        modified = (t + '|' + nm) in MODIFIED
        got = pc.get(k, first) if pc and not modified else None
        if got:
            items.append(got)
            report.append((nm, t, 'pc', len(got[1]), ''))
            continue
        got = pc.get_by_name(t, nm) if pc and not modified and t in ('Material', 'Mesh', 'MeshVolatile', 'MetaModel', 'HKX') else None
        if got:
            items.append(got)
            report.append((nm, t, 'pc-name', len(got[1]), ''))
            continue
        if t == 'Mesh':
            meshes[nm] = a['data']
        if t == 'MeshVolatile':
            if nm in meshes:
                try:
                    d = fmt_mesh.convert_volatile(a['data'], meshes[nm])
                    items.append(((swap_shdr_mapped if modified else swap_shdr)(a['hdr_raw'], len(d)), d))
                    report.append((nm, t, 'converted-mod' if modified else 'converted', len(d), ''))
                except Exception as e:
                    report.append((nm, t, 'error', len(a['data']), repr(e)[:80]))
            else:
                report.append((nm, t, 'unsolved', len(a['data']), 'no PS3 Mesh in this stream'))
            continue
        rule = RULES.get(t)
        if rule:
            try:
                d = rule(a['data'])
                items.append(((swap_shdr_mapped if modified else swap_shdr)(pc_rename(a['hdr_raw']) if t in ('NAV', 'TOB', 'HKX', 'BNK', 'RCB') else a['hdr_raw'], len(d)), d))
                report.append((nm, t, 'converted-mod' if modified else 'converted', len(d), ''))
                continue
            except Exception as e:
                report.append((nm, t, 'error', len(a['data']), repr(e)[:80]))
                continue
        if t == 'VFX' and VFX_PLACEHOLDER:
            items.append((swap_shdr(a['hdr_raw'], len(VFX_PLACEHOLDER)), VFX_PLACEHOLDER))
            report.append((nm, t, 'placeholder', len(VFX_PLACEHOLDER), ''))
            continue
        if t == 'SBK' and SBK_PLACEHOLDER:
            # sound bank we cannot convert yet: a tiny valid PC bank under Severed's own header (name/ID),
            # so references resolve (sounds are silent/wrong). See handoff_env.md section 13.
            items.append((swap_shdr(a['hdr_raw'], len(SBK_PLACEHOLDER)), SBK_PLACEHOLDER))
            report.append((nm, t, 'placeholder', len(SBK_PLACEHOLDER), ''))
            continue
        report.append((nm, t, 'unsolved', len(a['data']), ''))
        if unsolved == 'keep':
            items.append((swap_shdr(a['hdr_raw']), a['data']))
    return write_pc_str(items), report


def summarize(report):
    by = collections.defaultdict(lambda: [0, 0])
    for nm, t, how, n, _ in report:
        by[(how, t)][0] += 1
        by[(how, t)][1] += n
    tot = collections.Counter()
    for (how, t), (c, n) in by.items():
        tot[how] += c
    return by, tot


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('out')
    ap.add_argument('--game', required=True)
    ap.add_argument('--index', default=None)
    ap.add_argument('--unsolved', default='drop', choices=['drop', 'keep'])
    a = ap.parse_args()
    pc = PCAssets(a.game, a.index or os.path.join(a.game, 'pc_assets.csv'))
    b = open(a.src, 'rb').read()
    out, rep = port(b, pc, a.unsolved)
    open(a.out, 'wb').write(out)
    by, tot = summarize(rep)
    print('%s -> %s (%d bytes): %s' % (a.src, a.out, len(out), dict(tot)))
    for (how, t), (c, n) in sorted(by.items()):
        print('  %-10s %-14s %5d assets %10d bytes' % (how, t, c, n))
