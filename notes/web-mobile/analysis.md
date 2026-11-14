# web-mobile 逆向案例：Cocos 打包三消 → 纯 Canvas 复刻

> 样本：`targets\web-mobile`（Cocos Creator 2.x `web-mobile` 构建，3.8 MB）
> 原版逻辑：`assets/main/index.18f60.js`（7.2 KB，单行压缩、未混淆）
> 复刻：`out\web-mobile\game\index.html`（单文件，无依赖）
> 日期：2026-11-14

这份文档把「原版做了什么」和「复刻怎么写的」逐项对齐，既当复刻说明，也当一次
完整的网页游戏逆向案例：从发布产物定位逻辑、还原规则、重写实现，到自动化验证。

---

## 一、结论速览

| 问题 | 结论 |
|---|---|
| 游戏类型 | 5×5 点击升级、同级 3 连消除的休闲益智「拼消块块」 |
| 逻辑规模 | 5 个 Cocos 组件，约 600 行；核心规则可压缩到 300 行内 |
| 能否完整还原 | 能。棋盘表、坐标、阈值、动画时长、音量全在同一个脚本包里 |
| 资源情况 | 9 张方块图 + 5 张 UI + 9 段音频，明文 PNG / MP3，无图集、无加密 |
| 复刻技术栈 | 原生 Canvas 2D + `requestAnimationFrame`，零依赖 |
| 规则一致性 | 坐标、数值、状态流转、动画时序一致；引擎与音频实现方式不同 |
| 验证方式 | 无头 Chrome + CDP 做坐标、重力、消除、满级、结算与随机压测 |

---

## 二、产物与产出位置

| 路径 | 内容 |
|---|---|
| `targets\web-mobile\` | 原始打包产物（只读） |
| `targets\web-mobile\assets\main\index.18f60.js` | 全部游戏逻辑，7337 字节 |
| `out\web-mobile\assets-recovered\` | 提取后的资源（23 个文件，1.94 MB） |
| `out\web-mobile\game\` | 可运行复刻：`index.html` + `assets\` + `.serve.cjs` + `README.md` |
| `notes\web-mobile\analysis.md` | 本文 |
| `notes\web-mobile\rea-vs-manual.md` | REA 工具与手工阅读的对照 |

复刻运行方式：

```powershell
cd out\web-mobile\game
node .serve.cjs
# http://127.0.0.1:8777
```

---

## 三、逆向路径：怎么从打包产物找到全部逻辑

### 3.1 文件结构

```
targets\web-mobile\
├─ index.html                    标题 "Cocos Creator | Blocks"
├─ cocos2d-js-min.8ded5.js      引擎本体 1.8 MB（与玩法无关）
├─ main.fb3d8.js                 引擎启动器
├─ src\settings.0f08a.js         竖屏配置、首场景 db://assets/login.fire
└─ assets\main\
   ├─ index.18f60.js             ★ 游戏逻辑模块包
   ├─ config.18f60.json          资源清单（uuid → 类型）
   ├─ import\05\...json          main.fire 场景
   ├─ import\0e\...json          login.fire 场景
   └─ native\                    实际 PNG / MP3
