# CharacterMotion Type Remap — 动态发型方案规范

## 项目概述

**项目名称**：CharacterMotion Type Remap（运动类型重映射）  
**创建日期**：2026-05-16  
**优先级**：最高（P0）  
**状态**：探索验证阶段  

## 目标

将静态发型（如美丽梦想 ItemCode 25461）在运行时伪装为动态发型，使引擎自动创建 DDynamicActor 并初始化完整物理模拟，实现头发物理摆动效果。

## 核心思路

### 原理

游戏加载每个道具时，引擎通过以下链路决定是否启用物理：

```
服务器下发 CharacterMotion.bml
  → 解析每条 ItemCode 的 Type 字段 ("Static" / "Dynamic")
  → 工厂函数 0x021C1F00 读取 Type
  → Type="Static" → 创建 DStaticActor → 跳过物理初始化
  → Type="Dynamic" → 创建 DDynamicActor → 调用 DynamicInit → 完整物理
```

**我们的方案**：不碰代码段，不碰 JMP，只在**堆内存**中找到 CharacterMotion 解析结果，将目标 ItemCode 的 Type 字段从 `0x0C (Static)` 改为 `0x0B (Dynamic)`。引擎下次加载该道具时，工厂函数自然创建 DDynamicActor。

### 为什么这个方向成功率高

| 优势 | 说明 |
|------|------|
| **纯堆数据修改** | APOLLO 不检测堆内存读写，100% 安全 |
| **利用引擎自身逻辑** | 不是我们造物理效果，是让引擎的原生物理系统正常工作 |
| **不碰代码段** | 无需 JMP/Hook，不触发 CRC 校验 |
| **已有数据支撑** | 已知 FName 索引：Dynamic=0x0B, Static=0x0C |
| **已有脚本基础** | scan_itemcode.py 和 char_motion_remap.py 已就绪 |

### 与之前方案的区别

| 方案 | 做法 | 失败原因 |
|------|------|----------|
| ❌ 方案1-3 | 改代码段/调试器 | APOLLO 检测 |
| ❌ 方案4-6 | 改 DSkeleton 参数/骨骼 | 引擎不执行物理 |
| ❌ 方案7-8 | BML 替换/EffectCode | 外观/路径问题 |
| **✅ 本方案** | **改 Type 映射** | **让引擎自己做物理** |

## 已知关键数据

### FName 运动类型系统

| FName | 全局对象地址 | 索引值 |
|-------|-------------|--------|
| "Base" | 0x2A783F8 | 0x0A (10) |
| "Dynamic" | 0x2A78410 | **0x0B (11)** |
| "Static" | 0x2A783F4 | **0x0C (12)** |

### 关键函数

| 函数 | 地址 | 功能 |
|------|------|------|
| CharacterMotion 解析 | 0x21B46E0 | 解析 .bml，为每个道具创建运动对象 |
| 对象创建工厂 | 0x021C1F00 | 根据 Type→vtable 创建 Actor |
| DDynamicActor 构造 | 0x0229B0B0 | 动态运动对象构造函数 |
| DStaticActor 构造 | 0x0236B8A0 | 静态运动对象构造函数 |
| DynamicInit | 0x0229B4D0 | 物理引擎初始化 |
| DynamicPhysicsInit | 0x0229C2D0 | 物理参数初始化（含 flags 检查） |

### DStaticActor vs DDynamicActor 差异

| 偏移 | DStaticActor | DDynamicActor | 含义 |
|------|:---:|:---:|------|
| +0x00 | 0x284E114 | 0x284AA4C | vtable |
| +0x74 | 不同 | 0xA3 | flags（& 0x18 启用物理） |
| +0xC0 | 0x0C | 0x0B | 运动类型 FName 索引 |
| +0x460 | 可能零 | 非零 | 物理参数1 |

### DSkeleton 物理参数（full_dump 新发现）

| 偏移 | 静态值 | 动态值 | 含义 |
|------|--------|--------|------|
| +0x00C | 61 | 74 | 骨骼总数 |
| +0x01C | 1 | 24 | 物理骨骼数 |
| +0x020 | -0.1449 | 0.9583 | 刚度/阻尼 |
| +0x02C | 820(int) | 1.25(float) | 重力/质量 |
| +0x070-0x11C | 22个字段有差异 | 0x00(清零) | 未探索区域 |

