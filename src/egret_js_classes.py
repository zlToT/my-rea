#!/usr/bin/env python3
# 从 Egret/任意 minify 的主 js 抽取 __reflect 类名清单
#
# 用法: python src/egret_js_classes.py <main.min.js> <out.txt>
# 规则: 修改请直接改本文件；不要再往 out/ 里写一次性脚本。

import sys, collections

D = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = sys.argv[1]
OUT = sys.argv[2]
Q = chr(34); S = chr(39)
d = open(SRC, encoding="utf-8", errors="replace").read()

names = []
i = 0
while True:
    j = d.find("__reflect(", i)
    if j < 0: break
    k = d.find(Q, j)
    s = d.find(S, j)
    if k < 0: break
    if 0 <= s < k:
        k = s; q = S
    else:
        q = Q
    e = d.find(q, k + 1)
    if e > k and e - k < 200:
        names.append(d[k+1:e])
    i = j + 10
seen = []
set_ = set()
for n in names:
    if n not in set_:
        set_.add(n); seen.append(n)
print("reflect calls", len(names), "uniq", len(seen))
g = collections.Counter()
for n in seen:
    g[n.split("_")[0]] += 1
lines = ["# class inventory", ""]
lines.append("classes=%d" % len(seen))
lines.append("")
for k2, v in g.most_common(50):
    lines.append("prefix %-24s %d" % (k2, v))
lines.append("")
lines.extend(sorted(seen))
open(OUT, "w", encoding="utf-8").write(chr(10).join(lines))
print("wrote", OUT, len(lines))
print("first 20:", seen[:20])