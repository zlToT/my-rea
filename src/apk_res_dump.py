#!/usr/bin/env python3
# 把一整个 res 目录的 xml 批量转成可读文本（AXML 自动识别）
#
# 用法: python src/apk_res_dump.py <res目录> <out.txt>
# 规则: 修改请直接改本文件；不要再往 out/ 里写一次性脚本。

import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from apk_axml import parse_axml

MAGIC = b'\x03\x00\x08\x00'

def render(path):
    out = []
    for kind, depth, tag, attrs in parse_axml(path):
        pad = '  ' * depth
        if kind == 'start':
            s = pad + '<' + tag
            if attrs:
                out.append(s)
                for k, v in attrs:
                    out.append(pad + '    ' + k + '=' + str(v))
                # closing bracket deferred to end event
            else:
                out.append(s + '>')
        else:
            out.append(pad + '</' + tag + '>')
    return '\n'.join(out)

def main():
    root = sys.argv[1]
    dst = sys.argv[2]
    files = []
    for base, dirs, names in os.walk(root):
        for n in sorted(names):
            if n.lower().endswith('.xml'):
                files.append(os.path.join(base, n))
    buf = []
    ok = bad = 0
    for f in files:
        head = open(f, 'rb').read(4)
        buf.append('=' * 70)
        buf.append('FILE: ' + os.path.relpath(f, root) + '  (' + str(os.path.getsize(f)) + ' bytes)')
        if head == MAGIC:
            try:
                buf.append(render(f))
                ok += 1
            except Exception as e:
                buf.append('!! parse failed: ' + repr(e))
                bad += 1
        else:
            try:
                buf.append(open(f, 'r', encoding='utf-8', errors='replace').read())
                ok += 1
            except Exception as e:
                buf.append('!! read failed: ' + repr(e))
                bad += 1
    with open(dst, 'w', encoding='utf-8') as fp:
        fp.write('\n'.join(buf))
    print('files=%d ok=%d bad=%d -> %s' % (len(files), ok, bad, dst))

if __name__ == '__main__':
    main()
