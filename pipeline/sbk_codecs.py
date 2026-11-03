import os, sys, struct, collections, glob, json
sys.argv=[sys.argv[0],'x']
sys.path.insert(0,'.'); import port_str, strfile, fmt_sbk
W=os.path.expanduser('~/weller1')
def codecs(d, be):
    E='>' if be else '<'
    base=struct.unpack_from(E+'I',d,0x10)[0]; n=struct.unpack_from(E+'I',d,base+4)[0]
    out=[]
    for k in range(n):
        idx,mag,off,ff=struct.unpack_from(E+'IIII',d,base+8+16*k)
        p=base+off
        if p+8>len(d) or mag!=0x0313babe: out.append('BAD'); continue
        out.append('%02x' % d[p])
    return out
cnt=collections.Counter(); bad=0; nb=0
for p in sorted(glob.glob(W+'/**/*.str',recursive=True))[:int(sys.argv[1]) if False else 999]:
    for a in strfile.assets(open(p,'rb').read(),be=True,decode=True):
        if port_str.type_of(a)!='SBK': continue
        c=fmt_sbk.convert(a['data']); nb+=1
        for x in codecs(c,False): cnt[x]+=1
print('severed banks',nb,dict(cnt))
pc=collections.Counter()
for i in range(81):
    for x in codecs(open('pairs/SBK/%d.pc'%i,'rb').read(),False): pc[x]+=1
print('pc reference banks',dict(pc))
