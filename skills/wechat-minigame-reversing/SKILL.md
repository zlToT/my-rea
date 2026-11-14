---
name: wechat-minigame-reversing
description: "定位并解包微信小游戏 wxapkg（含雷电模拟器 WMPF 缓存），判断 LayaAir/Cocos/Egret/Unity 引擎，做静态分析与本地复刻。"
metadata:
  version: "1"
---

# 微信小游戏逆向

## 适用范围

用于目标是**微信小游戏**、手里只有 `wxapkg` 包、或模拟器里只有一个桌面快捷方式的情况。

典型场景：

- 雷电模拟器 9 里点开小游戏，但模拟器内没有安装微信；
- PC 微信的小程序/小游戏缓存；
- Android 微信的 `appbrand/pkg` 缓存（需 root）；
- 已有 `__WITHOUT_MULTI_PLUGINCODE__.wxapkg` 等分包，需要还原目录结构。

不适用于：原生 Android APK、Unity 独立包、纯服务端协议分析。遇到这些走 `reverse-engineer-anything` 的对应章节。

## 0. 先确认边界

- 只分析自己有权处理的样本；不传播素材、不做外挂/私服、不绕过服务端校验。
- 商业小游戏通常**服务端权威**：客户端逆向只能得到表现层、配置表、战斗演出，拿不到完整掉落/结算逻辑。
- 本仓库规则：安装/下载任何工具前先获得用户明确授权，见 `AGENTS.md`。

## 1. 判断运行形态

| 现象 | 运行形态 | 包在哪里 |
|---|---|---|
| 雷电桌面有图标，模拟器里没有微信 | 雷电 Windows 侧 WMPF | Windows `weixinsmallgameData\Applet\packages` |
| PC 微信里打开过 | PC 微信 Applet 缓存 | `WeChat Files\Applet\<appid>\<version>` |
| Android 微信里打开过 | Android WebView | `/data/data/com.tencent.mm/MicroMsg/<hash>/appbrand/pkg/` |
| 微信开发者工具项目 | 源码 | 项目目录，不需要解包 |

先判断形态，不要一上来就在模拟器 `/data/app` 里翻——那是 APK 安装目录，不是小游戏。

## 2. 找包

### 2.1 雷电模拟器（WMPF）

雷电 9 的微信小游戏由 Windows 侧的 `WeChatAppEx.exe` 运行，不在 Android 虚拟机内。

```powershell
Get-CimInstance Win32_Process -Filter "Name='WeChatAppEx.exe'" |
  Select-Object -ExpandProperty CommandLine
```

命令行里通常有：

```text
--wmpf_root_dir="D:\Program Files\leidian\LDPlayer9\weixinsmallgameData\"
```

包目录：

```text
<wmpf_root>\Applet\packages\<appid>\<version>\*.wxapkg
```

实例：

```text
D:\Program Files\leidian\LDPlayer9\weixinsmallgameData\Applet\packages\<appid>\48\
```

`<appid>` 可以从桌面快捷方式的 intent extras 里看：

```powershell
adb shell dumpsys package com.ld.wechat.minigame.<appid>
```

或者直接看 `weixinsmallgameData\Applet\packages` 下最近修改的目录。

**不要**在模拟器里找 `*.wxapkg`：`/data/app/com.android.flysilkworm-...` 这类目录是雷电应用商店的 APK 安装目录，与微信小游戏无关。

### 2.2 PC 微信

常见位置（以实际安装为准）：

```text
%USERPROFILE%\Documents\WeChat Files\Applet\<appid>\<version>\
```

直接搜：

```powershell
Get-ChildItem -Path $env:USERPROFILE -Recurse -Filter *.wxapkg -ErrorAction SilentlyContinue |
  Sort-Object LastWriteTime -Descending | Select-Object -First 20 FullName,Length,LastWriteTime
```

同一个小游戏可能保留多个版本目录，选与当前运行版本一致的那个；不确定就都解包，对比 `game.js` 大小/时间。

### 2.3 Android 微信（需 root）

```text
/data/data/com.tencent.mm/MicroMsg/<32位hash>/appbrand/pkg/
```

用 `adb root` 后 `adb pull`。没有 root 时，优先走 PC 微信或模拟器 WMPF。

## 3. 解包 wxapkg

### 3.1 容器格式

明文 wxapkg 的结构：

```text
0x00  1B   magic = 0xBE
0x01  4B   info1        # 有的变体是文件数，有的为 0
0x05  4B   indexLen     # 索引区长度
0x09  4B   bodyLen      # 数据区长度
0x0D  1B   mark = 0xED
0x0E  ...  索引区
...
          数据区
```

