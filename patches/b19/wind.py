import os,sys,struct,statistics,json,collections,math
sys.path.insert(0,os.path.expanduser('~/port'))
import strfile,port_str
G=os.path.expanduser('~/mnt/Dead Space 2')
def sub(a,b): return [a[k]-b[k] for k in range(3)]
def cross(a,b): return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def norm(a): l=math.sqrt(sum(x*x for x in a)) or 1; return [x/l for x in a]
def test(mc,full,nm,maxrec=4,out=None):
    U=lambda x: struct.unpack_from('<I',mc,x)[0]
    D=[dict(count=U(q+4),stride=struct.unpack_from('<H',mc,q+8)[0],off=U(q+12),index=q==U(0x6C)) for q in range(U(0x68),U(0x6C)+16,16)]
    g=[(D[i],D[i+1]) for i in range(len(D)-1) if D[i]['stride']==12 and D[i+1]['stride'] in(28,20) and D[i]['count']==D[i+1]['count']]
    ib=[x for x in D if x['index']][0]; idx=struct.unpack_from('<%dH'%ib['count'],full,ib['off'])
    for k in range(min(U(0x34),maxrec)):
        rr=U(0x50)+0xC0*k; cnt,start=struct.unpack_from('<II',mc,rr+0x30); prim=struct.unpack_from('<H',mc,rr+0x3C)[0]
        st=idx[start:start+cnt+2]; best=None
        for pd,vd in g:
            if max(st)>=pd['count']: continue
            P=lambda i: struct.unpack_from('<3f',full,pd['off']+12*i); R=[]
            no=20 if vd['stride']==28 else 12
            for t in range(len(st)-2):
                a,b_,cc=st[t],st[t+1],st[t+2]
                if a==b_ or b_==cc or a==cc: continue
                if t&1: b_,cc=cc,b_
                fn=norm(cross(sub(P(b_),P(a)),sub(P(cc),P(a)))); nb=full[vd['off']+a*vd['stride']+no:vd['off']+a*vd['stride']+no+3]
                nv=norm([x/255*2-1 for x in nb]); R.append(sum(fn[i]*nv[i] for i in range(3)))
            if len(R)>20:
                r=(sum(x>0 for x in R)/len(R),statistics.mean(abs(x) for x in R),len(R),pd['count'])
                if best is None or r[1]>best[1]: best=r
        if best: print(nm[-50:],'rec',k,'start',start,'pos-frac %.2f |dot| %.2f n%d grp%d'%best)
if __name__=='__main__':
    st=json.load(open(os.path.expanduser('~/b18/repack_state.json'))); f=open(G+'/DS2DAT3.DAT','rb')
    for o,s,hh,kind,p,so in st['index']:
        if kind!='file' or not any(x in p for x in sys.argv[1:]): continue
        f.seek(o); b=f.read(s); A=collections.defaultdict(dict)
        for a in strfile.assets(b,False):
            t=port_str.type_of(a)
            if t in('Mesh','MeshVolatile'): A[port_str.name_of(a)][t]=a['data']
        for nm,d in A.items():
            if 'Mesh' in d and 'MeshVolatile' in d and 'opt_model' in nm: test(d['Mesh'],d['Mesh']+d['MeshVolatile'],nm,30)
