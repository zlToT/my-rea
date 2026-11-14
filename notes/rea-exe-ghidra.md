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
## 附：一个闭源搜索类 exe 的实现骨架（案例）

下面是同一个样本拆到"数据布局 / 查询执行 / 索引构建 / 对外接口"四层后的结果，用来演示第 3 节的方法能读到多深；地址是 imagebase `0x140000000` 的绝对地址，只对这份样本有效。**未查明的部分单独列在最后，不做推测性补全。**

### 1. 数据模型

#### 1.1 名字存储
- 名字条目（name entry）：`+0x00..+0x07` 元数据（首 dword 复用为"匹配计数/标记"），**`+0x08` = 长度字节**，**`+0x09` 起 = 字符**。
- 长名：当 `+0x08 == 0xFF` 时，真实长度取 `ptr[-4]` 的 dword。
- 字符按窄字节存（`char`），非 wchar —— 与 `utf8` 选项/`utf8content:` 过滤键呼应；具体编码（UTF-8 vs ANSI）尚未实测确认。
- 证据：`db_get_result_name` 0x140019320（`*(char*)(entry+8)`、`entry+9`、`ptr[-4]`）；`db_get_result_path` 0x140019280。

#### 1.2 块化数组（样本程序的核心容器）
- 数组头：`+0x00` = 块指针数组，`+0x24` = 块数量。
- 块头：`+0x00` = 该块起始全局索引，`+0x10` = 元素区偏移，`+0x14` = 元素个数；元素为 8 字节指针。
- 查找 `FUN_140001b30`：先在块头数组上**二分**定位块（按 first_index），再块内下标直接寻址；`FUN_140001a60` 是"下一个元素"的顺序递增。
- 扩容 = 追加新块，旧块不搬迁 → 索引进行中可并发读，读取端永远看到"已完成的块"。这是"边建索引边能搜"的结构基础。

#### 1.3 查询对象（0x4f8 字节，`db_query_create` 0x140017000）
- 三条结果链：`+0x58`（数量 `+0x78`）、`+0x30`（`+0x50`）、`+0x08`（`+0x28`）；`db_get_result_count` = 三者之和，顺序取决于模式 `+0x434` 与排序类型 `+0x444`。
- 结果索引 → 记录：`FUN_140010e50` 按上述顺序换算，带 1 项缓存（`+0x170` 状态 / `+0x174` 下标 / `+0x178` 指针），因此"顺序遍历结果"是 O(1) amortized。
- 两条 term 链：`+0x128`（include，`+0x130` 尾指针）、`+0x138`（exclude），由 `FUN_14006ab50` 清空。
- term 节点 32 字节：`+0x00` next，`+0x18` type，`+0x20` **matcher 函数指针**，`+0x38` flags，`+0x40` 临时缓冲，`+0x48` matcher 私有状态。
- 构造节点：`FUN_140054f10`（自定义大小）/`FUN_140055090`（固定 0x20）。

### 2. 查询执行

1. `db_query_search` 0x140017580（1269 行）：日志 `search '%s' filter '%s' sort %d\n` → 清 term 链 → 解析（`FUN_140065860`，日志 `termtext %s`）→ 逐 term 走 `key:value` 分派 → 挂进 include/exclude 链 → 起线程。
2. 执行线程：`FUN_1400dfd80(FUN_1400af8b0, query)`；`FUN_1400af8b0` 处理 SET SORT/统计（`total size %I64u, calculated in %f seconds`）→ `FUN_1400ae4a0`（690 行）做真正的扫描。
3. 扫描循环（`FUN_1400ae4a0` L144 起）：
   ```
   for (node = query->terms; node; node = node->next) {
     switch (node->type) {
       case 0x16e: case 0x16f:   // 只打标记（命中 → entry[8]=1）
       case 0x170: case 0x171:   // 命中计数（entry 首 dword 累加）
       case 0x172: case 0x173:   // 第三类（子项/路径类）
     }
     for (block = ...; ...) for (p = elems; ...) {
        len = (entry->lenbyte == 0xff) ? entry[-4] : entry->lenbyte;
        if (node->matcher(entry->name, len, node->state, node->flags)) hit(entry);
     }
   }
   ```
   → 每个 term 独立一遍"全表扫描"，命中就地打在条目上（分支预测友好、无额外结果数组）。
4. 日志 `found %d folders, size %d, db search time taken: %f seconds`。
5. 排序：`FUN_1400152c0` + 日志 `SET SORT %d` / `bad flip sort %d`（结果链按需反转）。

