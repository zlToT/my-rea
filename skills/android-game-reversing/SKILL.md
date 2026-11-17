---
name: android-game-reversing
description: "逆向 Android 游戏 APK：先判定运行形态（原生引擎 / H5 壳 / RN / Flutter / 纯 WebView），再解包取证、解密渠道配置、抓 WebView 缓存还原远端资源，最后按规范产出报告。"
metadata:
  version: "1"
---

# Android 游戏逆向

## 适用范围

目标是 **Android 游戏 APK**（通常放 `targets/apk/`），需要回答三件事：这游戏用什么引擎/框架做的、资源在哪、能还原到什么程度。

典型场景：

- 商店下载的 APK，怀疑是 H5/小游戏套壳，包体很小（< 30 MB）却号称大型 RPG；
- 需要判定 Unity / UE / Cocos / Egret / Laya，以及是否套了渠道 SDK 壳；
- 需要还原远端 H5 的图集、配置、主逻辑代码；
- 需要给出伪代码 + 中文解释，而不是只丢一堆文件。

不适用于：微信小游戏 `wxapkg`（走 `skills/wechat-minigame-reversing/SKILL.md`）、iOS `ipa`、纯服务端协议逆向。

## 0. 先确认边界（写进笔记开头，别省略）

1. **只读样本**：不覆盖、不重打包、不改签名、不安装到真机以外的环境（用户明确提供设备时除外）。
2. **安装授权**：`jadx` / `apktool` / `Ghidra` / 任何下载都要先说明「装什么、多大、装到哪、什么副作用」，等用户回「可以」。能在项目内 `tools/` 装就不要全局装。
3. **默认不提交仓库**：产物写 `out/<项目名>/`（`.gitignore` 覆盖），结论写 `notes/`。
4. **去标识化**：报告里不出现具体游戏名、包名、域名、密钥、备案/ISBN/软著、公司名，全部占位（见第 9 节）。
5. 产物目录固定：`out/<项目名>/`、可复用脚本 `src/`（入库，先查 `src/README.md`）、笔记 `notes/<项目名>/analysis.md`。

## 1. 三十秒判形态：先看 so 和体积，再看代码

拿到 APK 先 `7z l` 列目录，**不要一开始就反编译 dex**。判断依据按可靠性排序：

| 观察点 | 结论 | 后续动作 |
|---|---|---|
| `lib/*/libunity.so` | Unity | 看 `libil2cpp.so`（IL2CPP）或 `assets/bin/Data/Managed/*.dll`（Mono）+ `global-metadata.dat` |
| `lib/*/libUE4.so` / `assets/*.pak` | Unreal | 走 UE 资源解析，注意 `*.uasset` 与 AES pak |
| `lib/*/libcocos2djs.so` + `assets/src/` | Cocos Creator（JSB） | `project.json` + `assets/**/*.js` 直接读 |
| `lib/*/libcocos2dlua.so` | Cocos2d-x Lua | `assets/src/*.lua` 或 `*.luac` |
| `lib/*/libhermes.so` + `assets/index.android.bundle` | React Native | `hermes-dec` 反字节码 |
| `lib/*/libflutter.so` | Flutter | `pnpm exec rea identify-flutter-build`，再抽 `kernel_blob.bin` |
| 只有渠道/校验 so（`libld-sdk.so`、`libqkcheck.so` 之类），assets 里只有 SDK 配置与 H5 桥 js | **H5 壳**：游戏在远端，壳只提供 WebView + 登录支付 | 走第 4、5 节 |
| assets 里有 `game.js`/`manifest.json`/`res/` 且无游戏引擎 so | 本地内嵌 H5 小游戏 | 直接读资源，跳过第 5 节 |

H5 壳的三条硬证据（凑两条即可定性）：

1. `AndroidManifest.xml` 里只有壳自己的 Activity（Splash + 一个 WebView Activity），没有游戏画面相关组件；
2. 壳的代码全部是 `WebView` + `addJavascriptInterface` + `loadUrl`，没有任何渲染/音频/资源加载逻辑；
3. 包内 class 名带渠道 SDK 前缀（`com.qk.*`、`com.quicksdk.*`、`com.ld.sdk.*`、渠道聚合 SDK），targetSdk 偏低，体积与「大型游戏」不符。

