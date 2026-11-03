import struct,collections,sys
a=open('sg/pair/ch01_hos.simgroup.bin.ps3','rb').read();b=open('sg/pair/ch01_hos.simgroup.bin.pc','rb').read()
S=0x214b0; P=S+0x3e10; N=0x100a
props=[struct.unpack_from('>IxxBxI',a,P+12*j) for j in range(N)]
ptrtypes=collections.Counter()
inline=collections.defaultdict(collections.Counter)
for j,(h,t,v) in enumerate(props):
    pa=a[P+12*j+8:P+12*j+12]; pb=b[P+12*j+8:P+12*j+12]
    inline[t]['same' if pa==pb else 'swap' if pa==pb[::-1] else 'h' if pa[1::-1]+pa[:1:-1]==pb else 'X']+=1
for t in sorted(inline): print(t,dict(inline[t]))
# pointer pool: offsets
offs=sorted(set(v for h,t,v in props if t in (5,10,12,14,15,16,17,22)))
print('pool from',hex(offs[0]),'to',hex(offs[-1]), 'P+off0=',hex(P+offs[0]))
nxt=dict(zip(offs,offs[1:]+[len(a)-P]))
want=int(sys.argv[1]) if len(sys.argv)>1 else 17
k=0
for j,(h,t,v) in enumerate(props):
    if t==want and k<12:
        k+=1; x=P+v; y=P+nxt[v]
        print(hex(v),y-x, a[x:y].hex(' '),'|',b[x:y].hex(' '))
