# web-mobile 逆向报告

目标：`targets\web-mobile`（Cocos Creator 2.x `web-mobile` 构建产物）
分析方式：静态阅读，未运行、未联网、未安装任何工具
产出日期：2026-11-14

---

## 一、结论先行

| 问题 | 答案 |
|---|---|
| 是什么游戏 | 「Blocks」——5×5 网格、点击升级方块、凑够 3 个相连同色即消除的休闲益智 |
| 代码规模 | **5 个脚本，约 600 行**，未混淆，变量名可读 |
| 逻辑能否 100% 还原 | **能**。全部规则、数值、阈值都在 `assets/main/index.18f60.js` 里，一个文件看完 |
| 资源能否复用 | **能**。9 张方块图 + 14 张 png + 9 段 mp3，直接躺在 `assets/main/native/`，未加密未打包 |
| 能否复刻 | 技术上完全可行；**但音乐文件名 `bgm_dnf.mp3` 指向商业游戏素材，有版权风险** |
| 工作量估计 | 逻辑重写 1–2 天；换成自己的美术 1–2 天 |

---

## 二、文件结构

```
targets\web-mobile\
├─ index.html                    启动页，标题 "Cocos Creator | Blocks"
├─ cocos2d-js-min.8ded5.js       Cocos 引擎本体 1.8 MB（非本项目代码）
├─ main.fb3d8.js                 引擎启动器 4.9 KB
├─ src\settings.0f08a.js         项目配置：竖屏、首场景 db://assets/login.fire
└─ assets\
   ├─ internal\                  Cocos 内置资源
   └─ main\                      游戏自己的 bundle
      ├─ index.18f60.js          ★ 全部游戏逻辑，7.2 KB
      ├─ config.18f60.json       资源清单（uuid → 类型）
      ├─ import\05\...json       场景 main.fire
      ├─ import\0e\...json       场景 login.fire
      ├─ import\02\...json       Texture2D 描述
      └─ native\                 实际图片 / 音频文件（png / mp3）
```

关键点：`assets/main/index.18f60.js` 是 **Cocos 2.x 的 `__require` 模块包**，虽然压成一行，
但类名、方法名、属性名全是原始命名（`main-blockManager`、`mapForCount`、`doActionForBook`…），
**没有混淆**。这是 Cocos 2.x 发布包的常态，也是这次能完整还原的直接原因。

---

## 三、玩法规则（从代码还原）

### 3.1 棋盘

```
5 行 × 5 列，每格 130 px
格子中心坐标：x = 130*col - 260 (col 0..4)
              y = 260 - 130*row (row 0..4)   → row 0 在最上面
```

### 3.2 方块状态

每个格子存一个整数 `level`：

| 值 | 含义 |
|---|---|
| `null` | 空格（只在动画中间态出现） |
| `0` ~ `8` | 方块等级，对应图片 `b1` ~ `b9` |

- 新生成的方块：`level` 随机取 `0..4`（5 种起始颜色）
- 点击升级：`level + 1`，到 `8` 封顶（再点无效，只打一条日志「到9了」）

### 3.3 核心循环

玩家点一下格子 → 该格 `level+1` → 检查它与四周相连的同级方块：

```
            ┌─ 相连数量 >= 3 ─→ 消除（保留点击的那个，它再升一级）
   点击 ───┤                     得分 += (level+1) × 相连数量
            │                     回血 +1
            │                     连击计数 +1，播连击音效
            │
            └─ 相连数量 <  3 ─→ 掉血 -1
                                  血量 <= 0 且未消除 → 1 秒后回登录页
```

**所以：这是一款「点错扣血、点对回血」的消除游戏。** 共 5 点血，血扣光就结束。

### 3.4 消除后的连锁

```
消除 → 上方方块下落填补（逐格下移 130 px，循环到稳定）
     → 顶部空位补新方块（随机 0..4，缩放 0→1 弹入）
     → 延迟 0.3 s 再扫一遍全盘
        → 若又出现 >=3 相连：自动再消除一次，得分 +1 血（连锁奖励）
        → 一直扫到没有可消除的组，才把触摸重新打开
```

连锁期间玩家不能操作，这是刻意的防连点设计。

### 3.5 得分公式

```js
score += (level + 1) * clusterSize
// level 为消除时点击块的等级索引（0..8），clusterSize 为相连方块数
// 例：等级 4 的方块凑出 5 连 → +25 分
```

