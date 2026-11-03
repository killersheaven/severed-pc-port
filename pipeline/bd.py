import sys,importlib
m=importlib.import_module(sys.argv[1]); f=sys.argv[2]
a=open(f+'.ps3','rb').read();b=open(f+'.pc','rb').read();c=m.convert(a)
bad=[i for i in range(len(b)) if i>=len(c) or b[i]!=c[i]]
print(len(bad),'bad of',len(b))
shown=set()
for i in bad:
    r=i&~15
    if r in shown: continue
    shown.add(r)
    if len(shown)>int(sys.argv[3] if len(sys.argv)>3 else 8): break
    print('%05x'%r,a[r:r+16].hex(' ',4),'|',c[r:r+16].hex(' ',4),'|',b[r:r+16].hex(' ',4))
