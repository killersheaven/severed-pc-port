"""Xbox 360 LZX (XMemCompress) decoder, as used by Dead Space 2 'LZXD' chunks.

Bitstream follows Microsoft LZX (CAB variant, 24-bit block sizes): 16-bit
little-endian words, bits consumed MSB first, 32 KB frames, 16-bit realign
after each frame. Xbox framing: each piece starts with 0xFF + u16 BE
uncompressed size + u16 BE compressed size, or just u16 BE compressed size
when the piece decompresses to a full 0x8000 bytes.
"""

NUM_CHARS = 256
PRETREE_NUM = 20
ALIGNED_NUM = 8
NUM_SECONDARY_LENGTHS = 249
FRAME = 0x8000

EXTRA_BITS = []
_j = 0
for _i in range(0, 52, 2):
    EXTRA_BITS += [_j, _j]
    if _i != 0 and _j < 17:
        _j += 1
POSITION_BASE = []
_j = 0
for _i in range(52):
    POSITION_BASE.append(_j)
    _j += 1 << EXTRA_BITS[_i]

SLOTS = {15: 30, 16: 32, 17: 34, 18: 36, 19: 38, 20: 42, 21: 50}


class LZXError(Exception):
    pass


def build_table(lengths):
    """Canonical Huffman -> (lookup dict keyed by (len, code), max_len)."""
    maxlen = max(lengths) if lengths else 0
    table = {}
    if maxlen == 0:
        return table, 0
    bl_count = [0] * (maxlen + 1)
    for l in lengths:
        if l:
            bl_count[l] += 1
    code = 0
    next_code = [0] * (maxlen + 2)
    for bits in range(1, maxlen + 1):
        code = (code + bl_count[bits - 1]) << 1
        next_code[bits] = code
    for sym, l in enumerate(lengths):
        if l:
            table[(l, next_code[l])] = sym
            next_code[l] += 1
    return table, maxlen


class BitReader:
    def __init__(self, data):
        self.d = data
        self.p = 0
        self.buf = 0
        self.n = 0

    def _fill(self):
        while self.n <= 16:
            if self.p + 1 < len(self.d):
                w = self.d[self.p] | (self.d[self.p + 1] << 8)
            elif self.p < len(self.d):
                w = self.d[self.p]
            else:
                w = 0
            self.p += 2
            self.buf = (self.buf << 16) | w
            self.n += 16

    def peek(self, k):
        if self.n < k:
            self._fill()
        return (self.buf >> (self.n - k)) & ((1 << k) - 1)

    def read(self, k):
        if k == 0:
            return 0
        v = 0
        while k > 16:
            v = (v << 16) | self.read(16)
            k -= 16
        if self.n < k:
            self._fill()
        self.n -= k
        r = (self.buf >> self.n) & ((1 << k) - 1)
        self.buf &= (1 << self.n) - 1
        return (v << k) | r

    def sym(self, tbl):
        table, maxlen = tbl
        if maxlen == 0:
            raise LZXError("empty huffman table")
        if self.n < maxlen:
            self._fill()
        for l in range(1, maxlen + 1):
            c = (self.buf >> (self.n - l)) & ((1 << l) - 1)
            s = table.get((l, c))
            if s is not None:
                self.n -= l
                self.buf &= (1 << self.n) - 1
                return s
        raise LZXError("bad huffman code")

    def align16(self):
        r = self.n & 15
        if r:
            self.read(r)


