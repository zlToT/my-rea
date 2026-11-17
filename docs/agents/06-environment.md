# 已知环境事实与 PowerShell 踩坑

> 本文件是 `AGENTS.md` 的分册。`AGENTS.md` 只保留硬性规则与索引，细节按需读这里。

## 已知环境事实（2026-11 实测）

- 平台：Windows x64；D 盘约 230 GB 空闲。
- Node v24.22.3（nvm-windows）、pnpm、REA 6.9.0（`pnpm exec rea`）。
- `missing_analysis_engine` 只在未激活 Ghidra 时出现；`config_drift`（`registration:*` / `skill:*`）表示未注册为 MCP 客户端，CLI 用法下可忽略。
- Windows 上不支持依赖 Linux 工具链的能力：固件分析、pcap、进程捕获、桌面应用捕获。
- **MCP 不要再试**：本机 REA 的 14 个工具入参 schema 带 `^[\uD800-\uDFFF]*$`，DeepSeek 服务端不认这个正则转义，
  一旦挂上 MCP 就整轮 `INVALID_REQUEST`（`Invalid schema for function 'mcp__rea__binary_session'`），
  且 `REA_MCP_INPUT_SCHEMA_PROFILE=compact` 不解决。历史配置已回滚，别重装 `Fanqi89/dsh-rea` 之类的桥接插件。

- **JADX 1.5.1 + Apktool 2.10.0 已装（项目内）**：tools\jadx\lib\jadx-1.5.1-all.jar、tools\apktool\apktool.jar，运行时复用 tools\jdk25。

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
| JADX 1.5.1 | `tools\jadx\lib\jadx-1.5.1-all.jar` | 用 `tools\jdk25\bin\java.exe` 跑，必须 `-cp ... jadx.cli.JadxCLI` |
| Apktool 2.10.0 | `tools\apktool\apktool.jar` | `java -jar` 直接可用；smali 目录一般可删（或加 `-s`） |

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
