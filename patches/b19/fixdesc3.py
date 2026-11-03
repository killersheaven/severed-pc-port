"""b19c: fix ALL extra index-block descriptors (after the main IB descriptor) in Severed meshes, in place in DS2DAT3.
PC: {2*count, count, flags, block offset}; flags 0x00020002 (strips, A=2) / 0x00010002 (lists, A=1). fixdesc.py (b19b)
handled only the strip kind (PS3 0x20200); the list kind (PS3 bytes -> 0x20100, 23 descriptors: hospital doors,
gurney, wheelchair, windows) kept PS3 offsets (64 bytes off) and flags. Blocks = distinct (+0x88 - 2*start) of the
records other than the main IB, sorted; matched 1:1 to the extra descriptors in order.  usage: fixdesc2.py [--apply]"""
import json,struct,sys,os,collections
sys.path.insert(0,'port')
import strfile
G=os.path.expanduser('~/mnt/Dead Space 2'); APPLY='--apply' in sys.argv
st=json.load(open(G+'/_off/b19/repack_state.json'))
f=open(G+'/DS2DAT3.DAT','r+b' if APPLY else 'rb')
FIX={0x20200:0x20002,0x20002:0x20002,0x20100:0x10002,0x10002:0x10002}
def walk(b):
    try: return _walk(b)
    except Exception: return []
def _walk(b):
    cur=None; out=[]
    for i,sub,raw in strfile.chunks(b,False):
        if sub=='SHDR': cur={'shdr':strfile.read_shdr(raw,False),'segs':[],'data':b'','ok':True}; out.append(cur)
        elif cur is not None:
            if sub=='SDAT': cur['segs'].append((len(cur['data']),i+12,len(raw)-12)); cur['data']+=raw[12:]
            else: cur['ok']=False
    return out
def fileoff(a,o,base):
    for ds,fo,ln in a['segs']:
        if ds<=o and o+4<=ds+ln: return base+fo+(o-ds)
    return None
patches=[]; C=collections.Counter(); problems=[]
for o,s,hh,kind,p,so in st['index']:
    if kind not in ('file','dat'): continue
    f.seek(o); b=f.read(s)
    if kind=='dat': p='dat@%d'%o
    for a in walk(b):
        if not a['ok']: continue
        q=a['data'][:a['shdr']['usize']]
        if len(q)<0xA0 or q[:4]!=b'MGAE': continue
        U=lambda x: struct.unpack_from('<I',q,x)[0]
        try:
            ibat=U(0x6C); ibo=U(ibat+12); x=ibat+16; ex=[]
            while x+16<=len(q) and U(x+4) and U(x)==2*U(x+4) and U(x+8) in FIX: ex.append(x); x+=16
            if not ex: continue
            B=collections.defaultdict(int)
            for k in range(U(0x34)):
                rr=U(0x50)+0xC0*k; cnt,start=struct.unpack_from('<II',q,rr+0x30); p88=U(rr+0x88)
                if not (0<p88<len(q)): continue
                blk=p88-2*start
                if blk!=ibo: B[blk]=max(B[blk],start+cnt)
        except struct.error: continue
        nm=a['shdr']['name'].split(b'\0')[0].decode('latin1')
        C['meshes']+=1
        blocks=sorted(B.items())
        if len(blocks)!=len(ex): problems.append((p.split('/')[-1],nm[-50:],len(ex),[(hex(k),v) for k,v in blocks],[(U(e+4),hex(U(e+12))) for e in ex])); continue
        nrel,rel=U(0x48),U(0x4C)
        for j,(at,(bo,cnt)) in enumerate(zip(ex,blocks)):
            old=q[at:at+16]; new=struct.pack('<4I',2*cnt,cnt,FIX[U(at+8)],bo)
            if old==new: C['ok']+=1; continue
            fo=fileoff(a,at,o)
            if fo is None or fileoff(a,at+12,o)!=fo+12: problems.append((nm,'spans chunks')); continue
            patches.append(dict(file=fo,old=old.hex(),new=new.hex(),mesh=nm,desc=j,stream=p)); C['desc patched']+=1
            if C['desc patched']<=12: print(p.split('/')[-1],nm.split('\\')[-1],'desc',j,struct.unpack('<4I',old),'->',struct.unpack('<4I',new))
            for i in range(nrel):
                if U(rel+8*i)==at+12:
                    vo=fileoff(a,rel+8*i+4,o); oldv=q[rel+8*i+4:rel+8*i+8]; newv=struct.pack('<I',bo)
                    if oldv!=newv: patches.append(dict(file=vo,old=oldv.hex(),new=newv.hex(),mesh=nm,desc=j,reloc=True,stream=p)); C['reloc patched']+=1
print(dict(C),'problems',len(problems))
for pr in problems[:20]: print('  ',pr)
json.dump(patches,open('fixdesc3_patches.json','w'))
if APPLY and not problems:
    log=G+'/_off/b19/extra_ibdesc_patch3_log.json'; json.dump(patches,open(log,'w'))
    bad=0
    for pt in patches:
        f.seek(pt['file']); cur=f.read(len(pt['old'])//2)
        if cur.hex()!=pt['old']: print('MISMATCH skipped',pt); bad+=1; continue
        f.seek(pt['file']); f.write(bytes.fromhex(pt['new']))
    f.flush(); os.fsync(f.fileno())
    for pt in patches:
        f.seek(pt['file']); bad+= f.read(len(pt['new'])//2).hex()!=pt['new']
    print('applied',len(patches),'mismatches',bad,'log',log)
