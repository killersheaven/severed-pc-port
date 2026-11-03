import sys,struct
a=open(sys.argv[1]+'.ps3','rb').read();b=open(sys.argv[1]+'.pc','rb').read()
U=lambda o: struct.unpack_from('>I',a,o)[0]
S=(U(4)+15)&~15; P=S+U(S+24); N=U(S+28); E=S+U(S+16); NE=U(S+20)
print('S %x ent %x n%d prop %x n%d'%(S,E,NE,P,N))
for i in range(NE):
    h,x,n,off=struct.unpack_from('>IHHI',a,E+12*i); idx=struct.unpack_from('>%dH'%n,a,S+off)
    print('ent',i,'%08x'%h,x,n,idx)
for j in range(N):
    o=P+12*j; h,e,t,ii,v=struct.unpack_from('>IHBBI',a,o)
    x=(o+8+v)&0xffffffff
    print(' prop',j,'%08x e=%04x t=%d i=%d v=%08x -> %x'%(h,e,t,ii,v,x), a[x:x+20].hex(' ') if x<len(a) else '')
