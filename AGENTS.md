# AGENTS.md

本仓库是 REA 逆向工作区。任何 AI 代理（Claude Code / Codex / OpenCode 等）在此执行命令前，先读本文件。

**本文件只放硬性规则与索引**；细节拆到 `docs\agents\` 下，按需读取，不要一次全读。

## 四条硬性规则

1. **Node 版本**：执行任何 `node` / `npm` / `pnpm` / `rea` 命令前先 `nvm use 24.22.3`（REA 要求 `^22.23.4 || ^24.22.1 || >=26.12.1`）。不要用安装包升级 Node，不要自行换版本。
2. **安装授权**：任何安装、下载、升级（`pnpm add`、下载引擎或二进制、`Invoke-WebRequest` / `curl` / `git clone`）都必须先说明「装什么、多大、装到哪、什么副作用」，等用户明确回「可以」。只读操作（读文件、跑已装命令、查版本）不需要授权。
3. **目录约定**：样本 `targets/`、产物 `out/<项目名>/`、笔记 `notes/`（入库）、工具 `tools/`（不入库，脚本除外）。不要污染仓库根目录。
4. **输出重定向**：`rea --json` 落盘必须 `cmd /c "pnpm exec rea ... --json > out\a.json"`，不要用 PowerShell 的 `>`（GBK 转码 → 非法 JSON）。

## 分册索引

| 何时读 | 文件 | 内容 |
|---|---|---|
| 切 Node、装依赖、动 pnpm 时 | `docs\agents\01-node-and-package.md` | nvm 规则、连带影响、包管理、onlyBuiltDependencies |
| 找 / 写 skill、判断 CLI vs MCP / 插件时 | `docs\agents\02-skills-and-distribution.md` | 项目内 skill 清单与 MCP→CLI 映射、分发形态 |
| 跑 `rea` 子命令、需要任务配方时 | `docs\agents\03-commands.md` | 目标类型→命令表、输出重定向坑 |
| 启用 Ghidra / JADX / Apktool、跑反编译时 | `docs\agents\04-engines.md` | 引擎状态表、启用步骤、冒烟三步、工具坑与镜像 |
| 要装东西、决定文件放哪、确认禁止事项时 | `docs\agents\05-rules.md` | 安装授权清单、目录约定、不要做的事 |
| 排查本机环境、工具绝对路径、pwsh 怪癖时 | `docs\agents\06-environment.md` | 已知环境事实、工具链表、PowerShell 踩坑 |

## 项目内 skill

| skill | 何时加载 |
|---|---|
| `.agents/skills/reverse-engineer-anything/SKILL.md` | 任务涉及逆向、反编译、分析发布产物时 |
| `skills/wechat-minigame-reversing/SKILL.md` | 目标是微信小游戏、`wxapkg`、雷电 WMPF 缓存时 |
| `skills/android-game-reversing/SKILL.md` | 目标是 Android 游戏 APK：判定引擎 / 壳、解包、WebView 缓存取证、资源还原时 |

## 产物与笔记

- 分析产物一律写 `out/<项目名>/`；结论写 `notes/<项目>/analysis.md`，并在 `notes/README.md` 登记。
- `out/` 是本机取证目录（不入库、不上传）：**不要改动 `out/` 里已有的产物**，也不要为了去标识化去改它；脚本产物直接新增即可。
- 需要去标识化的只有入库内容（`notes/`、`docs/`、`skills/`、`AGENTS.md`）。笔记必须**去标识化**：游戏名、包名、域名、密钥、备案 / ISBN / 软著、公司名、渠道 ID 都用占位符（`<Game>`、`<pkg>`、`<GameHost>`、`<AES_KEY>` 等），原始值只留在本机 `out/`（不入库）。
- 不要把 `node_modules/`、样本文件、反编译产物提交进 git。
