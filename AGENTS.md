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

本仓库有两类 skill，均已随仓库提交，可直接读取，无需安装：

- `.agents/skills/`：REA 自带的通用逆向 skill，升级 REA 时同步；
- `skills/`：本仓库针对具体目标类型整理的操作手册。

| skill | 路径 | 何时加载 |
|---|---|---|
| `reverse-engineer-anything` | `.agents/skills/reverse-engineer-anything/SKILL.md` | 任务涉及逆向、反编译、分析发布产物时 |
| `wechat-minigame-reversing` | `skills/wechat-minigame-reversing/SKILL.md` | 目标是微信小游戏、`wxapkg`、雷电 WMPF 缓存时 |

使用规则：

1. **开始任务前先读对应 `SKILL.md`**，再决定调用哪些 `rea` 子命令。
2. `SKILL.md` 末尾的 `references/` 是按需读的，不要一次性全读（合计 235 KB）。
3. `.agents/skills/` 里的 skill 原本面向 MCP 工具名编写。**本项目使用 CLI**，遇到 MCP 工具名时按下面映射替换：

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
| 原生二进制伪代码 | `pnpm exec rea decompile "<文件>" --procedure main --json` | Ghidra（已装，需按上节激活） |
| 全函数导出 | `pnpm exec rea decompile-all "<文件>" --output out\<项目>\ --json` | Ghidra（已装，需按上节激活） |

产出统一写到 `out\<项目名>\`。完整子命令列表用 `pnpm exec rea --help` 查（6.9.0 有 180+ 条）。

### 输出重定向（坑）

**不要用 PowerShell 的 `>` / `Out-File` 接收 `rea` 的 `--json` 输出。**
PowerShell 会按控制台代码页（GBK）重新编码，UTF-8 中文变成乱码，JSON 直接非法。

```powershell
# ❌ 错的（文件看似正常，JSON.parse 会报错）
pnpm exec rea analyze-javascript-application "x" --json > out\a.json