```

### 3.2 四个关键动作

| 顺序 | 看什么 | 得到什么 |
|---|---|---|
| 1 | `index.html` 标题、`settings` | 游戏名、竖屏、首场景是 login |
| 2 | `assets/main/index.18f60.js` | 5 个模块的完整源码 |
| 3 | 脚本里的 `"main-blockManager": [function..., {...}]` | Cocos 2.x 的 `__require` 模块表；函数名未混淆 |
| 4 | `import\05\...json` 场景 JSON | 节点树、坐标、尺寸、颜色、prefab 引用 |

原版模块包的结构是：

```js
__require("main-blockManager", function () {
  return {
    "main-blockManager": [function (require, module, exports) { ... }, {...}],
    // login-canvas / login-music / main-canvas / main-music 同理
  };
});
```

因此不需要反编译，只要按模块名搜函数即可。场景 JSON 则把布局参数直接写成了
`_contentSize`、`_position`、`_color`，连试错都省了。

---

## 四、模块映射总表

| 原版模块 | 原版职责 | 复刻落点（`index.html` 行号） |
|---|---|---|
| `login-canvas` | 登录页按钮摆动、点击进 main | `drawLogin()` 394–426；`pointerdown` 502–519 |
| `login-music` | 登录 BGM，跨场景持续 | `bgm` 89–92；`unlockAudio()` 96 |
| `main-blockManager` | 棋盘、升级、泛洪、消除、重力、补块、连锁 | `startGame()` 153–178；`flood()` 180–193；`doActionForBook()` 205–234；`blockDown()` 236–252；`checkNullBlock()` 254–266；`checkCount()` 268–282 |
| `main-canvas` | 输入、血量、分数、结束 | `G` 136–147；`tap()` 284–305；`gameOver()` 307–316；`drawHp()` 354–363；`drawScore()` 365–379 |
| `main-music` | 点击 / 结束 / 连击音效 | `sfx` 84–88；`play()` / `playCombo()` 94–95 |
| Cocos `Component` 生命周期 | `onLoad` / `start` / `update` | `G.mode` 状态机 + `advance()` 469–481 |
| `cc.NodePool` | 30 个方块节点复用 | 普通 JS 对象 + `G.dying` 数组（无节点创建） |
| `cc.runAction` / `scheduleOnce` | 补间与延时 | `tw()` 105–114；`timer()` 115；`step()` 118–133 |
| `cc.director.loadScene("login")` | 场景切换 | `G.mode = "login"` + `clearAnim()` |
| `cc.audioEngine` | 音乐 / 音效 | `HTMLAudioElement`（音量同为 0.2 / 0.4） |
---

## 五、逐项对照

### 5.1 设计分辨率与棋盘坐标

**原版**（`main.fire` + `blockManager`）：

```
设计分辨率 720×1280；棋盘节点在画布中心 (360,640)
格宽 130；格心相对棋盘节点：
  x = 130*col - 260      col 0..4
  y = 260 - 130*row      row 0..4，row 0 在最上面
```

**复刻**（`index.html:31-41`）：

```js
const W = 720, H = 1280, CX = 360, CY = 640;
const CELL = 130, GRID = 5, HALF = 325;
const cellX = c => CX + (CELL * c - CELL * (GRID - 1) / 2); // 100 + 130c
const cellY = r => CY - (CELL * (GRID - 1) / 2 - CELL * r); // 380 + 130r
const BOARD_L = CX - HALF, BOARD_T = CY - HALF;             // 35 / 315
```

两者等价：原版节点坐标 y 向上，复刻 Canvas y 向下，于是
`canvasY = CY - nodeY`，格心从 `380 + 130r` 开始。

### 5.2 开局铺盘

**原版 `gameStart`**：双重循环生成 `level = rand(0,4)`，如果与上邻或左邻同级就重 roll，
保证开局没有现成三连。

**复刻 `startGame()`（153–178）**：同样的上邻/左邻重 roll；同时重置 `score/hp/hits/
scoreScale/locked`，清空补间与定时器。复刻不做对象池，直接建 25 个普通对象：

```js
G.cells[r][c] = { level: lv, x: cellX(c), y: cellY(r), scale: 1 };
```

### 5.3 方块等级与满级

| 项 | 原版 | 复刻 |
|---|---|---|
| 状态 | `map[row][col]` 整数 | `G.cells[r][c].level` |
| 显示 | `blockSpriteFrames[level]` → b1..b9 | `BLOCK[level]` → `assets/blocks/bN.png` |
| 满级 | `level === 8` 时 `console.log("到9了")`，返回 `false`，**不扣血** | `tap()` 284 行：`if (cell.level >= MAX_LEVEL) return;` 在扣血之前 |

复刻保留满级保护，但去掉了调试日志；`window.game` 仍可观察状态。

### 5.4 点击主流程（顺序敏感）

**原版 `main-canvas.touchEnd`**：

```
playHit()
→ 屏幕坐标转格子坐标，越界则 console.log("不在范围内")
→ blockAddOne(row,col)：满级返回 false；否则 level+1 并换图
→ hp -= 1；updateHpShow(hp)
→ closeTouch() 关闭触摸
→ setZeroBook()；mapForCount(...) 统计整团
→ count < 3 ?
     是 → hp <= 0 ? playOver + 1s 后 loadScene("login") : openTouch()
     否 → clearHits()；doActionForBook(row,col)
