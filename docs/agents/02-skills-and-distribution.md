# 项目内 skill 与分发形态

> 本文件是 `AGENTS.md` 的分册。`AGENTS.md` 只保留硬性规则与索引，细节按需读这里。

## 项目内 skills

本仓库有两类 skill，均已随仓库提交，可直接读取，无需安装：

- `.agents/skills/`：REA 自带的通用逆向 skill，升级 REA 时同步；
- `skills/`：本仓库针对具体目标类型整理的操作手册。

| skill | 路径 | 何时加载 |
|---|---|---|
| `reverse-engineer-anything` | `.agents/skills/reverse-engineer-anything/SKILL.md` | 任务涉及逆向、反编译、分析发布产物时 |
| `wechat-minigame-reversing` | `skills/wechat-minigame-reversing/SKILL.md` | 目标是微信小游戏、`wxapkg`、雷电 WMPF 缓存时 |
| `android-game-reversing` | `skills/android-game-reversing/SKILL.md` | 目标是 Android 游戏 APK：判定引擎/壳、解包、WebView 缓存取证、资源还原时 |

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

## 分发形态

本项目使用 **CLI + 项目内 skill** 的组合，**不要安装 REA 插件**，也**不要运行 `rea setup`**。

| 形态 | 本项目是否使用 | 说明 |
|---|---|---|
| CLI（`pnpm exec rea`） | ✅ 唯一调用方式 | |
| 项目内 skill（`.agents/skills/` + `skills/`） | ✅ | 已随仓库提交 |
| MCP 注册（`rea setup`） | ❌ | 会改 `~/.claude.json`、`~/.codex/` 等客户端配置 |
| 插件（Claude / Codex / Cursor Marketplace） | ❌ | 绕开 `rea doctor` 管理，且与项目内 skill 重复 |

插件安装后 `doctor` 里的 `registration:*` / `skill:*` 仍会报 missing，这是两套状态互不认，**不要因此重装**。