索引区有两种常见布局：

1. `info1 = 文件数`，索引从第一条 entry 开始；
2. `info1 = 0`，索引开头 4 字节是文件数。

每条 entry：

```text
uint32 nameLen
bytes  name          # 常见以 "/" 开头，如 "/data/rank.json"
uint32 offset
uint32 size
```

**关键坑：`offset` 是相对整个文件的绝对偏移，不是相对数据区。**
如果写成 `body[offset:offset+size]`，每个文件都会多跳过 `14 + indexLen` 字节，表现为：

- JSON 从中间开始，报 `预期为文件结尾`；
- `.lh` / `.ls` 解析失败；
- PNG 丢文件头，全部打不开。

正确写法：

```python
f.write(data[offset:offset+size])   # data 是整个文件
```

### 3.2 用仓库脚本

脚本：`tools/unpack_wxapkg.py`

```powershell
python tools\unpack_wxapkg.py "D:\path\to\48" "out\wechat-minigame\unpacked"
```

脚本会：

- 遍历目录下所有 `*.wxapkg`，每个包解到以包名命名的子目录；
- 自动识别两种索引布局；
- 自动识别 offset 是绝对偏移还是相对偏移；
- 用 PNG 头、JSON 首字符、JS 关键字、`sum(size)==bodyLen` 做校验打分；
- 跳过 `../` 路径，去掉名称开头的 `/`。

输出示例：

```text
__WITHOUT_MULTI_PLUGINCODE__.wxapkg -> ...\unpacked\__WITHOUT_MULTI_PLUGINCODE__
  layout: count=index-count, offsets=absolute, files=96
  ok: 96/96 files, 3092753 bytes
```

如果报 `not a plain wxapkg`，先确认文件头是不是 `BE ... ED`；不是则可能是加密包或别的格式，不要硬套。

### 3.3 解包后立刻验证

```python
import json, os
# 1) JSON / Laya 场景 / prefab 全部能 parse
for rel in ["data/rank.json", "scene/MainScene.ls", "prefab/boss.lh"]:
    json.loads(open(os.path.join(root, rel), "rb").read().decode("utf-8"))

# 2) PNG 魔数
assert open(png, "rb").read(8) == b"\x89PNG\r\n\x1a\n"

# 3) game.js 开头/结尾
print(open(js, "rb").read(120))
print(open(js, "rb").read()[-120:])
```

Windows 上批量验证 PNG 可以不用装 Pillow：

```powershell
Add-Type -AssemblyName System.Drawing
Get-ChildItem $img -Recurse -Filter *.png | ForEach-Object {
  try { $i=[System.Drawing.Image]::FromFile($_.FullName); $i.Dispose(); $ok++ }
  catch { $bad++ }
}
```

注意：`_resources_img_` 里的 `.atlas` 是图集元数据 JSON，不是图片；`AutoAtlas.png` 等是雪碧图，打开是大图属正常。

## 4. 判断引擎

| 引擎 | 特征文件/字符串 |
|---|---|
| LayaAir | `.ls` 场景、`.lh` prefab、`Laya.`、`Laya.Sprite`、`p.version="3.x.x"`、`laya.core.js` |
| Cocos Creator 2.x | `assets/main/index.*.js`、`cc.game`、`settings.js`、`project.json`、`cc.` |
| Cocos Creator 3.x | `application.js`、`assets/`、`cc.`、`settings.json` |
| Egret | `egret.`、`.exml`、`manifest.json`、`egret.Web` |
| Unity WebGL | `Build/UnityLoader.js`、`.wasm`、`.data.unityweb`、`UnityCache` |
| 自研/其他 | `game.js` + `adapter.js`，大量 `wx.*` 调用 |

本仓库案例「赵云与阿斗」是 **LayaAir 3.3.12**：

- `game.js` 开头 `define("js/bundle.js", ...)`；
- 14 个 `.ls` 场景、70+ `.lh` prefab；
- `Laya.Spine2DRenderNode`、`wx.*` 27 处。

## 5. 静态分析

1. 先把 `game.js` 格式化（有现成 prettier 再用，不要为此安装新包）：

   ```powershell
   pnpm exec prettier --write out\wechat-minigame\unpacked\__WITHOUT_MULTI_PLUGINCODE__\game.js
   node --check out\...\game.js
   ```

2. 找入口与关键函数：

   ```powershell
   Select-String -Path out\...\game.js -Pattern 'startGame|gameOver|BattleScene|onClick|wx\.' |
     Select-Object -First 80
   ```

