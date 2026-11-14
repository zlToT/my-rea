# React Native / Hermes 类 APK 的静态逆向流程

> 通用方法论笔记，不含任何具体目标的信息。记录的是「拿到一个 RN 包该怎么下手」以及踩过的坑。

## 1. 先判定包的类型（决定后面值不值得上 JADX）

不装任何工具就能判，两个信号：

1. `lib/<abi>/` 下是否同时出现 `libhermes.so`、`libreactnativejni.so`、`libfabricjni.so`，且通常有 arm64-v8a / armeabi-v7a / x86 / x86_64 四套。
2. `assets/index.android.bundle` 是否为 MB 级单文件。

两者都命中 → 业务逻辑在 Hermes 字节码，dex 里只剩壳和 RN 运行时，**JADX 只能看到桥接层，收益很低**。
反之若见到 `libil2cpp.so` / `libunity.so` / `assets/bin/Data`，那是 Unity 路线，另说。

## 2. REA 在这条路线上的定位

- `pnpm exec rea doctor`：确认 CLI/配置状态。`missing_analysis_engine`、`config_drift` 属于预期提示，不是故障。
- Windows 上跑 `rea --json` **必须**重定向到文件再读：
  ```powershell
  cmd /c "pnpm exec rea <cmd> --json > out\x.json"
  ```
  用 PowerShell 的 `>` 会按 GBK 转码写文件，JSON 直接坏掉（非 ASCII 内容变成 `?`）。
- 安装类操作一律装进项目内（本地 venv / `tools/`），不要全局装；每次安装前说清体积和副作用。

## 3. Hermes 字节码：三步走

| 步骤 | 工具 | 产出 | 用途 |
|---|---|---|---|
| 1 | `hbc-file-parser` | 头部字段 | 判断能否解析 |
| 2 | `hbc-disassembler` | `.hasm` | 权威指令流、函数边界、行号锚点 |
| 3 | `hbc-decompiler` | `.hast` | **寄存器级伪 JS，读逻辑就看这个** |

头部里必须核对的字段：

- `magic`：**8 字节**（两个 32 位字拼起来，如 `0x1f1903c103bc1fc6`）。只按前 4 字节比对会得出"魔数被改过"的错误结论——这是本项目踩过的第一个坑。
- `version`：决定 opcode 表。版本不认识就必须换工具/换版本，硬着头皮读会得到全错的指令名。
- `functionCount` / `stringCount` / `identifierCount`：决定要不要建索引。
- `fileLength` / `sourceHash`：校验是否截断、拿来做样本指纹。

体积经验：3MB 左右的 bundle → `.hasm` 40MB+、`.hast` 20MB+，直接读不可能，**必须先建索引**。

## 4. 建索引（脚本思路）

`.hasm` 是高度规整的文本，切函数不用理解字节码：

- 函数头：`=> [Function #<id> "<name>" of <bytes> bytes]: <n> params, frame size=<f>, ... @ offset 0x...`
- 指令行：`==> <offset>: <Opcode>: <operands>  # String: '<值>' (String|Identifier)`

做法两步：

1. 按函数头把文件切成 N 段，记下每段的 `start`/`end` 行号；
2. 每行末尾的 `# String:` 注释抽出，(函数 id, 字符串) 建倒排表。

之后就可以用正则问"哪个函数提到了某关键字"，再按函数 id 回 .hasm/.hast 精读。这一步把"翻 40MB 文本"变成"查表"，是整条流程里性价比最高的投入。

## 5. 读代码时的常见坑

- **三方库噪音**：日期库、CSS 解析器、路由库会贡献大量字符串（尤其各种规范文档 URL），关键词命中先看函数名和调用方再投入。
- **匿名函数占比高**：三成以上的函数没有名字，找闭包体要看 `CreateClosure` 指令里的 `function_id`。
- **业务代码会重复多份**：多个子应用/页面各自打一份相同的工具函数，改的时候别只改一处。
- **async 编译成状态机**：`StartGenerator` / `SaveGenerator` / `ResumeGenerator`，读的时候按 `await` 的位置切段理解，别按线性流读。
- **百分比字段统一 `/100`**：数值公式里见到 `/100` 再 `1+x` 的写法，基本就是"基础值 × (1 + 百分比)"。
- `.hast` 里寄存器会复用，同一变量名 `r5` 在不同 case 里含义不同，要以 `case` 边界为准。

## 6. 边界

- 静态阅读不修改样本；要改包就得重打包 + 重签名，属于另一个量级的工作。
- 产物（样本、反编译输出）不入库，只入库方法与结论。

## 附：一个 RN + Hermes 游戏的存档与数值案例

把第 3~5 节的流程在同一个样本上跑完后得到的实际结论，作为"能挖到什么颗粒度"的参照。函数编号对应 `funcs.json` 的 id，行号对应 `index.hast`；均只对这份样本有效。

