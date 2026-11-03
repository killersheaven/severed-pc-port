import os,sys,csv,struct,collections,importlib
sys.path.insert(0,os.path.expanduser('~/port'))
import strfile,port_str,fmt_mesh
from ps3base import PS3Base
G=os.path.expanduser('~/mnt/Dead Space 2'); b=PS3Base(); C=collections.Counter(); meshes=0
def tris(ib,ibbase,start,cnt,prim,pos):
    seg=ib[ibbase+start:ibbase+start+cnt+(2 if prim==5 else 0)]; T=set()
    if prim==5:
        for t in range(len(seg)-2):
            a,b_,c=seg[t],seg[t+1],seg[t+2]
            if a==b_ or b_==c or a==c: continue
            if t&1: b_,c=c,b_
            T.add((pos(a),pos(b_),pos(c)))
    else:
        for t in range(0,len(seg)-2,3): T.add((pos(seg[t]),pos(seg[t+1]),pos(seg[t+2])))
    return {min((x,y,z),(y,z,x),(z,x,y)) for x,y,z in T}   # winding-preserving canonical form
def parse(q):
    U=lambda x: struct.unpack_from('<I',q,x)[0]
    D=[dict(count=U(x+4),stride=struct.unpack_from('<H',q,x+8)[0],off=U(x+12),idx=(x==U(0x6C))) for x in range(U(0x68),U(0x6C)+16,16)]
    ib=D[-1]; return U,D,ib
lim=int(sys.argv[1]) if len(sys.argv)>1 else 40
for r in csv.DictReader(open(G+'/pc_asset_index.csv',encoding='utf-8-sig')):
    if r['ext']!='Mesh' or not r['name'].startswith('opt_model'): continue
    h=int(r['entry_hash'],16)
    if h not in b.index: continue
    f=open(G+'/DS2DAT%s.DAT'%r['dat'],'rb'); f.seek(int(r['entry_offset'])); pc=f.read(int(r['entry_size']))
    P=collections.defaultdict(dict)
    for a in strfile.assets(b.read(h),True):
        if port_str.type_of(a) in('Mesh','MeshVolatile'): P[port_str.name_of(a).replace('.ps3','.win')][port_str.type_of(a)]=a['data']
    for a in strfile.assets(pc,False):
        if port_str.type_of(a)!='Mesh': continue
        pm=P.get(port_str.name_of(a))
        if not pm or 'Mesh' not in pm: continue
        m=pm['Mesh']; q=a['data']
        try: o=fmt_mesh.convert(m)
        except Exception as e: C['convert-error '+type(e).__name__]+=1; continue
        meshes+=1
        res=[]
        for name,dat in (('ours',o),('pc',q)):
            U,D,ib=parse(dat); I=struct.unpack_from('<%dH'%ib['count'],dat,ib['off'])
            vg=[d for d in D if not d['idx'] and d['stride']==12]
            out=[]
            for k in range(U(0x34)):
                rr=U(0x50)+0xC0*k; cnt,start=struct.unpack_from('<II',dat,rr+0x30); prim=struct.unpack_from('<H',dat,rr+0x3C)[0]
                p84=U(rr+0x84); p88=U(rr+0x88)
                g=[d for d in vg if d['off']<=p84<d['off']+12*d['count']]
                gbase=(p88-ib['off'])//2-start
                if not g or not (0<=gbase<=ib['count']): out.append(('nogroup',)); continue
                pd=g[0]
                pos=lambda i,pd=pd,dat=dat: struct.unpack_from('<3f',dat,pd['off']+12*i) if i<pd['count'] else ('OOR',i)
                pos2=lambda i,pd=pd,dat=dat: tuple(round(x,3) for x in pos(i)) if i<pd['count'] else ('OOR',i)
                out.append(tris(I,gbase,start,cnt,prim,pos2))
            res.append(out)
        multi=any(x for x in res[1])
        for k,(x,y) in enumerate(zip(*res)):
            C[('match' if x==y else 'MISMATCH')]+=1
    if meshes>=lim: break
print(meshes,'meshes',dict(C))
