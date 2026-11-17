#!/usr/bin/env python3
# 解析 Chromium simple-cache v3（WebView HTTP Cache）还原 H5 资源
#
# 用法: python src/webview_cache.py <HTTP Cache 目录> <outdir>
# 规则: 修改请直接改本文件；不要再往 out/ 里写一次性脚本。

import os, sys, struct, hashlib, json, gzip, io

EOFM = struct.pack('<Q', 0xF4FA6F45970D41D8)
MAGIC8 = b'\x30\x5c\x72\xa7\x1b\x6d\xfb\xfc'

def ascii_run(d, k):
    e = k
    n = len(d)
    while e < n and 32 <= d[e] < 127: e += 1
    return d[k:e].decode('latin1'), e

def sniff(body, ct):
    if body[:8] == b'\x89PNG\r\n\x1a\n': return '.png'
    if body[:3] == b'\xff\xd8\xff': return '.jpg'
    if body[:4] == b'RIFF': return '.webp'
    if body[:2] == b'\x1f\x8b': return '.gz'
    if body[:4] == b'DDS ': return '.dds'
    if body[:4] == b'\x00\x00\x02\x00': return '.ico'
    if body[:2] == b'BM': return '.bmp'
    t = body[:400].lstrip()
    if t[:1] in (b'{', b'['): return '.json'
    c = ct.lower()
    if 'html' in c: return '.html'
    if 'javascript' in c or 'ecmascript' in c: return '.js'
    if 'css' in c: return '.css'
    if 'json' in c: return '.json'
    if 'image' in c: return '.img'
    if t[:5] == b'<?xml': return '.xml'
    if t[:15].lower().find(b'<!doctype') >= 0: return '.html'
    return '.bin'

def parse(path):
    d = open(path, 'rb').read()
    if len(d) < 32 or d[0:8] != MAGIC8: return None
    k = d.find(b'http', 0, 96)
    if k < 0: return None
    key, pos = ascii_run(d, k)
    e = d.find(EOFM, pos)
    if e < 0: return None
    body = d[pos:e]
    meta = d[e:e + 20000]
    return {'url': key, 'body': body, 'meta': meta}

def ctype(meta):
    h = meta.lower()
    i = h.find(b'content-type:')
    if i < 0:
        i = h.find(b'content-type')
        if i < 0: return ''
    j = meta.find(b'\x00', i)
    if j < 0: j = min(len(meta), i + 100)
    return meta[i:j].decode('latin1').strip()

def main():
    src, dst = sys.argv[1], sys.argv[2]
    os.makedirs(dst, exist_ok=True)
    seen = {}
    for base, dirs, names in os.walk(src):
        for n in names:
            f = os.path.join(base, n)
            try: r = parse(f)
            except Exception: continue
            if not r: continue
            url = r['url']
            if not url.startswith('http'): continue
            old = seen.get(url)
            if old is not None and len(old['body']) >= len(r['body']): continue
            r['ct'] = ctype(r['meta'])
            seen[url] = r
    rows = []
    gz = 0
    for url, r in seen.items():
        body = r['body']
        if not body: continue
        if body[:2] == b'\x1f\x8b':
            try:
                body = gzip.decompress(body)
                gz += 1
            except Exception: pass
        u = url.split('?')[0].split('#')[0]
        base = u.rsplit('/', 1)[-1] or 'index.html'
        out = []
        for ch in base:
            out.append(ch if (ch.isalnum() or ch in '._-') else '_')
        base = ''.join(out)[:80]
        h = hashlib.md5(url.encode()).hexdigest()[:8]
        if '.' not in base:
            base = base + sniff(body, r['ct'])
        name = h + '_' + base
        open(os.path.join(dst, name), 'wb').write(body)
        rows.append({'file': name, 'url': url, 'type': r['ct'], 'size': len(body)})
    rows.sort(key=lambda x: -x['size'])
    json.dump(rows, open(os.path.join(dst, '_index.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('entries=%d saved=%d bytes=%d gunzip=%d' % (len(seen), len(rows), sum(x['size'] for x in rows), gz))

main()