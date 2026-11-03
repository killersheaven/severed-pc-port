import os,sys,csv,struct,collections,math,statistics
sys.path.insert(0,os.path.expanduser('~/port'))
import strfile,port_str
def sub(a,b): return [a[k]-b[k] for k in range(3)]
def cross(a,b): return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def norm(a): l=math.sqrt(sum(x*x for x in a)) or 1; return [x/l for x in a]
def analyse(q,full,verbose=False):
    U=lambda x: struct.unpack_from('<I',q,x)[0]
    D=[dict(count=U(x+4),stride=struct.unpack_from('<H',q,x+8)[0],off=U(x+12),idx=(x==U(0x6C))) for x in range(U(0x68),U(0x6C)+16,16)]
    ib=D[-1]; I=struct.unpack_from('<%dH'%ib['count'],full,ib['off'])
    pairs=[(D[i],D[i+1]) for i in range(len(D)-1) if D[i]['stride']==12 and D[i+1]['stride'] in(20,28) and D[i]['count']==D[i+1]['count']]
    C=collections.Counter()
    for k in range(U(0x34)):
        rr=U(0x50)+0xC0*k; cnt,start=struct.unpack_from('<II',q,rr+0x30); prim=struct.unpack_from('<H',q,rr+0x3C)[0]; p84=U(rr+0x84); p88=U(rr+0x88)
        g=[(pd,vd) for pd,vd in pairs if pd['off']<=p84<pd['off']+12*pd['count']]
        if not g: C['nogrp']+=1; continue
        pd,vd=g[0]; bv=(p84-pd['off'])//12; no=20 if vd['stride']==28 else 12
        res={}
        for sname,s0 in (('start',start),('p88',(p88-ib['off'])//2)):
            for bname,b0 in (('abs',0),('bv',bv)):
                seg=I[s0:s0+min(cnt,400)+2]; R=[]
                for t in range(len(seg)-2):
                    a,b_,c=seg[t]+b0,seg[t+1]+b0,seg[t+2]+b0
                    if a==b_ or b_==c or a==c or max(a,b_,c)>=pd['count']: continue
                    if t&1: b_,c=c,b_
                    pa,pb,pc_=[struct.unpack_from('<3f',full,pd['off']+12*i) for i in (a,b_,c)]
                    fn=norm(cross(sub(pb,pa),sub(pc_,pa)))
                    nv=norm([x/255*2-1 for x in full[vd['off']+a*vd['stride']+no:vd['off']+a*vd['stride']+no+3]]); R.append(sum(fn[i]*nv[i] for i in range(3)))
                res[sname+'/'+bname]=round(sum(x>0.3 for x in R)/len(R),2) if len(R)>5 else None
        ok=tuple(k_ for k_,v in res.items() if v and v>0.85)
        C[(('g%d'%pairs.index((pd,vd))), 'bv>0' if bv else 'bv0', ok)]+=1
        if verbose and not ok: print(k,start,cnt,bv,res)
    return C
if __name__=='__main__':
    G=os.path.expanduser('~/mnt/Dead Space 2'); n=0; T=collections.Counter()
    for r in csv.DictReader(open(G+'/pc_asset_index.csv',encoding='utf-8-sig')):
        if r['ext']!='Mesh' or not r['name'].startswith('opt_model') or r['dat']=='3': continue
        f=open(G+'/DS2DAT%s.DAT'%r['dat'],'rb'); f.seek(int(r['entry_offset'])); b=f.read(int(r['entry_size']))
        A=collections.defaultdict(dict)
        for a in strfile.assets(b,False):
            t=port_str.type_of(a)
            if t in('Mesh','MeshVolatile'): A[port_str.name_of(a)][t]=a['data']
        for nm,d in A.items():
            if 'Mesh' in d and 'opt_model' in nm:
                T+=analyse(d['Mesh'],d['Mesh']+d.get('MeshVolatile',b'')); n+=1
        if n>=int(sys.argv[1]): break
    for k,v in sorted(T.items(),key=str): print(v,k)
