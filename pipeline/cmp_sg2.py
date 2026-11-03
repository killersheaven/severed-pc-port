import sys,struct,fmt_simgroup
a=open(sys.argv[1]+'.ps3','rb').read();b=open(sys.argv[1]+'.pc','rb').read()
# learn hashmap from this pair: hash slots
U=lambda o: struct.unpack_from('>I',a,o)[0]
S=U(4)+8; nh=struct.unpack_from('>H',a,0x14)[0]; nl=struct.unpack_from('>H',a,0x18)[0]; lt=U(0x10)
slots=[0x3c+4*i for i in range(nh)]+[U(lt+4*i) for i in range(nl)]+[S+U(S+16)+12*i for i in range(U(S+20))]
hm={}
for o in slots: hm[U(o)]=struct.unpack_from('<I',b,o)[0]
c=fmt_simgroup.convert(a,hm)
bad=[i for i in range(len(b)) if c[i]!=b[i]]
print(len(bad),'bytes differ; hashmap entries changed:',sum(1 for k,v in hm.items() if k!=v))
runs=[];s=None;p=None
for i in bad:
    if s is None: s=p=i
    elif i<=p+4: p=i
    else: runs.append((s,p));s=p=i
if s is not None: runs.append((s,p))
print(len(runs),'runs')
for s,p in runs[:int(sys.argv[2]) if len(sys.argv)>2 else 30]:
    print(hex(s),p-s+1,a[s-4:p+5].hex(' '),'|',c[s-4:p+5].hex(' '),'|',b[s-4:p+5].hex(' '))