## 2. 解包基线：不装任何工具也能做完

| 目的 | 做法 |
|---|---|
| 列目录 / 解包 | `7z l <apk>`、`7z x <apk> -o<dir>`（经 `cmd /c` 调用，路径带空格时引号会被 PowerShell 包装器吃掉 → 先 `cd` 再相对路径） |
| 读二进制 Manifest | 自写 AXML 解析（`src/apk_axml.py`）：string pool 头是 5 个 u32（`<IIIII`），属性值常是资源引用，需配合 `resources.arsc` 或 apktool 才拿到真值 |
| DEX 字符串 / 类清单 | 自写 `src/apk_dex.py` → `strings_all.txt`、`classes_all.txt`；类数应与 jadx 差 < 1% |
| 引擎关键字初筛 | grep `cocos\|laya\|egret\|unity\|godot\|phaser\|pixi\|dragonbones\|harmony`。**先过滤超长行**（okhttp 的 public-suffix 正则会让终端刷屏，也会让 grep 结果全是噪音） |
| 资源清单 | `resources.arsc` 里的文件名、`res/` 下 png/xml 数量，判断壳 UI 占比 |

关于 `res/` 下的 XML：几乎全是 AppCompat 模板 + 渠道 SDK 的登录/充值界面，**不代表游戏 UI**。想快速统计归属，批量把二进制 AXML 转成文本（自写 `src/apk_res_dump.py`，魔数 `\x03\x00\x08\x00` 判 AXML），再按文件名前缀分组数一遍，报告里给一张占比表即可。

## 3. 装工具（项目内，需用户授权）

判定为原生引擎或需要看 Java 源码时，才需要真正的反编译工具。**都装在 `tools/` 下，不改 PATH**（`tools/*` 已在 `.gitignore` 里）。

~~~text
# JADX 1.5.1（dex → java）。注意必须用 -cp + 主类，java -jar 会拉起 GUI 并静默不产出
java -cp tools\jadx\lib\jadx-1.5.1-all.jar jadx.cli.JadxCLI ^
  -d out\<项目>\jadx-src --no-res -j 8 targets\apk\<name>.apk

# Apktool 2.10.0（资源 + 可读 Manifest + smali）
java -jar tools\apktool\apktool.jar d -f -o out\<项目>\apktool targets\apk\<name>.apk
~~~

两条产出会重复（jadx 已含源码，apktool 的 smali 通常 40 MB+ 冗余）：**只保留 Apktool 的资源与 Manifest，smali 目录删掉**。

`REA` 自带的 `inspect-android-package` 需要 `REA_JADX_MCP_JAR`，没配就报 `Set REA_JADX_MCP_JAR ... jadx-headless-mcp 0.7.1 JAR`，**不要在这上面反复重试**，直接用上面的 CLI。

## 4. 定位「游戏本体在哪」

### 4.1 先找 URL 与配置读取点

~~~text
grep -n "loadUrl\\|H5GameUrl\\|getConfigValue\\|getAssets().open" 在 jadx-src 里
~~~

H5 壳的典型形态：`MainActivity.onCreate` 里 `mUrl = AppConfig.getInstance().getConfigValue("H5GameUrl")`，为空就 `Toast` 一句「H5 游戏的 url 为空，请配置」——**这句话本身就是「游戏在远端」的铁证**，直接引到报告里。

### 4.2 渠道配置文件通常是密文

`assets/*.xml` 如果是 2000~3000 字节的 base64 大块，就是加密的渠道配置。解密路径一般是：

1. base64 decode → 得到 16 的整数倍密文；
2. 在壳代码里 grep `AES`、`SecretKeySpec`、`Cipher`、`decrypt`，找硬编码 key（常见是 16 字符 hex 或 ASCII 串）；
3. `AES/ECB/PKCS5Padding`（或 PKCS7）解出 XML。

key 找不到时，看解密方法所在类的**所有** `static final String` 常量，以及它的调用方是不是把 key 当参数传进去（本例 key 就在调用 decrypt 的 JS 桥类里）。

