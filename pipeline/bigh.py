"""Write an EA BIGH archive (Dead Space 2 PC DAT format)."""
import struct
def x65599(name):
    h=0
    for c in name.encode('latin1'): h=(h*65599+c)&0xffffffff
    return h
def write_bigh(path, files):
    """files: list of (name_or_hash, bytes). Returns index list."""
    items=[(x65599(n) if isinstance(n,str) else n, d) for n,d in files]
    items.sort(key=lambda t:t[0])
    hsz=16+12*len(items)+8  # index + 'L283' footer, as in retail DATs
    off=(hsz+0x7ff)&~0x7ff
    index=[]; body=bytearray()
    for h,d in items:
        index.append((off+len(body),len(d),h))
        body+=d
        body+=b'\0'*((-len(body))%0x800)
    total=off+len(body)
    out=bytearray(b'BIGH'+struct.pack('<I',total)+struct.pack('>II',len(items),hsz))
    for o,s,h in index: out+=struct.pack('>III',o,s,h)
    out+=bytes.fromhex('4c32383315050000')
    out+=b'\0'*(off-len(out)); out+=body
    assert len(out)==total
    open(path,'wb').write(out)
    return index
