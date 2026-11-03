"""Re-learn SimGroup hash/GUID maps from same-size base pairs in sg/v; keep only unanimous observations."""
import glob,struct,collections,json,sys
import fmt_simgroup as F
def slots(a):
    U=lambda o: struct.unpack_from('>I',a,o)[0]
    S=(U(4)+15)&~15; nh=struct.unpack_from('>H',a,0x14)[0]; nl=struct.unpack_from('>H',a,0x18)[0]; lt=U(0x10)
    return [0x3c+4*i for i in range(nh)]+[U(lt+4*i) for i in range(nl if lt else 0)]+[S+U(S+16)+12*i for i in range(U(S+20))]
H=collections.defaultdict(collections.Counter); Gm=collections.defaultdict(collections.Counter)
pairs=[]
for f in sorted(glob.glob('sg/v/*.ps3')):
    x=open(f,'rb').read(); y=open(f[:-4]+'.pc','rb').read()
    if len(x)!=len(y): continue
    pairs.append((x,y))
    try:
        for o in slots(x): H[struct.unpack_from('>I',x,o)[0]][struct.unpack_from('<I',y,o)[0]]+=1
        for g in F.guid_blobs(x): Gm[x[g:g+16]][y[g:g+16]]+=1
    except Exception as e: pass
hm={k:c.most_common(1)[0][0] for k,c in H.items() if len(c)==1}
gm={}
for k,c in Gm.items():
    if len(c)!=1: continue
    v=c.most_common(1)[0][0]; sw=b''.join(k[i:i+4][::-1] for i in range(0,16,4))
    gm[k]=v      # keep plain-swap entries too, so they override stale old entries
print('pairs',len(pairs),'hash keys',len(H),'unanimous',len(hm),'conflicting',len(H)-len(hm),'guid entries',len(gm),'conflicting g',sum(1 for c in Gm.values() if len(c)>1))
ok=sum(1 for x,y in pairs if F.convert(x,hm,gm)==y); print('exact with new maps',ok,'/',len(pairs))
ok2=sum(1 for x,y in pairs if F.convert(x)==y); print('exact with current filtered maps',ok2)
if '--save' in sys.argv:
    json.dump({'%08x'%k:'%08x'%v for k,v in hm.items()},open('simgroup_hashmap_v2.json','w'))
    json.dump({k.hex():v.hex() for k,v in gm.items()},open('simgroup_guidmap_v2.json','w'))
