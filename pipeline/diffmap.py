"""Classify each 4-byte word of a PS3/PC pair: S same, W u32 swap, H two u16 swaps, B byte-equal-ish(other), X unexplained."""
import sys
def cls(a, b):
    if a == b: return 'S' if a != b'\0\0\0\0' else '0'
    if a[::-1] == b: return 'W'
    if a[1::-1] + a[3:1:-1] == b: return 'H'
    if a[0]==b[0] and a[1]==b[1] and a[3:1:-1]==b[2:4]: return 'h'   # first u16 same(?), second swapped
    return 'X'
def mapit(p, c):
    return ''.join(cls(p[i:i+4], c[i:i+4]) for i in range(0, len(p) - 3, 4))
if __name__ == '__main__':
    p = open(sys.argv[1], 'rb').read(); c = open(sys.argv[2], 'rb').read()
    m = mapit(p, c)
    from collections import Counter
    print(len(p), Counter(m))
    w = int(sys.argv[3]) if len(sys.argv) > 3 else 64
    lim = int(sys.argv[4]) if len(sys.argv) > 4 else 40
    for i in range(0, min(len(m), w * lim), w):
        print('%06X %s' % (i * 4, m[i:i + w]))
