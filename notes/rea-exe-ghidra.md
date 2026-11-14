# REA + Ghidra：Windows 原生 exe 的静态分析流程

本文是一套可复用的**工作方法**（不含任何具体样本的产品名、地址或代码），目标是从一个闭源 Windows exe 走到"能讲清架构骨架"。

## 0. 前置

| 项 | 说明 |
|---|---|
| Ghidra | 解压到 `tools\ghidra`，`rea doctor` 的 `ghidra` 项要全绿 |
| JDK | **Ghidra 12.2 要 JDK 25+**，21 会在 `analyzeHeadless` 处报 `JDK 25+ (64-bit) could not be found` |
| 环境变量 | 只改当前会话：`JAVA_HOME`、`GHIDRA_INSTALL_DIR`、PATH 前置 `%JAVA_HOME%\bin;%GHIDRA_INSTALL_DIR%\support` |
| 检查 | `pnpm exec rea doctor`；`missing_analysis_engine`、`config_drift` 属预期 |

配套坑：
- `tools\*` 在 .gitignore 里，装引擎不进仓库。
- dot-source 一个 env 脚本可能被安全规则拦，直接在命令里设 env 更稳。
- 单次 shell 调用有 300 秒上限，长任务 `Start-Process` 后台 + 轮询。

## 1. 冒烟三步

```powershell
# 1) 只导入不分析，确认能开
analyzeHeadless <proj> <name> -import target.exe -noanalysis
# 2) 单个函数校准，验证反编译器可用（第一个入口一般 3~5 分钟）
pnpm exec rea decompile target.exe 0x<entry>
# 3) 全量
pnpm exec rea decompile-all target.exe --output out\<样本>\decompiled --json > out\<样本>\decompile-all.json
```

`decompile-all` 的 `counts` 里：`selected` 是候选、`written` 是真落盘、`external` 是导入/外部（没函数体）、`failed` 应关注。每个 `.c` 文件头部有一大段 `// provider / limitations` 注释——**建索引前先剥掉**，否则检索噪音极大。

## 2. 建导航（这一步决定效率）

不要一上来读函数，先把全局关系做成可查的表：

1. **调用图**：正则抓 `FUN_([0-9a-f]{6,})` 得到 callees，反向得到 callers，存 `callgraph.json`（`{callees:{addr:[...]}, callers:{...}}`）。
2. **fan-in 排序**：callers 最多的几乎都是基础设施（字符串构造、日志、内存包装）。先认它们，后面读业务函数能省一半猜。
3. **字符串/符号扫描**：按前缀聚类（`db_*`、`ntfs_*`、`http_*`…），并从残留调试串（`log("search '%s' ...")`、`.\src\xxx.c`）反推源码模块划分——闭源程序里的日志是最好的注释。
4. **按需打印**：写个小脚本支持 `body <addr> [max]`、`slice <addr> s e`、`calls <addr>`（只列调用行）、`import <API名>`（谁引用了某 API）、`refs <addr>`。

## 3. 读伪代码的套路

- 先抓"入口族"：`main`/`entry` → 服务/窗口/命令行分支 → 三个方向（配置、索引、对外接口）。
- 数据布局靠**小函数反推**：`get_result_name` 这种 5 行的取值函数，一行就能读出结构体字段偏移与变长规则，比自己翻大函数快得多。
- 看到 `(*(code *)ptr[i])(...)` 就是虚函数/回调表——这类结构说明设计上有"策略对象"，顺着类型常量去找分派表。
- 巨型函数（几千到上万行）多半是生成的跳转表或 `switch` 汇总，不要逐行读，先看 `case` 常量与日志串确认语义域。
- Ghidra 的 `undefined8`/`param_1` 别急着改名，等字段含义稳定后再一次性建 struct（Ghidra 里改会传播到引用点，早期改名纯浪费）。

## 4. 结论的可信度分级

给结论时严格标级别，否则很容易把"见过"说成"知道"：

| 级别 | 依据 | 表述 |
|---|---|---|
| 确认 | 读过实现 + 有日志串/常量对照 | "它这样做" |
| 推断 | 结构/调用关系合理但未读实现 | "应该是……" |
| 未知 | 只看到接口 | "这块还没查" |

## 5. 边界

闭源软件：反编译结果自用学习可以，**不要分发**代码片段、不要发布改造版；仓库里只放方法论与架构级描述，具体产物留在 gitignore 内。