```

**复刻 `tap()`（284–305）**：

```
if (mode !== play || locked) return
playHit()
if (level >= 8) return          // 不扣血
level++；hp--；locked = true
group = flood(r,c,level)
group.length < 3 ?
   是 → hp <= 0 ? gameOver() : locked = false
   否 → hits = 0；doActionForBook(r,c,group)
```

对应关系：`closeTouch/openTouch` ↔ `locked`；`mapForCount` ↔ `flood`；
`clearHits` ↔ `G.hits = 0`。扣血发生在升级之后、判定之前，与原版一致。

### 5.5 相连统计：一个容易看错的细节

**原版 `mapForCount(row,col,level)` 不会在入口标记起点**，只标记并计数邻居，
靠递归回到起点时再把起点计入。结果是：

| 整团大小 | 原版 `count` | 复刻 `flood().length` |
|---|---|---|
| 1（孤立块） | **0** | 1 |
| 2 | 2 | 2 |
| n ≥ 2 | n | n |

因为判定条件是 `count >= 3`，两者在「是否消除」上完全等价；`n >= 3` 时计分也相同。
写复刻时直接返回「含自身的整团数组」更直观，但文档里要记住原版这个 0/1 差异，
否则会误以为原版漏算了起点。

### 5.6 计分

**原版 `updateScoreLabel(count, level)`**：

```js
scaleTo(0.1, 1.2)
→ callFunc: score += (level + 1) * count; label = score
→ scaleTo(0.1, 1)
```

**复刻 `addScore(count, level)`（195–203）**：

```js
G.scoreScale = 1;
tw(G, { scoreScale: 1.2 }, 0.1);
timer(0.1, () => {
  G.score += (level + 1) * count;
  tw(G, { scoreScale: 1 }, 0.1);
});
```

注意 `level` 是消除前点击块的等级：原版先 `updateScoreLabel` 再在回调里
`blockAddOne`，复刻也先用旧等级算分，再升级。

### 5.7 消除

**原版 `doActionForBook(row,col)`**：

1. 先计分（带缩放动画）；
2. 遍历 `book` 表，除点击格外的同团块 `scaleTo(0.15, 0)` → 回对象池 → 置空；
3. 点击格 `scaleTo(0.15,1.2)` → `blockAddOne` → `scaleTo(0.15,1)` → `blockDown`；
4. `hp += 1`；`updateHpShow`；
5. `playCombo(hits)`；`hits += 1`。

**复刻 `doActionForBook(r,c,group)`（205–234）**：

1. `addScore(group.length, level)`；
2. 同团其余块从 `G.cells` 摘除，放进 `G.dying`，`tw(scale→0, 0.15)`，结束后从
   `dying` 移除（代替对象池回收）；
3. 点击块 `tw(scale→1.2, 0.15)` → 若未满级 `level++` → `tw(scale→1, 0.15)` → `blockDown`；
4. `G.hp += 1`；`playCombo(G.hits)`；`G.hits += 1`。

差异只在「节点回收」：原版复用 `cc.Node`，复刻直接丢弃普通对象；方块图片是预加载的
`Image`，不会因消除而重新解码。

### 5.8 重力

**原版 `blockDown`**：

```js
do {
  moved = false;
  for (col) for (row 0..3)
    if (mapNode[row][col] && !mapNode[row+1][col]) {
      mapNode[row][col].runAction(cc.moveBy(0.1, 0, -130)); // 相对位移
      交换 map / mapNode 指针;
      moved = true;
    }
} while (moved);
scheduleOnce(checkNullBlock, 0.3);
```

**复刻 `blockDown()`（236–252）**：逐列从底往上压紧，每个方块只补间一次到目标格：

```js
let dst = GRID - 1;
for (let r = GRID - 1; r >= 0; r--) {
  if (!o) continue;
  if (dst !== r) { 交换指针; tw(o, { y: cellY(dst) }, 0.1); }
  dst--;
}
timer(0.3, checkNullBlock);
```

**最终布局完全一致**，动画观感略有差别：原版是相对 `moveBy`，同一方块跨多格时
会在同一帧压入多个 0.1s 动作，可能一帧走两格；复刻是单段 0.1s 直接滑到最终格。
这是有意的实现简化，不是规则差异。

### 5.9 补块

**原版 `checkNullBlock`**：遍历全盘空格，`rand(0,4)` 生成新块，位置按格心，
`scale = 0` → `scaleTo(0.1, 1)`；完成后 `scheduleOnce(checkCount, 0.3)`。

**复刻 `checkNullBlock()`（254–266）**：同样遍历全盘、随机 0..4、`scale:0` →
`tw(scale→1, 0.1)`，再 `timer(0.3, checkCount)`。

### 5.10 连锁扫描

**原版 `checkCount`**：双重循环，每次 `setZeroBook()` 后 `mapForCount`；找到
`count >= 3` 就 `doActionForBook` 并 `break`；全部扫完没有才 `openTouch()`。

**复刻 `checkCount()`（268–282）**：行优先找第一个 `flood().length >= 3`，
调用 `doActionForBook` 后直接 `return`；没有才 `G.locked = false`。

连锁期间 `locked` 一直为 `true`（由 `tap` 设置），所以玩家不能插入操作；
每一轮消除都会 `hp += 1`，这是原版的「连锁回血」奖励。复刻保留了这一点。

### 5.11 血量

**原版**：`hp = 5`；`updateHpShow(v)` 把 `v` 钳到 `0..5`，按数量设置 5 个
`shape_0 copy` 节点的 `opacity`；`hp` 本身不封顶，连锁可以超过 5。

**复刻**：`G.hp` 同样不封顶；`drawHp()`（354–363）只画
`Math.min(G.hp, MAX_HP)` 条。布局沿用场景 JSON：

| 项 | 值 |
|---|---|
| 血条尺寸 | 110 × 50 |
| 间距 | 130 |
| 中心 y | `CY - 411 = 229` |
| 颜色 | `#ff5353`（原版对 `shape_0` 染色） |