解出的 XML 里值得抄进报告：入口 URL、渠道 ID 组、`app_secret`（占位）、服务端域名组、分包/版本参数。**注意**：项目自己的 `versionConfig.json` 之类是资源版本号，不是引擎版本，别当证据。

### 4.3 判断是否需要额外插件包

`assets/*_plug.zip` / `plugins/` 里的 `*.apk`/`*.jar` 通常是渠道动态插件（登录、支付、风控），解出来看 `AndroidManifest.xml` + 类名即可，一般不构成游戏本体，报告里一句带过。

## 5. 运行时 WebView 缓存取证（H5 壳必做，这是拿资源唯一的干净路子）

前提：用户在模拟器/真机里装了并跑过游戏；设备已 root（雷电模拟器自带 root）。**不要试图爆破 CDN 目录**，缓存里基本都有。

### 5.1 打包缓存

~~~text
set ADB=D:\Program Files\leidian\LDPlayer9\adb.exe
"%ADB%" devices
"%ADB%" shell su 0 tar -cf /sdcard/wv_cache.tar -C /data/data/<pkg>/cache/WebView/Default .
"%ADB%" pull /sdcard/wv_cache.tar out\<项目>\wv_cache.tar
tar -xf out\<项目>\wv_cache.tar -C out\<项目>\wvc
~~~

- 必须 `su 0 <cmd>`；`su -c "..."` 在部分镜像上会报 `Unknown id: /data/data/...`。
- `tar` 的 `-C` 指向**不含空格**的 `.../WebView/Default`，再 `tar .`，可绕开引号被 PowerShell 包装器吃掉的问题。
- 本地解包用 Windows 自带 `tar`（bsdtar）；7-Zip 经 `cmd /c` 调用时路径引号容易丢，报 `\ is not recognized`。
- 缓存主体在 `cache/WebView/Default/HTTP Cache`（20 MB 量级很常见）；`app_webview/Default` 只有 Cookies/LocalStorage，没有资源。

### 5.2 解析 Chromium simple-cache v3（`HTTP Cache` 目录）

每条缓存是一个文件，布局**和直觉相反：body 在前，HttpResponseInfo 在后**：

~~~text
offset 0   : magic8  = 30 5c 72 a7 1b 6d fb fc   (uint64 0xFCFB6D1BA7725C30)
offset 8   : version (u32, 实见 5)
offset 12  : key_length (u32)
offset 16  : key_hash (u32)
offset 20  : 4 字节保留
offset 24  : key = 完整 URL（ASCII）
key 末尾   : body（可能 gzip，1f 8b 开头）
body 末尾  : EOF 记录 20 字节 = magic8 F4FA6F45970D41D8 + flags(u32) + crc32(u32) + stream_size(u32)
EOF 之后   : HttpResponseInfo（含 P/1.1 200 OK 等文本）
~~~

切法：key 结束位置 → 第一个 EOF 魔数之间就是 body。文件名不可信（是 hash），**必须按 key 里的 URL 还原原始路径**：

~~~text
urlsplit(key) -> out/<项目>/site/<netloc>/<path>   （文件名用服务器原名）
~~~

先写 `_index.json`（file/url/type/size），后续按 URL 再去 CDN 补缺，全部有据可查。

### 5.3 常见失败模式

| 现象 | 原因 | 处理 |
|---|---|---|
| 解析出 0 条 | header 布局猜错，或把 EOF 当条目头 | 先 dump 前 64 字节手工对齐，别凭记忆写 |
| 解析出 400 条但 body 全是 `P/1.1 200 OK` 开头 | 切反了：body 在前、header 在后 | 从 key 末尾往后切到第一个 EOF |
| URL 全是空/乱码 | 生成脚本里写了 `\x20-\x7e` 之类正则，落盘后变成双反斜杠 | **手写 ASCII 扫描函数**，不要用带 `\x` 转义的正则 |
| 文件是 1 字节 | 缓存里是占位（没下载完） | 记进 `_index.json`，按 URL 从 CDN 补 |
| body 是乱码 | 响应带 `Content-Encoding: gzip` | `body[:2] == b"\x1f\x8b"` 就 gzip 解压 |

### 5.4 CDN 补缺