### 3.6 没有的东西

| 检查项 | 结果 |
|---|---|
| 本地存档 | ❌ 无 `localStorage` / `sessionStorage`，关掉就清零 |
| 网络请求 | ❌ 无 `fetch` / `XMLHttpRequest` / `WebSocket` |
| 排行榜 / 广告 / 内购 | ❌ 无 |
| 物理引擎 | ❌ 无 |
| 关卡 / 难度递增 | ❌ 没有。「难度」完全由 5 点血与随机补块自然产生 |

---

## 四、伪代码（按模块还原）

### 4.1 `login-canvas` —— 启动页

```js
class LoginCanvas extends cc.Component {
  startButton;                       // 开始按钮节点

  start() {
    // 按钮呼吸式摇摆：右转 4° → 左转 8° → 右转 4° → 停 0.5 s，无限循环
    startButton.runAction(cc.repeatForever(cc.sequence(
      cc.rotateBy(0.3,  4),
      cc.rotateBy(0.6, -8),
      cc.rotateBy(0.3,  4),
      cc.delayTime(0.5)
    )));
  }

  toMainScene() { cc.director.loadScene('main'); }   // 按钮 clickEvents 绑定
}
```

### 4.2 `login-music` —— 背景音乐

```js
class LoginMusic extends cc.Component {
  bgm;                               // AudioClip: bgm_dnf.mp3

  onLoad() { cc.audioEngine.setMusicVolume(0.2); }
  start()  {
    if (!cc.audioEngine.isMusicPlaying())
      cc.audioEngine.playMusic(this.bgm, /* loop */ true);
  }
}
// 注意：main 场景没有 bgm，音乐跨场景持续播放
```

### 4.3 `main-blockManager` —— 棋盘核心（约 100 行）

```js
class BlockManager extends cc.Component {
  blockPrefab;            // 单个方块的预制体
  blockSpriteFrames;      // 9 个 SpriteFrame：b1..b9
  mainCanvas;             // 反向引用 Canvas（回血、开触摸）
  musicRoot;              // 音效组件

  // ---------- 初始化 ----------
  onLoad() {
    this.map     = 5x5 null;      // 等级表
    this.mapNode = 5x5 null;      // 节点表
    this.book    = 5x5 0;         // 泛洪标记表
    this.count   = 0;             // 相连计数
    this.hits    = 0;             // 连击数
    this.pool    = new cc.NodePool();
    for (i = 0; i < 30; i++) pool.put(instantiate(blockPrefab));   // 预建 30 个
  }

  start() { this.gameStart(); }

  // ---------- 开局铺盘 ----------
  gameStart() {
    for (row 0..4) for (col 0..4) {
      x = 130*col - 260;
      y = 260 - 130*row;
      level = rand(0, 4);
      // 重roll，直到与上邻、左邻都不同 → 保证开局没有三连
      while (map[row-1][col] === level || map[row][col-1] === level)
        level = rand(0, 4);
      map[row][col]     = level;
      mapNode[row][col] = createBlock(x, y, level);
    }
  }

  createBlock(x, y, level) {
    node = pool.size() > 0 ? pool.get() : instantiate(blockPrefab);
    node.parent = this.node;
    node.setPosition(x, y);
    node.getComponent(cc.Sprite).spriteFrame = blockSpriteFrames[level];
    return node;
  }

  // ---------- 点一下：升级 ----------
  blockAddOne(row, col) {
    if (map[row][col] === 8) { console.log('到9了'); return false; }   // 封顶
    map[row][col] += 1;
    mapNode[row][col].getComponent(cc.Sprite).spriteFrame
      = blockSpriteFrames[ map[row][col] ];
    return true;
  }

  // ---------- 泛洪：统计相连同级 ----------
  mapForCount(row, col, level) {
    for (dir of [[-1,0],[0,1],[1,0],[0,-1]]) {
      r = row+dir[0]; c = col+dir[1];
      if (out of 5x5) continue;
      if (map[r][c] === level && book[r][c] === 0) {
        book[r][c] = 1;
        count++;
        mapForCount(r, c, level);
      }
    }
  }

  // ---------- 消除 ----------
  doActionForBook(row, col) {
    mainCanvas.updateScoreLabel(count, map[row][col]);   // 计分（见 3.5）

    // 除点击格外的所有标记格：缩放到 0 → 回收进对象池 → 置空
    for (r) for (c) {
      if ((r,c) === (row,col)) continue;
      if (book[r][c] === 1)
        mapNode[r][c].runAction(sequence(
          scaleTo(0.15, 0),
          callFunc(() => { pool.put(mapNode[r][c]); map[r][c] = null; mapNode[r][c] = null; })
        ));
    }

    // 点击格：放大 1.2 → 升级 → 缩回 1 → 触发下落
    mapNode[row][col].runAction(sequence(
      scaleTo(0.15, 1.2),
      callFunc(() => blockAddOne(row, col)),
      scaleTo(0.15, 1),
      callFunc(() => blockDown())
    ));

    mainCanvas.hp += 1;                       // 回血
    mainCanvas.updateHpShow(mainCanvas.hp);
    musicRoot.playCombo(this.hits);           // 连击音效（0..5 递减？见 4.5）
    this.hits += 1;
  }

  // ---------- 重力 ----------
  blockDown() {
    do {
      moved = false;
      for (col) for (row 0..3)
        if (mapNode[row][col] && !mapNode[row+1][col]) {
          mapNode[row][col].runAction(moveBy(0.1, 0, -130));
          mapNode[row+1][col] = mapNode[row][col];  map[row+1][col] = map[row][col];
          mapNode[row][col]   = null;               map[row][col]   = null;
          moved = true;
        }
    } while (moved);

    scheduleOnce(checkNullBlock, 0.3);
  }

  // ---------- 补块 ----------
  checkNullBlock() {
    for (row) for (col) if (!mapNode[row][col]) {
      level = rand(0, 4);                       // 新块只出 0..4 级
      node  = createBlock(130*col-260, 260-130*row, level);
      node.scale = 0;
      node.runAction(scaleTo(0.1, 1));
    }
    scheduleOnce(checkCount, 0.3);
  }

  // ---------- 连锁扫描 ----------
  checkCount() {
    found = false;
    for (row 0..4) for (col 0..4) {
      setZeroBook();                            // book 全清，count = 0
      mapForCount(row, col, map[row][col]);
      if (count >= 3) { doActionForBook(row, col); found = true; break; }
    }
    if (!found) mainCanvas.openTouch();          // 没有可消除的，交还操作权
  }

  randNum(min, max) { return Math.floor(min + (max - min + 1) * Math.random()); }
}
```

