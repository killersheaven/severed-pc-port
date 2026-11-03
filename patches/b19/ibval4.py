import os,sys,csv,struct,collections,importlib
sys.path.insert(0,os.path.expanduser('~/port'))
import strfile,port_str
fm=importlib.import_module(sys.argv[2] if len(sys.argv)>2 else 'fmt_mesh')
from ps3base import PS3Base
G=os.path.expanduser('~/mnt/Dead Space 2'); b=PS3Base(); C=collections.Counter(); meshes=0
def rtris(dat):
    U=lambda x: struct.unpack_from('<I',dat,x)[0]
    D=[dict(count=U(x+4),stride=struct.unpack_from('<H',dat,x+8)[0],off=U(x+12)) for x in range(U(0x68),U(0x6C)+16,16)]
    vg=[d for d in D[:-1] if d['stride']==12]; out=[]
    for k in range(U(0x34)):
        rr=U(0x50)+0xC0*k; cnt,start=struct.unpack_from('<II',dat,rr+0x30); prim=struct.unpack_from('<H',dat,rr+0x3C)[0]
        p84=U(rr+0x84); p88=U(rr+0x88)
        g=[d for d in vg if d['off']<=p84<d['off']+12*d['count']]
        if not g or p88+2*cnt>len(dat): out.append(None); continue
        pd=g[0]; seg=struct.unpack_from('<%dH'%(cnt+(2 if prim==5 else 0)),dat,p88) if p88+2*cnt+4<=len(dat) else struct.unpack_from('<%dH'%cnt,dat,p88)
        pos=lambda i: tuple(round(x,3) for x in struct.unpack_from('<3f',dat,pd['off']+12*i)) if i<pd['count'] else (1e9,1e9,float(i))
        T=set()
        if prim==5:
            seg=seg[:cnt]
            for t in range(len(seg)-2):
                a,b_,c=seg[t],seg[t+1],seg[t+2]
                if a==b_ or b_==c or a==c: continue
                if t&1: b_,c=c,b_
                x,y,z=pos(a),pos(b_),pos(c); T.add(min((x,y,z),(y,z,x),(z,x,y)))
        else:
            for t in range(0,cnt-2,3):
                x,y,z=pos(seg[t]),pos(seg[t+1]),pos(seg[t+2]); T.add(min((x,y,z),(y,z,x),(z,x,y)))
        out.append(T)
    return out
lim=int(sys.argv[1])
for r in csv.DictReader(open(G+'/pc_asset_index.csv',encoding='utf-8-sig')):
    if r['ext']!='Mesh': continue
    h=int(r['entry_hash'],16)
    if h not in b.index: continue
    f=open(G+'/DS2DAT%s.DAT'%r['dat'],'rb'); f.seek(int(r['entry_offset'])); pc=f.read(int(r['entry_size']))
    P={port_str.name_of(a).replace('.ps3','.win'):a['data'] for a in strfile.assets(b.read(h),True) if port_str.type_of(a)=='Mesh'}
    for a in strfile.assets(pc,False):
        if port_str.type_of(a)!='Mesh': continue
        m=P.get(port_str.name_of(a))
        if not m: continue
        q=a['data']
        try: o=fm.convert(m)
        except Exception as e: C['convert-error '+repr(e)[:60]]+=1; continue
        meshes+=1; lvl=port_str.name_of(a).split('\\')[-1].startswith('opt_model')
        for x,y in zip(rtris(o),rtris(q)):
            if y is None: C[('pc-unreadable',lvl)]+=1
            elif x==y: C[('match',lvl)]+=1
            elif x is None: C[('ours-unreadable',lvl)]+=1
            else:
                j=len(x&y); C[('mismatch','>99%' if j>=0.99*len(y) and len(x)<=len(y)*1.01 else '<99%',lvl)]+=1
                if C['shown']<5: C['shown']+=1; print(port_str.name_of(a)[-45:],'ours',len(x),'pc',len(y),'common',j,'rev-common',len({(t[0],t[2],t[1]) for t in x}&{(t[0],t[2],t[1]) for t in y}), sorted(x-y)[:1],sorted(y-x)[:1])
    if meshes>=lim: break
print(meshes,'meshes'); [print(v,k) for k,v in sorted(C.items(),key=str)]
