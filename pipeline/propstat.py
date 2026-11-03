import os,struct,collections
c=collections.defaultdict(collections.Counter); ex={}
for fn in sorted(os.listdir('sg/v')):
    if not fn.endswith('.ps3'): continue
    a=open('sg/v/'+fn,'rb').read(); b=open('sg/v/'+fn[:-4]+'.pc','rb').read()
    if len(a)!=len(b): continue
    U=lambda o: struct.unpack_from('>I',a,o)[0]
    S=(U(4)+15)&~15; P=S+U(S+24); N=U(S+28)
    for j in range(N):
        o=P+12*j; t=a[o+6]; p=a[o+8:o+12]; q=b[o+8:o+12]
        k='same' if p==q else 'W' if p[::-1]==q else 'H' if p[1::-1]+p[:1:-1]==q else 'X'
        if p==p[::-1]: k='sym'
        c[t][k]+=1
        if k in('same','X') and (t,k) not in ex: ex[(t,k)]=(fn,hex(o),p.hex(),q.hex(),a[o+4:o+6].hex(),b[o+4:o+8].hex())
for t in sorted(c): print(t,dict(c[t]))
for k,v in ex.items(): print(k,v)
