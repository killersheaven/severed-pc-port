"""Dump all assets of a type from a stream. usage: dumptype.py TYPE OUTDIR be|le FILE [dat_offset size]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import strfile, port_str
T, out, endian, path = sys.argv[1:5]
os.makedirs(out, exist_ok=True)
f = open(path, 'rb')
if len(sys.argv) > 5:
    f.seek(int(sys.argv[5])); b = f.read(int(sys.argv[6]))
else:
    b = f.read()
n = 0
for a in strfile.assets(b, be=(endian == 'be'), decode=True):
    if port_str.type_of(a) != T: continue
    nm = port_str.name_of(a).split('\\')[-1]
    open(os.path.join(out, nm), 'wb').write(a['data']); n += 1
    print(len(a['data']), port_str.name_of(a), [hex(x) for x in a['shdr']['f'][:5]], hex(a['shdr']['w0']), a['shdr']['h'])
print(n, 'written')
