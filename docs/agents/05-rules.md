# 安装授权、目录约定与禁止事项

> 本文件是 `AGENTS.md` 的分册。`AGENTS.md` 只保留硬性规则与索引，细节按需读这里。

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
| `skills/` | 项目自建 skill（按目标类型） | 是 |
| `tools/` | Ghidra 12.2、JDK 25、Python venv 等本地工具链；`tools/unpack_wxapkg.py`、`tools/ghidra-env.ps1` 例外，入库 | 否（脚本除外） |

分析产物一律写到 `out/<项目名>/`，不要污染 `targets/` 或仓库根目录。

## 不要做的事

- 不要修改 `~/.claude/settings.json`、`~/.cc-switch/` 等与本项目无关的配置。
- 不要在未获授权时下载或安装任何东西，规则见上文「安装授权」。
- 不要为了“让命令跑通”而临时全局安装包；先确认项目内是否已有依赖。
- 不要提交 `node_modules/`、样本文件、反编译产物。
