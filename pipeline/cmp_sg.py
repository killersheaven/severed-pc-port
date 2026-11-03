import sys,fmt_simgroup
a=open(sys.argv[1]+'.ps3','rb').read();b=open(sys.argv[1]+'.pc','rb').read()
c=fmt_simgroup.convert(a,{})
bad=[i for i in range(len(b)) if c[i]!=b[i]]
print(len(bad),'bytes differ')
import itertools
runs=[];s=None;p=None
for i in bad:
    if s is None: s=p=i
    elif i<=p+4: p=i
    else: runs.append((s,p));s=p=i
if s is not None: runs.append((s,p))
print(len(runs),'runs')
for s,p in runs[:int(sys.argv[2]) if len(sys.argv)>2 else 30]:
    print(hex(s),p-s+1,a[s-4:p+5].hex(' '),'|',c[s-4:p+5].hex(' '),'|',b[s-4:p+5].hex(' '))