复刻用离屏 canvas：先铺 `#ff5353`，再用 `destination-in` 套 `shape_0` 的透明度形状，
等价于原版的「白块染色」。

### 5.12 分数显示

| 项 | 原版 | 复刻 |
|---|---|---|
| 位置 | `(0, 551.6)` 相对画布中心 | `(CX, CY - 551.6)` |
| 字号 | 59.62 | 60 px |
| 缩放动画 | 1 → 1.2 → 1，各 0.1s | 同 |
| 样式 | 白色字 + 深色描边 | `#fff` + 8px `#2b0a14` 描边 |

### 5.13 结束与回登录

**原版**：`playOver()` → `console.log("游戏结束")` → `scheduleOnce(loadScene("login"), 1)`。

**复刻**：`gameOver()`（307–316）把 `mode` 设为 `over`、锁定输入、播结束音，
`timer(1.0)` 后 `mode = "login"`。`render()` 在 over 时画结算层
（「游戏结束 / 得分 N / 马上返回首页」）并压暗棋盘。

场景切换 vs 状态切换的差别：原版重新加载 login 场景，节点和组件重建；复刻只是切
`mode`，下一次 `startGame()` 会重建 `cells` 并清空补间/定时器，效果等价。

### 5.14 登录页

**原版 `login-canvas`**：开始按钮无限循环
`rotateBy(0.3, +4°) → rotateBy(0.6, -8°) → rotateBy(0.3, +4°) → delay(0.5)`，
总周期 1.7s；按钮 `clickEvents` 绑定 `loadScene("main")`。

