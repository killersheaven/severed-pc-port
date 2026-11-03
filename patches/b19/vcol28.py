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
b=PS3Base(); t0=time.time(); res=collections.Counter(); bytec=collections.Counter(); ex=[]
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
            pcv={}
            for i in range(N): pcv.setdefault(q[base+i*s+4:base+i*s+20],i)
            for i in range(N):
                j=pcv.get(o[base+i*s+4:base+i*s+20])
                if j is None: res['uv-nomatch']+=1; continue
                for w,kind in enumerate('SWWWWNS'):
                    a_=o[base+i*s+4*w:base+i*s+4*w+4]; b_=q[base+j*s+4*w:base+j*s+4*w+4]
                    res[(w,kind,a_==b_)]+=1
                    if w==6 and a_!=b_:
                        src=v[base+i*s:base+i*s+4]
                        for perm in ((3,2,1,0),(1,2,3,0),(3,0,1,2),(2,1,0,3),(0,3,2,1)):
                            if bytes(src[k] for k in perm)==b_: bytec[perm]+=1
                        if len(ex)<8: ex.append((nm[-40:],src.hex(),a_.hex(),b_.hex()))
print(sorted(res.items(),key=str)); print('color perms matching PC',bytec.most_common()); [print(e) for e in ex]
