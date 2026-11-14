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

## 常用命令

```powershell
pnpm exec rea --version
pnpm exec rea doctor --json
pnpm exec rea analyze-javascript-application "<目标目录>" --json
pnpm exec rea decompile "<目标文件>" --procedure <函数名> --json
```

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
- 不要在未获用户同意时下载或安装任何工具（Ghidra、JDK、JADX 等）。
- 不要为了“让命令跑通”而临时全局安装包；先确认项目内是否已有依赖。
- 不要提交 `node_modules/`、样本文件、反编译产物。

## 已知环境事实

- 平台：Windows x64
- `rea doctor` 中的 `missing_analysis_engine` 属于预期缺口（未装 Ghidra/IDA/JADX）。
- `config_drift`（`registration:*` / `skill:*`）表示未注册为 MCP 客户端，CLI 用法下可忽略。
- Windows 上不支持依赖 Linux 工具链的能力：固件分析、pcap、进程捕获、桌面应用捕获。
