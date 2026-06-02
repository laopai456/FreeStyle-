# SSKF 文件格式文档（SMD 二进制格式）

> 从老源码 `DSkin.cpp` / `DSkeleton.h` / `DGraphicObj.cpp` 提取
> 源码路径：`C:\Users\w\Desktop\fs\QXJL10256\QXJL10256\FS\program\client\Net_Directx9\Source\Scud\`

---

## 一、文件整体结构

SSKF 文件 = `DMeshPrimitive::Serialize()` 的二进制序列化输出。

```
[SPackHeader 8字节]      魔数 "SSKF" + 版本号
[SName]                  Mesh 名称
[DSkeleton]              骨骼数据
[TArray<SMaterial>]      材质数组
[TArray<SVector>]        顶点位置数组
[TArray<SVector>]        法线数组
[TArray<STexturedVertex>] Wedge（纹理顶点）数组
[TArray<SSkinTriangle>]  面片数组
[TArray<SBoneInfluence>] 骨骼权重影响数组
--- 以上为 DMeshPrimitive 基类 ---
[DProgressiveMesh 扩展字段]
```

---

## 二、字段详细定义

### 2.1 SPackHeader（8字节）

```cpp
struct SPackHeader {
    char    Identity[4];    // "SSKF"
    dword   Version;        // SKIN_LASTEST_VERSION = 0
};
```

| 偏移 | 大小 | 类型 | 说明 |
|------|------|------|------|
| 0x00 | 4 | char[4] | 魔数 "SSKF" |
| 0x04 | 4 | dword | 版本号，当前为 0 |

版本号会被存入 `DArchive::m_dwVer`，影响后续骨骼数据的读取逻辑。

---

### 2.2 SName（名称类型）

SName 的序列化格式通常是：`[int 字符串长度][char[] 字符串数据]`（具体取决于 DArchive 的 SName 序列化实现）。

---

### 2.3 DSkeleton（骨骼系统）

```cpp
DSkeleton::Serialize(Ar) {
    Ar << Name << Bones;  // 名称 + 骨骼数组
}
```

#### SBone（单个骨骼）

```cpp
struct SBone {
    SName   Name;           // 骨骼名称，如 "Bone01"、"Bip01"
    SName   Group;          // 骨骼分组
    int     ParentIndex;    // 父骨骼索引（-1 = 根骨骼）
    int     NumChildren;    // 子骨骼数量
    int     Depth;          // 在骨骼树中的深度
    dword   Flags;          // 标志位
    SVector Pos;            // 位置 (X, Y, Z) 各 float
    SQuat   Quat;           // 旋转四元数 (X, Y, Z, W) 各 float
};
```

**关键：版本影响读取逻辑！**

- **Version <= 1**（老格式）：序列化末尾多读一个 `SVector Scale`（12字节）
  ```
  Name, Group, ParentIndex, NumChildren, Depth, Flags, Pos, Quat, Scale
  ```

- **Version >= 2**（新格式）：不读 Scale
  ```
  Name, Group, ParentIndex, NumChildren, Depth, Flags, Pos, Quat
  ```

当前 SSKF Version = 0，所以**走 Version <= 1 分支**，每个骨骼末尾有 12 字节的 Scale 数据。

#### SBone 字段大小估算

| 字段 | 类型 | 大小 |
|------|------|------|
| Name | SName | ~变长 |
| Group | SName | ~变长 |
| ParentIndex | int | 4 |
| NumChildren | int | 4 |
| Depth | int | 4 |
| Flags | dword | 4 |
| Pos | SVector (3×float) | 12 |
| Quat | SQuat (4×float) | 16 |
| Scale (v<=1) | SVector (3×float) | 12 |

---

### 2.4 SCtrlPoint（控制点 - DProgressiveMesh 扩展）

```cpp
struct SCtrlPoint {
    SName   Name;           // 控制点名称
    int     ParentBone;     // 所属骨骼索引（-1 = 无父骨骼）
    SVector Pos;            // 位置 (3×float = 12字节)
    SQuat   Quat;           // 旋转 (4×float = 16字节)
    // SMatrix Matrix;      // 不参与序列化，运行时计算
};
```

**这是 AttachSMD 的关键**：游戏加载 SMD 后，遍历 CtrlPoints 数组，通过 ParentBone 找到对应骨骼名称，挂载到角色骨骼树上。

```cpp
// AttachSMD 核心逻辑 (DGrpActor.cpp L198)
for(nCPoint=0; nCPoint<pObject->CtrlPoints.Num(); ++nCPoint) {
    SCtrlPoint *pCPoint = &pObject->CtrlPoints[nCPoint];
    if(pCPoint->ParentBone < 0)
        AddCtrlPointGrp(pCPoint->Name, pCPoint->Pos, pCPoint->Quat, NONE);
    else
        AddCtrlPointGrp(pCPoint->Name, pCPoint->Pos, pCPoint->Quat,
                        pObject->Skeleton.Bones[pCPoint->ParentBone].Name);
}
```

---

### 2.5 SMaterial（材质）

```cpp
struct SMaterial {
    SName       Name;       // 材质名称
    EBlendType  BlendType;  // 混合类型 (enum, sizeof = 4)
    bool        bTwosided;  // 双面渲染
    bool        bUseAlpha;  // 使用透明
    byte        Alpha;      // 透明度
    EElement    Element;    // 元素类型 (enum)
    SName       DiffuseTex; // 漫反射贴图名称（如 "i50125031_mt"）
};
```

---

### 2.6 STexturedVertex（纹理顶点/Wedge）

```cpp
struct STexturedVertex {
    word  PointIndex;   // 指向 Points 数组的索引
    float U, V;         // 纹理坐标
};
// 每个大小：2 + 4 + 4 = 10 字节
```

---

### 2.7 SSkinTriangle（三角面片）

```cpp
struct SSkinTriangle {
    byte  MaterialIndex;       // 材质索引
    word  WedgeIndex[3];       // 3个 Wedge 索引
};
// 每个大小：1 + 2×3 = 7 字节
```

---

### 2.8 SBoneInfluence（骨骼蒙皮权重）

```cpp
struct SBoneInfluence {
    float   Weight;        // 权重 (4字节)
    int     BoneIndex;     // 骨骼索引 (4字节)
    SVector LocalPos;      // 局部位置 (12字节)
    SVector LocalNormal;   // 局部法线 (12字节)
};
// 每个大小：4 + 4 + 12 + 12 = 32 字节
```

---

### 2.9 DProgressiveMesh 扩展字段

在 DMeshPrimitive 基类数据之后，还有：

```cpp
DProgressiveMesh::Serialize(Ar) {
    Super::Serialize(Ar);  // 上面所有基类数据
    Ar << LodVertexNum           // int (4字节)
       << MinLodVertexNum        // int (4字节)
       << LodBias                // float (4字节)
       << CtrlPoints             // TArray<SCtrlPoint>
       << Sections               // TArray<SMeshSection>
       << InvisibleSections      // TArray<SStaticSection>
       << CollisionMesh          // ?
       << FaceLevels             // TArray<?>
       << CollapseWedgeIndex     // TArray<?>
       << Blends                 // TArray<?>
       << StaticBlend;           // ?
}
```

---

## 三、TArray 序列化格式

TArray 是引擎的动态数组，序列化格式通常是：

```
[int Count]           元素数量
[Element[0]]          第一个元素
[Element[1]]          第二个元素
...
[Element[Count-1]]    最后一个元素
```

---

## 四、动态发型 vs 静态发型的关键差异

| 项目 | 静态发型 | 动态发型 |
|------|---------|---------|
| 骨骼数 | ~44（标准 Bip01） | ~55（额外 Bone01-11） |
| 文件大小 | ~919KB | ~353KB |
| CtrlPoints | 标准控制点 | 包含物理骨骼控制点 |
| 骨骼名称 | Bip01 系列 | Bip01 + Bone01-11 |

**动态发型独有的物理骨骼**：
```
Bone01, Bone02, Bone03(mirrored), Bone03(mirrored)(mirrored),
Bone03, Bone03(mirrored)234, Bone04, Bone05, Bone06,
Bone06(mirrored), Bone07, Bone08, Bone09, Bone09(mirrored),
Bone10, Bone11
```

---

## 五、加载流程（AcquireSMD）

```
1. DGraphicStore::AcquireSMD(filename, preset)
2.   打开文件（DFileGPack，从 pak 中读取）
3.   读前4字节，判断是否 "SSKF"
4.   如果是 SSKF：
       全部读入内存 → DMemoryReader → pMesh->Serialize(reader)
