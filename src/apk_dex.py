#!/usr/bin/env python3
# 纯 Python DEX 解析：导出全字符串 / 类与方法清单
#
# 用法: python src/apk_dex.py strings|classes <out.txt> <classes.dex ...>
# 规则: 修改请直接改本文件；不要再往 out/ 里写一次性脚本。

import sys, struct, io

def uleb(d, p):
    r = 0; s = 0
    while True:
        b = d[p]; p += 1
        r |= (b & 0x7f) << s
        if not (b & 0x80):
            return r, p
        s += 7

class Dex:
    def __init__(self, path):
        self.path = path
        self.d = open(path, 'rb').read()
        d = self.d
        assert d[:4] == b'dex\n', d[:8]
        (self.string_ids_size, self.string_ids_off,
         self.type_ids_size, self.type_ids_off,
         self.proto_ids_size, self.proto_ids_off,
         self.field_ids_size, self.field_ids_off,
         self.method_ids_size, self.method_ids_off,
         self.class_defs_size, self.class_defs_off) = struct.unpack_from('<12I', d, 56)

    def string(self, i):
        off = struct.unpack_from('<I', self.d, self.string_ids_off + 4*i)[0]
        n, p = uleb(self.d, off)
        e = self.d.index(b'\x00', p)
        return self.d[p:e].decode('utf-8', 'replace')

    def type_name(self, i):
        sidx = struct.unpack_from('<I', self.d, self.type_ids_off + 4*i)[0]
        return self.string(sidx)

    def method(self, i):
        cls, proto, name = struct.unpack_from('<HHI', self.d, self.method_ids_off + 8*i)
        return self.type_name(cls), self.string(name), proto

    def proto_desc(self, pi):
        shorty, ret, params = struct.unpack_from('<III', self.d, self.proto_ids_off + 12*pi)
        out = self.type_name(ret)
        if params:
            n = struct.unpack_from('<I', self.d, params)[0]
            pl = [self.type_name(x) for x in struct.unpack_from('<%dH' % n, self.d, params + 4)]
            out += '(' + ','.join(pl) + ')'
        else:
            out += '()'
        return out

    def class_defs(self):
        for i in range(self.class_defs_size):
            yield struct.unpack_from('<8I', self.d, self.class_defs_off + 32*i)

    def class_data(self, off):
        p = off
        sf, p = uleb(self.d, p); inf, p = uleb(self.d, p)
        dm, p = uleb(self.d, p); vm, p = uleb(self.d, p)
        fields = []
        fidx = 0
        for _ in range(sf + inf):
            diff, p = uleb(self.d, p); acc, p = uleb(self.d, p)
            fidx += diff
            fields.append((fidx, acc))
        methods = []
        midx = 0
        for _ in range(dm):
            diff, p = uleb(self.d, p); acc, p = uleb(self.d, p); code, p = uleb(self.d, p)
            midx += diff
            methods.append((midx, acc, code))
        # NOTE: virtual methods restart their index accumulator (dexlib2 behaviour)
        midx = 0
        for _ in range(vm):
            diff, p = uleb(self.d, p); acc, p = uleb(self.d, p); code, p = uleb(self.d, p)
            midx += diff
            methods.append((midx, acc, code))
        return methods

def dump(paths, out):
    o = io.StringIO()
    for path in paths:
        dx = Dex(path)
        o.write('===DEX %s\n' % path)
        for st in range(dx.string_ids_size):
            try:
                o.write(dx.string(st).replace('\n', '\\n') + '\n')
            except Exception:
                pass
    open(out, 'w', encoding='utf-8').write(o.getvalue())

def classes(paths, out):
    o = io.StringIO()
    for path in paths:
        dx = Dex(path)
        o.write('===DEX %s (%d classes)\n' % (path, dx.class_defs_size))
        for cidx, acc, sup, ifaces, src, anno, cdata, sval in dx.class_defs():
            name = dx.type_name(cidx)
            supn = dx.type_name(sup) if sup != 0xffffffff else '-'
            o.write('CLASS %s extends %s\n' % (name, supn))
            if not cdata:
                continue
            try:
                for midx, macc, code in dx.class_data(cdata):
                    cn, mn, proto = dx.method(midx)
                    o.write('    M %s%s acc=0x%x code=0x%x\n' % (mn, dx.proto_desc(proto), macc, code))
            except Exception as e:
                o.write('    !!parse error %s at cdata 0x%x\n' % (e, cdata))
    open(out, 'w', encoding='utf-8').write(o.getvalue())

if __name__ == '__main__':
    mode = sys.argv[1]
    out = sys.argv[2]
    paths = sys.argv[3:]
    if mode == 'strings':
        dump(paths, out)
    elif mode == 'classes':
        classes(paths, out)