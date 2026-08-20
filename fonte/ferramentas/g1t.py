# -*- coding: utf-8 -*-
"""Parser G1T (GT1G0600) - Koei Tecmo."""
import struct

FMT = {0x00:"RGBA8", 0x01:"RGBA8", 0x02:"RGBA8", 0x06:"BC1", 0x07:"BC2", 0x08:"BC3",
       0x09:"RGBA8", 0x0A:"RGBA8", 0x10:"BC4", 0x12:"BC5",
       0x59:"BC1", 0x5A:"BC2", 0x5B:"BC3", 0x5C:"BC4", 0x5D:"BC5", 0x5E:"BC6H", 0x5F:"BC7",
       0x60:"BC1", 0x62:"BC3", 0x72:"BC7", 0x71:"BC6H", 0x73:"BC7"}
BPB = {"BC1":8, "BC4":8, "BC2":16, "BC3":16, "BC5":16, "BC6H":16, "BC7":16}

def parse(d):
    assert d[:4] == b"GT1G"
    size, hsize, count, plat = struct.unpack("<4I", d[8:24])
    flags = struct.unpack("<%dI" % count, d[0x1C:0x1C + count*4])
    offs = struct.unpack("<%dI" % count, d[hsize:hsize + count*4])
    out = []
    for i, o in enumerate(offs):
        p = hsize + o
        mipsys, fmt, dxdy, b3 = d[p], d[p+1], d[p+2], d[p+3]
        extra = struct.unpack("<I", d[p+4:p+8])[0]
        w = 1 << (dxdy & 0xF); h = 1 << (dxdy >> 4)
        mips = mipsys >> 4
        hdr = 8
        if b3 & 0xF0:  # header estendido
            xs = struct.unpack("<I", d[p+8:p+12])[0]
            hdr = 8 + xs
        end = hsize + offs[i+1] if i+1 < count else size
        out.append(dict(i=i, off=p, data=p+hdr, end=end, fmt=fmt, name=FMT.get(fmt, "?%02x" % fmt),
                        w=w, h=h, mips=mips, b3=b3, extra=extra, nbytes=end-(p+hdr)))
    return dict(count=count, plat=plat, hsize=hsize, size=size, tex=out)