5.   如果不是 SSKF（旧格式）：
       用 GMeshGrp 加载 → ImportOtherMesh 转换
6.   pMesh->BuildVertexBuffer()
7.   加载材质纹理
8.   返回 Handle

9. 角色调用 AttachSMD(Handle)
10.  遍历 pObject->CtrlPoints
11.  根据 ParentBone 找骨骼名 → AddCtrlPointGrp 挂载
```

**加载失败的可能原因**：
1. CtrlPoints 引用的 ParentBone 索引超出 Skeleton.Bones 范围
2. 角色基础骨骼树中找不到 CtrlPoints 引用的骨骼名
3. 物理骨骼（Bone01-11）在角色基础骨骼中不存在，AddCtrlPointGrp 失败

---

## 六、源码文件索引

| 文件 | 路径 | 作用 |
|------|------|------|
| DSkin.h | Scud/Physics/ | SSKF 数据结构定义（STexturedVertex, SSkinTriangle, SBoneInfluence, DMeshPrimitive） |
| DSkin.cpp | Scud/Physics/ | SSKF Serialize 实现（魔数 "SSKF" + 全字段序列化） |
| DSkeleton.h | Scud/Physics/ | SBone, SCtrlPoint, DSkeleton, DAnimation 数据结构 |
| DSkeleton.cpp | Scud/Physics/ | 骨骼序列化 + 动画系统 + 角色骨骼挂载(AssignSkel/AssignAnim) |
| DGraphicObj.cpp | Scud/Graphic/ | AcquireSMD 实现（文件读取 + SSKF 解析 + 纹理加载） |
| DGrpActor.cpp | Scud/Graphic/ | AttachSMD / DetachSMD（骨骼控制点挂载/卸载） |
| DProgressiveMesh.h | Scud/Graphic/ | DProgressiveMesh 定义（CtrlPoints, Sections 等） |
| DProgressiveMesh.cpp | Scud/Graphic/ | ProgressiveMesh::Serialize（基类 + LOD + CtrlPoints） |
| DGraphics.h | Scud/Base/ | SMaterial, EBlendType, EElement 定义 |
