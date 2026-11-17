#!/usr/bin/env python3
# 跨 dex 定位哪些方法引用了指定字符串
#
# 用法: python src/apk_findstr.py <关键字1,关键字2> <classes.dex ...>   # 结果写 ./findstr_out.txt
# 规则: 修改请直接改本文件；不要再往 out/ 里写一次性脚本。

import sys, struct
from apk_dex import Dex, uleb
import apk_disasm as D

def scan(path, needles, o):
    dx = Dex(path)
    hits = {}
    for i in range(dx.string_ids_size):
        try:
            s = dx.string(i)
        except Exception:
            continue
        if any(n in s for n in needles):
            hits[i] = s
    if not hits:
        return
    o.append('=== %s: %d matching strings' % (path, len(hits)))
    for cidx, acc, sup, ifaces, src, anno, cdata, sval in dx.class_defs():
        if not cdata:
            continue
        name = dx.type_name(cidx)
        p = cdata
        sf, p = uleb(dx.d, p); inf, p = uleb(dx.d, p)
        dm, p = uleb(dx.d, p); vm, p = uleb(dx.d, p)
        fidx = 0
        for _ in range(sf + inf):
            d1, p = uleb(dx.d, p); a, p = uleb(dx.d, p)
        groups = []
        midx = 0
        for _ in range(dm):
            d1, p = uleb(dx.d, p); a, p = uleb(dx.d, p); c, p = uleb(dx.d, p); midx += d1
            groups.append((midx, c))
        midx = 0
        for _ in range(vm):
            d1, p = uleb(dx.d, p); a, p = uleb(dx.d, p); c, p = uleb(dx.d, p); midx += d1
            groups.append((midx, c))
        for m, coff in groups:
            cn, mn, proto = dx.method(m)
            if not coff:
                continue
            regs, ins, outs, tries = struct.unpack_from('<HHHH', dx.d, coff)
            dbg, n = struct.unpack_from('<II', dx.d, coff + 8)
            base = coff + 16
            pc = 0
            while pc < n:
                pos = base + pc*2
                if pos + 2 > len(dx.d):
                    break
                op = dx.d[pos]
                if op == 0x00:
                    sk = D.payload_skip(dx, base, pc)
                    if sk:
                        pc += sk
                        continue
                w = D.SIZE[op]
                if pos + w*2 > len(dx.d):
                    break
                args = struct.unpack_from('<%dH' % w, dx.d, pos)
                idx = None
                if op == 0x1a:
                    idx = args[1]
                elif op == 0x1b:
                    idx = struct.unpack_from('<I', dx.d, pos+2)[0]
                if idx in hits:
                    o.append('%s -> %s%s : %s' % (name, mn, dx.proto_desc(proto), hits[idx]))
                pc += w

if __name__ == '__main__':
    needles = sys.argv[1].split(',')
    o = []
    for dp in sys.argv[2:]:
        scan(dp, needles, o)
    open('findstr_out.txt', 'w', encoding='utf-8').write('\n'.join(o))