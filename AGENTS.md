# AGENTS.md

本仓库是 REA 逆向工作区。任何 AI 代理（Claude Code / Codex / OpenCode 等）在此执行命令前，先读本文件。

## 必须：Node 版本由 nvm 管理

本机的 Node 使用 **nvm-windows** 管理，全局包按版本隔离。**每次新开 shell、执行任何 `node` / `npm` / `pnpm` / `rea` 命令之前，先切换到项目要求的版本：**

```powershell
nvm use 24.22.3
node -v          # 必须输出 v24.22.3
```

规则：

1. **不要**用 winget / MSI / 安装包直接升级 Node，会破坏 nvm 的软链接布局。
2. **不要**假设当前版本正确。nvm 的当前版本是**全局状态**，别的项目可能切走了。
3. `nvm use` 在 Windows 上需要**管理员权限**（它要重建 `C:\Program Files\nodejs` 软链接）。失败时提示用户以管理员身份重开终端，不要尝试用其他方式改 PATH。
4. 版本不满足 REA 要求时报错即可，不要自行更换 Node 版本。

REA 要求：`^22.23.4 || ^24.22.1 || >=26.12.1`。

### 切换版本后的连带影响

nvm 的全局包按版本隔离。切到另一个版本后，`claude`、`pnpm` 等命令可能“消失”，这是正常的，不是环境损坏。需要时在该版本下重新安装：

```powershell
npm i -g @anthropic-ai/claude-code pnpm
```

## 包管理

- **只用 pnpm**，不要用 npm 安装本项目依赖。
- **不要全局安装 REA**（`npm i -g rea-agents` / `pnpm add -g`）。本项目的 REA 已锁定在 `package.json` 中，通过 `pnpm exec rea` 调用。
- **不要删除 `D:\.pnpm-store`**。D 盘所有 pnpm 项目的文件都硬链接在此，删除会导致全量重下。
- `pnpm-workspace.yaml` 里的 `onlyBuiltDependencies` 是为了放行 `frida` 的安装脚本，不要移除。

## 项目内 skills

本仓库自带 skill，位于 `.agents/skills/`，**已随仓库提交，可直接读取，无需安装**。

| skill | 路径 | 何时加载 |
|---|---|---|
| `reverse-engineer-anything` | `.agents/skills/reverse-engineer-anything/SKILL.md` | 任务涉及逆向、反编译、分析发布产物时 |

使用规则：

1. **开始逆向任务前先读对应 `SKILL.md`**，再决定调用哪些 `rea` 子命令。
2. `SKILL.md` 末尾的 `references/` 是按需读的，不要一次性全读（合计 235 KB）。
3. 该 skill 原本面向 MCP 工具名编写。**本项目使用 CLI**，遇到 MCP 工具名时按下面映射替换：

| skill 里的 MCP 说法 | 本项目用 |
|---|---|
| 调用 REA 工具 | `pnpm exec rea <子命令> --json` |
| `rea doctor` 检查连接 | `pnpm exec rea doctor --json` |
| 等待 MCP 连接 / 重启客户端 | 不适用，直接看命令的 stderr |

4. 升级 REA 后 skill 可能过期（`SKILL.md` frontmatter 里有 `metadata.version`）。需要重新同步时：

```powershell
robocopy "node_modules\.pnpm\rea-agents@<版本>\node_modules\rea-agents\skills\reverse-engineer-anything" `
         ".agents\skills\reverse-engineer-anything" /MIR
