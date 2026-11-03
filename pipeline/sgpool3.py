import struct,collections,sys
a=open(sys.argv[1]+'.ps3','rb').read();b=open(sys.argv[1]+'.pc','rb').read()
S=0x214b0; P=S+0x3e10; N=0x100a
for j in range(N):
    h,t,v=struct.unpack_from('>IxxBxI',a,P+12*j)
    if t in (15,22,2,10,0,7,5):
        x=(P+12*j+8+v)&0xffffffff
        n=0
        while x+4*n+4<=len(a) and a[x+4*n:x+4*n+4]==b[x+4*n:x+4*n+4][::-1] and a[x+4*n:x+4*n+4]!=a[x+4*n:x+4*n+4][::-1]: n+=1
        print(t,hex(v),'x=%x'%x,'swapwords',n, a[x:x+8].hex())
