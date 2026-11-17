# src/ — 可复用脚本

逆向分析用的**常驻脚本**放这里（入库）。约定：

- 先看下面的索引，有现成的就直接用/改它，**不要再往 `out/<项目名>/scripts/` 里重写一遍**。
- `out/<项目名>/scripts/` 只放一次性验证脚本（不复用、可随时丢）。
- 脚本自带用法头（`# 用法: ...`），统一用 `python` 跑；本仓库用 `tools\.venv\Scripts\python.exe`（3.12，含 capstone/pefile）。
- 纯标准库实现，不依赖 pip 安装；Windows 下输出统一 UTF-8。

## 索引

| 脚本 | 用途 | 用法 |
| --- | --- | --- |
| `apk_axml.py` | 解析 Android 二进制 AXML（Manifest、res 下 xml），打印缩进树 + 属性资源 ID | `python src\apk_axml.py <file.xml>` |
| `apk_res_dump.py` | 批量把整个 res 目录的 xml 转成可读文本（自动识别 AXML） | `python src\apk_res_dump.py <res目录> <out.txt>` |
| `apk_dex.py` | 纯 Python DEX 解析：导出全部字符串 / 类与方法清单 | `python src\apk_dex.py strings\|classes <out.txt> <classes.dex ...>` |
| `apk_disasm.py` | Dalvik 反汇编，按类名子串过滤，输出 const-string / invoke / 字段访问 | `python src\apk_disasm.py <out.txt> <类名子串1,子串2\|-> <classes.dex ...>` |
| `apk_findstr.py` | 跨 dex 找"谁引用了某个字符串"（定位 key、URL、action 名） | `python src\apk_findstr.py <关键字1,关键字2> <classes.dex ...>`（结果写 `./findstr_out.txt`） |
| `webview_cache.py` | 解析 Chromium simple-cache v3（WebView HTTP Cache），还原 H5 资源 + `_index.json` | `python src\webview_cache.py <HTTP Cache 目录> <outdir>` |
| `url_tree.py` | 按 `_index.json` 的真实 URL 把 hash 命名的产物还原成 `<host>/<path>` 目录树（离线，不联网） | `python src\url_tree.py <cache导出目录> <站点根目录>` |
| `egret_js_classes.py` | 从 Egret（或任意 minify）主 js 里抽 `__reflect` 类名清单 | `python src\egret_js_classes.py <main.min.js> <out.txt>` |
| `decrypt_aes_cfg.ps1` | 解 base64 + AES/PKCS7 的配置文件（渠道 xml 常见） | `powershell -NoProfile -File src\decrypt_aes_cfg.ps1 -Src x.xml -Dst plain.xml -Key <16/24/32字符>` |
| `unpack_wxapkg.py` | 微信小程序包解包（`.wxapkg` 或目录） | `python src\unpack_wxapkg.py <file.wxapkg\|目录> [outdir]` |

## 典型串联流程（H5 壳类游戏）

~~~text
7z e -o out\<proj> targets\apk\<x>.apk AndroidManifest.xml classes*.dex assets\*.xml
python src\apk_axml.py  out\<proj>\AndroidManifest.xml            # 壳/引擎/组件
python src\apk_dex.py   strings out\<proj>\strings_all.txt out\<proj>\classes*.dex
python src\apk_dex.py   classes out\<proj>\classes_all.txt out\<proj>\classes*.dex
python src\apk_findstr.py "H5GameUrl,AES_KEY,assets" out\<proj>\classes*.dex
python src\apk_disasm.py  out\<proj>\dis.txt "MainActivity,AppConfig" out\<proj>\classes*.dex
powershell -NoProfile -File src\decrypt_aes_cfg.ps1 -Src out\<proj>\assets\cfg.xml -Dst out\<proj>\plain.xml -Key <key>
# 运行时：adb shell su 0 tar -cf /sdcard/c.tar -C <app>/cache/WebView/Default . 然后 adb pull
python src\webview_cache.py out\<proj>\wvc\HTTP-Cache out\<proj>\assets
python src\url_tree.py     out\<proj>\assets out\<proj>\site
~~~

## 坑（写脚本前先看）

- `apk_dex.py` 的 DEX 解析：`code_item` 头是 `<HHHH` + `<II`（不是 `<IIIIII`）；类数据里 `virtual_methods` 的 `method_idx_diff` 累加器要重置；指令流要跳过 `0x0100/0x0200/0x0300` payload。
- `webview_cache.py` 的条目布局：magic 8 字节 + version/key_length/key_hash 各 4 字节 + 4 字节保留，**key（完整 URL）从偏移 24 开始**；key 之后是 **body**，再往后才是 HttpResponseInfo（顺序与直觉相反）。
- 不要用带 `\x` 转义的正则解析二进制（经 PowerShell 写盘易变双反斜杠）：手写字节扫描。
- PowerShell 下 `-In` / `-Iv` 这类参数名与公共参数别名冲突，脚本参数统一用 `-Src` / `-Dst`。