**复刻 `drawLogin()`（394–426）**：按 1.7s 周期把上述序列写成分段函数：

```js
p = loginT % 1.7
p < 0.3 → ang = 4 * p/0.3
p < 0.9 → ang = 4 - 8 * (p-0.3)/0.6
p < 1.2 → ang = -4 + 4 * (p-0.9)/0.3
```

**差异**：

- 原版只有按钮可点；复刻登录页任意位置都可开始（移动端更好点，也负责解锁音频）。
- logo / 按钮 / 文案位置是按场景与截图近似摆放的，不是逐像素还原。
- 复刻加了「点一下开始」「点方块升级…」两行说明，原版登录页没有这段文案。

### 5.15 音频

| 项 | 原版 | 复刻 |
|---|---|---|
| 音乐 | `login-music` 播放 `bgm_dnf.mp3`，loop，音量 0.2；main 场景无 BGM，跨场景继续 | 单个 `Audio`，loop，音量 0.2，首次交互解锁 |
| 点击 / 结束 | `playEffect(hit/over)`，音量 0.4 | 同，音量 0.4 |
| 连击 | `combo[0..5]`，`n < 0` 不播，`n > 5` 截断 | `playCombo` 同样截断 |
| 播放策略 | Cocos `audioEngine` | `currentTime = 0` 后 `play()`，失败静默 |

浏览器的自动播放限制由 `unlockAudio()` 处理：第一次 `pointerdown` 或登录页按键时
尝试播放 BGM。原版没有这个问题（Cocos 在用户点击后初始化音频）。

### 5.16 背景与装饰

**原版主场景**有两块 `shape_1` 斜纹装饰，染色 `#ff9494`，做缩放/旋转/镜像；
复刻 `drawDecor()`（381–392）用同一张图，去掉染色、`globalAlpha = 0.07`，
左右各一块镜像。属于观感近似，不是精确还原。

背景渐变、棋盘外框位置（700×700，居中）来自场景 JSON。

### 5.17 引擎与主循环

| 项 | 原版 | 复刻 |
|---|---|---|
| 驱动 | Cocos 主循环 + 组件调度器 | `requestAnimationFrame` + 16ms `setInterval` 双驱动 |
| 计时 | `scheduleOnce` / `runAction` | `timer()` / `tw()`，共享 `last` 按真实时间推进 |
| 帧间隔 | 引擎内部 | `dt > 0.5s` 截断，避免切后台回来跳帧 |
| 适配 | Cocos 设计分辨率策略 | `fit()` 等比 contain，按 DPR 设置后备分辨率 |

双驱动共用同一个 `last`，两路各自只消耗「距上次调用的时间」，所以不会让游戏变快；
好处是无头/后台标签页里 `rAF` 被节流时，`setInterval` 仍能推进逻辑。

### 5.18 调试接口

原版 `main-canvas.start` 里就有 `window.game = this`。复刻保留同名入口，并额外暴露：

```js
window.game = G;
window.__game = { G, startGame, tap, flood, blockDown };
```

自动化验证就是通过这两个对象读取 `cells/hp/score/locked/mode`，并直接调用 `tap()`
构造边界局面。
---

## 六、关键数值表

