# 微信小游戏「赵云与阿斗」逆向记录

## 1. 结论速览

- 目标：微信小游戏「赵云与阿斗」，appid `<appid>`，本地缓存版本号 `48`。
- 引擎：**LayaAir 3.3.12**，构建产物为微信小游戏 `game.js` + `.ls` 场景 + `.lh` prefab + `resources` 资源分包。
- 样本：5 个 `wxapkg`，合计 12,848,785 字节；已复制到 `targets/wechat-minigame/<appid>/48/`。
- 解包：5 个包全部解包成功，共 344 个文件；主包 96 个文件、3,092,753 字节；JSON、场景、prefab、PNG 均已抽样或全量校验。
- 关键发现：小游戏包**不在 Android 模拟器里**。雷电 9 用 Windows 侧 WMPF 运行小游戏，包在 `weixinsmallgameData\Applet\packages\...`；模拟器里的 `/data/app/com.android.flysilkworm-...` 是雷电应用商店 APK 的安装目录，与本游戏无关。
- 当前状态：**已完成找包、复制、解包、引擎判定、资源完整性验证**；本地 Web 运行壳（`wx` shim）尚未实现。

## 2. 样本来源

### 2.1 实际路径

```text
D:\Program Files\leidian\LDPlayer9\weixinsmallgameData\Applet\packages\<appid>\48\
```

复制到仓库：

```text
targets\wechat-minigame\<appid>\48\
```

### 2.2 文件与校验

| 文件 | 字节数 | SHA-256 |
|---|---:|---|
| `__WITHOUT_MULTI_PLUGINCODE__.wxapkg` | 3,096,187 | `a4d6d9ca913f4e78621dd6fdd2fddcaed08e331bf9d35a867851eb9e41e25b4d` |
| `_resources_anim_.wxapkg` | 1,277,774 | `b24e2579f1ff4507f51dffdc48175fa969f2feac943ab92bac473105fe493d0b` |
| `_resources_img_.wxapkg` | 4,269,202 | `efe87ba10e16448b4ded1dc75c6e8b1f150fdaf83018c203287e2a454b9da656` |
| `_resources_music_.wxapkg` | 1,877,780 | `0766097ca0b90990d08c4174035926c769f1818d134de15d1fe38a1d8beab4b4` |
| `_resources_sound_.wxapkg` | 2,327,842 | `fc0b77284d4ae2f462f7e36a45dc6c9e63ecbb83d353ab4fa24bb5083e9bb58f` |

### 2.3 为什么不在模拟器里

- 雷电桌面上的「赵云与阿斗」只是快捷方式，intent 指向 `com.ld.wechat.minigame.<appid>/.MainActivity`，extras 含 `id=<appid>`、`game_name=赵云与阿斗`；直接 `am start` 报 `Activity class ... does not exist`。
- 模拟器内 `pm list packages` 只有 68 个系统包，没有微信、也没有该小游戏包；全盘 `find` 无 `*.wxapkg`。
- Windows 上实际运行的是：

```text
D:\Program Files\leidian\LDPlayer9\RadiumWMPF_2.2.3.520\runtime\WeChatAppEx.exe
--wmpf_root_dir="D:\Program Files\leidian\LDPlayer9\weixinsmallgameData\\"
```

即雷电用 Windows 侧 WMPF 运行小游戏，包自然落在 `weixinsmallgameData`。

## 3. wxapkg 格式与解包

### 3.1 文件头

以主包为例：

```text
BE 00 00 00 00 00 00 0D 5C 00 2F 31 11 ED
```

按 14 字节解析：

| 字段 | 值 | 含义 |
|---|---|---|
| magic | `0xBE` | wxapkg 标记 |
| info1 | `0x00000000` | 本样本为 0 |
| indexLen | `0x00000D5C` = 3,420 | 索引区长度 |
| bodyLen | `0x002F3111` = 3,092,753 | 数据区长度 |
| mark | `0xED` | 尾部标记 |

### 3.2 索引结构

本样本的索引区在文件偏移 14，结构为：

```text
uint32 entryCount
repeat entryCount:
  uint32 nameLen
  bytes  name
  uint32 offset
  uint32 size
```

**关键坑：`offset` 是相对整个文件头的绝对偏移，不是相对数据区。**

第一版解包器写成 `body[off:off+size]`，等于每个文件都多跳过 `14 + indexLen` 字节：

- 主包多跳 3,434 字节；
- `_resources_img_` 多跳 4,538 字节；
- `_resources_sound_` 多跳 4,375 字节。

结果就是 JSON 从中间开始、PNG 丢文件头，全部无法打开。改为：

```python
f.write(data[off:off + size])
```

后所有文件恢复正常。

解包器已通用化并入库：

```text
tools/unpack_wxapkg.py
```

