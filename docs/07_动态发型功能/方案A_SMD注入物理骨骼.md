# 方案A：SMD 文件注入物理骨骼

## 核心思路

不改变 BML 指向，直接**修改静态发型的 SMD 文件**，把动态发型的物理骨骼（Bone01-11）注入进去。这样角色加载的就是一个"自带物理骨骼的静态发型"。

## 问题根因

```
角色基础骨骼：Bip01 系列（~44个）
动态发型 SMD：Bip01 + Bone01-11（~55个）

AttachSMD 遍历 CtrlPoints → 找 ParentBone 对应的骨骼名
→ 角色骨骼树中找不到 "Bone01" → 挂载失败 → 光头
```

但如果我们把静态发型 SMD 本身就改造成包含 Bone01-11 的版本，CtrlPoints 引用的骨骼在 SMD 自己的 Skeleton 里就能找到，AttachSMD 应该能成功。

## 实施步骤

### 第1步：用 Python 解析 SSKF 格式

根据 `SSKF文件格式文档.md` 的定义，写一个 SSKF 解析器：

```
输入：静态发型 SMD (i50125001_MT.smd, ~919KB)
      动态发型 SMD (i50125031_MT.smd, ~353KB)

解析流程：
1. 读 SPackHeader（8字节）→ 确认 "SSKF" + Version
2. 读 SName → Mesh 名称
3. 读 DSkeleton → Name + TArray<SBone>
   - 每个 SBone: Name, Group, ParentIndex, NumChildren, Depth, Flags, Pos, Quat
   - Version=0 所以每个骨骼末尾还有 Scale (12字节)
4. 读 TArray<SMaterial>
5. 读 TArray<SVector> Points
6. 读 TArray<SVector> Normals
7. 读 TArray<STexturedVertex> Wedges
8. 读 TArray<SSkinTriangle> Faces
9. 读 TArray<SBoneInfluence> Influences
10. 读 DProgressiveMesh 扩展字段（LodVertexNum, CtrlPoints 等）
```

### 第2步：提取动态发型的物理骨骼数据

从动态发型 SMD 中提取：
- Bone01-11 的 SBone 条目（~11个）
- 引用这些骨骼的 CtrlPoints
- 引用这些骨骼的 SBoneInfluence（蒙皮权重）

### 第3步：合并注入

```
静态发型 SMD 的 Bones 数组：
  [0..43] Bip01 系列骨骼（保持不变）

→ 追加动态发型的物理骨骼：
  [44..54] Bone01-11（ParentIndex 需要调整）

→ 合并 CtrlPoints（追加动态发型的物理控制点）
→ 合并 Influences（追加物理骨骼的蒙皮权重）
→ Points / Normals / Wedges / Faces 保持静态发型原始数据
```

### 第4步：重新序列化 + 打包回 pak

按 SSKF 格式重新序列化，用 `resources.exe` 打包回 res764.pak。

## 关键难点

| 难点 | 说明 | 解决思路 |
|------|------|---------|
| SName 序列化格式不确定 | 不知道 SName 在二进制中是长度前缀还是其他格式 | 先解析两个 SMD 对比验证 |
| TArray 序列化格式不确定 | 可能是 int + 元素数组，也可能有额外字段 | 先解析验证 |
| 物理骨骼的 ParentIndex | Bone01-11 可能挂在不同父骨骼下，需要正确映射 | 从动态发型 SMD 中读取原始父子关系 |
| SBoneInfluence.BoneIndex | 蒙皮权重的骨骼索引需要对应新的骨骼数组位置 | 重新映射索引 |

## 验证方法

1. 先只做**解析**：用 Python 读两个 SMD，打印所有字段，验证格式理解正确
2. 读入静态 SMD → 不做修改 → 重新序列化 → 对比原文件是否一致（round-trip 测试）
3. 注入物理骨骼 → 打包回 pak → 游戏测试

## 风险

- **中等**：SSKF 格式的 TArray/SName 序列化细节可能和文档推断不一致，需要实际解析验证
- **中等**：即使注入了骨骼，游戏可能在 AcquireSMD 阶段做额外校验（如骨骼数量上限）
- **低**：打包回 pak 的步骤已经验证过会导致问题（之前是改 BML 大小不同导致崩溃），但这次改的是 SMD 不是 BML，pak 结构可以保持大小不变

## 优势

- **不依赖调试器**，纯文件操作，完全绕开 Apollo
- 可重复、可自动化，集成到 FS服装搭配专家 工具中
- 我们已经有了完整的 SSKF 格式文档
