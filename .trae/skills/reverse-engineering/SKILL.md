---
name: "reverse-engineering"
description: "FreeStyle 游戏逆向分析助手。当用户需要分析二进制文件格式、定位函数地址、理解类继承关系、RTTI分析、vtable映射时调用此技能。"
auto_load: true
---

# FreeStyle 逆向分析助手

## 项目背景

逆向分析 FreeStyle.exe（街头篮球游戏客户端），目标是实现动态发型（物理摆动效果）。

## 已知关键地址

| 符号 | 地址 | 说明 |
|------|:----:|------|
| DStaticActor vtable | `0x0284E114` | 静态发型虚函数表 |
| DDynamicActor vtable | `0x0284AA4C` | 动态发型虚函数表 |
| DStaticActor ctor | `0x0236B8A0` | 构造函数入口 |
| DDynamicActor ctor | `0x0229B0B0` | 构造函数入口 |
| DynamicInit | `0x0229B4D0` | 动态物理初始化函数 |
| SetMotionType | `0x02297810` | 设置运动类型函数 |
| CharacterMotion parse | `0x021B46E0` | .bml 文件解析 |
| PATCH_SITE | `0x0236B998` | 构造函数中设置 vtable 处 |
| 工厂函数 | `0x021C1F00` | 根据 vtable 创建运动对象 |
| SSKF 加载器 | `0x22ECCD0` | SMD 文件加载函数 |
| DynamicPhysicsInit | `0x0229C2D0` | 物理初始化 |

### RTTI 类名

| 类名 | RTTI 地址 | vtable 地址 |
|------|-----------|-------------|
| `.?AVDDynamicActor@@` | 0x29EB78C | 0x284AA4C |
| `.?AVDStaticActor@@` | 0x2A147A0 | 0x284E114 |
| `.?AVDActor@@` | 0x29EB7AC | - |
| `.?AVCCharacter@@` | 0x29EB824 | - |

### 字段偏移

| 偏移 | 含义 | DDynamicActor 典型值 |
|:---:|------|:-------------------:|
| +0x00 | vtable 指针 | `0x0284AA4C` |
| +0x74 | flags 标志位 | `0xA3` (bit 0,1,5,7) |
| +0xC0 | 运动类型 FName 索引 | `0x0B` (Dynamic) |
| +0x460 | 物理参数1 (float) | 非零 |
| +0x464 | 物理参数2 (float) | - |
| +0x46C | vtable[0xA0] 参数 | - |

### FName 运动类型

| 名称 | 全局对象地址 | 索引值 |
|------|-------------|--------|
| "Base" | 0x2A783F8 | 10 (0x0A) |
| "Dynamic" | 0x2A78410 | 11 (0x0B) |
| "Static" | 0x2A783F4 | 12 (0x0C) |

## 类继承关系

```
CCharacter → CDummyCharacter → CDSkeleton → ... → DActor → {DDynamicActor, DStaticActor}
```

DDynamicActor 和 DStaticActor 是**不同的 C++ 类**，不是同一类的不同状态。

## 关键源码文件

| 文件 | 路径 | 作用 |
|------|------|------|
| Character.cpp | GameEx/ | LoadItemFile、RefreshItem、UnloadItem |
| DGraphicObj.cpp | Scud/Graphic/ | AcquireSMD（SSKF 加载）|
| DGrpActor.cpp | Scud/Graphic/ | AttachSMD、DetachSMD（骨骼挂载）|
| DSkin.cpp | Scud/Physics/ | SSKF 格式序列化 |

## 工作流程

### 新的逆向分析任务

1. **明确目标**：要找什么函数/数据结构/地址？
2. **搜索锚点**：用已知字符串地址（上表）做锚点
3. **交叉引用**：在代码段搜索 `push <地址>` 指令定位引用点
4. **反汇编分析**：从引用点回溯函数体
5. **记录发现**：更新本文件和 `debug_log.md`

### 地址搜索方法

```
1. 已知字符串地址 → 搜索 push <addr> 指令 → 定位引用函数
2. 已知函数地址 → 反汇编 → 分析调用链
3. 已知 vtable → 读 vtable 条目 → 定位虚函数
4. RTTI 类型描述符 → 定位 vtable → 定位构造函数
```

## 道具对照表

| 名称 | ItemCode | Item Pak | Res Pak | 类型 |
|------|----------|----------|---------|------|
| 可爱加倍发型 | 50125001 | item764 | res764 | 静态 |
| 破坏者超赛发型 | 50125031 | item764 | res764 | 动态 |
| 美丽梦想发型 | 25461 | item767 | res767 | 静态 |

