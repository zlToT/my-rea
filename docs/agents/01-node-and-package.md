# Node 与包管理

> 本文件是 `AGENTS.md` 的分册。`AGENTS.md` 只保留硬性规则与索引，细节按需读这里。

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
