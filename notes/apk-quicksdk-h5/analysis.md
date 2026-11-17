# apk-quicksdk-h5 逆向案例：QuickSDK H5 壳 + Egret 5.4.1 远端资源

> 样本：`targets\apk\<Game>.apk`（8,668,657 字节）
> 产物：`out\wujinzhilv\`（主报告 `report.md` 九节 / jadx 源码 4,930 个 .java / 还原站点 `site\` 383 文件 25 MB）
> 日期：2026-11-17　边界：只读样本、工具只装项目内、不提交

一句话：**APK 里没有游戏**。它是 QuickSDK 的 H5 JS 壳（`com.qk.plugin.js.shell`）+ 雷电渠道 SDK + 支付宝 + Sensors 埋点；
真正的游戏是远端 H5，用 **Egret Engine 5.4.1（白鹭）+ EUI + RES + DragonBones** 构建，入口 `https://<GameHost>/<game-path>`。

## 占位符约定

| 占位符 | 含义 |
|---|---|
| `<Game>` | 游戏 / 产品名 |
| `<pkg>` | 应用包名 |
| `<GameHost>` / `<CdnHost>` / `<SdkApiHost>` 等 | 游戏域名 / 资源 CDN / SDK 接口域名 |
| `<Corp>` / `<Publisher>` / `<Publishing>` | 开发方 / 运营方 / 出版单位 |
| `<ICP>` / `<ISBN>` / `<Copyright>` / `<Approval>` | 备案号 / ISBN / 软著号 / 版号批文 |
| `<AES_KEY>` / `<APP_SECRET>` / `<PRODUCT_CODE>` / `<PRODUCT_KEY>` / `<CERT_MD5>` | 配置密钥、签名与证书标识 |
| `<GAME_ID>` / `<CHANNEL_ID>` / `<SUN_CHANNEL_ID>` | 渠道配置 ID |
| `<vendor>` / `<Province>` / `<City>` | 签名厂商代号 / 证书主体所在地 |
| `<Product>` | 渠道侧产品名 |

