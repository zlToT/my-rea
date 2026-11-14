# notes

逆向笔记索引。约定：

- 一个逆向目标一个文件夹：`targets/<name>` 对应 `notes/<name>/`。
- 每个目标的主报告固定为 `analysis.md`，内容是「原版行为 → 复刻实现」的逐项对照，
  兼顾结论、证据与验证记录。
- 专题对比、补充材料放同目录并单独命名，不塞进主报告。
- 跨项目通用的环境快照留在本目录根，不归属某个目标。
- 只做侦察、不产出 `analysis.md` 的样本，仍在此登记一小节说明范围；样本本体与产物一律不入库。

## web-mobile

Cocos Creator 2.x 打包的 5×5 三消小游戏，复刻在 `out/web-mobile/game/`。

| 文件 | 内容 |
|---|---|
| [`web-mobile/analysis.md`](web-mobile/analysis.md) | 主报告：逆向路径、模块映射、5.1–5.18 逐项对照、数值表、两处初版复刻缺陷、验证记录、证据索引、版权边界、最短复刻路径 |
| [`web-mobile/rea-vs-manual.md`](web-mobile/rea-vs-manual.md) | REA 工具分析与手工读包在速度、证据强度、适用场景上的实测对照 |

## 根目录

| 文件 | 内容 |
|---|---|
| `env-snapshot.json` | 本机 Node/pnpm/工具链版本快照，跨项目复用 |

## wechat-minigame

雷电模拟器 9 的微信小游戏「样本 A」，LayaAir 3.3.12；包在 Windows 的 WMPF 缓存，不在 Android 虚拟机。

| 文件 | 内容 |
|---|---|
| [`wechat-minigame/analysis.md`](wechat-minigame/analysis.md) | 主报告：取包路径、wxapkg 格式与绝对 offset 坑、解包验证、引擎与 wx API、场景/分包结构、玩法观察、本地还原路线、证据索引 |

## apk-rn-hermes

Android 侧样本 B：React Native + Hermes 字节码包（业务逻辑全在 `assets/index.android.bundle`，dex 只剩壳与运行时）。
用途是**验证 RN 包的静态逆向路径**，跑完首轮侦察（类型判定 → header 解析 → 反汇编/反编译 → 建函数索引）即停止，不做深挖。

| 文件 | 内容 |
|---|---|
| [`rea-apk-hermes.md`](rea-apk-hermes.md) | 由该样本沉淀出的通用方法论：类型判定、REA/工具链定位、`.hasm` 建索引、读字节码的常见坑 |

> 样本本体、反编译产物与逐条结论不入库（`targets/*`、`out/*` 已在 .gitignore 中）。

## exe-static-analysis

Windows 原生 exe 的静态反编译路线（REA + Ghidra）。样本是单个 exe，验证「无引擎 → 装引擎 → 全量反编译 → 建调用图 → 读架构」这条链路能走通，不做逐函数精读。

| 文件 | 内容 |
|---|---|
| [`rea-exe-ghidra.md`](rea-exe-ghidra.md) | 方法论：JDK 版本坑、冒烟三步、调用图/符号聚类导航、读伪代码的套路、结论可信度分级 |
