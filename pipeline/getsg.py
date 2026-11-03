import os,sys,csv,struct,strfile,port_str
from ps3base import PS3Base
G=os.path.expanduser('~/mnt/Dead Space 2'); want=sys.argv[1]; out=sys.argv[2]
b=PS3Base()
for r in csv.DictReader(open(os.path.join(G,'pc_asset_index.csv'),encoding='utf-8-sig')):
    if r['ext']=='SimGroup' and r['name'].lower()==want.lower():
        f=open(os.path.join(G,'DS2DAT%s.DAT'%r['dat']),'rb'); f.seek(int(r['entry_offset'])); pc=f.read(int(r['entry_size']))
        ps3=b.read(int(r['entry_hash'],16))
        for d,be,ext in ((ps3,True,'.ps3'),(pc,False,'.pc')):
            for a in strfile.assets(d,be=be,decode=True):
                if port_str.name_of(a).lower()==want.lower(): open(out+ext,'wb').write(a['data'])
        break