```

## 常用命令与任务配方

```powershell
pnpm exec rea --version
pnpm exec rea doctor --json
```

| 目标类型 | 命令 | 需要引擎 |
|---|---|---|
| JS / Electron 产物 | `pnpm exec rea analyze-javascript-application "<目录>" --json` | 否 |
| 网页 bundle | `pnpm exec rea analyze-web-bundle "<URL>" --json` | 否 |
| .NET 程序集 | `pnpm exec rea analyze "<文件>" --json` | 否 |
| APK 结构 / 签名 | `pnpm exec rea analyze "<apk>" --json` | 否（结构）／JADX（反编译） |
| 原生二进制伪代码 | `pnpm exec rea decompile "<文件>" --procedure main --json` | Ghidra / IDA |
| 全函数导出 | `pnpm exec rea decompile-all "<文件>" --output out\<项目>\ --json` | Ghidra / IDA |

产出统一写到 `out\<项目名>\`。完整子命令列表用 `pnpm exec rea --help` 查（6.9.0 有 180+ 条）。

## 分析引擎状态

| 引擎 | 状态 | 用途 |
|---|---|---|
| 内置解析器 | 可用 | JS/Electron、.NET、Godot PCK、IL2CPP metadata、APK 结构、HAR/SAZ、PE/ELF 头 |
| Ghidra 12.1.4 + JDK 21 | 未安装 | 原生二进制伪代码（Windows 为实验性、只读、仅 x64 PE） |
| JADX | 未安装 | APK 反编译（需 JDK + `jadx-headless-mcp` 0.7.1 JAR） |
| IDA / Hopper / Kuna | 不适用 | 付费或不支持 Windows |

**需要引擎的能力一律先停下申请授权，不要自行下载安装。**

## 分发形态

本项目使用 **CLI + 项目内 skill** 的组合，**不要安装 REA 插件**，也**不要运行 `rea setup`**。

| 形态 | 本项目是否使用 | 说明 |
|---|---|---|
| CLI（`pnpm exec rea`） | ✅ 唯一调用方式 | |
| 项目内 skill（`.agents/skills/`） | ✅ | 已随仓库提交 |
| MCP 注册（`rea setup`） | ❌ | 会改 `~/.claude.json`、`~/.codex/` 等客户端配置 |
| 插件（Claude / Codex / Cursor Marketplace） | ❌ | 绕开 `rea doctor` 管理，且与项目内 skill 重复 |

插件安装后 `doctor` 里的 `registration:*` / `skill:*` 仍会报 missing，这是两套状态互不认，**不要因此重装**。

## 安装授权（硬性规则）

**本项目内任何安装、下载、升级行为，都必须先获得用户明确授权，逐次确认，不得默认同意。**

包括但不限于：

- `pnpm add` / `pnpm install <新包>` / `npm i -g` / `pnpm dlx`
- 下载分析引擎（Ghidra、JDK、JADX、adb、Frida 等）或任何二进制
- 升级 Node、pnpm、REA 版本，或修改 `package.json` 的依赖
- 修改项目之外的全局配置（`~/.claude`、`~/.cc-switch`、`~/.codex`、`D:\.pnpm-store`）
- 从网络取回任何可执行内容（`Invoke-WebRequest`、`curl`、`git clone`）

正确做法：**先说明要装什么、多大、装到哪、有什么副作用，等用户回“可以”再执行。**
只读操作（读文件、跑已装好的命令、查询版本）不需要授权。

## 目录约定

| 目录 | 用途 | 是否入库 |
|---|---|---|
| `targets/` | 待分析样本，一个目标一个子目录 | 否 |
| `out/` | 反编译产物、evidence 导出 | 否 |
| `notes/` | 结论、环境快照、对比记录 | 是 |
| `tools/` | Ghidra、JDK 等可选工具链 | 否 |

分析产物一律写到 `out/<项目名>/`，不要污染 `targets/` 或仓库根目录。

## 不要做的事

- 不要修改 `~/.claude/settings.json`、`~/.cc-switch/` 等与本项目无关的配置。
- 不要在未获授权时下载或安装任何东西，规则见上文「安装授权」。
- 不要为了“让命令跑通”而临时全局安装包；先确认项目内是否已有依赖。
- 不要提交 `node_modules/`、样本文件、反编译产物。

## 已知环境事实

- 平台：Windows x64
- `rea doctor` 中的 `missing_analysis_engine` 属于预期缺口（未装 Ghidra/IDA/JADX）。
- `config_drift`（`registration:*` / `skill:*`）表示未注册为 MCP 客户端，CLI 用法下可忽略。
- Windows 上不支持依赖 Linux 工具链的能力：固件分析、pcap、进程捕获、桌面应用捕获。