它会自动识别两种索引布局（`info1` 即 entryCount / 索引首 4 字节为 entryCount）以及绝对/相对 offset，并用 PNG/JSON/JS 魔数和 `sum(size) == bodyLen` 打分。

### 3.3 解包命令

```powershell
python tools\unpack_wxapkg.py `
  "targets\wechat-minigame\<appid>\48\__WITHOUT_MULTI_PLUGINCODE__.wxapkg" `
  "out\wechat-minigame\unpacked\__WITHOUT_MULTI_PLUGINCODE__"
```

其余 4 个包同理，输出到 `out/wechat-minigame/unpacked/_resources_*_/`。

## 4. 解包结果与完整性验证

| 包 | 文件数 | 解包后字节数 |
|---|---:|---:|
| 主包 `__WITHOUT_MULTI_PLUGINCODE__` | 96 | 3,092,753 |
| `_resources_anim_` | 55 | 1,275,156 |
| `_resources_img_` | 96 | 4,264,664 |
| `_resources_music_` | 5 | 1,877,539 |
| `_resources_sound_` | 92 | 2,323,467 |

已验证：

- `data/rank.json`：18,189 字节，合法 JSON，54 条记录；
- `data/rankData.json`：4,213 字节，JSON OK；
- `data/weapon.json`：11,172 字节，JSON OK；
- `data/weaponTxt.json`：4,581 字节，JSON OK；
- `scene/MainScene.ls`：13,015 字节，JSON OK；
- `prefab/boss.lh`：945 字节，JSON OK；
- `prefab/mapBg0.lh`：1,729 字节，JSON OK；
- `game.js`：2,358,768 字节，开头 `define("js/bundle.js", ...)`，结尾 `require("js/index.js"); require("game.js");`；
- `_resources_img_` 共 96 项：81 个 PNG、13 个 `.atlas`、1 个 `fileconfig.json`、1 个 `game.js`；81/81 PNG 解码成功，首字节均为 `89 50 4E 47 0D 0A 1A 0A`。

注意：`.atlas` 是图集元数据（JSON），不是图片；`AutoAtlas.png` 等是雪碧图，打开是大图属正常。

## 5. 引擎与运行时结构

### 5.1 引擎判定

- `p.version = "3.3.12"`；
- 场景 `.ls`、prefab `.lh`；
- 代码使用 `Laya.Sprite`、`Laya.Image`、`Laya.Text`、`Laya.Tween`、`Laya.Pool`、`Laya.timer`；
- Spine：`spine-core-3.7.js` + `laya.spine.js`；
- 微信适配层：`libs/laya.adapter-weixin.js`。

结论：**LayaAir 3.3.12**。

### 5.2 入口与模块

`game.js` 不是普通入口，而是一个模块集合：

```js
define("js/bundle.js", function(require, module, exports){ ... });
...
require("libs/laya.adapter-weixin.js");
require("js/bundle.js");
require("js/index.js");
require("game.js");
```

`Laya.init` 在 `game.js` 中出现 1 次，位于 bundle 内；`laya.adapter-weixin.js` 已在包内，说明引擎本身已经为微信环境做过适配，本地跑只需要补 `wx` 对象。

### 5.3 wx API 使用面

去重后共 22 个：

```text
getSystemInfoSync, getLaunchOptionsSync, login, getStorageInfoSync,
createCanvas, createImage, createInnerAudioContext,
onTouchStart, onTouchMove, onTouchEnd, onTouchCancel,
getSystemInfo, getNetworkStateChange, onNetworkStateChange,
getLocation, request, connectSocket,
readFile, getStorageSync, setStorageSync, removeStorageSync, clearStorageSync
```

另外：

- `wx.loadSubpackage` 在 bundle/适配层中出现 8 次；
- `wx.getFileSystemManager` 出现 4 次；
- 这些是本地 Web 运行壳需要重点补的 API。

### 5.4 目录结构

主包：

```text
app-config.json
fileconfig.json
game.js
data/        rank.json, rankData.json, weapon.json, weaponTxt.json
dialog/
prefab/      33 个 .lh（boss、mapBg0..3、damageNum、lvlUpEff 等）
resources/   仅 loading/
scene/       14 个 .ls
shader/      basicShader, buttonShapeGlow, sweepLight
```

场景清单：

```text
AvatarSettingScene, BattleScene, GameOverScene, GMScene,
LoadMaskScene, LoadScene, MainScene, MapEditor, MatchScene,
RankScene, SettingScene, ShopScene, TestWeaponScene, WeaponScene
```

`app-config.json` 声明的分包：

```json
{"name":"resources/anim","root":"/resources/anim/"}
{"name":"resources/music","root":"/resources/music/"}
{"name":"resources/sound","root":"/resources/sound/"}
{"name":"resources/img","root":"/resources/img/"}
```

解包后的对应目录正好是 `_resources_anim_/resources/anim`、`_resources_img_/resources/img` 等，合并进主包 `resources/` 即可形成完整资源树。这是本地还原的关键一步。
## 6. 玩法与代码观察（初步）

