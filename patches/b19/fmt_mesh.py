"""Mesh (EAGM .geo) PS3 v2 big-endian -> PC v3 little-endian, plus its MeshVolatile vertex streams.
Constructive conversion (PC meshes were exported separately, so output is equivalent, not byte-identical):
- header 0xA0 / draw records (0xC0 each, at u32[0x50], count u32[0x34]) / stream descriptors (u32[0x68]..u32[0x6C]+16):
  u32 words with u16 pairs at hdr 0x38-0x44, record +0x38, +0x40, +0xAC; bytes at record +0x04, +0x24, +0x2C;
  record +0x28 = 2 bytes + u16; descriptor +8 = u16 stride + 2 format bytes.
- name strings u32[0x20]..u32[0x4C] as is; relocation table at u32[0x4C] (u32[0x48] entries {field, value}).
- vertex streams by (stride, A, B): floats swapped, packed normals (11:11:10) -> 4 x u8, colours/bone bytes as is.
- skinned draw records (decl byte +0x25 != 0): 32-byte vertices at record +0x84 {pos, normal, tangent s8x4 (w,z,y,x),
  4 bone bytes, 4 x u16 weights}.
- indices: PS3 strips with restart 0xFFFF (RSX prim 6) -> one PC strip joined by degenerate triangles (D3D prim 5);
  triangle lists (format byte 1) just byte-swapped. Data after the index buffer moves; pointers fixed via the reloc table."""
import struct

def s8(x): return x - 256 if x > 127 else x
def pack_normal(u):
    x = u & 0x7FF; y = (u >> 11) & 0x7FF; z = (u >> 22) & 0x3FF
    if x >= 1024: x -= 2048
    if y >= 1024: y -= 2048
    if z >= 512: z -= 1024
    f = lambda v, s: max(0, min(255, round(v / s * 127 + 127)))
    return bytes([f(x, 1023), f(y, 1023), f(z, 511), 255])
def pack_tangent(p):
    return bytes([(s8(p[3]) + 127) & 255, (s8(p[2]) + 127) & 255, (s8(p[1]) + 127) & 255, 0 if s8(p[0]) > 0 else 255])

# per-format field kinds: W = swap u32, S = bytes as is, N = packed normal, T = tangent, H = two u16
LAYOUT = {
    (28, 0, 2): 'SWWWWNS', (20, 2, 2): 'SWWNS', (16, 6, 2): 'WWNS', (20, 6, 0): 'WWWNS', (20, 2, 0): 'WWWNS',
    (12, 2, 2): 'WWS', 'skin32': 'WWWNTSHH',
}
def convert_vertices(src, dst, off, count, stride, layout):
    for v in range(count):
        b = off + v * stride
        if b + stride > len(src): break
        for k, kind in enumerate(layout):
            o = b + 4 * k
            p = src[o:o + 4]
            if kind == 'W': dst[o:o + 4] = p[::-1]
            elif kind == 'S': dst[o:o + 4] = p
            elif kind == 'N': dst[o:o + 4] = pack_normal(int.from_bytes(p, 'big'))
            elif kind == 'T': dst[o:o + 4] = pack_tangent(p)
            elif kind == 'H': dst[o:o + 4] = p[1::-1] + p[:1:-1]
        for o in range(b + 4 * len(layout), b + stride, 4):     # rest of the vertex: floats
            dst[o:o + 4] = src[o:o + 4][::-1]

def join_strips(idx):
    out = []; cur = []; strips = []
    for i in idx:
        if i == 0xFFFF:
            if cur: strips.append(cur); cur = []
        else: cur.append(i)
    if cur: strips.append(cur)
    for s in strips:
        if out:
            out.append(out[-1]); out.append(s[0])
            if len(out) % 2: out.append(s[0])
        out.extend(s)
    return out

def join_map(idx):
    """join_strips plus a map old position -> new position (a restart maps to the next real index)."""
    out = []; m = {}; strips = []; cur = []; pos = []
    for p, i in enumerate(idx):
        if i == 0xFFFF:
            if cur: strips.append((cur, pos)); cur = []; pos = []
            m[p] = None
        else: cur.append(i); pos.append(p)
    if cur: strips.append((cur, pos))
    for s, ps in strips:
        if out:
            out.append(out[-1]); out.append(s[0])
            if len(out) % 2: out.append(s[0])
        for i, p in zip(s, ps): m[p] = len(out); out.append(i)
    nxt = len(out)
    for p in sorted(m, reverse=True):
        if m[p] is None: m[p] = nxt
        else: nxt = m[p]
    m[len(idx)] = len(out)
    return out, m

def descriptors(d):
    U = lambda o: struct.unpack_from('>I', d, o)[0]
    res = []
    for o in range(U(0x68), U(0x6C) + 16, 16):
        res.append(dict(at=o, size=U(o), count=U(o + 4), stride=struct.unpack_from('>H', d, o + 8)[0],
                        A=d[o + 10], B=d[o + 11], off=U(o + 12), index=(o == U(0x6C))))
    return res

