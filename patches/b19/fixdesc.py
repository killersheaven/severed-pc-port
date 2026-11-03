"""b19b: fix the extra index-block descriptors (after the main IB descriptor at u32[0x6C]) in Severed level meshes,
in place in DS2DAT3. PC layout (verified on 40 base-PC meshes): {2*count, count, 0x00020002, block offset}, one per
extra vertex group, block = the index block the group's records point to (+0x88 - 2*start). fmt_mesh (b19) moved/re-
stripped the blocks but left these with PS3 offset/size and flags 0x20200 -> engine built wrong IBs -> invisible floors.
usage: fixdesc.py [--apply]"""
import json,struct,sys,os,collections
sys.path.insert(0,'port')
import strfile,port_str
G=os.path.expanduser('~/mnt/Dead Space 2'); APPLY='--apply' in sys.argv
st=json.load(open(G+'/_off/b19/repack_state.json'))
f=open(G+'/DS2DAT3.DAT','r+b' if APPLY else 'rb')
patches=[]; C=collections.Counter(); problems=[]
def walk(b):
    cur=None; out=[]
    for i,sub,raw in strfile.chunks(b,False):
        if sub=='SHDR':
            cur={'shdr':strfile.read_shdr(raw,False),'segs':[],'data':b'','ok':True}; out.append(cur)
        elif cur is not None:
            if sub=='SDAT': cur['segs'].append((len(cur['data']),i+12,len(raw)-12)); cur['data']+=raw[12:]
            else: cur['ok']=False
    return out
def fileoff(a,o,base):
    for ds,fo,ln in a['segs']:
        if ds<=o<ds+ln:
            if o+4>ds+ln: return None          # field spans chunks: refuse
            return base+fo+(o-ds)
    return None
for o,s,hh,kind,p,so in st['index']:
    if kind!='file': continue
    f.seek(o); b=f.read(s)
    for a in walk(b):
        if not a['ok']: continue
        a['name']=a['shdr']['name']
        q=a['data'][:a['shdr']['usize']]
        if len(q)<0xA0 or q[:4]!=b'MGAE': continue
        U=lambda x: struct.unpack_from('<I',q,x)[0]
        try:
            ibat=U(0x6C); x=ibat+16; ex=[]
            while x+16<=len(q) and U(x+8) in (0x20002,0x20200) and U(x+4) and U(x)==2*U(x+4): ex.append(x); x+=16
        except struct.error: continue
        if not ex: continue
        C['meshes with extra descs']+=1
        nm=a['shdr']['name'].split(b'\0')[0].decode('latin1')
        pos=[(U(y+12),U(y+4)) for y in range(U(0x68),ibat,16) if struct.unpack_from('<H',q,y+8)[0]==12]
        ibo,ibc=U(ibat+12),U(ibat+4)
        B=collections.defaultdict(lambda:[0,set()])
        for k in range(U(0x34)):
            rr=U(0x50)+0xC0*k; w=struct.unpack_from('<48I',q,rr); p84,p88=w[33],w[34]; cnt,start=w[12],w[13]
            if not (0<p88<len(q)): continue
            blk=p88-2*start
            if blk==ibo: continue
            g=[i for i,(po,c) in enumerate(pos) if po<=p84<po+12*c]
            B[blk][0]=max(B[blk][0],start+cnt); B[blk][1].add(g[0] if g else -1)
        blocks=sorted(B.items())
        gl=[next(iter(v[1])) if len(v[1])==1 else None for k,v in blocks]
        if len(blocks)!=len(ex) or None in gl or gl!=sorted(gl) or len(set(gl))!=len(gl):
            problems.append((nm,len(ex),[(hex(k),v[0],sorted(v[1])) for k,v in blocks])); continue
        nrel,rel=U(0x48),U(0x4C)
        for j,(at,(bo,(cnt,_))) in enumerate(zip(ex,blocks)):
            old=q[at:at+16]; new=struct.pack('<4I',2*cnt,cnt,0x20002,bo)
            if old==new: C['already ok']+=1; continue
            fo=fileoff(a,at,o)
            if fo is None or fileoff(a,at+12,o)!=fo+12: problems.append((nm,'desc spans chunks')); continue
            patches.append(dict(file=fo,old=old.hex(),new=new.hex(),mesh=nm,desc=j,stream=p))
            C['desc patched']+=1
            for i in range(nrel):
                if U(rel+8*i)==at+12:
                    vo=fileoff(a,rel+8*i+4,o); oldv=q[rel+8*i+4:rel+8*i+8]; newv=struct.pack('<I',bo)
                    if oldv!=newv: patches.append(dict(file=vo,old=oldv.hex(),new=newv.hex(),mesh=nm,desc=j,reloc=True,stream=p)); C['reloc patched']+=1
            if C['desc patched']<=8: print(nm[-70:],'desc',j,'old',struct.unpack('<4I',old),'new',struct.unpack('<4I',new))
print(dict(C)); print('problems',len(problems))
for pr in problems[:15]: print('  ',pr)
json.dump(patches,open('fixdesc_patches.json','w'))
if APPLY:
    log=G+'/_off/b19/extra_ibdesc_patch_log.json'
    json.dump(patches,open(log,'w'))
    for pt in patches:
        f.seek(pt['file']); cur=f.read(len(pt['old'])//2)
        if cur.hex()!=pt['old']: print('MISMATCH, skipped',pt); continue
        f.seek(pt['file']); f.write(bytes.fromhex(pt['new']))
    f.flush(); os.fsync(f.fileno())
    bad=0
    for pt in patches:
        f.seek(pt['file']); bad+= f.read(len(pt['new'])//2).hex()!=pt['new']
    print('applied',len(patches),'verify mismatches',bad,'log',log)