> 原始值只留在本机 `out\` 下的取证产物里（不入库）。本笔记只保留技术结论与可复现方法。

---

## 一、结论速览

| 问题 | 结论 | 证据强度 |
|---|---|---|
| 引擎 / 框架 | Egret Engine 5.4.1（eui + assetsManager + dragonBones + socket） | 强：`egret.min_3a39dfa6.js` 内 `version = 5.4.1` |
| APK 的角色 | 渠道壳：WebView + 登录/支付桥 + 埋点 | 强：Manifest + jadx 真源码 |
| 游戏资源在哪 | 远端 CDN `<CdnHost>`，APK 内零游戏资源 | 强：APK 全量列表 + 缓存域名统计 |
| 入口地址来源 | 配置项 `H5GameUrl`，值以 AES 密文存在 `assets\quicksdk.xml` | 强：解密成功 + 真源码断言 |
| 能否拿到资源 | 能：412 条 WebView 缓存 → 401 资源，补拉 9 张图集，按原目录还原 383 文件 | 强 |
| 能否拿到皮肤源码 | 不能：`.exml` 编译进 `default.thm.min.js`；但 `window.skins` 有 656 条定义可读 | 中 |
| 主代码是否混淆 | 只 minify 未混淆：2,149 个类名全保留（`ui.*` 834、`vo.*` 1,272） | 强 |

---

## 二、判定「游戏不在包里」的路径

顺序很重要：先否定原生引擎 → 再否定包内资源 → 最后才去找远端。

1. **看 so**：`lib\arm64-v8a` 只有 `libld-sdk.so`(235,736) 与 `libqkcheck.so`(14,016)，没有 `libcocos2djs.so` / `libUE4.so` / `libunity.so` / `libhermes.so` → 排除原生引擎。
2. **看 dex 构成**：6 个 dex 共 9,748 类，`com.quicksdk.*`、`com.qk.plugin.*`、`com.ld.*`、`com.alipay.*`、`Lkotlin/*` 占绝大多数，没有游戏逻辑包。
3. **看 Manifest**：application 为 `com.qk.plugin.js.shell.GameApplication`，主界面 `MainActivity` + `GameWebView extends android.webkit.WebView`，Splash 带 `h5gameapp://quicksdkchannel/quicksdk_deeplinkCode` → 典型 H5 壳。
4. **看 assets**：只有 H5↔客户端桥 `libQuickSDKH5_To_Client.js`(44,163，Zepto 时代写法)、`quicksdk.xml`(2,668 密文)、`ldsdk_plug.zip`(849,995 → 内嵌 `ldsdk.apk` 967,959，雷电动态插件，无游戏资源)、两个内容为 `1` 的标记文件。
5. **搜引擎关键字**：对 6 dex 全量字符串（2.9 MB）grep `cocos|laya|egret|unity|godot|phaser|pixi`，只命中 okhttp 的 public-suffix 正则噪音 → 壳里连引擎名都没出现。
6. **找 URL 来源**：真源码 `MainActivity.onCreate` 只有一句 `this.mUrl = AppConfig.getInstance().getConfigValue("H5GameUrl")`，为空则 Toast「H5游戏的url为空，请配置」。
7. **解配置**：`assets\quicksdk.xml` = base64(AES)，密钥是 `Constant.AES_KEY`，解出 `H5GameUrl=https://<GameHost>/<game-path>`。

## 三、壳的分层

| 层 | 内容 | 说明 |
|---|---|---|
| H5 宿主 | `com.qk.plugin.js.shell`：`MainActivity` + 19 个匿名类、`GameWebView`、`QuickJsInterface`、`util.*` | 主壳 |
| 悬浮窗 / 角色 | `com.qk.plugin.qkfx.*`（关闭按钮、SetGameRolePlugin） | 小 |
| 渠道 SDK | QuickSDK `com.quicksdk.*` + 雷电 `com.ld.sdk.*` / `com.ld.analytics.sdk.*`（Sensors 6.7.2） | 最大头 |
| 支付 | `com.alipay.sdk.*` | 中 |
| 签名校验 | `com.game.apkverify.Check` | 小 |
| 语言运行时 | Kotlin stdlib（集中在 classes5） | 中 |

签名证书（`META-INF\<vendor>.RSA`）：`C=cn, S=<Province>, L=<City>, OU=<Corp>, CN=<vendor>`，证书 MD5 `<CERT_MD5>`。

Manifest meta-data（apktool 解出真值）：`CHANNEL_ID=<CHANNEL_ID>`、`SUN_CHANNEL_ID=<SUN_CHANNEL_ID>`、`GAME_ID=<GAME_ID>`、`SHOW_CANCEL_ACCOUNT=true`。

## 四、配置解密（拿游戏入口的唯一钥匙）

~~~text
assets/quicksdk.xml      2,668 B  纯 base64
  → base64 decode       2,000 B  密文（16 的倍数）
  → AES-128 / ECB / PKCS7，key = <AES_KEY>
  → 1,997 B  明文 XML（<resources><string name=...>）
~~~

- 密钥来源：`com.qk.plugin.js.shell.util.Constant.AES_KEY`；同一常量在 JS 桥里被用来解密这份配置。
- 真实逻辑（jadx 复核 `MainActivity$QuickJsInterface.callAndroidFunction`）：读 `quicksdk.xml` 文本（失败退 `channelcfg.xml`）→ 若不含 `resources` 就 `CommonUtil.decrypt(content, Constant.AES_KEY)` → `DocumentBuilder` 按 `<string name>` 灌进 `AppConfig`。
- 解出的关键项：`H5GameUrl`（游戏地址）、`game_id=<GAME_ID>`、`channel_id=<CHANNEL_ID>`、`sun_channel_id=<SUN_CHANNEL_ID>`、`product_code`、`product_key`、`app_secret`（敏感，主报告里已标注勿外传）。
- 走过的弯路：先按「证书 MD5 / 包名 MD5 / so 里 16 字节常量」等 9 组候选暴力试解全失败（`Crypto` / `pyaes` 都没装且当时不许装）。教训：**先找解密调用点和 key 常量，再考虑爆破**。

## 五、运行时取证（不装抓包工具也能拿全量资源）

前提：样本已装在雷电模拟器（`emulator-5554`，Android 9，已 root），游戏跑过一次，WebView 缓存落地。

~~~powershell
# 1) 打包 WebView 缓存：-C 指向无空格目录，避开引号地狱
adb shell su 0 tar -cf /sdcard/wv_cache.tar -C /data/data/<pkg>/cache/WebView/Default .
adb pull /sdcard/wv_cache.tar out\wujinzhilv\device\wv_cache.tar   # 20,023,296 B
# 2) 本地解包：用 Windows 自带 bsdtar（7z 经 cmd 调用时引号会被吃）
tar -xf wv_cache.tar -C wvc          # 412 条目 / 19,700,622 B
# 3) 解析 simple-cache
python scripts\wvcache.py "device\wvc\HTTP Cache" device\assets   # 401 资源 / 14.6 MB
~~~

adb 用 `D:\Program Files\leidian\LDPlayer9\adb.exe`；**root 必须写 `su 0 <cmd>`**，`su -c "..."` 会报 `Unknown id: /data/data/...`。

### Chromium simple-cache v3 的真实布局（踩 3 轮才对准）

~~~text
[0..8)    magic 0xFCFB6D1BA7725C30
[8..12)   version = 5
[12..16)  key_length
[16..20)  key_hash
[20..24)  保留
[24..)    key（完整 URL）
其后      响应体 body（gzip 则 1f 8b 开头）
EOF 记录  magic 0xF4FA6F45970D41D8，20 字节：magic + flags + crc32 + stream_size
~~~

反直觉的点：**body 在 HttpResponseInfo 之前**，头文本（`HTTP/1.1 200 OK`、服务器 IP）在文件后部。用「从文件尾反推长度」或「body 之后找 header」都会得到 0 条；正确切法是 key 结束位置 → 第一个 EOF 魔数。

## 六、引擎硬确认

缓存里的 `bflr/manifest.json`（383 B）就是 Egret 的启动清单：

~~~text
initial: egret.min / egret.web.min / eui.min / assetsManager.min / tween.min
         socket.min / game.min / promise.min / dragonBones.min
game:    main.min_a8e0e92b.js / default.thm.min_47a1644.js
~~~

再直取 `https://<CdnHost>/bflr/js/egret.min_3a39dfa6.js`（208,494 B，需 `Referer: https://<GameHost>/` + UA 含 `QuickBrowserAndroid`），文件内 `version = "5.4.1"` → **Egret Engine 5.4.1**。

页面侧证据：`<div id="container" class="egret-player" data-entry-class="ui.Main" data-scale-mode="showAll" data-frame-rate="60" data-content-width="640" data-content-height="1136">`；启动流程 `manifest.initial.concat(manifest.game, [./sdkjs/egret_webgl_guard.js])` → `egret.runEgret({...})`；UA 含 `egretwebview` 时 `tickMode` 取 1。

## 七、资源构成（还原后 383 文件 / 25.4 MB）

| 类别 | 规模 | 说明 |
|---|---|---|
| 图集 png | 19 套 | TextureMerger 图集，帧定义在同名 json；19/19 配对完整（其中 9 张是补拉的） |
| 技能特效 | 182 个 / 9.2 MB | `resource\assets\effect\mc\skill\` |
| 骨骼动画 | 5 个 ske.json + 贴图 | `effect\dragonbones\`（英雄 / 装备 / 道具图标） |
| 配置 json | 54 个 / 1.2 MB | `effectSkillConfig.json` 562 KB、`attackEffects.json` 76 KB、`config.json` 60 KB 等 |
| 主代码 | 3.75 MB | `main.min_a8e0e92b.js`，minify 未混淆 |
| 皮肤主题 | 2.04 MB | `default.thm.min_47a1644.js`，`window.skins` 656 条 |
| 引擎本体 | 约 0.8 MB | egret / eui / assetsManager / tween / socket / dragonBones |

类名分布（`main_classes.txt`）：`vo.*` 1,272（协议 `vo.C2S` 166 / `vo.S2C` 155）、`ui.*` 834、其它 43；`ui.*` 头部模块 welfare 95、build 35、fight 34、cross 33、lg 31。骨架：`ui.Main` 入口 + `BaseClass / BaseEuiLayer / ui.Controller / ui.BaseContainer / ui.PopPanel / ui.ItemRenderer`。

图集帧数前几名：commonsheet 157、battle_hurt_sheet 87、mainuisheet 64、heroImage_sheet 63、headIcon_sheet 47、rolesheet 46。

域名分布（401 条缓存的来源）：`<CdnHost>` 315、`h5sdk-res.ldmnq.com` 57、`res.ldmnq.com` 11、`img.ldmnq.com` 9、`sdk.rum.aliyuncs.com` 2、其余零星。

## 八、EUI 皮肤到底能不能拿到

- **拿不到原文件**：`.exml` 是开发期源文件，`egret build` 后编译进 `default.thm.min.js`，发布产物不含 exml。
- **能拿到编译后的定义**：`window.skins` 656 条皮肤（652 处 exml 名）可读，配合图集可按结构重搭界面，但不等于原工程。
- 想要更完整的界面证据：模拟器里多走几个界面再 tar 缓存，或用 `chrome://inspect` 远程调试 WebView 直接抓全量。

## 九、jadx / apktool 复核（项目内安装）

~~~powershell
java -cp tools\jadx\lib\jadx-1.5.1-all.jar jadx.cli.JadxCLI -d out\wujinzhilv\jadx-src --no-res -j 8 targets\apk\<Game>.apk
java -jar tools\apktool\apktool.jar d targets\apk\<Game>.apk -o out\wujinzhilv\apktool -f
~~~

- jadx 产出 4,930 个 .java（报 9,738 类 / 76,413 方法 / 1,595,990 指令），与自写 `dex2.py` 的 9,748 类差 10 个合成类 → 视为一致。
- apktool 补出了原先只能显示资源 ID 的 Manifest 值，与解密后的 `quicksdk.xml` 完全吻合，形成两路互证。
- 坑：`java -jar jadx-1.5.1-all.jar` 会拉起 GUI 且静默不产出（必须 `-cp ... jadx.cli.JadxCLI`）；`--deobf` 会把包名改成 `com.p042qk...` 形式；jadx 可能在仓库根建 `PowerShell 7.6.6\skylot\...` 缓存目录，跑完要检查。

## 十、可复现清单

| 步骤 | 命令 / 脚本 |
|---|---|
| APK 解包 | `7z.exe x targets\apk\<Game>.apk -oout\wujinzhilv\apk` |
| Manifest 解析 | `python scripts\axml.py apk\AndroidManifest.xml` |
| dex 字符串 / 类清单 | `python scripts\dex2.py strings|classes <out> <dex...>` |
| dalvik 反汇编定位 | `python scripts\disasm.py <out> <类名子串> <dex...>` |
| 跨 dex 找字符串使用者 | `python scripts\findstr.py` |
| 配置解密 | `scripts\dec_cfg.ps1`（.NET `Aes`，无需第三方库） |
| WebView 缓存解析 | `python scripts\wvcache.py <HTTP Cache 目录> <输出目录>` |
| 图集补拉 | `python scripts\fix_atlas.py` |
| 按原目录还原站点 | `python scripts\organize.py` |
| res 下 374 个 XML 转文本 | `python scripts\dump_res_xml.py` |

产物：`out\wujinzhilv\report.md`（九节主报告）、`site\`（按域名/目录还原的 383 文件）、`jadx-src\`、`apktool\`、`res_xml_all.txt`、`cfg_pretty.txt`、`main_classes.txt`。

## 十一、踩坑合集

| # | 坑 | 正解 |
|---|---|---|
| 1 | DEX `class_data_item` 的 virtual_methods 沿用上个累加器 → midx 越界（2,776 处解析失败） | virtual_methods 的 `method_idx_diff` 累加器要**重置为 0** |
| 2 | `code_item` 按 `<IIIIII` 解 → 所有方法立刻 truncated | 真实布局 `<HHHH`(registers/ins/outs/tries) + `<II`(debug_info_off/insns_size) |
| 3 | 线扫指令流撞上 switch / array payload | 跳过 0x0100 / 0x0200 / 0x0300 伪指令（按各自长度公式） |
| 4 | `dex2.Dex.method()` 已返回 str，再套 `string()` 抛 TypeError，被 except 吞成 `invoke-virtual ?NNNN` | 直接用返回值 |
| 5 | 脚本里写 `\x27` / `\x20` 转义，经 pwsh 数组落盘变双反斜杠 → 正则全失效 | 手写 ASCII 扫描函数，或用 `chr(34)` 拼接 |
| 6 | 命令里出现反引号 / here-string / ` ``` ` 围栏 → 静默失败或围栏被吃 | 用 `~~~` 围栏；长文用单引号数组 + `Add-Content -Encoding UTF8`，每块 ≤ 3 KB |
| 7 | 7z 经 `cmd /c` 调用时带空格路径报 `\ is not recognized` | 先把文件放到无空格路径，或改用 bsdtar |
| 8 | `pnpm exec rea analyze <apk>` 报 `unsupported_provider` | REA 的 analyze 只认可执行文件，APK 要自己解或用 apktool / jadx |
| 9 | `inspect-android-package` 要求 `REA_JADX_MCP_JAR` | 改为项目内装 jadx CLI，不走 MCP |
| 10 | WebView 缓存解析第一版假设 header 在前，结果 0 条命中 | body 在前、HttpResponseInfo 在后，见第五节 |

## 十二、边界与未做

- 样本只读：未修改、未重打包、未分发；还原出的图集与代码仅作分析记录，`out\` 不入库。
- 未做运行时动态调试（Frida 未装）、未实测支付链路、未尝试绕过任何风控。
- 未拿到 `.exml` 工程文件，也未拿到远端 `default.res.json` 的完整清单（缓存只覆盖访问过的路径）。
- 本次新增安装：JADX 1.5.1、Apktool 2.10.0，均在 `tools\` 下，未改 PATH、未提交。