缓存缺的少数文件（皮肤主题、个别图集 png）直接按 index 里的 URL 直取，通常需要两个头：

~~~text
Referer: https://<GameHost>/
User-Agent: ...（含游戏壳注入的 UA 标记，如 QuickBrowserAndroid；不加会 403/404）
~~~

静态域一般可直连；**不要**因为一个 404 就断定资源不存在，先比对 Referer/UA。

## 6. 引擎版本要「硬确认」，不要靠猜

定性到引擎家族后，版本号必须来自文件内容，不能从资源版本号或 URL 猜。

| 引擎 | 硬指纹 | 版本来源 |
|---|---|---|
| Egret | `manifest.json` 的 `initial`/`game` 数组列出 `egret.min_<hash>.js`、`eui.min_*.js`、`dragonBones.min_*.js`；HTML 里 `<div class="egret-player" data-entry-class=...>` | 下载 `egret.min_*.js`，grep `version` 得到如 `5.4.1` |
| Cocos Creator | `cc.game.run`、`settings.js`、`assets/**/import/**` | `settings.js` 里的 `engineVersion` / `cc.ENGINE_VERSION` |
| LayaAir | `Laya.init`、`laya.core.js`、`Laya.Stat` | `Laya.version` |
| Unity WebGL | `UnityLoader.js` / `Build/*.wasm` + `data.unityweb` | `ProjectVersion.txt`（原生包里是 `globalgamemanagers`） |

Egret 细节：模块化分文件（`egret.min` + `egret.web.min` + `eui.min` + `assetsManager.min`）是 5.x 的特征；4.x 是单文件 `egret.min.js`。

## 7. 「能拿到什么」：先给可得性表，再交付

| 目标 | 是否可得 | 说明 |
|---|---|---|
| 图集 png + 图集 json | 可得 | json 是 TextureMerger/spritesheet 格式（`{"file":"x.png","frames":{name:{x,y,w,h,offX,offY,sourceW,sourceH}}}`），缓存里 json 常比 png 全 → 按 json 里的 `file` 字段补 png |
| 配置 json（技能/战斗/关卡/掉落） | 可得 | 明文 json，往往就是玩法数值的全部 |
| 主逻辑 js | 可得 | 多数只 minify 不混淆：类名、包名保留（Egret 有 `__reflect(Cls,"name")`、`__extends`），可导出类清单当骨架 |
| 皮肤 exml 源码 | **不可得** | 发布时编进 `default.thm.min_*.js`；可从里面列出 `window.skins` 的皮肤名与 exml 名（数百个），但拿不到布局源码 |
| 引擎运行时 | 可得 | CDN 直取 |
| 服务端协议 | 部分 | 只有 `vo.C2S`/`vo.S2C` 类与字段名，业务校验在服务端 |
| 美术源文件（psd/fbb） | 不可得 | 只有导出后的图集与骨骼 |

代码侧快速产出一份「类清单」：从主 js 里抽 `__reflect(X,"pkg.Cls")` 的第二个参数，去重排序，按前缀分组统计（`vo.*` / `ui.*` 各多少），报告里能直接看出游戏有哪些系统。

## 8. 反编译复核（有 jadx 时必做）

- 用 jadx 的真源码复核自己手写反汇编的关键结论（onCreate 取值、解密链、JS 桥 action 列表）；
- 用 apktool 的 `AndroidManifest.xml` 补出资源引用的真值（渠道 ID、game_id 等）；
- 对账：自写 dex 解析的类数与 jadx 的类数应差 < 1%，差得多说明解析器有 bug（先查 `class_data_item` 的 `method_idx_diff` 累加器是否在 virtual_methods 前重置为 0）。

## 9. 报告规范

建议结构（可直接照抄本仓库 `notes/` 里的样例）：

1. **结论速览**：一句话引擎 + 一句话「游戏在哪」，每条结论标证据强度（实测/源码/推断）；
2. **判定过程**：否定法最有说服力——「为什么不是 Unity/UE/Cocos」逐条排除；
3. **壳分层表**：每个包（渠道 SDK / H5 壳 / 支付 / 埋点 / 校验）一行；
4. **配置解密**：算法 + key 来源 + 解出的关键字段表；
5. **运行时取证**：命令、缓存布局、坑；
6. **资源构成**：类型/数量/体积表 + 目录树；
7. **可得性表**（第 7 节）；
8. **可复现清单**：从零到结果的命令序列；
9. **踩坑表**；
10. **边界与未做**：什么没验证、为什么。

