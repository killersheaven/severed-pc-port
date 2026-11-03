import os,sys,struct,collections,json,time
import strfile,port_str,fmt_simgroup
W=os.path.expanduser('~/mnt/weller1')
hm=fmt_simgroup.HASHMAP; gm=fmt_simgroup.GUIDMAP
c=collections.Counter(); t0=time.time(); os.makedirs('sg/sev',exist_ok=True)
for dp,dn,fn in os.walk(W):
    if 'clod' in dp: continue
    for f in fn:
        if not f.endswith('.str'): continue
        d=open(os.path.join(dp,f),'rb').read()
        for a in strfile.assets(d,be=True,decode=True):
            if port_str.type_of(a)!='SimGroup': continue
            x=a['data']; nm=port_str.name_of(a)
            open('sg/sev/'+nm.split('\\')[-1],'wb').write(x)
            U=lambda o: struct.unpack_from('>I',x,o)[0]
            S=(U(4)+15)&~15; P=S+U(S+24); E=S+U(S+16)
            nl=struct.unpack_from('>H',x,0x18)[0]; lt=U(0x10)
            for i in range(U(S+20)):
                h,_,n,off=struct.unpack_from('>IHHI',x,E+12*i)
                ts={x[P+12*j+6] for j in struct.unpack_from('>%dH'%n,x,S+off)}
                if ts & {12,13,14,15}: c['ent_blob_mapped' if h in hm else 'ent_blob_UNMAPPED']+=1
                else: c['ent_plain']+=1
            for i in range(nl if lt else 0):
                h=U(U(lt+4*i)); c['layout_mapped' if h in hm else 'layout_unmapped']+=1
            for g in fmt_simgroup.guid_blobs(x):
                p=x[g:g+16]
                if p[0:4]==p[4:8]==p[8:12]: c['hguid_mapped' if p in gm else 'hguid_UNMAPPED']+=1
                else: c['guid_plain']+=1
            c['files']+=1
print(dict(c), '%.0fs'%(time.time()-t0))