### 4.4 `main-canvas` —— 输入、血量、分数

```js
class MainCanvas extends cc.Component {
  hp = 5;
  score = 0;
  hpManager;         // 5 颗心的父节点
  showScoreLabel;    // 分数 Label
  blockManager;
  musicRoot;

  start() { window.game = this; openTouch(); updateHpShow(hp); }

  touchEnd(event) {
    musicRoot.playHit();

    // 屏幕坐标 → 格子坐标
    // 325 = 棋盘半边长（5 × 130 / 2），不是画布半宽
    p  = convertToNodeSpaceAR(event.getLocation());
    row = Math.floor((325 - p.y) / 130);
    col = Math.floor((325 + p.x) / 130);
    if (row/col 越界) return;

    if (!blockManager.blockAddOne(row, col)) return;   // 已满级，不扣血

    hp -= 1;  updateHpShow(hp);  closeTouch();          // 锁触摸，防连点

    level = blockManager.map[row][col];
    blockManager.setZeroBook();
    blockManager.mapForCount(row, col, level);

    if (blockManager.count < 3) {
      // 没凑成组：白扣一血
      if (hp <= 0) {
        musicRoot.playOver();
        scheduleOnce(() => cc.director.loadScene('login'), 1);   // 1 秒后回登录
      } else {
        openTouch();
      }
    } else {
      blockManager.clearHits();                         // 连击数归零
      blockManager.doActionForBook(row, col);           // 进入消除 + 连锁流程
    }
  }

  updateHpShow(v) {           // 只影响显示，hp 变量本身可超 5
    v = clamp(v, 0, 5);
    hpManager.children[0..4].opacity = 0;
    for (i < v) hpManager.children[i].opacity = 255;
  }

  updateScoreLabel(count, level) {
    showScoreLabel.node.runAction(sequence(
      scaleTo(0.1, 1.2),
      callFunc(() => { score += (level + 1) * count; showScoreLabel.string = score; }),
      scaleTo(0.1, 1)
    ));
  }
}
```

### 4.5 `main-music` —— 音效

