import struct,collections
a=open('sg/pair/ch01_hos.simgroup.bin.ps3','rb').read();b=open('sg/pair/ch01_hos.simgroup.bin.pc','rb').read()
S=0x214b0
c=collections.Counter(); tc=collections.Counter()
for i in range(1238):
    h,x,n,off=struct.unpack_from('>IHHI',a,S+0x408+12*i); H=struct.unpack_from('<I',b,S+0x408+12*i)[0]
    idx=struct.unpack_from('>%dH'%n,a,S+off)
    ts=frozenset(a[S+0x3e10+12*j+6] for j in idx)
    c[(tuple(sorted(ts)),h==H)]+=1
    for t in ts: tc[(t,h==H)]+=1
for k,v in sorted(tc.items()): print(k,v)
