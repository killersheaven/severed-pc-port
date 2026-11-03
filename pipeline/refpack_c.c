#include <stdint.h>
#include <string.h>
/* EA RefPack decoder. Returns bytes written, or -1 on malformed input. */
int refpack_decode(const uint8_t *d, int n, uint8_t *out, int cap)
{
    int p = 0, o = 0;
    if (n < 5 || d[1] != 0xFB) return -1;
    int big = d[0] & 0x80, sz = big ? 4 : 3;
    p = 2;
    if (d[0] & 0x01) p += sz;
    p += sz;
    while (p < n) {
        int b0 = d[p], lit, len, off;
        if (b0 < 0x80) {
            if (p + 1 >= n) return -1;
            int b1 = d[p+1]; p += 2;
            lit = b0 & 3; len = ((b0 >> 2) & 7) + 3; off = ((b0 & 0x60) << 3) + b1 + 1;
        } else if (b0 < 0xC0) {
            if (p + 2 >= n) return -1;
            int b1 = d[p+1], b2 = d[p+2]; p += 3;
            lit = b1 >> 6; len = (b0 & 0x3F) + 4; off = ((b1 & 0x3F) << 8) + b2 + 1;
        } else if (b0 < 0xE0) {
            if (p + 3 >= n) return -1;
            int b1 = d[p+1], b2 = d[p+2], b3 = d[p+3]; p += 4;
            lit = b0 & 3; len = ((b0 & 0x0C) << 6) + b3 + 5; off = ((b0 & 0x10) << 12) + (b1 << 8) + b2 + 1;
        } else if (b0 < 0xFC) {
            p += 1; lit = ((b0 & 0x1F) << 2) + 4; len = 0; off = 0;
        } else {
            p += 1; lit = b0 & 3;
            if (p + lit > n || o + lit > cap) return -1;
            memcpy(out + o, d + p, lit); o += lit; p += lit;
            break;
        }
        if (p + lit > n || o + lit + len > cap) return -1;
        memcpy(out + o, d + p, lit); o += lit; p += lit;
        if (len) {
            if (off > o) return -1;
            for (int i = 0; i < len; i++) { out[o] = out[o - off]; o++; }
        }
    }
    return o;
}