```js
class MainMusic extends cc.Component {
  hit;     // 点击音
  over;    // 游戏结束音
  combo;   // AudioClip[6]：Combo1..Combo6

  onLoad() { cc.audioEngine.setEffectsVolume(0.4); }

  playHit()      { cc.audioEngine.playEffect(hit,  false); }
  playOver()     { cc.audioEngine.playEffect(over, false); }
  playCombo(n)   { if (n < 0) return; n = min(n, 5);
                   cc.audioEngine.playEffect(combo[n], false); }
}
```

---

## 五、关键数值表

| 参数 | 值 | 出处 |
|---|---|---|
| 棋盘 | 5 × 5 | `map[5][5]` |
| 格宽 | 130 px | `130*t-260` |
| 方块等级范围 | 0 ~ 8（显示 b1..b9） | `blockAddOne` 封顶判断 |
| 新块等级范围 | 0 ~ 4 | `randNum(0,4)` |
| 初始血量 | 5 | `this.hp = 5` |
| 消除阈值 | 相连 ≥ 3（不含自己则 ≥ 3，含自己共 ≥ 4） | `count >= 3` |
| 消散扣血 | 1 / 次 | `this.hp -= 1` |
| 消除回血 | 1 / 次（含连锁每次） | `this.mainCanvas.hp += 1` |
| 得分 | `(level+1) × clusterSize` | `updateScoreLabel` |
| 对象池容量 | 30 | `pool.put` 循环 |
| 补块/扫描延迟 | 0.3 s | `scheduleOnce` |
| 结束回登录延迟 | 1 s | `scheduleOnce` |
| 音效音量 | 0.4 | `setEffectsVolume` |
| 音乐音量 | 0.2 | `setMusicVolume` |

> **注意一处代码上的模糊**：`mapForCount` 不会在入口处标记自己，而是在递归回到自己时才标记，
> 所以 `count` 最终等于整团方块数，但计数时机依赖遍历顺序。效果上无误，写文档时可直接按「整团数量」理解。

---

## 六、能不能复刻

### 能，而且这是最省事的一类

| 维度 | 情况 | 复刻难度 |
|---|---|---|
| 逻辑 | 5 个组件、约 600 行，无加密、无混淆、无网络 | ★☆☆☆☆ |
| 素材 | png / mp3 明文存放，可直接取用或替换 | ★☆☆☆☆ |
| 场景 | 两个场景，节点数少，靠人工重建即可 | ★★☆☆☆ |
| 手感 | 全部动画参数都在代码里（0.15 s、1.2 倍缩放、0.3 s 延迟） | ★★☆☆☆ |

### 用别的技术栈复现，成本更低

原版是 Cocos Creator 2.x（2018 年的技术栈）。如果用现代方案重写：

| 方案 | 说明 |
|---|---|
| Phaser 3/4 + TypeScript | 你已有的 `mech_ruins` 就是这套，棋子/网格游戏很轻 |
| 纯 Canvas + 无引擎 | 这游戏没有物理、没有复杂动画，200 行足够 |
| Cocos Creator 3.x | 想保持原滋味就用它，但 2.x → 3.x 的 API 迁移反而麻烦 |

### 必须先说的一件事：版权

| 证据 | 判断 |
|---|---|
| BGM 文件名 `bgm_dnf.mp3` | 疑似《地下城与勇士》素材 |
| 方块贴图 `b1..b9`、`shape_0/1`、`kuang` | 来源不明，需你确认是否有授权 |
| `splash.85cfd.png`、`logo` | 同上 |

**逻辑可以自由重写，素材不能直接照搬。** 如果只是学习或自用没问题；
要发布就得换一套自己的美术和音乐 —— 但这反而是好事，说明游戏本身值得做。

### 复刻建议路线

```
1. 先按本文档的规则表写一个纯逻辑原型（命令行或纯色方块），验证手感
2. 把「点错扣血 / 点对回血 / 连锁加血」这三个规则调到自己满意
3. 再决定要不要用 Phaser 包装画面
4. 素材全部自行绘制或购买授权
```

第 2 步是关键 —— **这个游戏的全部乐趣在血量经济**，不在画面上。

---

## 七、证据索引