| 参数 | 值 | 原版出处 | 复刻位置 |
|---|---|---|---|
| 设计分辨率 | 720 × 1280 | `Canvas._contentSize` | `index.html:31` |
| 棋盘 | 5 × 5 | `map[5][5]` | `GRID` / `cells` |
| 格宽 | 130 px | `130*t-260` | `CELL` |
| 方块等级 | 0 ~ 8（b1..b9） | `blockAddOne` 封顶 | `MAX_LEVEL` |
| 新块等级 | 0 ~ 4 | `randNum(0,4)` | `rand(0,4)` |
| 初始血量 | 5 | `this.hp = 5` | `MAX_HP` |
| 消除阈值 | 整团 ≥ 3 | `count >= 3` | `group.length >= 3` |
| 未消除扣血 | 1 / 次 | `this.hp -= 1` | `G.hp--` |
| 消除回血 | 1 / 次（含连锁） | `mainCanvas.hp += 1` | `G.hp += 1` |
| 得分 | `(level+1) × 整团数` | `updateScoreLabel` | `addScore` |
| 对象池 | 30 | `cc.NodePool` | 无（普通对象） |
| 重力步长 | 每格 130 px / 0.1s | `moveBy(0.1,0,-130)` | 单段 0.1s 到目标格 |
| 补块/扫描延迟 | 0.3 s | `scheduleOnce` | `timer(0.3, ...)` |
| 结束回登录 | 1 s | `scheduleOnce(...,1)` | `timer(1.0, ...)` |
| 音乐音量 | 0.2 | `setMusicVolume` | `bgm.volume` |
| 音效音量 | 0.4 | `setEffectsVolume` | `sfx.*.volume` |

---

## 七、两处初版复刻缺陷（不是原版缺陷）

上一轮对 `out\web-mobile\game\index.html` 的初版脚手架做审计时，发现两个会导致
「逻辑与画面错位」的问题。它们出在**复刻脚手架的坐标/补间实现**里，原版 Cocos 代码
本身没有这两个问题——这一点在当逆向案例写文档时必须分清。

### 7.1 点击行坐标上下翻转

初版复刻用：

```js
row = Math.floor((CY - y + HALF) / CELL);   // 等价于 (965 - y)/130
```

而正确的画布映射是：

```js
row = Math.floor((y - BOARD_T) / CELL);      // BOARD_T = 315
```

错误公式把 y 轴方向弄反，点顶行会命中底行。实测：点击画布 `(100,380)`
（顶行左列）后，变化的是 `cells[4][2]` 而不是 `cells[0][0]`。

原版公式 `row = floor((325 - nodeY) / 130)` 是在「y 向上」的棋盘节点坐标里写的，
本身正确；初版复刻把它直接翻译到「y 向下」的画布坐标时没有翻转。

**修正后验证**：点击 `(100,380)` 命中 `cells[0][0]`，等级 0→1，血量 5→4。

### 7.2 重力多段补间互相覆盖

初版复刻的 `blockDown` 在 `while` 循环里对同一个方块反复调用：

```js
tw(o, { y: cellY(newRow) });   // from 在创建补间时取旧值
```

多个 0.1s 补间同时写同一个 `y`，最终值被最后一次覆盖，方块可能停在两格之间。
实测某方块数据已在 `row 4`，`y` 却停在 510，而正确格心是 `cellY(4)=900`。

原版用 `cc.moveBy(0.1, 0, -130)`（相对位移），不存在「绝对目标互相覆盖」的问题；
它只是可能在同一帧压入多个相对动作，视觉上偏快，但最终位置正确。

**修正后实现**：逐列从底向上压紧，每个方块只补间一次到最终格心。
实测强制单块在 col 0 下落后，最终 `y = 900 = cellY(4)`。

---

## 八、验证记录

复刻完成后用 Headless Chrome + CDP 驱动，`.serve.cjs` 提供静态服务，
通过 `window.__game` 读写状态、构造局面并截图。

