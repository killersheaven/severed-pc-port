"""Graph (AI path graph, .graph) PS3 big-endian -> PC.
Header 0xA0: u32 words except u16 pairs at 0x0C (nNodes, nEdges), 0x2C, 0x3C (.., nLinks), 0x4C. Pointers:
 0x20 nodes (48 B: 5 u32, 2 u16, 2 bytes, u16, 4 u16, 4 bytes, 2 u32)      0x24 edges and 0x30 extra edges (16 B: u32, 6 u16)
 0x28 GUIDs (16 B, u32 words)                                0x50 n x {u32, 4 bytes}, 0x58/0x60 n x 2 u32, 0x68 u32 + GUIDs (0x6C bytes), 0x70 byte table (0x74 bytes)
 0x34..0x40 u16s, 0x40..0x48 byte table                      0x48 links (48 B: 8 u32, 6 u16, u32)
 0x44 u16 array to end of file."""
import struct
def convert(d):
    out = bytearray(d)
    U = lambda o: struct.unpack_from('>I', d, o)[0]
    def w(o): out[o:o + 4] = d[o:o + 4][::-1]
    def h(o): out[o:o + 2] = d[o:o + 2][::-1]
    nn = struct.unpack_from('>H', d, 0x0C)[0]
    nl = struct.unpack_from('>H', d, 0x3E)[0]
    for o in range(0, 0xA0, 4):
        if o in (0x0C, 0x2C, 0x3C, 0x4C): h(o); h(o + 2)
        else: w(o)
    nodes, edges, links, arr = U(0x20), U(0x24), U(0x48), U(0x44)
    x30, x34, x40, x68 = U(0x30), U(0x34), U(0x40), U(0x68)
    x50, n50, x70 = U(0x50), U(0x54), U(0x70)
    ends = [v for v in (x50, U(0x58), U(0x60), x68, x70, x34, links, arr) if v > edges]
    eend = min(ends) if ends else len(d)        # end of edges + extra edges
    wend = x70 or x34 or links or arr or len(d)
    for o in range(0xA0, wend & ~3, 4): w(o)   # nodes, GUIDs, edges, 0x50/0x58/0x60/0x68 tables: u32 words, refined below
    for i in range(nn if nodes else 0):
        o = nodes + 48 * i
        out[o + 0x14:o + 0x1C] = d[o + 0x14:o + 0x1C]
        h(o + 0x14); h(o + 0x16); h(o + 0x1A)
        out[o + 0x1C:o + 0x28] = d[o + 0x1C:o + 0x28]; h(o + 0x1C); h(o + 0x1E); h(o + 0x20); h(o + 0x22)
    for o in range(edges, eend if edges else 0, 16):
        out[o + 4:o + 16] = d[o + 4:o + 16]
        for k in range(4, 16, 2): h(o + k)
    for i in range(n50 if x50 else 0):
        out[x50 + 8 * i + 4:x50 + 8 * i + 8] = d[x50 + 8 * i + 4:x50 + 8 * i + 8]
    if x34 and x40:
        for o in range(x34, x40, 2): h(o)
    for i in range(nl if links else 0):
        o = links + 48 * i
        for k in range(0, 0x30, 4):
            if k in (0x20, 0x24, 0x28): h(o + k); h(o + k + 2)
            else: w(o + k)
    if arr:
        for o in range(arr, len(d) - 1, 2): h(o)
    return bytes(out)
