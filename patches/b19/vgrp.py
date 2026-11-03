import os,sys,struct,statistics,math,collections
sys.path.insert(0,os.path.expanduser('~/port'))
def sub(a,b): return [a[k]-b[k] for k in range(3)]
def cross(a,b): return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def norm(a): l=math.sqrt(sum(x*x for x in a)) or 1; return [x/l for x in a]
def groups(mc,full):
    U=lambda x: struct.unpack_from('<I',mc,x)[0]
    D=[dict(i=j,count=U(q+4),stride=struct.unpack_from('<H',mc,q+8)[0],off=U(q+12),index=q==U(0x6C)) for j,q in enumerate(range(U(0x68),U(0x6C)+16,16))]
    G=[(D[i],D[i+1]) for i in range(len(D)-1) if D[i]['stride']==12 and D[i+1]['stride'] in (20,28) and D[i]['count']==D[i+1]['count']]
    ib=[x for x in D if x['index']][0]; idx=struct.unpack_from('<%dH'%ib['count'],full,ib['off'])
    out=[]
    for k in range(U(0x34)):
        rr=U(0x50)+0xC0*k; cnt,start=struct.unpack_from('<II',mc,rr+0x30)
        st=idx[start:start+min(cnt,600)+2]; best=(-1,None)
        for gi,(pd,vd) in enumerate(G):
            if max(st)>=pd['count']: continue
            no=20 if vd['stride']==28 else 12; R=[]
            P=lambda i: struct.unpack_from('<3f',full,pd['off']+12*i)
            for t in range(len(st)-2):
                a,b_,cc=st[t],st[t+1],st[t+2]
                if a==b_ or b_==cc or a==cc: continue
                if t&1: b_,cc=cc,b_
                fn=norm(cross(sub(P(b_),P(a)),sub(P(cc),P(a)))); nb=full[vd['off']+a*vd['stride']+no:vd['off']+a*vd['stride']+no+3]
                nv=norm([x/255*2-1 for x in nb]); R.append(sum(fn[i]*nv[i] for i in range(3)))
            if R:
                sc=sum(x>0.3 for x in R)/len(R)
                if sc>best[0]: best=(sc,gi)
        out.append((k,rr,best))
    return out,G