| 用例 | 结果 |
|---|---|
| 资源加载 | 14/14，无 404 |
| 初始状态 | mode=login，25 格，hp=5，score=0 |
| 点击映射 | `(100,380)` → `cells[0][0]` 0→1，hp 5→4 |
| 重力 | 强制单块 col0 → 最终 `y=900`，数据/视觉一致 |
| 3 连消除 | 点击块 3→4，hp 净回满，分数先 0 后按 `(level+1)*count` 增加并触发连锁 |
| 满级保护 | lv8 点击后 hp 不变、level 仍 8、不锁输入 |
| 棋盘外点击 | `(20,20)` 无任何状态变化 |
| 两连 | 只扣 1 血、不消除、不得分 |
| 预置 3 连 + `checkCount` | 自动消除并继续补块/连锁 |
| 游戏结束 | hp=1 点无效块 → over → 1.2s 后 login |
| 随机压测 | 18s / 11 局 / 56 次点击：invalid=0、非法等级/坐标/缩放=0、无 JS 异常 |
| 连锁收敛 | 停止操作后轮询，局面能结束并回到 login，无卡死 |

压测里还观察到一个符合原版设计的现象：连锁补块如果又凑出 3 连，会继续自动消除，
分数和血量都会上涨，所以单次点击的最终得分可能高于首消公式值。
---

## 九、证据索引

| 结论 | 文件 | 定位方式 |
|---|---|---|
| 游戏标题、竖屏、首场景 | `index.html`、`src/settings.0f08a.js` | 全文 |
| 全部游戏逻辑 | `assets/main/index.18f60.js` | 模块名 `login-canvas` / `login-music` / `main-blockManager` / `main-canvas` / `main-music` |
| 棋盘与坐标 | 同上 | `main-blockManager.gameStart` / `createBlock` |
| 触摸换算 | 同上 | `main-canvas.touchEnd`：`(325 - nodeY)/130`、`(325 + nodeX)/130` |
| 扣血 / 满级 | 同上 | `blockAddOne` / `touchEnd` |
| 泛洪计数 | 同上 | `mapForCount`（起点不先标记） |
| 计分 | 同上 | `updateScoreLabel` |
| 消除 / 重力 / 补块 / 连锁 | 同上 | `doActionForBook` / `blockDown` / `checkNullBlock` / `checkCount` |
| 血量 / 分数布局 | `assets/main/import/05/...json` | `hpManager` / `shape_0 copy` / `score` 节点 |
| 9 级方块图 | `assets/main/import/05/...json` | 字符串表 b1..b9 |
| 无存档、无联网 | `assets/main/index.18f60.js` | 全文搜 `localStorage` / `fetch` / `WebSocket` 均为 0 |
| 音频 / 图片实体 | `assets/main/native/` | 9 个 mp3、14 个 png |
| 复刻实现 | `out\web-mobile\game\index.html` | 见第四节行号表 |

---

## 十、版权与复用边界

| 证据 | 判断 |
|---|---|
| BGM 文件名 `bgm_dnf.mp3` | 疑似《地下城与勇士》素材，版权风险明确 |
| 方块图 `b1..b9`、`shape_0/1`、`kuang`、`logo` | 来源不明，发布前必须替换或取得授权 |
| 玩法与数值 | 规则本身不受版权保护，可自由重写 |

**逻辑可以复刻，素材不要直接商用。** 本案例的复刻仅用于本地验证与学习；
要发布就换一套自己的美术和音乐。

---

## 十一、如果再来一次：最短路径

1. 读 `index.html` 与 `settings`，确认首场景；
2. 在 bundle 里按 `__require("模块名"` 定位模块表，列 5 个组件；
3. 从场景 JSON 抄布局（棋盘 700×700、格宽 130、血条 110×50 / 间距 130、分数 y）；
4. 先写纯逻辑：`cells` 二维数组 + `flood` + 消除/重力/补块/连锁；
5. 再写渲染与输入：画布坐标映射、DPR 适配、点击/触摸；
6. 用调试钩子构造边界局面（满级、两连、3 连、空棋盘）做自动化验证；
7. 最后核对数值表与音效音量，补 README。

对这类未混淆的 Cocos 2.x 小游戏，**手工读 7 KB 脚本比跑大型分析工具更快**；
REA 更适合大 bundle、Electron `asar`，或需要「无联网/无存档」这类可仲裁的否定性证据。
工具与手工的实测对照见同目录 `rea-vs-manual.md`。