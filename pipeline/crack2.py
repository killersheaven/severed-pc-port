import struct
from crack import F
cases=[('>',0x21187daf,0x6b4e739c),('<',0x1d8415f7,0xa50db85a),('>',0x56b1dbea,0x7bd5c340),('>',0xe37e8c0b,0x11803e62),('<',0xf1f79453,None)]
for e,h,k in cases:
    for nb in (4,8,12):
        bs=struct.pack(e+'I',h)*(nb//4)
        for f in F:
            for bb in (bs,bs[::-1]):
                if f(bb)==k: print('HIT',e,hex(h),nb,f.__name__)
print('done')
