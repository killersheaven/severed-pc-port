"""Find NAV assets in DS2DAT3 Severed streams with a bad checksum; plan in-place literal patches in Rpak data."""
import os,sys,json,struct
sys.path.insert(0,os.path.expanduser('~/port'))
import strfile,port_str,fmt_nav
from refpack import _py_refpack as dec
G=os.path.expanduser('~/mnt/Dead Space 2'); DAT=G+'/DS2DAT3.DAT'
def track(d):
    flags=d[0]; n=4 if flags&0x80 else 3; p=2+(n if flags&1 else 0); p+=n; src=[]
    while p<len(d):
        b0=d[p]
        if b0<0x80: lit=b0&3; ln=((b0>>2)&7)+3; p+=2
        elif b0<0xC0: lit=d[p+1]>>6; ln=(b0&0x3F)+4; p+=3
        elif b0<0xE0: lit=b0&3; ln=((b0&0x0C)<<6)+d[p+3]+5; p+=4
        elif b0<0xFC: lit=((b0&0x1F)<<2)+4; ln=0; p+=1
        else:
            lit=b0&3; p+=1; src+=list(range(p,p+lit)); break
        src+=list(range(p,p+lit)); p+=lit; src+=[-1]*ln
    return src
st=json.load(open(os.path.expanduser('~/b18/repack_state.json')))
plan=[]; stats={'nav':0,'ok':0,'bad_raw':0,'bad_rpak':0}
f=open(DAT,'rb')
for o,s,hh,kind,p,so in st['index']:
    if kind!='file': continue
    f.seek(o); b=f.read(s)
    cur=None; navs=[]
    for i,sub,raw in strfile.chunks(b,False):
        if sub=='SHDR': cur={'shdr':strfile.read_shdr(raw,False),'raw':raw,'parts':[]}; navs.append(cur)
        else: cur['parts'].append((i,sub,raw))
    for a in navs:
        aa={'shdr':a['shdr'],'hdr_raw':a['raw']}
        if port_str.type_of(aa)!='NAV': continue
        stats['nav']+=1
        out=b''; 
        for i,sub,raw in a['parts']:
            k,dd=strfile.data_of(sub,raw,False); out+= dd if k=='raw' else dec(dd)
        out=out[:a['shdr']['usize']]
        want=fmt_nav.nav_checksum(out); have=struct.unpack_from('<I',out,0x34)[0]
        if want==have: stats['ok']+=1; continue
        i,sub,raw=a['parts'][0]; k,dd=strfile.data_of(sub,raw,False)
        name=port_str.name_of(aa)
        if k=='raw': stats['bad_raw']+=1; print('RAW bad',name); continue
        stats['bad_rpak']+=1
        src=track(dd); pos=src[0x34:0x38]; nb=struct.pack('<I',want)
        if -1 in pos: print('NONLITERAL',name,pos); continue
        dd2=bytearray(dd)
        for q,c in zip(pos,nb): dd2[q]=c
        new=dec(bytes(dd2)); exp=bytearray(dec(dd)); exp[0x34:0x38]=nb
        okv=new==bytes(exp)
        base=o+i+16   # Rpak payload starts at raw[16]
        plan.append({'name':name,'abs':[base+q for q in pos],'old':dd[pos[0]:pos[0]+1].hex() if False else [dd[q] for q in pos],'new':list(nb),'verified':okv,'have':'%08x'%have,'want':'%08x'%want})
        print('PLAN',name,okv,'%08x->%08x'%(have,want))
print(stats)
json.dump(plan,open('navfix_plan.json','w'),indent=1)
