# ai-rea

本地 AI 逆向工作区。核心工具是 [REA](https://github.com/morluto/rea)（`rea-agents`），
以 CLI 方式调用，不注册 MCP，不污染其他客户端的配置。

## 环境

| 组件 | 版本 | 说明 |
|---|---|---|
| Node.js | 24.22.3 | 由 nvm-windows 管理 |
| pnpm | 12.18.0 | 按项目安装，非全局 |
| REA | 6.9.0 | 锁在 `package.json`，不自动升级 |

REA 的 Node 要求：`^22.23.4 || ^24.22.1 || >=26.12.1`。换版本后必须重新满足。

## 目录

```
ai-rea\
├─ targets\    待分析样本，一个目标一个子目录（不入库）
├─ out\        反编译产物 / evidence 导出（不入库）
├─ notes\      环境快照、结论记录（入库）
└─ tools\      可选工具链：Ghidra、JDK 等（不入库）
```

## 常用命令

```powershell
# 版本与环境自检
pnpm exec rea --version
pnpm exec rea doctor --json

# JS / Electron 应用静态分析（不需要任何引擎）
pnpm exec rea analyze-javascript-application "D:\path\to\app" --json

# 单函数反编译（需要 Ghidra / IDA 引擎）
pnpm exec rea decompile "D:\path\to\target.exe" --procedure main --json
```

## 分析引擎状态

| 引擎 | 状态 | 用途 |
|---|---|---|
| 内置解析器 | 可用 | JS/Electron、.NET、Godot PCK、IL2CPP metadata、APK 结构、HAR/SAZ、PE/ELF 头 |
| Ghidra 12.1.4 + JDK 21 | 未安装 | 原生二进制伪代码（Windows 为实验性、只读、仅 x64 PE） |
| JADX | 未安装 | APK 反编译（需 JDK + `jadx-headless-mcp` 0.7.1 JAR） |
| IDA / Hopper / Kuna | 不适用 | 付费或不支持 Windows |

`rea doctor` 中 `missing_analysis_engine` 属于预期缺口；
`config_drift`（registration:*/skill:*）表示未注册为 MCP 客户端，CLI 用法下可忽略。

## 注意事项

- **不要 `npm i -g` 或 `pnpm add -g` 装 REA**，保持项目内安装，避免与其他工具冲突。
- **升级前先看 release notes**：REA 迭代很快，`--json` 的字段可能变化。
- **不要删 `D:\.pnpm-store`**：所有 D 盘项目的包都硬链接在这里。
- nvm 切换 Node 版本后，全局包（claude-code、pnpm）按版本隔离，需要重新安装。
- Windows 上不支持依赖 Linux 工具链的能力（固件、pcap、进程捕获、桌面捕获）。

## 复刻游戏时的能力边界

- 能帮：逻辑层——规则计算、状态机、协议、数据结构、Unity IL2CPP 符号还原
- 不能帮：内容层——美术资源、动画、数值表、手感参数（需要 AssetStudio / AssetRipper 等专用工具）