从 scene / prefab / bundle 字符串可见，这不是简单三消，而是**2D 合成 + 塔防/对战 + 武将技能 + 波次**的小游戏，包含主界面、战斗、商店、武器、排位、匹配、设置、GM 等场景。

`game.js` 中可读到的技能示例（仅代码字符串观察，完整公式待运行/细读）：

| 技能 | 字符串描述 |
|---|---|
| 望梅止渴 | 对方每合成一个武将，我方的馒头就多加 5 个 |
| 割发代首 | 阿斗剩最后一滴血时，会脱下帽子躲藏 5 秒再回到原地 |
| 身在曹营 | 对面的关羽放技能时，有 50% 概率跳过来放 |
| 桃园结义 | 可合成刘关张武将，合成后长满桃树为阿斗回血 |
| 青梅煮酒 | 场上有武将升至 3 级时，阿斗献酒，该武将攻速提升 50% |
| 上将克星 | 获得 1 个马忠碎片 |

GM 面板里还能看到调试项：加钱、AI 加钱、下波必出 boss、武将升一级、天数 +1、处死对手、出 boss、测试场景、直接开始、随机道具、清除武器数据、加体力、随机武器碎片、下一赛季、锦马超、专属碎片 +1、马忠碎片 +1 等。

这些说明：

- 战斗/数值/技能主要逻辑在客户端 bundle 内；
- 但登录、排行榜、商店、赛季等仍有服务端/平台依赖；
- 完整复刻前需要先确定「单机可玩范围」和「必须 mock 的接口」。

## 7. 本地还原路线（未完成）

目标不是「双击打开」，而是做一个和 `out/web-mobile/game` 同类的本地 Web 运行壳：

~~~text
out/wechat-minigame/web/
  index.html
  wx-shim.js
  game/
    game.js
    data/
    scene/
    prefab/
    resources/   (主包 + 4 个分包合并)
    shader/
~~~

步骤：
1. 复制主包到 `game/`，把 4 个分包的 `resources/` 合并进 `game/resources/`；
2. 写 `wx-shim.js`，优先覆盖这些 API：

| wx API | 浏览器实现 |
|---|---|
| `createCanvas` | 页面 canvas |
| `createImage` | `new Image()` |
| `createInnerAudioContext` | HTMLAudioElement 包装 |
| `onTouch*` | canvas pointer/touch 事件 |
| storage | `localStorage` |
| `login` | 返回假 code |
| `request` | fetch 或本地 mock |
| `loadSubpackage` | 直接 resolve（资源已合并） |
| `getSystemInfoSync` | 固定 720x1280 / devicePixelRatio |
| `getLaunchOptionsSync` | `{scene: 1001, query: {}}` |

3. 用本地 HTTP 服务打开 `index.html`，先过 loading，再补缺失 API；
4. 用浏览器 DevTools 看第一个异常，按调用栈补 shim；
5. 需要联网的接口先用 mock JSON 顶住，不接真实服务端。

卡点：
- `game.js` 是压缩 bundle，类名/模块名混淆，不能 1:1 还原源码；
- 分包加载路径、`fileconfig.json`、图集路径要按原结构摆放；
- 登录/排行榜/商店/赛季依赖服务端，单机只能跑客户端可玩部分；
- LayaAir 3.3.12 与微信小游戏的 canvas/输入模型有差异，需要适配。

## 8. 结论与边界

- 这个样本适合做「本地客户端还原/研究」，不适合直接再发布。
- 技术栈明确（LayaAir 3.3.12 + 微信小游戏 wxapkg），解包与资源恢复已经跑通。
- 真正的难点不是解包，而是运行时适配与服务端依赖。
- 版权/平台边界：仅本地学习；不传播解包资源，不运营私服，不做未授权换皮。

## 9. 证据索引

| 内容 | 路径 |
|---|---|
| 原始包 | `targets/wechat-minigame/<appid>/48/` |
| 解包结果 | `out/wechat-minigame/unpacked/` |
| 解包脚本 | `tools/unpack_wxapkg.py` |
| 技能 | `skills/wechat-minigame-reversing/SKILL.md` |
| 入口 | `out/wechat-minigame/unpacked/__WITHOUT_MULTI_PLUGINCODE__/game.js` |
| 场景 | `.../scene/MainScene.ls`、`.../scene/BattleScene.ls` |
| 配置 | `.../app-config.json` |
| 数据 | `.../data/rank.json`、`.../data/weapon.json` |

## 10. 后续待办

- [ ] 补 `wx` shim，跑通 loading 与主界面；
- [ ] 记录第一个运行时异常与修复；
- [ ] 判断单机可玩边界（战斗是否完全客户端结算）；
- [ ] 如继续，补 mock 登录/排行榜/商店接口；
- [ ] 输出最小可玩 Demo 或分析结论。

