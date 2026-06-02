# 方案A 实测失败分析报告

## 结论

**方案A（SMD 文件注入物理骨骼）已实测失败。** 注入骨骼后发型无物理摆动效果。

## 实测过程

### 第一轮：替换 i50125461_mt.smd（错误目标）

- 从 res767.pak 提取 `i50125461_mt.smd`（59骨，PAK低细节版）
- 从 res764 本地完整版 `i50125031_MT_dynamic.smd`（75骨）提取 17 个物理骨骼
- 注入后 76 骨，round-trip 验证通过
- 打包回 res767.pak，游戏测试：**发型正常显示，但无物理摆动**
- 失败原因：BML 指向的是 `i50125601_FN.smd`，不是 `i50125461_mt.smd`

### 第二轮：替换 i50125601_fs.smd（错误目标）

- 读取 BML 发现美丽梦想发型(50125461) 的 BML 引用 `i50125601` 系列
- 替换 `i50125601_fs.smd`（女静态）和 `i50125601_ms.smd`（男静态）
- 注入后 76/75 骨，round-trip 验证通过
- 打包回 res767.pak，游戏测试：**发型没有任何改变**
- 失败原因：BML 中女角色 type=4 的主对象是 `i50125601_FN.smd`，不是 FS

### 关键发现：PAK 内动态发型也没有物理骨骼

这是最重要的发现：

| 文件 | 来源 | 骨骼数 | CtrlPoints | raw_tail |
|------|------|--------|------------|----------|
| i50125031_MT_dynamic.smd | 本地完整版 | **75** | 0 | 175,427 bytes |
| i50125031_mt.smd | PAK 内 | **59** | 0 | 15,534 bytes |
| i50125001_MT_static.smd | 本地完整版 | **58** | 0 | 830,667 bytes |
| i50125001_mt.smd | PAK 内 | **58** | 0 | 9,482 bytes |

**PAK 里的动态发型 SMD 只有 59 骨，没有物理骨骼！** 但游戏中动态发型确实有物理摆动效果。

完整版 SMD 的 raw_tail 以 PAK 版 raw_tail 开头，后面多了 159,893 bytes 额外数据（包含嵌入的 PNG 贴图），这是开发版，不是游戏使用的版本。

### 结论：物理效果不是靠 SMD 骨骼触发的

游戏引擎在运行时根据某种机制（角色类型、BML 配置、或内部逻辑）决定是否为发型创建物理模拟。仅往 SMD 里注入骨骼数据无法触发物理效果。

## BML 文件结构发现

美丽梦想发型 (50125461) 的 BML 内容：

```xml
<root>
   <channel>1</channel>
   <character type="1">  <!-- 男角色 -->
      <object>
         <type>normal</type>
         <mesh>res767\i50125601_MN.smd</mesh>
      </object>
      <object type="2">
         <type>normal</type>
         <mesh>res767\i50125601_MS.smd</mesh>
      </object>
   </character>
   <character type="4">  <!-- 女角色 -->
      <object>
         <type>normal</type>
         <mesh>res767\i50125601_FN.smd</mesh>  <!-- 主对象，游戏加载这个 -->
      </object>
      <object type="2">
         <type>normal</type>
         <mesh>res767\i50125601_FS.smd</mesh>
      </object>
   </character>
</root>
```

关键点：
- BML 的 ItemCode（50125461）和 mesh 文件名（50125601）**不一定相同**
- 女角色 type=4 的**主对象**（第一个 object）是 FN，不是 FS
- 动态发型（50125331）的 BML 中女角色主对象是 **FT**，不是 FN

## SMD 文件后缀含义

| 后缀 | 含义 | 说明 |
|------|------|------|
| MN | Male Normal | 男角色普通模型（主对象） |
| MS | Male Static | 男角色静态模型（次要对象） |
| MT | Male Total | 男角色完整模型 |
| MF | Male Fat | 男角色胖体型 |
| FN | Female Normal | 女角色普通模型（主对象） |
| FS | Female Static | 女角色静态模型（次要对象） |
| FT | Female Total | 女角色完整模型 |
| FSC | Female Special | 女角色特殊体型 |

## 已开发的工具

虽然方案A失败，但开发过程中产出的工具仍然有价值：

| 工具 | 路径 | 状态 | 用途 |
|------|------|------|------|
| sskf_tool.py | FreeStyle/sskf_tool.py | 已验证 | SSKF 二进制格式解析/序列化 |
| inject_physics_bones.py | FreeStyle/inject_physics_bones.py | 已验证 | 物理骨骼注入（方案A用） |
| inject_physics_bones_767.py | FreeStyle/inject_physics_bones_767.py | 已验证 | res767 版本注入 |
| inject_physics_bones_50125601.py | FreeStyle/inject_physics_bones_50125601.py | 已验证 | 50125601 版本注入 |
| repack_pak.py | FreeStyle/repack_pak.py | 已验证 | PGFN PAK 打包/验证/对比 |

## 方案B 进展（x32dbg MCP 逆向分析）

方案A失败的根本原因已通过 x32dbg MCP 调试确认：**物理效果不是靠 SMD 骨骼数据触发的，而是由引擎根据运动类型创建不同的 C++ 类**。

### 核心发现

1. **两个不同的 C++ 类**：
   - `DDynamicActor`：带物理初始化，vtable 在 0x284AA4C
   - `DStaticActor`：无物理初始化，vtable 在 0x284E114

2. **运动类型存储在对象偏移 0xC0**：
   - 11 (0x0B) = Dynamic
   - 12 (0x0C) = Static

3. **物理初始化条件**（0x0229C2D0）：
   - `this->flags & 0x18` 必须非零
   - `this->field_0x460` 必须非零

4. **BML 配置**：`CharacterMotion.bml` 文件使用 `ItemCode%d` 格式配置运动类型

### 关键地址速查表

| 函数/数据 | 地址 |
|-----------|------|
| DDynamicActor 构造函数 | 0x229B0B0 |
| DStaticActor 构造函数 | 0x236B8A0 |
| DynamicInit | 0x229B4D0 |
| StaticInit | 0x24C5910 |
| SetMotionType | 0x02297810 |
| DynamicPhysicsInit | 0x0229C2D0 |
| BML ItemCode 解析器 | 0x21B6070 |
| "CharacterMotion.bml" 字符串 | 0x283C750 |
| "ItemCode%d" 字符串 | 0x283C76C |

### 下一步

详细分析结果见 [调试总结.md](./调试总结.md) 第九章。正在追踪工厂决策函数和 CharacterMotion.bml 配置。