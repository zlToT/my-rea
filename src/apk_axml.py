#!/usr/bin/env python3
# 解析 Android 二进制 AXML（AndroidManifest.xml、res 下的 xml）
#
# 用法: python src/apk_axml.py <file.xml>
# 规则: 修改请直接改本文件；不要再往 out/ 里写一次性脚本。
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


import sys, struct

def parse_string_pool(d, off):
    typ, hsize, csize = struct.unpack_from('<HHI', d, off)
    cnt, styc, flags, sstart, sstyle = struct.unpack_from('<IIIII', d, off+8)
    utf8 = (flags & 0x100) != 0
    offs = struct.unpack_from('<%dI' % cnt, d, off + hsize)
    base = off + sstart
    out = []
    for o in offs:
        p = base + o
        if utf8:
            n = d[p]; p += 1
            if n & 0x80:
                p += 1
            n2 = d[p]; p += 1
            if n2 & 0x80:
                p += 1
            e = d.index(b'\x00', p)
            out.append(d[p:e].decode('utf-8', 'replace'))
        else:
            n = struct.unpack_from('<H', d, p)[0]; p += 2
            if n & 0x8000:
                n = ((n & 0x7fff) << 16) | struct.unpack_from('<H', d, p)[0]; p += 2
            e = p + n * 2
            out.append(d[p:e].decode('utf-16-le', 'replace'))
    return out

def parse_axml(path):
    d = open(path, 'rb').read()
    typ, hsize, total = struct.unpack_from('<HHI', d, 0)
    off = hsize
    strings = []
    resmap = []
    events = []
    stack = []
    while off < total:
        ctype, chsize, csize = struct.unpack_from('<HHI', d, off)
        if csize == 0:
            break
        if ctype == 0x0001:
            strings = parse_string_pool(d, off)
        elif ctype == 0x0180:
            n = (csize - chsize) // 4
            resmap = list(struct.unpack_from('<%dI' % n, d, off + chsize))
            resmap = [0x01000000 + ((r >> 16) & 0xff) * 0 for r in resmap]
        elif ctype == 0x0102:
            nsidx, nameidx = struct.unpack_from('<iI', d, off + 16)
            astart, asize, acount = struct.unpack_from('<HHH', d, off + 20 + 4)
            attrs = []
            p = off + 16 + astart
            for i in range(acount):
                ans, aname, araw, atyp, adata = struct.unpack_from('<iiIHB', d, p)
                p += 20
                nm = strings[aname] if 0 <= aname < len(strings) else '?'
                rid = resmap[aname] if 0 <= aname < len(resmap) else None
                if rid:
                    nm = '%s(%08x)' % (nm, rid)
                if araw != -1 and araw < len(strings):
                    val = strings[araw]
                elif atyp == 0x03:
                    val = strings[adata] if adata < len(strings) else '?'
                elif atyp == 0x12:
                    val = 'true' if adata else 'false'
                elif atyp == 0x01:
                    val = '0x%08x' % adata
                else:
                    val = str(adata)
                attrs.append((nm, val))
            tag = strings[nameidx]
            events.append(('start', len(stack), tag, attrs))
            stack.append(tag)
        elif ctype == 0x0103:
            stack.pop()
            events.append(('end', len(stack), strings[struct.unpack_from('<I', d, off + 20)[0]], []))
        off += csize
    return events

if __name__ == '__main__':
    for ev in parse_axml(sys.argv[1]):
        kind, depth, tag, attrs = ev
        pad = '  ' * depth
        if kind == 'start':
            print('%s<%s>' % (pad, tag))
            for k, v in attrs:
                print('%s    %s = %s' % (pad, k, v))
        else:
            print('%s</%s>' % (pad, tag))
