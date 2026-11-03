import os,struct,collections,sys
T=[int(x) for x in sys.argv[1].split(',')]
k=0
for fn in sorted(os.listdir('sg/v')):
    if not fn.endswith('.ps3'): continue
    a=open('sg/v/'+fn,'rb').read(); b=open('sg/v/'+fn[:-4]+'.pc','rb').read()
    if len(a)!=len(b): continue
    U=lambda o: struct.unpack_from('>I',a,o)[0]
    S=(U(4)+15)&~15; P=S+U(S+24); N=U(S+28)
    for j in range(N):
        o=P+12*j; t=a[o+6]
        if t in T and U(o+8) and k<int(sys.argv[2]):
            k+=1; x=(o+8+U(o+8))&0xffffffff
            print(t,fn[:25],'v=%x'%U(o+8),a[x:x+24].hex(' ',4),'|',b[x:x+24].hex(' ',4))
