import os,sys,csv,collections,struct,time
sys.path.insert(0,os.path.expanduser('~/port'))
import strfile,port_str,fmt_mesh
from ps3base import PS3Base
G=os.path.expanduser('~/mnt/Dead Space 2')
streams=[];seen=set()
for r in csv.DictReader(open(os.path.join(G,'pc_asset_index.csv'),encoding='utf-8-sig')):
    if r['ext']=='MeshVolatile' and r['name'].startswith('opt_model'):
        k=(r['dat'],int(r['entry_offset']),int(r['entry_size']),int(r['entry_hash'],16))
        if k not in seen: seen.add(k); streams.append(k)
b=PS3Base(); S=[]; C=collections.Counter(); t0=time.time(); res=collections.Counter(); bytec=collections.Counter(); ex=[]
for dat,off,size,h in streams[::7]:
    if time.time()-t0>140 or h not in b.index: continue
    f=open(os.path.join(G,'DS2DAT%s.DAT'%dat),'rb'); f.seek(off); pc=f.read(size)
    P=collections.defaultdict(dict)
    for a in strfile.assets(b.read(h),be=True,decode=True):
        t=port_str.type_of(a)
        if t in('Mesh','MeshVolatile'): P[port_str.name_of(a).replace('.ps3','.win')][t]=a['data']
    for a in strfile.assets(pc,be=False,decode=True):
        if port_str.type_of(a)!='MeshVolatile': continue
        nm=port_str.name_of(a); d=P.get(nm)
        if not d or 'Mesh' not in d or 'MeshVolatile' not in d: continue
        m=d['Mesh']; v=d['MeshVolatile']; q=a['data']; o=fmt_mesh.convert_volatile(v,m); n=len(m)
        for ds in fmt_mesh.descriptors(m):
            if ds['index'] or ds['off']<n or (ds["stride"],ds["A"],ds["B"])!=(28,0,2): continue
            s=28; base=ds['off']-n; N=ds['count']
            for i in range(N):
                if q[base+i*s+4:base+i*s+20]!=o[base+i*s+4:base+i*s+20]: C['order-diff']+=1; continue
                C['same']+=1
                S.append((v[base+i*s+20:base+i*s+28].hex(), q[base+i*s+20:base+i*s+28].hex(), o[base+i*s+20:base+i*s+28].hex()))
import json; json.dump(S[:400000],open('nt_pairs.json','w')); print(C, len(S))
