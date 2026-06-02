# Progress 2026-05-27: IDA Pro 分析

> ⏳ **已归档** — 信息已提取到 01_知识库 / 02_试验记录 / 03_常量地址表


## §82: IDA Pro Headless 分析成功

**工具**: IDA Pro 9.3 (idat.exe headless) + 自写 IDAPython 脚本
**输入**: dump_text_pe.exe (PE32 wrapper of dump_text.bin, 40MB)
**方法**: PE32 wrapper 解决 binary 文件 32/64bit 模式选择问题

### 脚本链

| 版本 | 脚本 | 结果 |
|------|------|------|
| v1 | ida_analyze.py | auto_wait 卡住（40MB 全局分析） |
| v2 | ida_analyze_v2.py | create_dword API 错误 |
| v3 | ida_analyze_v3.py | auto_wait 仍然卡住 |
| **v4** | **ida_analyze_v4.py** | **成功** — 手动扫描 call 指令，跳过全局等待 |
| v5 | ida_find_vtable_refs.py | **成功** — 全段扫描 vtable 引用 |
| v6 | ida_find_factory.py | **成功** — 工厂函数分析 |

### §83: 完整函数分析结果

**13 个已知函数成功定义**:
- CharacterMotion_parser: 4153B, 113 calls, 56 jumps
- DDynamicActor_ctor: 123B, 3 calls
- DStaticActor_ctor: 64B, 1 call
- DynamicInit: 157B, 0 calls (纯数据初始化)
- base_ctor: 1184B, 6 calls
- SetMotionType: 735B, 4 calls

### §84: VTable 完整内容

**DDynamicActor vtable (0x0284A9EC)**:
| Offset | Value | Name |
|--------|-------|------|
| 0x00 | 0x229AE80 | DDynamicActor_ctor (也是 vfunc[0]) |
| 0x04 | 0x229AE60 | 析构? |
| 0x08 | 0x229B170 | |
| 0x0C | 0x229B270 | |
| 0x10 | 0x229C570 | **DynamicInit 调用的虚函数** |
| 0x14 | 0x2295F80 | ← 共享 |
| 0x18 | 0x2296000 | ← 共享 |
| 0x1C | 0x22960F0 | ← 共享 |
| 0x20 | 0x22962E0 | ← 共享 |

**DStaticActor vtable (0x0284E0B4)**:
| Offset | Value | Name |
|--------|-------|------|
| 0x00 | 0x236CC20 | (完整构造函数，不是简单 ctor) |
| 0x04 | 0x236CC00 | |
| 0x08 | 0x24C5560 | |
| 0x0C | 0x24C5610 | |
| 0x10 | 0x24C5630 | |
| 0x14 | 0x2295F80 | ← 与 Dynamic 共享 |
| 0x18 | 0x2296000 | ← 共享 |
| 0x1C | 0x22960F0 | ← 共享 |
| 0x20 | 0x22962E0 | ← 共享 |

### §85: VTable 引用全段扫描

**DDynamicActor vtable (0x0284A9EC) — 7 处引用**:
| 地址 | 函数 | 用途 |
|------|------|------|
| 0x229AD50 | 两阶段构造 | 先设 base(284A92C)→覆盖 Dynamic |
| 0x229ADF0 | 构造变体 | 直接设 vtable→DynamicInit |
| **0x229AE80** | **已知 ctor** | SEH + flags |
| 0x229AF00 | **工厂函数** | base_ctor→覆盖 Dynamic→物理初始化 (545B) |
| 0x22F28CB | 误报 | IDA 反汇编错误 |
| 0x22FA6A5 | INT3 路径 | 异常处理中的构造 |
| 0x230436C | 部分误报 | base→Dynamic 两阶段 |

**DStaticActor vtable (0x0284E0B4) — 4 处引用**:
| 地址 | 函数 | 用途 |
|------|------|------|
| 0x236B5E6 | INT3 路径 | 异常处理中的构造 |
| 0x236CBA0 | 构造变体 | SEH |
| 0x236CC20 | vtable[0] | 完整构造函数 |
| **0x24C5520** | **已知 ctor** | base_ctor→vtable→无物理 |

### §86: 工厂函数 — 关键发现

**DStaticActor 工厂函数 (0x236B36B, 337B)**:
```
call DStaticActor_ctor      → vtable=284E0B4, +460h=0, +8=3
call 0x22E2F80              → 初始化 +464h
mov [eax], 284E00C          → 覆盖 vtable！（实际运行时 vtable）
mov [ecx+464h], 284DFA4     → 子 vtable
4x call 0x437F40            → 子对象 +5A4h,+5CCh,+5D8h,+5E4h
call 0x438780               → +5F8h
```

**DDynamicActor 工厂函数 (0x229AF00, 545B)**:
```
call base_ctor              → 构造基类
mov [eax], 284A9EC          → 设 Dynamic vtable
+460h = globals(2A43CA4)    → 物理参数块
+46Ch = 0                   → 物理状态
+470h = float(26A1B04)      → 物理参数
+47Ch = vec3(0,0,0)         → 物理位置
+48Ch = vec3(0,0,0)         → 物理速度
call 0x229B130 × 2          → 子对象 +514h, +578h
+47Ch,+48Ch = globals       → 物理数据
+8 = 1                      → TYPE_DYNAMIC
```

### §87: Static→Dynamic 转换理论可行

**所有修改都在堆内存，不触 .text CRC！**

| 偏移 | Static 值 | Dynamic 值 | 说明 |
|------|-----------|------------|------|
| +0 | 284E00C | 284A9EC | vtable |
| +8 | 3 | 1 | 类型标记 |
| +460h | 0 | globals(2A43CA4) | 物理参数块 |
| +46Ch | - | 0 | 物理状态 |
| +470h | - | float(26A1B04) | 物理参数 |
| +47Ch | - | globals+vec3 | 物理位置 |
| +48Ch | - | globals+vec3 | 物理速度 |

**实现方式**: Pymem 扫描堆 → 找到 vtable=284E00C 的对象 → 逐字段修改

### 关键地址修正

| 旧地址 | 新地址 | 说明 |
|--------|--------|------|
| DStaticActor vtable 0x0284E0B4 | **实际运行时 vtable 0x0284E00C** | 工厂函数覆盖了构造函数设的值 |

### 两个工厂函数的调用者

**两者均 0 个直接 E8 caller** — 通过函数指针间接调用。决策点在更上层。
