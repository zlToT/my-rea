# ai-rea

本地 AI 逆向工作区。核心工具是 [REA](https://github.com/morluto/rea)（`rea-agents`），
以 CLI 方式调用，不注册 MCP，不污染其他客户端的配置。

## 快速开始

```powershell
nvm use 24.22.3            # 必须先切版本
pnpm install               # 首次或依赖变更后
pnpm exec rea doctor --json
```

`doctor` 里 `missing_analysis_engine` 是预期缺口（没装 Ghidra/JADX），不影响 JS/.NET 分析。

## 怎么提需求

逆向任务最容易失败的地方不是工具，是**问题不具体**。按下面格式说，能省掉大半轮次。

### 四行模板

```
目标：<路径或名字>
想问：<1~3 个具体问题>
产出：<报告 / 对照表 / 可运行代码 / JSON>
边界：<能不能运行它？能不能联网？能不能装工具？>
```

### 例子

**最小可用**

```
目标：targets\mech-ruins-dist
想问：敌人波次是怎么生成的
产出：伪代码 + 中文解释
边界：只读，别装东西
```

**标准版**

```
目标：targets\mech-ruins-dist
背景：Vite 生产包，1.7 MB，无 sourcemap，Phaser 4
想问：
  1. 玩家伤害公式是什么
  2. 敌人波次刷新规则
  3. 存档写在哪
产出：每个问题给一段还原后的代码 + 证据位置
边界：只读；结果写 out\mech-ruins\
```

**探索型（不知道想看什么时）**

```
目标：<路径>
我不知道该看什么，先给一个概览，再列 3 个最值得深入的点，我来选
边界：只读
```

### 好问题 vs 坏问题

| ❌ 太泛 | ✅ 具体 |
|---|---|
| 看看这个游戏怎么做的 | 敌人移动是朝玩家直线追，还是有寻路？ |
| 分析一下这个 exe | 启动时读了哪些配置文件，路径怎么拼的？ |
| 有没有加密 | 请求 body 是明文还是加密？密钥从哪来？ |
| 能不能复刻 | 核心战斗循环需要哪几个数据结构？给字段定义 |

原则：**能被一个“是/否”或“一段代码”回答的问题，才是好问题。**

### 权限档位

默认按「只读 + 可写工作区」执行，超出就停下来确认。

| 档位 | 允许做的事 |
|---|---|
| 只读 | 读文件、跑已装的命令、不联网 |
| 可写工作区 | 可以在 `out\`、`targets\` 里生成文件 |
| 可运行目标 | 可以启动程序 / 网页，观察运行时行为 |
| 可联网 | 可以抓包、访问线上站点 |
| 可装工具 | 可以申请安装 JADX / Ghidra（逐项报体积与副作用） |

安装任何东西都需要显式授权 —— 见 `AGENTS.md` 的「安装授权」。

### 目标放哪

```
targets\<项目名>\
```

复制进去，不要移动原文件。`targets\` 已被 gitignore，不会误提交。

## 目录

```
ai-rea\
├─ targets\    待分析样本，一个目标一个子目录（不入库）
├─ out\        反编译产物 / evidence 导出（不入库）
├─ notes\      环境快照、结论记录（入库）
├─ tools\      可选工具链：Ghidra、JDK 等（不入库）
└─ .agents\    项目内 skills（入库）
```

## 常见任务配方

| 目标类型 | 命令 | 需要引擎 |
|---|---|---|
| JS / Electron 产物 | `pnpm exec rea analyze-javascript-application "<目录>" --json` | 否 |
| 网页 bundle | `pnpm exec rea analyze-web-bundle "<URL>" --json` | 否 |
| .NET 程序集 | `pnpm exec rea analyze "<文件>" --json` | 否 |
| APK 结构 / 签名 | `pnpm exec rea analyze "<apk>" --json` | 否（结构）／JADX（反编译） |
| 原生二进制伪代码 | `pnpm exec rea decompile "<文件>" --procedure main --json` | Ghidra / IDA |
| 全函数导出 | `pnpm exec rea decompile-all "<文件>" --output out\<项目>\ --json` | Ghidra / IDA |
| 环境自检 | `pnpm exec rea doctor --json` | — |

产出统一写到 `out\<项目名>\`。

## 分析引擎状态

| 引擎 | 状态 | 用途 |
|---|---|---|
| 内置解析器 | 可用 | JS/Electron、.NET、Godot PCK、IL2CPP metadata、APK 结构、HAR/SAZ、PE/ELF 头 |
| Ghidra 12.1.4 + JDK 21 | 未安装 | 原生二进制伪代码（Windows 为实验性、只读、仅 x64 PE） |
| JADX | 未安装 | APK 反编译（需 JDK + `jadx-headless-mcp` 0.7.1 JAR） |
| IDA / Hopper / Kuna | 不适用 | 付费或不支持 Windows |

## 注意事项

- **不要 `npm i -g` 或 `pnpm add -g` 装 REA**，保持项目内安装。
- **不要装 REA 插件 / 不要跑 `rea setup`**，会改客户端配置且与项目内 skill 重复。
- **升级前先看 release notes**：REA 迭代很快，`--json` 的字段可能变化。
- **不要删 `D:\.pnpm-store`**：所有 D 盘项目的包都硬链接在这里。
- nvm 切换 Node 版本后，全局包按版本隔离，需要重新安装。
- Windows 上不支持依赖 Linux 工具链的能力（固件、pcap、进程捕获、桌面捕获）。

## 复刻游戏时的能力边界

- 能帮：逻辑层 —— 规则计算、状态机、协议、数据结构、Unity IL2CPP 符号还原
- 不能帮：内容层 —— 美术资源、动画、数值表、手感参数（需要 AssetStudio / AssetRipper 等专用工具）