def convert(d):
    U = lambda o: struct.unpack_from('>I', d, o)[0]
    n = len(d)
    w = bytearray(b''.join(d[i:i + 4][::-1] for i in range(0, n & ~3, 4)) + d[n & ~3:])
    def H(o): w[o:o + 2] = d[o:o + 2][::-1]; w[o + 2:o + 4] = d[o + 2:o + 4][::-1]
    names, nrel, rel = U(0x20), U(0x48), U(0x4C)
    if 0 < names <= rel <= n: w[names:rel] = d[names:rel]
    struct.pack_into('<I', w, 0x08, 3)
    for o in (0x38, 0x3C, 0x40, 0x44): H(o)
    ndraw, drec = U(0x34), U(0x50)
    descs = descriptors(d)
    for ds in descs:
        o = ds['at']; w[o + 8:o + 10] = d[o + 8:o + 10][::-1]; w[o + 10:o + 12] = d[o + 10:o + 12]
    ibd = [ds for ds in descs if ds['index']][0]
    recs = []
    for i in range(ndraw):
        r = drec + 0xC0 * i
        for k in (0x04, 0x24, 0x2C): w[r + k:r + k + 4] = d[r + k:r + k + 4]
        w[r + 0x28:r + 0x2A] = d[r + 0x28:r + 0x2A]; w[r + 0x2A:r + 0x2C] = d[r + 0x2A:r + 0x2C][::-1]
        for k in (0x38, 0x40, 0xAC): H(r + k)
        recs.append((U(r + 0x34), U(r + 0x30), struct.unpack_from('>H', d, r + 0x3C)[0], r))
        if d[r + 0x24] == 0xFF and d[r + 0x25] != 0:               # skinned: 32-byte vertices in this asset
            vp, nv = U(r + 0x84), struct.unpack_from('>H', d, r + 0x38)[0]
            if 0 < vp < n: convert_vertices(d, w, vp, nv, 32, LAYOUT['skin32'])
    for ds in descs:                                                 # vertex streams stored in this asset
        if ds['index'] or not (0 < ds['off'] < n): continue
        lay = LAYOUT.get((ds['stride'], ds['A'], ds['B']))
        if lay: convert_vertices(d, w, ds['off'], ds['count'], ds['stride'], lay)
    # index buffer(s). A record's indices live at its +0x88 pointer. Vertex group 0 (and single-group meshes) use the
    # IB descriptor; each further vertex group (picked by the record's +0x84 position pointer) has its own index block
    # after the IB, not covered by the descriptor, with starts relative to that block. Same scheme on PC (blocks
    # 64-byte aligned); the engine makes one D3D index buffer per block. (2026-10-18; before this all records were read
    # from the main IB, so group 1+ draws in multi-group level meshes were garbage.)
    ib_off, ib_count = ibd['off'], ibd['count']
    ib_end0 = ib_off + 2 * ib_count
    strips = (ibd['A'], ibd['B']) == (2, 0)
    p88 = {r: U(r + 0x88) for _, _, _, r in recs}
    info = {r: (start, cnt, prim) for start, cnt, prim, r in recs}
    blocks = {}                                      # block key -> records; key 0 = main IB
    old_region_end = ib_end0
    for start, cnt, prim, r in recs:
        inmain = not (0 < p88[r] < n) or ib_off <= p88[r] < ib_end0
        if inmain: blocks.setdefault(0, []).append(r)
        else:
            blocks.setdefault(p88[r] - 2 * start, []).append(r)
            old_region_end = max(old_region_end, p88[r] + 2 * cnt)
    place = {}; maps = {}; boff = {}                 # boff: record -> byte offset of its block (absolute, new layout)
    new = []
    for r in sorted(blocks.get(0, []), key=lambda r: info[r][0]):
        start, cnt, prim = info[r]
        seg = list(struct.unpack_from('>%dH' % cnt, d, ib_off + 2 * start)) if cnt else []
        if strips and prim == 6: seg, maps[r] = join_map(seg)
        place[r] = (len(new), len(seg)); new.extend(seg); boff[r] = ib_off
    main_count = len(new)
    nb = bytearray(struct.pack('<%dH' % len(new), *new))
    for key in sorted(k for k in blocks if k):
        while (ib_off + len(nb)) % 64: nb += b'\0'
        bo = ib_off + len(nb); blk = []
        for r in sorted(blocks[key], key=lambda r: info[r][0]):
            start, cnt, prim = info[r]
            seg = list(struct.unpack_from('>%dH' % cnt, d, p88[r])) if cnt else []
            if strips and prim == 6: seg, maps[r] = join_map(seg)
            place[r] = (len(blk), len(seg)); blk.extend(seg); boff[r] = bo
        nb += struct.pack('<%dH' % len(blk), *blk)
    # per-record spatial grid at record +0x8C: AABB/scale floats (u32), then u16 data: nx, ny, nz, count, nCells,
    # count index-buffer positions (relative to the record; remapped through the strip join), cell start table
    targets = sorted({U(rel + 8 * i + 4) for i in range(nrel)}) if 0 < rel < n else []
    for start, cnt, prim, r in recs:
        p = U(r + 0x8C)
        if not (0 < p < n - 0x3C): continue
        end = min([v for v in targets if v > p] + [n])
        for o in range(p + 0x30, end - 1, 2): w[o:o + 2] = d[o:o + 2][::-1]
        npos = struct.unpack_from('>H', d, p + 0x36)[0]
        m = maps.get(r)
        if m and p + 0x3A + 2 * npos <= end:
            for j in range(npos):
                o = p + 0x3A + 2 * j
                v = struct.unpack_from('>H', d, o)[0]
                struct.pack_into('<H', w, o, min(m.get(v, v), 0xFFFF))
    # per-record bone palette at record +0x44: byte array (skeleton bone index per local bone), stored as is on both platforms
    for start, cnt, prim, r in recs:
        p = U(r + 0x44)
        if 0 < p < n:
            end = min([v for v in targets if v > p] + [n])
            w[p:end] = d[p:end]
    for start, cnt, prim, r in recs:
        s, c = place[r]
        struct.pack_into('<II', w, r + 0x30, c, s)
        # RSX prim 6 (strip) -> D3D 5 with index count; RSX 5 (triangle list) -> D3D 4 with triangle count
        if prim == 6: struct.pack_into('<HH', w, r + 0x3C, 5, c & 0xFFFF)
        elif prim == 5: struct.pack_into('<HH', w, r + 0x3C, 4, (c // 3) & 0xFFFF)
        else: struct.pack_into('<HH', w, r + 0x3C, prim, c & 0xFFFF)
    old_end = (old_region_end + 15) & ~15
    nb = bytes(nb)
    new_end = (ib_off + len(nb) + 15) & ~15
    delta = new_end - old_end
    w = bytearray(bytes(w[:ib_off]) + nb + bytes(new_end - ib_off - len(nb)) + bytes(w[old_end:]))
    sh = lambda v: v + delta if v >= old_end else v
    rel2 = sh(rel)
    for i in range(nrel):
        fo, val = U(rel + 8 * i), U(rel + 8 * i + 4)
        struct.pack_into('<II', w, rel2 + 8 * i, sh(fo), sh(val))
        if sh(fo) + 4 <= len(w): struct.pack_into('<I', w, sh(fo), sh(val))
    for start, cnt, prim, r in recs:                               # +0x88: this record's indices in the merged IB
        if 0 < p88[r] < n:
            v88 = boff[r] + 2 * place[r][0]; struct.pack_into('<I', w, r + 0x88, v88)
            for i in range(nrel):
                if U(rel + 8 * i) == r + 0x88: struct.pack_into('<I', w, rel2 + 8 * i + 4, v88)
    struct.pack_into('<I', w, 0x0C, U(0x0C) + delta); struct.pack_into('<I', w, 0x9C, U(0x9C) + delta)
    for ds in descs:
        if ds['off']: struct.pack_into('<I', w, ds['at'] + 12, sh(ds['off']))
    struct.pack_into('<II', w, ibd['at'], 2 * main_count, main_count)
    # extra index-block descriptors (one per extra vertex group) follow the IB descriptor: PC = {2*count, count,
    # 0x00020002, block offset}; the engine builds each group's D3D index buffer from them (2026-10-26: b19 left the PS3
    # offset/size + flags 0x20200 -> wrong IBs -> invisible floors). Order = block order.
    x = ibd['at'] + 16; ex = []
    while x + 16 <= n and U(x + 4) and U(x) == 2 * U(x + 4) and struct.unpack_from('>H', d, x + 8)[0] == 2: ex.append(x); x += 16
    keys = sorted(k for k in blocks if k)
    if len(ex) == len(keys):
        for at, key in zip(ex, keys):
            bo = boff[blocks[key][0]]; cntb = max(place[r][0] + place[r][1] for r in blocks[key])
            struct.pack_into('<IIHBBI', w, at, 2 * cntb, cntb, 2, d[at + 10], d[at + 11], bo)
            for i in range(nrel):
                if U(rel + 8 * i) == at + 12: struct.pack_into('<I', w, rel2 + 8 * i + 4, bo)
    return bytes(w)

def convert_volatile(v, mesh_ps3):
    """MeshVolatile: vertex streams whose descriptor offsets point past the end of the Mesh asset."""
    n_mesh = len(mesh_ps3)
    w = bytearray(b''.join(v[i:i + 4][::-1] for i in range(0, len(v) & ~3, 4)) + v[len(v) & ~3:])
    for ds in descriptors(mesh_ps3):
        if ds['index'] or ds['off'] < n_mesh: continue
        lay = LAYOUT.get((ds['stride'], ds['A'], ds['B']))
        if lay: convert_vertices(v, w, ds['off'] - n_mesh, ds['count'], ds['stride'], lay)
    return bytes(w)
