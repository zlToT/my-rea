# notes

逆向笔记索引。约定：

- 一个逆向目标一个文件夹：`targets/<name>` 对应 `notes/<name>/`。
- 每个目标的主报告固定为 `analysis.md`，内容是「原版行为 → 复刻实现」的逐项对照，
  兼顾结论、证据与验证记录。
- 专题对比、补充材料放同目录并单独命名，不塞进主报告。
- 跨项目通用的环境快照留在本目录根，不归属某个目标。

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

雷电模拟器 9 的微信小游戏「赵云与阿斗」，LayaAir 3.3.12；包在 Windows 的 WMPF 缓存，不在 Android 虚拟机。

| 文件 | 内容 |
|---|---|
| [`wechat-minigame/analysis.md`](wechat-minigame/analysis.md) | 主报告：取包路径、wxapkg 格式与绝对 offset 坑、解包验证、引擎与 wx API、场景/分包结构、玩法观察、本地还原路线、证据索引 |