### 1. 整体架构

- React Native + Hermes（version 90），业务全部在 `assets/index.android.bundle`。
- 3 个内置网页小游戏，共用一个大 redux store，action 前缀 `setSmallGame00XData`：
  | 编号 | 存档 action（`funcs.json` #4174 `reducer`） |
  |---|---|
  | 001 | `setSmallGame001Data`（主游戏） |
  | 002 | `setSmallGame002Data` |
  | 003 | `setSmallGame003UserData`（挂机/放置类） |
- 状态键：`smallGame001UserData` / `smallGame002UserData` / `smallGame003UserData`，另有 `smallGame00XMenu`、`smallGame001Equip` / `Dan` / `Passive` / `Hero`。

### 2. 存档协议（服务端，无本地持久化主路径）

`funcs.json` #12192 `createUserData`（hasm line 505677）：
```
POST http://<host>/addSaveData
body = { json: JSON.stringify(userData), redeem: <redeem> }
```
`funcs.json` #12199（hasm line 505851，async generator）：
```
POST http://<host>/getSaveData
body = { redeem: <redeem> }
→ resp.json → JSON.parse(resp.json)
→ if (json.gameId !== routerData.gameId)  弹 Alert「此导入码不是「<gameName>」的！\n是否强制导入？可能导致存档损坏！」
→ dispatch({ type: 'setSmallGame'+gameId+'Data', data: json, label: '更换存档' })
→ Toast.success('导入存档成功')
```
- 客户端键名规则：`'smallGame' + routerData.gameId + 'UserData'`。
- `redeem` 就是导入码/存档身份，服务端以它做 key；**同一 redeem 可跨设备取回存档**。
- 三份拷贝对应 3 个小游戏：#12192/12199（game001）、#13769/#13776（game002）、#14809/#14816（game003）。
- AsyncStorage 只在库里（#5203 `PlatformLocalStorage`），主存档路径不走本地。

### 3. 战斗数值（funcs.json #12030 `fightOneRound`，hast L462414）

```
先手 = (hero.atk速度等效 >= enemy速度等效) ? 'hero' : 'enemy'
  速度等效 = attribute.speed * (1 + speedPercent/100)

for a of attacker.animalData:            // 最多 2 个（animalChooseIndex / animalTogetherIndex）
    if (a.effectPercent > rand(1,100)):  // 千分/百分比节奏判定
        atk  = attribute.atk * (1 + atkPercent/100)
        mult = 1 + (attribute.damagePercent - defender.reduceDamagePercent)/100
        base = atk * mult
        val  = max(1, base * a.effectValue / 100)
        if a.effectType === 'damage': defender.hp -= val   // 「造成了<中文数字>伤害」
        else:                        attacker.hp += val    // 「恢复了<中文数字>生命」
    else: 标签 '未触发'
// 双方各打一轮；enemy.hp<=0 时本方不还手（且标签全填 '未触发'）
// 结尾：hero.hp<=0 且 !hero.status.isYunxuan → '被击败了'
```
- 百分比字段统一 `/100` 归一，默认值 0，即 `damagePercent=0` 时倍率为 1。
- `attribute.hpMax` 在 #12027 `getFightResult` 里被设为开战前的 `hp`。
- 敌人数值来自 `towerFloorNum2EnemyAttribute(floorNum)`（hast L162544），即**层数→敌人属性**的纯函数，改层数或改函数即可控敌强度。
- `attribute2Power`（#4195）、`randomOneEquip`（#4218）、`addItem`（#4204/#11947）、`useOldEquip`（#12024）是配套的装备/道具/战力换算。

### 4. 挂机钻石（自动化收益的核心，funcs.json #14108 `onPressGetDiamond`，hast L576623）

```
每次领取 = 6480 钻石
冷却     = 300 秒（giftData.getDiamondTimeStamp + 300*1000 与 now 比较）
if (giftData.lifeCardTest) → 直接 diamond += 6480，不更新冷却时间戳   // 「开发者模式已开启，钻石+6480」
else                        → diamond += 6480，更新 getDiamondTimeStamp
```
- 之后 dispatch `{type:'setSmallGame003UserData', label:'挂机钻石领取'}`；**新存档上传走 createUserData → addSaveData**。
- 同一函数还有分层奖励：`floorNum < 阈值` 时奖励文案变成 `钻石+6480*floorNum`。
- 其他钻石入口：#13100 / #14108 `onPressGetDiamond`、#14495「立刻获得64800钻石」「每5分钟可领取6480钻石」。

### 5. 待办

- 存档 userData 完整字段表（diamond / floorNum / animalList / oldEquipChooseList / giftData 已确认存在）。
- 小游戏 001 的关卡/推图逻辑、装备品质与战力公式。
- 是否需要"改包"（需要 hbctool 重打包 → 会改签名）。
