# 常用命令与任务配方

> 本文件是 `AGENTS.md` 的分册。`AGENTS.md` 只保留硬性规则与索引，细节按需读这里。

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
