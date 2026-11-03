"""Learn SimGroup hash map (PS3->PC) from all base-game pairs and check structure conversion.
Resumable: state in learn_sg_state.json. usage: learn_sg.py BUDGET_S"""
import os, sys, csv, collections, struct, time, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import strfile, port_str, fmt_simgroup
from ps3base import PS3Base
T='SimGroup'; budget=float(sys.argv[1]) if len(sys.argv)>1 else 160
DUMP='--dump' in sys.argv
G = os.path.expanduser('~/mnt/Dead Space 2')
st = json.load(open('learn_sg_state.json')) if os.path.exists('learn_sg_state.json') else {'k':0,'map':{},'ok':0,'bad':[],'conf':0,'seen':[],'miss':0}
hm = {int(k,16):int(v,16) for k,v in st['map'].items()}; gmap={bytes.fromhex(k):bytes.fromhex(v) for k,v in st.get('gmap',{}).items()}; st.setdefault('gconf',0); seen=set(st['seen'])
streams = []
for r in csv.DictReader(open(os.path.join(G, 'pc_asset_index.csv'), encoding='utf-8-sig')):
    if r['ext'] == T:
        k=(r['dat'], int(r['entry_offset']), int(r['entry_size']), int(r['entry_hash'], 16))
        if k not in streams: streams.append(k)
b = PS3Base(); t0=time.time()
def slots(a):
    U=lambda o: struct.unpack_from('>I',a,o)[0]
    S=(U(4)+15)&~15; nh=struct.unpack_from('>H',a,0x14)[0]; nl=struct.unpack_from('>H',a,0x18)[0]; lt=U(0x10)
    return [0x3c+4*i for i in range(nh)]+[U(lt+4*i) for i in range(nl if lt else 0)]+[S+U(S+16)+12*i for i in range(U(S+20))]
k=st['k']
while k < len(streams) and time.time()-t0 < budget:
    dat, off, size, h = streams[k]; k+=1
    if h not in b.index: st['miss']+=1; continue
    f = open(os.path.join(G, 'DS2DAT%s.DAT' % dat), 'rb'); f.seek(off); pc = f.read(size)
    ps3 = b.read(h)
    P = {port_str.name_of(a): a['data'] for a in strfile.assets(ps3, be=True, decode=True) if port_str.type_of(a) == T}
    for a in strfile.assets(pc, be=False, decode=True):
        if port_str.type_of(a) != T: continue
        nm = port_str.name_of(a)
        if nm not in P or nm in seen: continue
        seen.add(nm); x=P[nm]; y=a['data']
        if DUMP and len(x)<40000:
            bn=nm.split('\\')[-1]; open('sg/v/'+bn+'.ps3','wb').write(x); open('sg/v/'+bn+'.pc','wb').write(y)
        try:
            loc={}
            for o in slots(x):
                loc[struct.unpack_from('>I',x,o)[0]]=struct.unpack_from('<I',y,o)[0]
            gl={}
            for g in fmt_simgroup.guid_blobs(x):
                p,q=x[g:g+16],y[g:g+16]
                sw=b''.join(p[i:i+4][::-1] for i in range(0,16,4))
                if q!=sw: gl[p]=q
            for p,q in gl.items():
                if p in gmap and gmap[p]!=q: st['gconf']+=1
                gmap[p]=q
            o2=fmt_simgroup.convert(x,loc,gl)
            if o2==y: st['ok']+=1
            else:
                fd=next((i for i in range(min(len(o2),len(y))) if o2[i]!=y[i]),None)
                st['bad'].append([nm,len(x),len(y),fd])
            for p,q in loc.items():
                if p in hm and hm[p]!=q: st['conf']+=1
                hm[p]=q
        except Exception as e:
            st['bad'].append([nm,len(x),len(y),repr(e)])
st['k']=k; st['seen']=sorted(seen); st['map']={'%08x'%p:'%08x'%q for p,q in hm.items()}; st['gmap']={p.hex():q.hex() for p,q in gmap.items()}
json.dump(st,open('learn_sg_state.json','w'))
print('gmap %d gconf %d'%(len(gmap),st['gconf'])); print('streams %d/%d ok %d bad %d conflicts %d map %d (changed %d) miss %d %.0fs'%(k,len(streams),st['ok'],len(st['bad']),st['conf'],len(hm),sum(1 for p,q in hm.items() if p!=q),st['miss'],time.time()-t0))
for x in st['bad'][:10]: print(' BAD',x)
