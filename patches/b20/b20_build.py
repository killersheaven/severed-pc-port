"""Build 20: re-convert broken Severed meshes in streams build 19 never touched (kind 'dat' in the b19 repack index).
A Mesh is replaced only if (a) its records fall outside its IB descriptors (stale layout), (b) the fresh fmt_mesh
conversion of the PS3 source passes the check, (c) vertex descriptors (count, stride, A, B) are unchanged.
usage: b20_build.py [--write]   (writes patch_out/<rel>)"""
import json,struct,sys,os,collections
sys.path.insert(0,os.path.expanduser('~/port/port')); sys.path.insert(0,os.path.expanduser('~/port'))
import strfile,port_str,fmt_mesh
import importlib.util as _iu
_sp=_iu.spec_from_file_location('fmt_mesh_b20',os.path.expanduser('~/port/fmt_mesh.py')); fmt_mesh=_iu.module_from_spec(_sp); _sp.loader.exec_module(fmt_mesh)
print('fmt_mesh from',fmt_mesh.__file__)
G=os.path.expanduser('~/mnt/Dead Space 2'); W=os.path.expanduser('~/mnt/weller1'); WRITE='--write' in sys.argv
M=json.load(open(os.path.expanduser('~/port/dat_streams.json')))
def check(q):
    U=lambda x: struct.unpack_from('<I',q,x)[0]
    ibat=U(0x6C); descs=[(U(ibat+12),U(ibat+4))]; x=ibat+16
    while x+16<=len(q) and U(x+4) and U(x)==2*U(x+4): descs.append((U(x+12),U(x+4))); x+=16
    bad=0
    for k in range(U(0x34)):
        rr=U(0x50)+0xC0*k; cnt,start=struct.unpack_from('<II',q,rr+0x30); p88=U(rr+0x88)
        if not (0<p88<len(q)): continue
        d=[dd for dd in descs if dd[0]==p88-2*start]
        if not d or start+cnt>d[0][1]: bad+=1
    return bad
def vdescs(q):
    U=lambda x: struct.unpack_from('<I',q,x)[0]
    return [(U(y+4),q[y+8:y+12]) for y in range(U(0x68),U(0x6C),16)]
f=open(G+'/DS2DAT3.DAT','rb'); log={}
for o,s,rel in M:
    f.seek(o); b=f.read(s)
    try: A=strfile.assets(b,False,True)
    except Exception: continue
    if not any(port_str.type_of(a)=='Mesh' for a in A): continue
    src=open(os.path.join(W,rel.replace('\\','/')),'rb').read()
    PM={}
    for a in strfile.assets(src,True,True):
        if port_str.type_of(a)=='Mesh': PM.setdefault(port_str.name_of(a),[]).append(a['data'])
    items=[]; c=collections.Counter(); seen=collections.Counter()
    for a in A:
        if port_str.type_of(a)=='Mesh':
            nm=port_str.name_of(a); q=a['data']
            if q[:4]==b'MGAE' and check(q):
                cands=PM.get(nm) or PM.get(nm.replace('.win','.ps3')) or []
                k=seen[nm]; seen[nm]+=1
                pick=None
                for m in ([cands[k]] if k<len(cands) else [])+cands:
                    try: d=fmt_mesh.convert(m)
                    except Exception as e: continue
                    if check(d)==0 and vdescs(d)==vdescs(q): pick=d; break
                if pick is not None:
                    h=bytearray(a['hdr_raw']); struct.pack_into('<I',h,40,len(pick)); items.append((bytes(h),pick)); c['replaced']+=1
                    print('  ',rel.split('\\')[-1],nm,'bad recs',check(q),'-> 0; size',len(q),'->',len(pick)); continue
                c['broken, no valid replacement']+=1; print('  !!',rel.split('\\')[-1],nm,'broken, no valid replacement (cands %d)'%len(cands))
            elif q[:4]==b'MGAE': c['ok']+=1
        items.append((a['hdr_raw'],a['data']))
    log[rel]=dict(c)
    if c['replaced'] and WRITE:
        out=os.path.join('patch_out',rel.replace('\\','/')); os.makedirs(os.path.dirname(out),exist_ok=True)
        open(out,'wb').write(port_str.write_pc_str(items,b[8:12]))
json.dump(log,open('b20_log.json','w'),indent=1)
print('TOTAL',dict(sum((collections.Counter(v) for v in log.values()),collections.Counter())))