class LZXDecoder:
    def __init__(self, window_bits=17):
        self.wsize = 1 << window_bits
        self.slots = SLOTS[window_bits]
        self.window = bytearray(self.wsize)
        self.wpos = 0
        self.R = [1, 1, 1]
        self.main_len = [0] * (NUM_CHARS + self.slots * 8)
        self.len_len = [0] * NUM_SECONDARY_LENGTHS
        self.header_read = False
        self.block_remaining = 0
        self.block_type = 0
        self.block_length = 0
        self.intel_filesize = 0

    def _read_lengths(self, br, lens, first, last):
        pre = [br.read(4) for _ in range(PRETREE_NUM)]
        pt = build_table(pre)
        x = first
        while x < last:
            z = br.sym(pt)
            if z == 17:
                y = br.read(4) + 4
                for _ in range(y):
                    lens[x] = 0; x += 1
            elif z == 18:
                y = br.read(5) + 20
                for _ in range(y):
                    lens[x] = 0; x += 1
            elif z == 19:
                y = br.read(1) + 4
                z = br.sym(pt)
                z = lens[x] - z
                if z < 0:
                    z += 17
                for _ in range(y):
                    lens[x] = z; x += 1
            else:
                z = lens[x] - z
                if z < 0:
                    z += 17
                lens[x] = z; x += 1

    def decompress(self, br, out_len):
        """Decode out_len bytes from bitreader br, returning bytes."""
        out = bytearray()
        w = self.window
        wmask = self.wsize - 1
        while len(out) < out_len:
            frame_left = min(FRAME, out_len - len(out))
            if not self.header_read:
                if br.read(1):
                    self.intel_filesize = (br.read(16) << 16) | br.read(16)
                self.header_read = True
            produced = 0
            while produced < frame_left:
                if self.block_remaining == 0:
                    if self.block_type == 3 and (self.block_length & 1):
                        br.p += 1  # pad byte after odd uncompressed block
                    self.block_type = br.read(3)
                    self.block_length = self.block_remaining = (br.read(16) << 8) | br.read(8)
                    if self.block_type == 2:
                        al = [br.read(3) for _ in range(ALIGNED_NUM)]
                        self.aligned = build_table(al)
                    if self.block_type in (1, 2):
                        self._read_lengths(br, self.main_len, 0, NUM_CHARS)
                        self._read_lengths(br, self.main_len, NUM_CHARS, len(self.main_len))
                        self.main = build_table(self.main_len)
                        self._read_lengths(br, self.len_len, 0, NUM_SECONDARY_LENGTHS)
                        self.lens = build_table(self.len_len)
                    elif self.block_type == 3:
                        if br.n >= 16:
                            back = (br.n // 16) * 2
                            br.p -= back
                        br.buf = 0; br.n = 0
                        rr = []
                        for _ in range(3):
                            rr.append(int.from_bytes(br.d[br.p:br.p + 4], 'little')); br.p += 4
                        self.R = rr
                    else:
                        raise LZXError("bad block type %d" % self.block_type)
                run = min(self.block_remaining, frame_left - produced)
                if self.block_type == 3:
                    chunk = br.d[br.p:br.p + run]
                    br.p += run
                    for c in chunk:
                        w[self.wpos & wmask] = c; self.wpos += 1
                    out += chunk
                    produced += run
                    self.block_remaining -= run
                    continue
                target = produced + run
                while produced < target:
                    m = br.sym(self.main)
                    if m < NUM_CHARS:
                        w[self.wpos & wmask] = m; self.wpos += 1
                        out.append(m)
                        produced += 1
                        continue
                    m -= NUM_CHARS
                    ml = m & 7
                    if ml == 7:
                        ml += br.sym(self.lens)
                    ml += 2
                    mo = m >> 3
                    if mo > 2:
                        if self.block_type == 1:
                            if mo != 3:
                                mo = POSITION_BASE[mo] - 2 + br.read(EXTRA_BITS[mo])
                            else:
                                mo = 1
                        else:
                            extra = EXTRA_BITS[mo]
                            mo = POSITION_BASE[mo] - 2
                            if extra > 3:
                                mo += br.read(extra - 3) << 3
                                mo += br.sym(self.aligned)
                            elif extra == 3:
                                mo += br.sym(self.aligned)
                            elif extra > 0:
                                mo += br.read(extra)
                            else:
                                mo = 1
                        self.R = [mo, self.R[0], self.R[1]]
                    elif mo == 0:
                        mo = self.R[0]
                    elif mo == 1:
                        mo = self.R[1]; self.R = [mo, self.R[0], self.R[2]]
                    else:
                        mo = self.R[2]; self.R = [mo, self.R[1], self.R[0]]
                    src = self.wpos - mo
                    for _ in range(ml):
                        c = w[src & wmask]; src += 1
                        w[self.wpos & wmask] = c; self.wpos += 1
                        out.append(c)
                    produced += ml
                    if produced > target:
                        raise LZXError("match ran past block end")
                self.block_remaining -= run
            br.align16()
            if self.intel_filesize:
                raise LZXError("E8 translation not implemented")
        return bytes(out)


def xmem_decompress(data, out_size, window_bits=17):
    """Decode an Xbox XMem LZX stream made of framed pieces."""
    dec = LZXDecoder(window_bits)
    out = bytearray()
    p = 0
    while len(out) < out_size and p < len(data):
        if data[p] == 0xFF:
            usize = (data[p + 1] << 8) | data[p + 2]
            csize = (data[p + 3] << 8) | data[p + 4]
            p += 5
        else:
            usize = FRAME
            csize = (data[p] << 8) | data[p + 1]
            p += 2
        if csize == 0:
            break
        br = BitReader(data[p:p + csize])
        out += dec.decompress(br, min(usize, out_size - len(out)))
        p += csize
    return bytes(out)
