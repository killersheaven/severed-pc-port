import struct,zlib,itertools
a=open('sg/pair/ch01_hos.simgroup.bin.ps3','rb').read();b=open('sg/pair/ch01_hos.simgroup.bin.pc','rb').read()
S=0x214b0;P=S+0x3e10
def x65599(bs,h=0):
    for c in bs: h=(h*65599+c)&0xffffffff
    return h
def fnv1a(bs,h=0x811c9dc5):
    for c in bs: h=((h^c)*0x01000193)&0xffffffff
    return h
def fnv1(bs,h=0x811c9dc5):
    for c in bs: h=((h*0x01000193)^c)&0xffffffff
    return h
def oaat(bs,h=0):
    for c in bs:
        h=(h+c)&0xffffffff; h=(h+(h<<10))&0xffffffff; h^=h>>6
    h=(h+(h<<3))&0xffffffff; h^=h>>11; h=(h+(h<<15))&0xffffffff; return h
def djb(bs,h=5381):
    for c in bs: h=(h*33+c)&0xffffffff
    return h
def sdbm(bs,h=0):
    for c in bs: h=(c+(h<<6)+(h<<16)-h)&0xffffffff
    return h
def crc(bs): return zlib.crc32(bs)
def crcn(bs): return zlib.crc32(bs)^0xffffffff
def crcs(bs): return (zlib.crc32(bs,0xffffffff)^0xffffffff)&0xffffffff
def lookup2(k,initval=0):
    def mix(a,b,c):
        a=(a-b-c)&0xffffffff;a^=c>>13
        b=(b-c-a)&0xffffffff;b^=(a<<8)&0xffffffff
        c=(c-a-b)&0xffffffff;c^=b>>13
        a=(a-b-c)&0xffffffff;a^=c>>12
        b=(b-c-a)&0xffffffff;b^=(a<<16)&0xffffffff
        c=(c-a-b)&0xffffffff;c^=b>>5
        a=(a-b-c)&0xffffffff;a^=c>>3
        b=(b-c-a)&0xffffffff;b^=(a<<10)&0xffffffff
        c=(c-a-b)&0xffffffff;c^=b>>15
        return a,b,c
    n=len(k);A=B=0x9e3779b9;C=initval;i=0
    while n-i>=12:
        A=(A+k[i]+(k[i+1]<<8)+(k[i+2]<<16)+(k[i+3]<<24))&0xffffffff
        B=(B+k[i+4]+(k[i+5]<<8)+(k[i+6]<<16)+(k[i+7]<<24))&0xffffffff
        C=(C+k[i+8]+(k[i+9]<<8)+(k[i+10]<<16)+(k[i+11]<<24))&0xffffffff
        A,B,C=mix(A,B,C);i+=12
    C=(C+len(k))&0xffffffff;r=k[i:]+bytes(12)
    rl=len(k)-i
    A=(A+sum(r[j]<<(8*j) for j in range(min(rl,4))))&0xffffffff
    B=(B+sum(r[4+j]<<(8*j) for j in range(max(0,min(rl-4,4)))))&0xffffffff
    C=(C+sum(r[8+j]<<(8*(j+1)) for j in range(max(0,min(rl-8,3)))))&0xffffffff
    return mix(A,B,C)[2]
F=[x65599,fnv1a,fnv1,oaat,djb,sdbm,crc,crcs,lookup2]
def test(i):
    res=[]
    for d,e in ((a,'>'),(b,'<')):
        h,x,n,off=struct.unpack_from(e+'IHHI',d,S+0x408+12*i)
        idx=struct.unpack_from(e+'%dH'%n,d,S+off)
        parts={}
        recs=b'';vals=b'';blobs=b''
        for j in idx:
            r=d[P+12*j:P+12*j+12]; recs+=r
            t=d[P+12*j+6]; v=struct.unpack_from(e+'I',d,P+12*j+8)[0]
            if t in (12,14,15,5):
                L={12:16,14:16,15:64,5:16}[t]; xx=P+12*j+8+v; blobs+=d[xx:xx+L]; vals+=r[:8]+d[xx:xx+L]
            else: vals+=r
        parts={'blobs':blobs,'vals':vals,'recs':recs,'b0':blobs[:16]}
        res.append((h,parts))
    return res
for i in (1088,1131,1133,1058):
    for (h,parts) in test(i):
        for nm,bs in parts.items():
            for f in F:
                if f(bs)==h: print('HIT',i,nm,f.__name__)
print('done')