| 结论 | 文件 | 定位方式 |
|---|---|---|
| 游戏标题、竖屏、首场景 | `index.html`、`src/settings.0f08a.js` | 全文 |
| 全部游戏逻辑 | `assets/main/index.18f60.js` | 模块名 `login-canvas` / `login-music` / `main-blockManager` / `main-canvas` / `main-music` |
| 5×5 棋盘与 130 px 格宽 | 同上 | `main-blockManager.gameStart` / `createBlock` |
| 血量、得分、触摸判定 | 同上 | `main-canvas.touchEnd` / `updateHpShow` / `updateScoreLabel` |
| 消除与重力 | 同上 | `doActionForBook` / `blockDown` / `checkNullBlock` / `checkCount` |
| 方块 9 级（b1..b9） | `assets/main/import/05/05bd34bd4.00bbc.json` | 字符串表 |
| 场景节点结构 | 同上的 `login` / `main` 场景段 | `mainCanvas` / `hpManager` / `blockManager` / `musicRoot` / `blockPrefab` |
| 无存档、无联网 | `assets/main/index.18f60.js` | 全文 grep `localStorage` / `fetch` / `WebSocket` 均为 0 |
| 音频 / 图片实体 | `assets/main/native/` | 9 个 mp3、14 个 png |

---

## 八、资源提取结果

**全部资源都已提取**，见 `out\web-mobile\assets-recovered\`（23 个文件，1.94 MB）。

| 类别 | 数量 | 情况 |
|---|---|---|
| 方块 1~9 级 | 9 | 120×120 PNG，**图上直接印着数字** |
| UI | 5 | logo、开始按钮、外框、白块、斜纹装饰 |
| 音频 | 9 | bgm / 点击 / 结束 / 连击 1~6，MP3 原始字节 |

关键点：**没有图集**。所有 SpriteFrame 的 `rect` 都是 `[0,0,w,h]`、`offset [0,0]`，
即一张图一个文件，不存在需要按 rect 切图的情况，所以提取是无损的。
唯一的损失是原始文件名被换成了 uuid 前缀。

明细和命名依据见 `out\web-mobile\assets-recovered\README.md`。

### 画布与布局参数（这次一并还原）

| 项 | 值 | 出处 |
|---|---|---|
| 设计分辨率 | 720 × 1280（竖屏） | `Canvas` 节点 `_contentSize` |
| 棋盘外框 | 700 × 700 | `kuang` 节点 |
| 棋盘 | 650 × 650（5 × 130） | 格宽 × 5 |
| 血量心 | 5 个 110 × 50 节点，间距 130，y = 0 | 5 个 `shape_0 copy` |
| 血量条容器 | 640 × 60，位于 (0, 411) | `hpManager` |
| 分数标签 | 位于 (0, 551.6)，字号 59.62 | `score` 节点 |

## 九、REA 工具在同一次分析里的表现（附）

同一目标也跑了一遍 `pnpm exec rea analyze-javascript-application`，用于对照工具能力。

| 项 | 结果 |
|---|---|
| 产出体积 | **48.8 MB** JSON（目标本身 3.8 MB） |
| 收录文件 | 12 个（5 个 JS 全部解析成功，0 解析失败） |
| AST 节点 | 592,462 |
| 应用图节点 | 307，其中 **287 个是未解析的 `require(...)`** |
| 引擎噪声占比 | 276 / 307 个节点来自 `cocos2d-js-min.8ded5.js` |
| 识别出的模块数 | **0**（Cocos 2.x 的 `__require` 模块表未被当作模块系统） |
| Electron / IPC / 网络 | 全部 0，与手工 grep 一致 |
| 语义图 | 22,069 节点 / 8,868 关系 |

### 它做对的部分

- 抓到了全部中文日志字符串：`到9了`、`游戏结束`、`不在范围内`
- 抓到了属性级读写：`read:/mainCanvas/hp`、`write:/hp`、`write:/score`、
  `read:/doActionForBook`、`read:/mapForCount`、`read:/blockManager/blockAddOne`
- 正确报告「无 localStorage / 无网络」这类**否定性结论**

### 它没做到的部分

- 没认出 `"main-blockManager": [function..., {...}]` 这种模块表，`statistics.modules = 0`
- 因此无法给出「模块 → 依赖 → 导出」的结构，也没法直接回答「玩法是什么」
- 48.8 MB 里绝大部分是压缩引擎的噪声

### 结论

对这个目标，**直接读 7.2 KB 的脚本包比读 48.8 MB 的 Evidence 更快更准**。
REA 的价值在于：目标大到读不完（如 1.7 MB 压缩包）、或需要「有没有联网/存档」这类
可仲裁的否定性证据时。选型判断见 `notes/rea-vs-manual.md`。