### 去标识化占位符（硬要求）

| 占位符 | 替换 |
|---|---|
| `<Game>` | 游戏名 |
| `<pkg>` | 包名 |
| `<GameHost>` / `<CdnHost>` / `<Domain>` | 游戏入口域名 / 静态 CDN / 主域 |
| `<SdkApiHost>` 等 | 渠道聚合 SDK 的各域名 |
| `<AES_KEY>` / `<APP_SECRET>` / `<PRODUCT_KEY>` | 密钥类 |
| `<GAME_ID>` / `<CHANNEL_ID>` / `<SUN_CHANNEL_ID>` | 渠道参数 |
| `<ICP>` / `<ISBN>` / `<Copyright>` / `<Approval>` | 备案 / ISBN / 软著 / 版号 |
| `<Corp>` / `<Publisher>` / `<Product>` | 公司 / 出版单位 / 产品名 |

原始值只留在本机 `out/`（不入库）。平台方域名（模拟器厂商等）可保留，不算游戏隐私。

## 10. 常见坑（本类任务反复踩到的）

| 坑 | 现象 | 处理 |
|---|---|---|
| pwsh 包装器吃内容 | 含反引号或 here-string 的写文件命令**静默失败**，文件不生成或 ExitCode=1 | 长文只用单引号数组 + `Add-Content -Encoding UTF8`，每块 ≤ 3 KB，写完查文件长度 |
| Markdown 围栏被吃 | 写进去的 ` ``` ` 变成单个反引号 | 统一用 `~~~` 围栏 |
| stdout 编码 | 直接跑 `python`/`node` 的 stdout 是 GBK，`UnicodeEncodeError` | 让脚本自己写 UTF-8 文件，别用 PowerShell 重定向接 Unicode 输出 |
| `rea --json` 落盘 | 用 `>` 得到非法 JSON | `cmd /c "pnpm exec rea ... --json > out\a.json"` |
| `java -jar jadx` | 拉起 GUI 假死、输出目录 0 文件 | `java -cp ...jadx-1.5.1-all.jar jadx.cli.JadxCLI` |
| `react` 相关正则刷屏 | `strings_all.txt` 里有数万字长行 | grep 前先按行长度过滤 |
| 生成脚本里的转义 | `\x27`、`\x20` 落盘变双反斜杠，正则全失效 | 脚本里用 `chr(39)` 拼字符、手写扫描函数 |
| `adb pull` 大文件超时 | 前台命令 300 s 被切断 | 分步执行或后台 `Start-Process` |
| CDN 404 | 直接 curl 全部 404，误判「资源不存在」 | 加 `Referer` + 游戏壳 UA 再试一次 |

## 11. 验收清单

- [ ] 报告第一屏能回答：什么引擎、什么版本、游戏本体在哪、为什么这么判断；
- [ ] 每条关键结论都有可复现的命令或源码位置（文件 + 方法名）；
- [ ] 图集 png 与图集 json 数量对得上，缺失的写清原因；
- [ ] 主逻辑代码已拿到并给出类清单（按包前缀分组统计）；
- [ ] 明确写出「拿不到什么」（如 exml 源码），而不是含糊带过；
- [ ] 报告里没有任何真实游戏名/包名/域名/密钥（grep 自查过）；
- [ ] `git status` 里只有预期的笔记改动，样本与产物都没入库；
- [ ] 没装任何全局工具，`tools/` 之外没有新文件。

## 相关文件

- `AGENTS.md`：硬性规则与分册索引；
- `docs/agents/04-engines.md`：JADX / Apktool / Ghidra 的启用步骤与更多工具坑；
- `docs/agents/06-environment.md`：本机路径、pwsh 怪癖；
- `skills/wechat-minigame-reversing/SKILL.md`：微信小游戏（`wxapkg`）路线；
- `notes/`：已完成的样例分析（H5 壳 + 远端 Egret 那一份覆盖了第 4~7 节全流程）。

