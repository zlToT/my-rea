# 分析引擎与工具链启用

> 本文件是 `AGENTS.md` 的分册。`AGENTS.md` 只保留硬性规则与索引，细节按需读这里。

## 分析引擎状态

| 引擎 | 状态 | 用途 |
|---|---|---|
| 内置解析器 | 可用 | JS/Electron、.NET、Godot PCK、IL2CPP metadata、APK 结构、HAR/SAZ、PE/ELF 头 |
| **Ghidra 12.2 + JDK 25** | **已装（项目内）** | 原生二进制伪代码；Windows 只读、仅 x64 PE |
| 项目内 Python venv | 已装 | Hermes 字节码（`hbc-*`）、PE 解析（`pefile`）、反汇编（`capstone`） |
| **JADX 1.5.1** | **已装（项目内）** | APK → Java 源码；命令行主类 jadx.cli.JadxCLI，见下方工具链表 |
| **Apktool 2.10.0** | **已装（项目内）** | APK → 可读 Manifest / resources / assets；见下方工具链表 |
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

### 启用 JADX / Apktool（项目内，2026-11 装）

两个工具都在 tools\ 下（被 .gitignore 覆盖），不在 PATH、不写注册表，复用仓库自带 JDK 25：

~~~powershell
java -cp tools\jadx\lib\jadx-1.5.1-all.jar jadx.cli.JadxCLI -d out\<项目>\jadx-src --no-res -j 8 <apk>
java -jar tools\apktool\apktool.jar d <apk> -o out\<项目>\apktool -f
~~~

坑：

1. 直接 java -jar jadx-1.5.1-all.jar 会拉起 GUI 且静默不产出（进程活着、输出目录空），必须 -cp + jadx.cli.JadxCLI。
2. --deobf 会把包名改成 com.p042qk.plugin.p044js.shell 这类形式，默认不要开。
3. apktool 默认还产出 6 个 smali 目录（约 44 MB），与 jadx 输出重复，不需要就加 -s 跳过。
4. jadx 的 user.home 可能识别歪，会在仓库根建 PowerShell 7.6.6\skylot\... 缓存目录，跑完检查并删掉。
5. 大文件下载：github.com:443 直连超时（curl exit 7）。镜像实测 ghfast.top 可用（约 0.5 MB/s）、ghproxy.net 太慢（约 30 KB/s）；kkgithub.com / ghp.ci / hub.gitmirror.com / gh.llkk.cc 均不可用；repo1.maven.org 可达（备用）。jadx zip 111 MB，解包后删 zip。
