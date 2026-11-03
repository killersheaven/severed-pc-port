"""Build 19: re-convert Severed Mesh assets with the multi-index-block fix (fmt_mesh 2026-10-18). Reads each Severed
stream from the installed DS2DAT3 (keeps all in-place patches), replaces Mesh assets that equal the old converter's
output, writes changed streams to patch_out/<rel>. Resumable, time-budgeted."""
import os,sys,json,struct,time
sys.path.insert(0,os.path.expanduser('~/port'))
import strfile,port_str,fmt_mesh,fmt_mesh_b18
G=os.path.expanduser('~/mnt/Dead Space 2'); W=os.path.expanduser('~/weller1')
SF='b19_state.json'
st=json.load(open(os.path.expanduser('~/b18/repack_state.json')))
S=json.load(open(SF)) if os.path.exists(SF) else {'done':[],'log':{}}
t0=time.time(); budget=float(sys.argv[1]) if len(sys.argv)>1 else 150
f=open(G+'/DS2DAT3.DAT','rb')
for o,s,hh,kind,p,so in st['index']:
    if kind!='file' or p in S['done']: continue
    if time.time()-t0>budget: break
    rel=p[len('patch_out/'):]
    f.seek(o); b=f.read(s)
    src=open(os.path.join(W,rel),'rb').read()
    PM={}
    for a in strfile.assets(src,True,True):
        if port_str.type_of(a)=='Mesh': PM.setdefault(port_str.name_of(a),a['data'])
    A=strfile.assets(b,False,True); items=[]; c={'replaced':0,'kept':0,'unmatched':0}
    for a in A:
        if port_str.type_of(a)=='Mesh':
            nm=port_str.name_of(a); m=PM.get(nm) or PM.get(nm.replace('.win','.ps3'))
            if m is not None and fmt_mesh_b18.convert(m)==a['data']:
                d=fmt_mesh.convert(m)
                if d!=a['data']:
                    h=bytearray(a['hdr_raw']); struct.pack_into('<I',h,40,len(d)); items.append((bytes(h),d)); c['replaced']+=1; continue
                c['kept']+=1
            else: c['unmatched']+=1
        items.append((a['hdr_raw'],a['data']))
    if c['replaced']:
        out=os.path.join('patch_out',rel); os.makedirs(os.path.dirname(out),exist_ok=True)
        open(out,'wb').write(port_str.write_pc_str(items,b[8:12]))
    S['done'].append(p); S['log'][rel]=c
    json.dump(S,open(SF,'w'))
tot={k:sum(v[k] for v in S['log'].values()) for k in ('replaced','kept','unmatched')}
print('streams %d/%d'%(len(S['done']),sum(1 for e in st['index'] if e[3]=='file')),tot)