### APOLLO 安全矩阵

| 操作 | 安全性 |
|------|:------:|
| ReadProcessMemory | ✅ 安全 |
| WriteProcessMemory 写堆内存 | ✅ 安全 |
| WriteProcessMemory 写代码段 | ❌ 被杀 |
| x64dbg / 硬件断点 | ❌ 被杀 |
| CreateRemoteThread | ⚠️ 待验证 |

## 实施阶段

### 阶段 1：定位 Type 字段（当前）

**目标**：找到堆内存中 ItemCode → Type 的映射关系。

**方法**：
1. 扫描堆上所有 ItemCode 25461 出现的位置
2. 对每个命中位置，向前回溯找 vtable（确认对象类型）
3. 在命中位置 ±0x200 范围搜索 0x0B / 0x0C 值
4. 确认 Type 字段相对于 ItemCode 的偏移

**工具**：`char_motion_remap.py`

**验证**：
- 静态发型附近应有 0x0C (Static)
- 动态发型附近应有 0x0B (Dynamic)
- 偏移量一致

### 阶段 2：Type 修改 + 重装备测试

**目标**：修改 Type 字段，重新装备发型，验证物理效果。

**方法**：
1. 将目标 ItemCode 的 Type 从 0x0C 改为 0x0B
2. 游戏中卸下发型 → 重新装备
3. 引擎工厂函数读取到 Dynamic → 创建 DDynamicActor
4. 观察：是否崩溃、是否显示正常、是否有物理摆动

**前置条件**：
- PAK 中已部署含物理骨骼的 SMD（res767_injected.pak 已有）
- Type 修改后引擎需要重新加载道具

**风险与应对**：

| 风险 | 可能性 | 应对 |
|------|--------|------|
| Type 字段被引擎覆盖 | 中 | 持续监控 + 自动重写 |
| 引擎检测到骨骼数不匹配 | 低 | SMD 已注入76根骨骼 |
| 显示异常（光头/撕裂） | 中 | 检查 BML mesh 路径 |
| 无物理效果 | 低 | 如果是 DDynamicActor 就一定有物理 |

### 阶段 3：通用化 + 自动化

**目标**：输入任意 ItemCode → 自动完成 Type 重映射。

**方法**：
1. 封装为通用脚本
2. 支持命令行参数指定 ItemCode
3. 自动监控 + 覆盖保持
4. 开机自启动选项

### 阶段 4：备选方案（如果 Type 字段不与 ItemCode 在同一结构中）

如果 Type 和 ItemCode 不在同一个对象中，需要：

**备选 A：全局 CharacterMotion 表定位**
- 已知全局地址：`ItemCount` at 0x283C778, `CharacterName` at 0x283C788
- 从这些全局变量出发，遍历 CharacterMotion 数组
- 找到目标 ItemCode 的条目，修改其 Type

**备选 B：工厂函数输入参数修改**
- 在工厂函数 0x021C1F00 被调用前，修改其参数
- 纯数据修改，不碰代码段
- 需要定位工厂函数的调用者

**备选 C：外部骨骼矩阵物理模拟**
- 完全绕过引擎物理系统
- Python 端运行弹簧-阻尼模型
- 以 ~30fps 轮询写入骨骼变换矩阵
- 成功率 100%，但效果可能不如原生物理自然

## 已有脚本清单

| 脚本 | 功能 | 状态 |
|------|------|------|
| `char_motion_remap.py` | CharacterMotion Type 扫描+重映射 | 🔄 新建 |
| `full_dump.py` | DSkeleton 完整 0x120 字节 dump+对比 | ✅ 完成 |
| `scan_itemcode.py` | ItemCode 堆扫描 + vtable 回溯 | ✅ 完成 |
| `hair_diff.py` | 静态/动态内存快照对比 | ✅ 完成 |
| `physics_v3.py` | DSkeleton 参数注入实验 | ✅ 完成 |
| `physics_safe.py` | 安全版物理注入 | ✅ 完成（参数生效但无效果） |
| `obj_clone.py` | 运行时对象克隆 | ⚠️ 已证明不可行 |

## 变更日志

| 日期 | 变更 |
|------|------|
| 2026-05-16 | 初始版本：CharacterMotion Type Remap 方案 |
