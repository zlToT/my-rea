#!/usr/bin/env python3
# Dalvik 反汇编（按类名子串过滤，输出 const-string/invoke/字段访问）
#
# 用法: python src/apk_disasm.py <out.txt> <类名子串1,子串2|-> <classes.dex ...>
# 规则: 修改请直接改本文件；不要再往 out/ 里写一次性脚本。

import sys, struct, io
from apk_dex import Dex, uleb

SIZE = [1]*256
def _set(lo, hi, n):
    for i in range(lo, hi+1):
        SIZE[i] = n
for a, b, n in [(2,2,2),(3,3,3),(5,5,2),(6,6,3),(8,8,2),(9,9,3),(0x13,0x13,2),(0x14,0x14,3),(0x15,0x15,2),(0x16,0x16,2),(0x17,0x17,3),(0x18,0x18,5),(0x19,0x19,2),(0x1a,0x1a,2),(0x1b,0x1b,3),(0x1c,0x1c,2),(0x1f,0x20,2),(0x22,0x23,2),(0x24,0x26,3),(0x29,0x29,2),(0x2a,0x2c,3),(0x2d,0x3d,2),(0x44,0x6d,2),(0x6e,0x72,3),(0x74,0x78,3),(0x90,0xaf,2),(0xd0,0xd7,2),(0xd8,0xe2,2),(0xfa,0xfb,4),(0xfc,0xfd,3),(0xfe,0xff,2)]:
    _set(a, b, n)

FI = {}
for i, n in enumerate(['iget','iget-wide','iget-object','iget-boolean','iget-byte','iget-char','iget-short','iput','iput-wide','iput-object','iput-boolean','iput-byte','iput-char','iput-short','sget','sget-wide','sget-object','sget-boolean','sget-byte','sget-char','sget-short','sput','sput-wide','sput-object','sput-boolean','sput-byte','sput-char','sput-short']):
    FI[0x52+i] = n
MI = {}
for i, n in enumerate(['invoke-virtual','invoke-super','invoke-direct','invoke-static','invoke-interface']):
    MI[0x6e+i] = n
for i, n in enumerate(['invoke-virtual/range','invoke-super/range','invoke-direct/range','invoke-static/range','invoke-interface/range']):
    MI[0x74+i] = n
TI = {0x1c:'const-class',0x1f:'check-cast',0x20:'instance-of',0x22:'new-instance',0x23:'new-array',0x24:'filled-new-array',0x25:'filled-new-array/range'}
def S(dx, i):
    if 0 <= i < dx.string_ids_size:
        try:
            return dx.string(i)
        except Exception:
            pass
    return '?%d' % i

def field_str(dx, i):
    if not (0 <= i < dx.field_ids_size):
        return '?%d' % i
    c, t, n = struct.unpack_from('<HHI', dx.d, dx.field_ids_off + 8*i)
    return '%s->%s:%s' % (dx.type_name(c), S(dx, n), dx.type_name(t))

def payload_skip(dx, base, pc):
    tag = struct.unpack_from('<H', dx.d, base + pc*2)[0]
    if tag == 0x0100:
        size = struct.unpack_from('<H', dx.d, base + pc*2 + 2)[0]
        n = size*2 + 4
    elif tag == 0x0200:
        size = struct.unpack_from('<H', dx.d, base + pc*2 + 2)[0]
        n = size*4 + 2
    elif tag == 0x0300:
        w, cnt = struct.unpack_from('<HI', dx.d, base + pc*2 + 2)
        n = ((w*cnt + 1)//2)*2 + 4
    else:
        return None
    if n % 2:
        n += 1
    return n

def walk(dx, o, coff):
    regs, ins, outs, tries = struct.unpack_from('<HHHH', dx.d, coff)
    dbg, n = struct.unpack_from('<II', dx.d, coff + 8)
    off = coff + 16
    pc = 0
    while pc < n:
        pos = off + pc*2
        if pos + 2 > len(dx.d):
            o.write('      !! truncated\n')
            return
        op = dx.d[pos]
        if op == 0x00:
            skip = payload_skip(dx, off, pc)
            if skip:
                o.write('      0x%04x payload %d units\n' % (pc, skip))
                pc += skip
                continue
        w = SIZE[op]
        if pos + w*2 > len(dx.d):
            o.write('      !! truncated\n')
            return
        args = struct.unpack_from('<%dH' % w, dx.d, pos)
        line = None
        if op == 0x1a:
            line = 'const-string v%d "%s"' % ((args[1] >> 8) & 0xff, S(dx, args[1]))
        elif op == 0x1b:
            line = 'const-string/jumbo v%d "%s"' % ((args[1] >> 8) & 0xff, S(dx, struct.unpack_from('<I', dx.d, pos+2)[0]))
        elif op in TI:
            try:
                line = '%s %s' % (TI[op], dx.type_name(args[1]))
            except Exception:
                line = '%s ?%d' % (TI[op], args[1])
        elif op in FI:
            line = '%s v%d, %s' % (FI[op], (args[1] >> 8) & 0xff, field_str(dx, args[1]))
        elif op in MI:
            try:
                mc, mn, mp = dx.method(args[1])
                line = '%s {%04x}, %s->%s%s' % (MI[op], args[0], mc, mn, dx.proto_desc(mp))
            except Exception:
                line = '%s ?%d' % (MI[op], args[1])
        if line:
            o.write('      0x%04x %s\n' % (pc, line))
        pc += w

def dump(dexpath, pats, o):
    dx = Dex(dexpath)
    o.write('=== %s\n' % dexpath)
    for cidx, acc, sup, ifaces, src, anno, cdata, sval in dx.class_defs():
        name = dx.type_name(cidx)
        key = name[1:-1].lower() if name.endswith(';') else name.lower()
        if pats and not any(p.lower() in key for p in pats):
            continue
        o.write('\n===== CLASS %s extends %s\n' % (name, dx.type_name(sup) if sup != 0xffffffff else '-'))
        if not cdata:
            continue
        p = cdata
        sf, p = uleb(dx.d, p)
        inf, p = uleb(dx.d, p)
        dm, p = uleb(dx.d, p)
        vm, p = uleb(dx.d, p)
        fidx = 0
        for _ in range(sf + inf):
            diff, p = uleb(dx.d, p)
            a, p = uleb(dx.d, p)
            fidx += diff
            o.write('  F %s acc=0x%x\n' % (field_str(dx, fidx), a))
        groups = []
        midx = 0
        for _ in range(dm):
            diff, p = uleb(dx.d, p)
            a, p = uleb(dx.d, p)
            c, p = uleb(dx.d, p)
            midx += diff
            groups.append((midx, a, c))
        midx = 0
        for _ in range(vm):
            diff, p = uleb(dx.d, p)
            a, p = uleb(dx.d, p)
            c, p = uleb(dx.d, p)
            midx += diff
            groups.append((midx, a, c))
        for m, a, coff in groups:
            cn, mn, proto = dx.method(m)
            o.write('  --- %s%s acc=0x%x\n' % (mn, dx.proto_desc(proto), a))
            if coff:
                try:
                    walk(dx, o, coff)
                except Exception as e:
                    o.write('      !! %s\n' % e)

if __name__ == '__main__':
    out = sys.argv[1]
    pats = sys.argv[2].split(',') if sys.argv[2] != '-' else []
    o = io.StringIO()
    for dp in sys.argv[3:]:
        dump(dp, pats, o)
    open(out, 'w', encoding='utf-8').write(o.getvalue())