3. Laya 场景用 JSON 思路读：

   - `scene/*.ls`：`_$id`、`_$type`、`_$props`、节点树；
   - `prefab/*.lh`：prefab 定义；
   - `data/*.json`：排行榜、武器、关卡等配置表。

4. 建立「入口 → 场景 → prefab → 数据表」的映射，写进 `notes/<project>/analysis.md`。

5. 压缩代码里保留的函数名（`startGame`、`gameOver`）通常还能直接搜到；先抓这些，再沿调用链展开。

## 6. 本地跑 / 动态调试

微信 WebView 接 DevTools 比较麻烦，常用做法是补 `wx.*` stub，在浏览器里跑 LayaAir/Cocos 构建产物。

最小 stub 思路：

```js
globalThis.wx = {
  getSystemInfoSync: () => ({ platform: 'devtools', screenWidth: 720, screenHeight: 1280, pixelRatio: 1 }),
  login: ({ success }) => success && success({ code: 'dev' }),
  createInnerAudioContext: () => ({ play(){}, pause(){}, stop(){}, destroy(){}, onEnded(){} }),
  onTouchStart(){}, onTouchMove(){}, onTouchEnd(){},
  getStorageSync: () => '', setStorageSync(){}, removeStorageSync(){},
  request: () => {}, connectSocket: () => {},
};
```

然后：

```powershell
python -m http.server 8000 -d out\wechat-minigame\unpacked\__WITHOUT_MULTI_PLUGINCODE__
```

用 Chrome 打开 `http://127.0.0.1:8000/`，看 Console/Network。

注意：

- 不要连生产环境接口；能断网就断网，或把请求 mock 掉；
- `game.js` 可能是 Laya 的 bundle，入口在 `js/index.js` / `game.js` 的 require 链里；
- 掉帧/黑屏先看资源路径大小写、`fileconfig.json`、图集是否解对。

## 7. 记录与复刻

目录约定（见 `notes/README.md`）：

```text
targets/<project>/          原始包（不入库）
out/<project>/unpacked/     解包产物
out/<project>/game/         复刻实现（如要做）
notes/<project>/analysis.md 逆向报告
```

报告至少写：

- 引擎与版本、包结构、入口文件；
- 场景/prefab/数据表清单；
- 关键流程（登录、开局、战斗、结算、存档）；
- 关键数值与公式；
- 与原版不一致的地方；
- 验证方式（截图、自动化、日志）。

复刻时把「原版逻辑 → 复刻实现」逐项对照，不要把复刻脚手架自己的 bug 写成原版 bug。

## 8. 常见坑

| 现象 | 原因 | 处理 |
|---|---|---|
| JSON 从中间开始、`预期为文件结尾` | offset 当成相对数据区 | 用 `data[off:off+size]` |
| PNG 全部打不开 | 同上，丢了文件头 | 重新解包 |
| `mkdir: embedded null character` | 文件名解析错/偏移错 | 检查 nameLen 与 offset 基准 |
| 索引解析失败 | `info1` 变体不同/加密包 | dump 前 64B，换布局或先解密 |
| 图片是大图 | 图集雪碧图 | 配 `.atlas` 切片，不是损坏 |
| 只看到一个小 `game.js` | 解到了图片分包 | 主包在 `__WITHOUT_MULTI_PLUGINCODE__.wxapkg` |
| `/data/app/...` 里没有 wxapkg | 那是 APK 安装目录 | 去 WMPF/PC 微信缓存找 |
| `am start` 报 Activity 不存在 | 只是雷电快捷方式，包未安装 | 走 Windows WMPF |

## 9. 验收清单

- [ ] 确认运行形态，找到真实包目录；
- [ ] 5 个（或 N 个）`*.wxapkg` 全部解包，文件数与大小合理；
- [ ] 所有 `.json` / `.ls` / `.lh` 可 parse；
- [ ] 所有 `.png` 可解码；
- [ ] `game.js` 开头/结尾完整；
- [ ] 引擎与版本已确认；
- [ ] `notes/<project>/analysis.md` 已写；
- [ ] 样本与产物没有提交进 git。

## 10. 相关文件

- `tools/unpack_wxapkg.py`：通用 wxapkg 解包器；
- `AGENTS.md`：仓库规则与 skill 索引；
- `notes/README.md`：notes 目录约定；
- `notes/web-mobile/analysis.md`：Cocos 2.x 小游戏复刻案例，可对照写法。
