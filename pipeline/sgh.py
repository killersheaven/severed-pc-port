import struct,zlib,sys
a=open('sg/pair/ch01_hos.simgroup.bin.ps3','rb').read();b=open('sg/pair/ch01_hos.simgroup.bin.pc','rb').read()
S=0x214b0
def ent(d,e,i):
    return struct.unpack_from(e+'IHHI',d,S+0x408+12*i)
def x65599(bs,h=0):
    for c in bs: h=(h*65599+c)&0xffffffff
    return h
def fnv(bs,h=0x811c9dc5):
    for c in bs: h=((h^c)*0x01000193)&0xffffffff
    return h
def fnv1(bs,h=0x811c9dc5):
    for c in bs: h=((h*0x01000193)^c)&0xffffffff
    return h
for i in (5,6,11):
  for d,e in ((a,'>'),(b,'<')):
    h,x,n,off=ent(d,e,i)
    idx=struct.unpack_from(e+'%dH'%n,d,S+off)
    recs=b''.join(d[S+0x3e10+12*j:S+0x3e10+12*j+12] for j in idx)
    print(i,e,'%08x'%h,x,n,idx)
    for k in range(n): print('   ',recs[12*k:12*k+12].hex(' ',4))
    cands={}
    for nm,bs in (('recs',recs),('idx',d[S+off:S+off+2*n])):
      for f in (zlib.crc32,x65599,fnv,fnv1):
        cands[nm+f.__name__]=f(bs)
    print('   match:',[k for k,v in cands.items() if v==h])