## 相关文档

- `FreeStyle/debug_log.md` — 完整调试日志
- `docs/07_动态发型功能/调试总结.md` — 调试总结
- `FreeStyle/工作总结.md` — 工作总结
- `FreeStyle/开发文档.md` — 开发文档
- `FreeStyle/lib/game-re-framework/METHODOLOGY.md` — 游戏逆向方法论（参考）

---
## 逆向方法论（来自 game-re-framework 集成）

> 来源: [lbh666/game-re-framework](https://github.com/lbh666/game-re-framework) — 只狼/真三国无双实战提炼
> 本地路径: `FreeStyle/lib/game-re-framework/METHODOLOGY.md`

### 核心原则

| # | 原则 | 在本项目的应用 |
|---|------|--------------|
| 1 | **横向优先于纵向** | 排除一个函数后先看同层兄弟函数，别继续深入或往上游追 |
| 2 | **先枚举再深入** | 进入函数分析前，先列出同层所有调用并标注角色，全部标注完才能选深入方向 |
| 3 | **分析一步，验证一步** | 每个推断必须调试验证，不允许连续猜测多步 |
| 4 | **双路并行** | 自顶向下（调用链追踪）和自底向上（特征指令搜索）同时进行 |
| 5 | **两次排除即跳出** | 同一函数排除了 2 个候选 → 必须跳出，横向检查同层其他函数 |
| 6 | **"不触发"是最强线索** | 断点在某场景下不触发 → 追问"走了哪条路径"，不继续在当前路径深挖 |
| 7 | **写补丁前纸面验证完整性** | 不要边写边修 |

### Phase 1.5: 特征指令预扫描（关键方法）

这是我们在 SSKF 扫描失败后学到的：**不要扫数据字节，要扫引用数据的指令。**

| 目标行为 | 搜索模式 | 适用于 FreeStyle |
|---------|---------|-----------------|
| SSKF 魔数比较 | 扫描引用 SSKF 数据地址 `+0x244b9c4` 的指令 | `68 C4 B9 84 02`（push offset） `81 3D ?? ?? ?? C4 B9 84 02`（cmp）|
| 时机判定 | COMISS / UCOMISS | 格挡/技能时间窗口判断 |
| 随机判定 | IMUL + 常数 → SHR → MOD | 抽奖/暴击 |
| 距离判定 | sqrt + COMISS | 攻击范围 |
| 角度判定 | MUL + ADD（点积）| 正面/背面 |
| vtable 调用 | `CALL [RAX+offset]` | 虚函数分发 |

**搜索参照物的原则：搜索 CODE 中引用已知 DATA 的指令，比搜索 DATA 字节本身可靠得多。**

### 双路并行实践

```
路径A（自顶向下）             路径B（自底向上）
     │                              │
 ReadFile hook              扫描 .text 中引用
 捕获 SSKF 读取              SSKF 数据地址的指令
     │                              │
 调用栈回溯 → 返回地址        定位 CMP 'SSKF' 指令
     │                              │
 从返回地址回溯函数入口       从 CMP 指令回溯函数入口
     │                              │
     └────────── 交叉验证 ──────────┘
                  │
            AcquireSMD 入口
```

**两条路径交替推进。** 路径 A 连续 3 轮无进展 → 切到路径 B；反之亦然。

### 策略切换触发器

| 触发条件 | 应该做什么 |
|---------|----------|
| 在同一函数内排除了 2 个候选 | 跳出，横向检查同层级其他函数 |
| 自顶向下追踪连续 3 轮无进展 | 切换到特征指令搜索 |
| 断点在目标场景下不触发 | 立即检查同一分支点的另一侧路径 |
| 修改某变量后影响了非目标实体 | 需要加实体过滤条件 |
| 连续两次补丁修复无效 | 重新审视分析方向 |

### 反模式（禁止做的事）

| 反模式 | 例子 |
|--------|------|
| 不要只走一条路卡住后不切换 | 扫 SSKF 字节 16KB 找不到 → 应该立即切 ReadFile 或引用扫描，而不是继续加大到 64KB |
| 不要强制跳过中间代码 | 补丁跳过初始化代码 → 后续逻辑依赖的状态未设置 |
| 不要忽略函数早期代码 | 序言之后的核心逻辑前往往是对象初始化 |
| 不要在 call 指令前后 hook | call 会改变栈和寄存器状态 |
| 不要连续猜测多步 | 推断 → 调试 → 推断 → 调试交替 |