# ✅ 对的（原样落盘）
cmd /c "pnpm exec rea analyze-javascript-application ""x"" --json > out\a.json"
```

`analyze-javascript-application` 的完整 Evidence 体积巨大 —— 本仓库对一个 3.8 MB 的 Cocos 游戏
产出 **48.8 MB** JSON，其中大半是压缩引擎里 `require(...)` 的未解析引用。
需要结论时用 `--format md` 或 `--filter-output <键路径>`，不要直接把完整 Evidence 读进上下文。

## 分析引擎状态

| 引擎 | 状态 | 用途 |
|---|---|---|
| 内置解析器 | 可用 | JS/Electron、.NET、Godot PCK、IL2CPP metadata、APK 结构、HAR/SAZ、PE/ELF 头 |
| **Ghidra 12.2 + JDK 25** | **已装（项目内）** | 原生二进制伪代码；Windows 只读、仅 x64 PE |
| 项目内 Python venv | 已装 | Hermes 字节码（`hbc-*`）、PE 解析（`pefile`）、反汇编（`capstone`） |
| JADX | 未装（多数情况不需要） | APK → Java 源码，需 JDK17+ 与 `jadx-headless-mcp` 0.7.1 JAR |
| IDA / Hopper / Kuna | 不适用 | 付费或不支持 Windows |

**需要新增引擎（或重装）时一律先停下申请授权，不要自行下载安装。** 已装好的直接按下面激活，不要再装。

### 启用 Ghidra（每会话一次）

引擎在 `tools\` 下，**不在 PATH、不写注册表、不影响其他项目**。用之前设三个环境变量：

```powershell
$env:JAVA_HOME          = "D:\ai-code\ai-rea\tools\jdk25"
$env:GHIDRA_INSTALL_DIR = "D:\ai-code\ai-rea\tools\ghidra"
$env:PATH = "$env:JAVA_HOME\bin;$env:GHIDRA_INSTALL_DIR\support;$env:PATH"
pnpm exec rea doctor --json     # ghidra / ghidra-version / ghidra-java 应全 ok
```

- `tools\ghidra-env.ps1` 是同样内容；但 dot-source 可能被命令安全检查拦，直接写 env 更稳。
- **Ghidra 12.2 要求 JDK 25+**。用 JDK 21 会在 analyzeHeadless 报
  `JDK 25+ (64-bit) could not be found and must be manually chosen!` 然后交互卡死。`tools\jdk25` 就是为此装的。
- 体积：`tools\ghidra` 866 MB、`tools\jdk25` 290 MB，均被 `.gitignore` 的 `tools/*` 挡住，不入库。
- Ghidra 的安装 zip 已删；要重装需重新下 543 MB（`ghidra_12.2_PUBLIC_20261016.zip`，SHA256 `2c2cd776db3c1f6a097ba418922378ac3649cadd5e844a6f5f088ae628a7be67`）。

### 首次分析某个二进制：冒烟三步

```powershell
# 1) 只导入不分析（秒级），确认引擎能开这份文件
& "$env:GHIDRA_INSTALL_DIR\support\analyzeHeadless.bat" "$env:TEMP\ghproj" tmp -import "targets\exe\X.exe" -noanalysis

# 2) 单函数校准（首个函数 3~5 分钟属正常）
cmd /c "pnpm exec rea decompile ""targets\exe\X.exe"" <入口地址> --json > out\p.json"

# 3) 全量导出（实测 3049 选中 / 2618 写出 / 431 external / 0 failed，约 6 分钟）
cmd /c "pnpm exec rea decompile-all ""targets\exe\X.exe"" --output out\<项目>\decompiled --json > out\<项目>\decompile-all.json"
```

导出的 `.c` 文件头有一段 `// provider / limitations` 注释，检索前先剥掉，否则全是噪音。

## 分发形态

本项目使用 **CLI + 项目内 skill** 的组合，**不要安装 REA 插件**，也**不要运行 `rea setup`**。

| 形态 | 本项目是否使用 | 说明 |
|---|---|---|
| CLI（`pnpm exec rea`） | ✅ 唯一调用方式 | |
| 项目内 skill（`.agents/skills/` + `skills/`） | ✅ | 已随仓库提交 |
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
| `skills/` | 项目自建 skill（按目标类型） | 是 |
| `tools/` | Ghidra 12.2、JDK 25、Python venv 等本地工具链；`tools/unpack_wxapkg.py`、`tools/ghidra-env.ps1` 例外，入库 | 否（脚本除外） |

分析产物一律写到 `out/<项目名>/`，不要污染 `targets/` 或仓库根目录。

## 不要做的事

- 不要修改 `~/.claude/settings.json`、`~/.cc-switch/` 等与本项目无关的配置。
- 不要在未获授权时下载或安装任何东西，规则见上文「安装授权」。
- 不要为了“让命令跑通”而临时全局安装包；先确认项目内是否已有依赖。
- 不要提交 `node_modules/`、样本文件、反编译产物。

## 已知环境事实（2026-11 实测）

- 平台：Windows x64；D 盘约 230 GB 空闲。
- Node v24.22.3（nvm-windows）、pnpm、REA 6.9.0（`pnpm exec rea`）。
- `missing_analysis_engine` 只在未激活 Ghidra 时出现；`config_drift`（`registration:*` / `skill:*`）表示未注册为 MCP 客户端，CLI 用法下可忽略。
- Windows 上不支持依赖 Linux 工具链的能力：固件分析、pcap、进程捕获、桌面应用捕获。
- **MCP 不要再试**：本机 REA 的 14 个工具入参 schema 带 `^[\uD800-\uDFFF]*$`，DeepSeek 服务端不认这个正则转义，
  一旦挂上 MCP 就整轮 `INVALID_REQUEST`（`Invalid schema for function 'mcp__rea__binary_session'`），
  且 `REA_MCP_INPUT_SCHEMA_PROFILE=compact` 不解决。历史配置已回滚，别重装 `Fanqi89/dsh-rea` 之类的桥接插件。

### 项目内工具链与绝对路径（都不在 PATH）

| 用途 | 路径 | 备注 |
|---|---|---|
| Python（Hermes/PE 分析） | `tools\.venv\Scripts\python.exe` | 3.12.4；hermes-dec 0.1.8、pefile、capstone |
| Hermes 反汇编/反编译 | `tools\.venv\Scripts\hbc-file-parser.exe` / `hbc-disassembler.exe` / `hbc-decompiler.exe` | 只读 Hermes 字节码 |
| Ghidra | `tools\ghidra` | 需先设 `GHIDRA_INSTALL_DIR` |
| JDK 25 | `tools\jdk25` | Ghidra 12.2 硬性要求；`java -version` 应 25.0.5 |
| 7-Zip 22.01 | `D:\Program Files\7-Zip\7z.exe` | 解 APK/zip 比 `Expand-Archive` 快很多 |
| adb 34.0.4 / aapt | `D:\Program Files\leidian\LDPlayer9\` | 雷电模拟器自带 |
| Android 设备 | `emulator-5554` | 雷电 9，Android 9，x86_64，1600x900，可直接装 APK 跑 |

### Windows / PowerShell 踩坑备忘

- **`pwsh` 单次调用 300 秒超时**：超时会杀进程并重置持久 shell（env、cwd 全丢）。长任务一律
  `Start-Process` 后台跑 + 轮询文件大小，不要把 10 分钟的命令放在前台。
- **本机 `curl` 是 7.55.1**（WinSSL），**没有 `--parallel`**（需 ≥7.66）。
- `curl -K <配置文件>`：文件里路径必须用**正斜杠**，写 `D:\...` 会被当转义，文件会落到别处。
- `[IO.File]::WriteAllText` 默认写 UTF-8 **带 BOM**，BOM 会让 `curl -K` 解析失败 → 传 `New-Object System.Text.ASCIIEncoding`。
- PowerShell 5.1 的 `Wait-Process` **没有 `-Timeout`**，加了会立即返回；用 `while` 轮询 `HasExited`。
- `Start-Process -ArgumentList` 不自动加引号：URL 带 `&` / `%` 会被截断 → 长 URL 走配置文件或手工转义。
- `npm view` 在本目录会因 `package.json` 的 `devEngines` 报 `EBADDEVENGINES`，要用请换临时目录或直接 `pnpm`。
- 需要写多行文本/脚本时，用 `[IO.File]::WriteAllText(..., New-Object System.Text.UTF8Encoding($false))`，
  比 `Out-File` 稳（不会带 BOM、不会按 GBK 转码）。
