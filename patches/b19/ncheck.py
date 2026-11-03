import os,sys,struct,statistics,glob,collections,math
sys.path.insert(0,os.path.expanduser('~/port'))
import strfile,port_str,fmt_mesh
p=glob.glob(os.path.expanduser('~/weller1/pdlc1_ch01_mng/**/drill_cavern_01.str'),recursive=True)[0]
A={}
for a in strfile.assets(open(p,'rb').read(),True):
    if port_str.name_of(a).endswith('pdlc_drill_cavern_01\\opt_model1.geo'): A[port_str.type_of(a)]=a['data']
m=A['Mesh']; v=A['MeshVolatile']
o=fmt_mesh.convert_volatile(v,m); mc=fmt_mesh.convert(m)
U=lambda o_: struct.unpack_from('<I',mc,o_)[0]
D=[]
for q in range(U(0x68),U(0x6C)+16,16): D.append(dict(count=U(q+4),stride=struct.unpack_from('<H',mc,q+8)[0],off=U(q+12),index=q==U(0x6C)))
ib=[x for x in D if x['index']][0]; idx=struct.unpack_from('<%dH'%ib['count'],mc,ib['off'])
vd=[x for x in D if x['count']==47416 and x['stride']==28][0]; base=vd['off']-len(mc)
pd=[x for x in D if x['count']==47416 and x['stride']==12][0]
P=lambda i: struct.unpack_from('<3f',mc,pd['off']+12*i)
def dec(b,mode):
    x=[(c/255*2-1) for c in b[:4]]
    return {'xyz':x[:3],'zyx':x[2::-1],'wzy':[x[3],x[2],x[1]],'yzw':x[1:4]}[mode]
def sub(a,b): return [a[k]-b[k] for k in range(3)]
def cross(a,b): return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def norm(a): l=math.sqrt(sum(x*x for x in a)) or 1; return [x/l for x in a]
for ln in open('draws.txt'):
    s,c=map(int,ln.split()); st=idx[s:s+c+2]
    R=collections.defaultdict(list); fn=[]
    for t in range(len(st)-2):
        a,b,cc=st[t],st[t+1],st[t+2]
        if a==b or b==cc or a==cc or max(a,b,cc)>=47416: continue
        if t&1: b,cc=cc,b
        f=norm(cross(sub(P(b),P(a)),sub(P(cc),P(a)))); fn.append(f)
        for mode in ('xyz','zyx','wzy','yzw'):
            nv=norm(dec(o[base+a*28+20:base+a*28+24],mode))
            R[mode].append(sum(f[k]*nv[k] for k in range(3)))
    if not fn: continue
    up=[round(statistics.mean(f[k] for f in fn),2) for k in range(3)]
    print('start%6d tris%5d facenormal mean %s  '%(s,len(fn),up)+'  '.join('%s %.2f'%(k,statistics.mean(v_)) for k,v_ in R.items()))
