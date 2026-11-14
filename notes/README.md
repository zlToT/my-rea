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
| `env-snapshot.json` | 环境快照：Node/pnpm/REA 版本、引擎（Ghidra 12.2 + JDK 25、venv 包）、外部工具绝对路径、模拟器、`rea doctor` 预期缺口与已知限制 |

## wechat-minigame

雷电模拟器 9 的微信小游戏「样本 A」，LayaAir 3.3.12；包在 Windows 的 WMPF 缓存，不在 Android 虚拟机。

| 文件 | 内容 |
|---|---|
| [`wechat-minigame/analysis.md`](wechat-minigame/analysis.md) | 主报告：取包路径、wxapkg 格式与绝对 offset 坑、解包验证、引擎与 wx API、场景/分包结构、玩法观察、本地还原路线、证据索引 |

## apk-rn-hermes

Android 侧样本 B：React Native + Hermes 字节码包（业务逻辑全在 `assets/index.android.bundle`，dex 只剩壳与运行时）。
用途是**验证 RN 包的静态逆向路径**，走完一轮（类型判定 → header 解析 → 反汇编/反编译 → 建函数索引 → 定位业务逻辑），并在文末附一份去标识化的案例分析（存档协议、战斗数值、自动化收益），不写具体应用名。

| 文件 | 内容 |
|---|---|
| [`rea-apk-hermes.md`](rea-apk-hermes.md) | 方法论：类型判定、REA/工具链定位、`.hasm` 建索引、读字节码的常见坑；附录：同一份 bundle 的存档协议与战斗数值公式（去标识化） |

> 样本本体与反编译产物不入库（`targets/*`、`out/*` 已在 .gitignore 中）。笔记里保留分析与方法，具体应用名一律以 `<Name>` / `<vendor>` / `<host>` / `<pkg>` 代替。

## exe-static-analysis

Windows 原生 exe 的静态反编译路线（REA + Ghidra）。样本是单个 exe，验证「无引擎 → 装引擎 → 全量反编译 → 建调用图 → 读架构」这条链路能走通，附一份去标识化的案例拆解（数据结构、查询执行、索引构建），不写产品名。

| 文件 | 内容 |
|---|---|
| [`rea-exe-ghidra.md`](rea-exe-ghidra.md) | 方法论：JDK 版本坑、冒烟三步、调用图/符号聚类导航、读伪代码的套路、结论可信度分级；附录：数据模型 / 查询执行 / 索引构建的拆解（去标识化） |
