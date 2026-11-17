#!/usr/bin/env python3
# 按 _index.json 里的真实 URL，把 webview_cache.py 的 hash 命名产物还原成原始目录树
#
# 用法: python src/url_tree.py <cache导出目录> <站点根目录>
#   <cache导出目录> 里要有 webview_cache.py 生成的 _index.json
# 结果: <站点根目录>/<host>/<path...>，文件名用服务器原名（去掉 hash 前缀）
# 只做本地复制，不联网；缺文件写 <站点根目录>/_missing.txt，自行按需补。

import json, os, shutil, sys
from urllib.parse import urlsplit, unquote

def main():
    if len(sys.argv) < 3:
        print("usage: url_tree.py <cache dir with _index.json> <site root>")
        return 2
    src, site = sys.argv[1], sys.argv[2]
    idx = json.load(open(os.path.join(src, "_index.json"), encoding="utf-8"))
    n = 0
    missing = []
    for r in idx:
        f = os.path.join(src, r["file"])
        if not os.path.exists(f):
            missing.append(r["url"])
            continue
        u = urlsplit(r["url"])
        path = unquote(u.path).lstrip("/")
        if not path or path.endswith("/"):
            path += "index"
        dst = os.path.join(site, u.netloc, *path.split("/"))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(f, dst)
        n += 1
    print("files=%d missing=%d -> %s" % (n, len(missing), site))
    if missing:
        open(os.path.join(site, "_missing.txt"), "w", encoding="utf-8").write("\n".join(missing) + "\n")
    return 0

if __name__ == "__main__":
    sys.exit(main())

