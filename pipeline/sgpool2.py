import struct,collections,sys
a=open(sys.argv[1]+'.ps3','rb').read();b=open(sys.argv[1]+'.pc','rb').read()
S=0x214b0; P=S+0x3e10; N=0x100a
show=int(sys.argv[2]) if len(sys.argv)>2 else -1
seen=collections.Counter()
def isstr(d,x):
    e=d.find(b'\0',x); s=d[x:e]
    return e>=x and len(s)>0 and all(32<=c<127 for c in s)
for j in range(N):
    h,t,v=struct.unpack_from('>IxxBxI',a,P+12*j)
    x=(P+12*j+8+v)&0xffffffff
    if x>=len(a): continue
    k='str' if isstr(a,x) and a[x:x+32]==b[x:x+32] else 'bin'
    seen[(t,k)]+=1
    if t==show and seen[(t,k)]<=6:
        print(t,k,hex(v),a[x:x+20].hex(' '),'|',b[x:x+20].hex(' '))
print(sorted(seen.items()))