#### 查询语言（已确认的过滤键 → 解析函数）
`size:`(0x140055530) `infolder:`/`parent:`/`nosubfolders:`(0x140056460) `parents:`/`depth:`(0x140057050) `runcount:`(0x140057330) `count:`(0x140057600) `filelist:`(0x140058190) `attributes:`/`attrib:`(0x140058600) `startwith:`(0x140058a30) `endwith:`(0x140058cf0) `type:`(0x140059410) `filelistfilename:`(0x140059900) `content:`/`ansicontent:`/`wcharcontent:`(0x140059d60) `child:`(0x14005af80) `childcount:`(0x14005b360) `childfilecount:`(0x14005b6c0) `childfoldercount:`(0x14005ba20) `datemodified:`(0x140060cc0) `dateaccessed:`(0x140061150) `recentchange:`(0x1400615b0) `wholefilename:`/`exact:`(0x140065860 内) ；全局开关 `case:` `nocase:` `regex:` `wholeword:` `diacritics:` `utf8content:`。

### 3. 索引构建与增量更新

`db_rebuild` 0x140025ed0 的日志顺序即流程：
```
save run history → set ood → clear queries → clear folder updates → clear monitors
→ destroy service → clear read dir changes → clear filelist monitor → remove events
→ create volume list → copy config → fire create events → start rebuild thread
```
- 重建线程 = `FUN_14001d760`（6037 行，最大单函数之一），由 `FUN_1400dfd80` 起，指针写回 `*db`。
- **NTFS 直读**（`FUN_1400cfc60`）：`DeviceIoControl(handle, 0x90064)` = FSCTL_GET_NTFS_VOLUME_DATA；`DeviceIoControl(handle, 0x90068, &frn, 8, out, ...)` = FSCTL_GET_NTFS_FILE_RECORD；随后**手工解析 MFT FILE 记录**：attribute list、`_NTFS_ATTRIBUTE_TYPE_DATA`、mapping pairs → 簇偏移 → `ReadFile` 读簇；错误串 `FSCTL_GET_NTFS_FILE_RECORD failed %u` / `FRN not in use %I64x` / `retry with base %I64x`（父记录/属性扩展记录的重试）。
- USN 增量：`FUN_1400df550`（CreateFileW `\\.\X:` + DeviceIoControl 读 USN 日志），原因位解释表 `0x14004be10` / `0x14004c9e0`；目录级变更另靠 `ReadDirectoryChangesW`（日志 `clear read dir changes`）。
- 其它索引类型：ntfs（0x140010060）、refs（0x140010260）、filelist（0x140010420）、folder（0x140010510）——类型变化即整库重建。
- 建库日志：`build indexes`、`ntfs index: %d folders, %d files`；损坏提示在 0x140015230（串 `.\src\db.c`）。

### 4. 对外接口
- 服务：`CreateServiceW("<Name> Client", ..., 0x10 SERVICE_WIN32_OWN_PROCESS, AUTO_START)`，binPath `"\"%s\" -client-svc"`；控制/删除/`StartServiceCtrlDispatcherW` 见 0x140005a30 / 0x140005910 / 0x1400ec0e0 / 0x1400056b0 / 0x1400f0ac0。
- HTTP：0x1400c50a0（`HTTP/1.0 %d %s`、Basic realm、`HTTP Server`），0x1400c8da0 WSAStartup。
- ETP/FTP：0x1400b8990（`Welcome to <Product> ETP/FTP`）、0x1400b6aa0（`ftp://%s/%s`）。
- 配置：`%APPDATA%\样本程序\样本程序.ini`；注册表 0x1400e2110 / 0x1400da720 / 0x14010f300。
- 外联：仅 0x14016b800 → `http://www.<vendor>.com/<vendor>/beta-update.ini`。

### 5. 仍黑盒
1. **matcher 内部**：0x16e/0x170/0x172 三族的具体比较实现、大小写折叠表、diacritics 表、通配/正则引擎。
2. **排序比较器** `FUN_14006f530`（16028 行，case 0x16e/0x170/0x172）——大小写/自然排序规则。
3. **名字编码**：窄字节到底 UTF-8 还是 ANSI（影响"中文能否全文匹配"）。
4. 内存分配策略（`FUN_1400cf700`/`FUN_1400cf780` 上层池）。
5. 索引线程与搜索线程的并发一致性细节（块数组 append-only 是推断，未读到写锁实现）。
