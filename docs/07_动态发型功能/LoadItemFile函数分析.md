# LoadItemFile函数分析

## 函数概述

**文件**: `C:\Users\w\Desktop\fs\QXJL10256\QXJL10256\FS\program\client\Current\Source\GameEx\Character.cpp`

**函数**: `void LoadItemFile(int iItemCode, LPCTSTR szFilename)`

**作用**: 从BML文件加载道具信息，包括道具类型、模型文件、纹理文件等

## 完整代码解析

```cpp
void CCharacter::LoadItemFile(int iItemCode, LPCTSTR szFilename)
{
    int i, j;

    // 1. 从文件名提取道具名称
    // 去除路径和扩展名，只保留文件名
    SString sFilename = szFilename;
    sFilename = DCutPath(sFilename);        // 去除路径
    sFilename = DCutFileExt(sFilename);    // 去除扩展名


    // 2. 如果已经加载了同名道具，先移除旧的道具
    // 这确保每个道具只加载一次，更新时移除旧版本
    for(i=0; i<m_ItemCharArray.Num(); i++)
    {
        if(m_ItemCharArray[i].sItemName == sFilename)
        {
            m_ItemCharArray.Remove(i);
            break;
        }
    }

    // 3. 创建新的道具对象并添加到数组
    // 从BML文件加载的道具信息将存储在这里
    SItemChar *pItem = new (m_ItemCharArray) SItemChar;
    pItem->iItemCode = iItemCode;
    pItem->sItemName = sFilename;


    // 4. 从pak包中加载BML文件并解析为XML
    // 4.1 构造完整的BML文件名
    // 注意：这里使用的是二进制XML格式(.bml)
    SFullName nameItem("item", sFilename + ".bml");

    // 4.2 从pak包打开文件
    DFileGPack packItem;
    packItem.Open(nameItem);

    // 4.3 使用CFileSys::LoadBinaryXML解析BML文件为XML文档对象
    // 关键：BML是二进制XML格式，可以转换为标准的XML DOM
    CFileSys::LoadBinaryXML(pDoc, packItem.GetFile(), packItem.GetSize());
    packItem.Close();

    // 注释掉的代码显示最初使用直接XML文件的方式：
    // pDoc.CreateInstance(__uuidof(DOMDocument40));
    // pDoc->load((_variant_t)szFilename);


    // 5. 解析channel信息
    // channel是道具的装备位置标识（位掩码）
    IXMLDOMNodePtr pNodeChannel = pDoc->selectSingleNode(L"/root/channel");
    _bstr_t channel = pNodeChannel->GetnodeTypedValue();
    pItem->dwChannel = atoi((LPCTSTR)channel);


    // 6. 解析角色特定的道具信息
    // BML文件中可能包含多个角色类型的数据，这里选择当前角色的数据
    IXMLDOMNodePtr pNodeCharacter = NULL;
    IXMLDOMNodeListPtr pNodeListObject = NULL;

    SString str;
    str.Format("/root/character[@type=\"%d\"]", m_iCharacterType);
    pNodeCharacter = pDoc->selectSingleNode((LPCTSTR)str);

    // 如果没有找到匹配的角色类型数据，直接返回
    if(pNodeCharacter == NULL)
    {
        return;
    }


    // 7. 解析道具的网格组件（mesh components）
    // 每个道具最多可以有5个网格组件
    pNodeListObject = pNodeCharacter->selectNodes(L"./object");
    for(j=0; j<pNodeListObject->Getlength(); j++)
    {
        IXMLDOMNodePtr pNodeObject = pNodeListObject->Getitem(j);

        // 7.1 解析网格类型
        // 类型决定了道具如何渲染和装备
        IXMLDOMNodePtr pNodeType = pNodeObject->selectSingleNode(L"./type");
        _bstr_t strType = pNodeType->GetnodeTypedValue();

        // 类型映射：
        // 0 - normal: 普通道具，独立渲染
        // 2 - fskin: 面部皮肤
        // 3 - uskin: 上身皮肤
        // 4 - lskin: 下身皮肤
        if(!strcmp(strType, "normal"))      pItem->aItemResource[j].iMeshType = 0;
        else if(!strcmp(strType, "fskin")) pItem->aItemResource[j].iMeshType = 2;
        else if(!strcmp(strType, "uskin")) pItem->aItemResource[j].iMeshType = 3;
        else if(!strcmp(strType, "lskin")) pItem->aItemResource[j].iMeshType = 4;

        // 7.2 解析模型文件（SMD文件）
        // SMD是骨骼模型文件，包含顶点、面片、骨骼等数据
        IXMLDOMNodePtr pNodeMesh = pNodeObject->selectSingleNode(L"./mesh");
        if(pNodeMesh)
        {
            _bstr_t strMesh = pNodeMesh->GetnodeTypedValue();
            pItem->aItemResource[j].sFileSMD = strMesh;
        }

        // 7.3 解析纹理文件（PNG/TGA等）
        // 纹理定义了模型表面的外观
        IXMLDOMNodePtr pNodeTexture = pNodeObject->selectSingleNode(L"./texture");
        if(pNodeTexture)
        {
            _bstr_t strTexture = pNodeTexture->GetnodeTypedValue();
            pItem->aItemResource[j].sFileTexture = strTexture;
        }
    }

    // 8. 释放XML文档对象
    pDoc.Release();
}
```

## 关键发现

### 1. BML文件是二进制XML格式

**证据**:
```cpp
SFullName nameItem("item", sFilename + ".bml");
DFileGPack packItem;
packItem.Open(nameItem);
CFileSys::LoadBinaryXML(pDoc, packItem.GetFile(), packItem.GetSize());
```

**含义**:
- BML文件不是自定义的二进制格式
- 而是压缩/编码后的XML文档
- 可以通过`CFileSys::LoadBinaryXML`解码为标准的XML DOM

**XML路径结构**（从代码推断）:
```xml
<?xml version="1.0"?>
<root>
    <channel>位掩码值</channel>
    <character type="角色类型ID">
        <object>
            <type>normal/fskin/uskin/lskin</type>
            <mesh>模型文件.smd</mesh>
            <texture>纹理文件.png</texture>
        </object>
        <object>
            ...
        </object>
        ...
    </character>
    <character type="其他角色类型ID">
        ...
    </character>
</root>
```

### 2. 道具支持多网格组件

**数据结构**（Character.h）:
```cpp
struct SItemResource
{
    int iMeshType;           // 网格类型
    SString sFileSMD;       // SMD模型文件
    SString sFileTexture;   // 纹理文件
};

struct SItemChar
{
    int iItemCode;                           // 道具代码
    SString sItemName;                       // 道具名称
    dword dwChannel;                         // 装备位掩码
    SItemResource aItemResource[MAX_MESH_COMP]; // 最多5个网格组件
};
```

**重要发现**:
- 每个道具最多可以有5个网格组件（MAX_MESH_COMP = 5）
- 这意味着一个道具可以包含多个独立的3D模型
- 对于发型，可能包含主体、刘海、后发等多个部分

### 3. 没有发现物理模拟相关字段

**观察**:
- `LoadItemFile`函数中只加载了基本信息：
  - channel（装备位置）
  - object类型（normal/fskin/uskin/lskin）
  - mesh（SMD模型文件）
  - texture（纹理文件）

**没有找到**:
- 物理参数（重力、弹性、阻尼等）
- 物理骨骼绑定信息
- 动态效果标志位
- 物理模拟开关

**推测**:
- 物理模拟参数可能存储在SMD模型文件中
- 或者物理系统在加载SMD时自动判断/设置
- 或者有单独的物理配置文件

## BML文件XML结构推测

基于代码分析，BML文件的XML结构应该是：

```xml
<?xml version="1.0"?>
<root>
    <!-- channel: 装备位掩码 -->
    <!-- 1<<0: 位置1 -->
    <!-- 1<<1: 位置2 -->
    <!-- ... -->
    <channel>8</channel>

    <!-- character节点按角色类型分组 -->
    <!-- type="1,2,3,4,5" 对应不同的角色模型 -->
    <character type="1">
        <!-- 每个道具可以有多个object -->
        <object>
            <!-- 网格类型 -->
            <type>normal</type>  <!-- 或 fskin/uskin/lskin -->

            <!-- SMD模型文件 -->
            <mesh>art/effect/hair_model.smd</mesh>

            <!-- 纹理文件 -->
            <texture>art/effect/hair_texture.png</texture>
        </object>

        <!-- 复杂道具可能有多个object -->
        <object>
            <type>normal</type>
            <mesh>art/effect/hair_model2.smd</mesh>
            <texture>art/effect/hair_texture2.png</texture>
        </object>
    </character>

    <!-- 同一道具可能支持多个角色类型 -->
    <character type="2">
        <!-- 类似的结构 -->
    </character>
</root>
```

## 下一步分析计划

### 1. 解析实际的BML文件

**目标**: 将BML文件转换为可读的XML

**方法**:
- 研究`CFileSys::LoadBinaryXML`的实现
- 理解二进制XML的编码方式
- 开发Python脚本将BML转换为XML

**预期产出**:
```xml
<!-- 示例：i50125031.bml (破坏者超赛发型) -->
<?xml version="1.0"?>
<root>
    <channel>32</channel>
    <character type="1">
        <object>
            <type>normal</type>
            <mesh>hair_50125031_part1.smd</mesh>
            <texture>hair_50125031_part1.png</texture>
        </object>
        <object>
            <type>normal</type>
            <mesh>hair_50125031_part2.smd</mesh>
            <texture>hair_50125031_part2.png</texture>
        </object>
    </character>
</root>
```

### 2. 分析SMD模型文件

**目标**: 理解SMD模型文件的格式，特别是物理模拟相关数据

**任务**:
- 查找SMD文件加载代码（`DGraphicAcquireSMD`）
- 研究SMD文件格式规范
- 对比动态发型和静态发型的SMD文件

**关键问题**:
- SMD文件是否包含骨骼数据？
- 物理参数是否在SMD文件中？
- 静态发型和动态发型的SMD文件有何不同？

### 3. 研究道具显示流程

**目标**: 理解道具从BML加载到最终显示的完整流程

**关键函数**:
- `RefreshItem()` - 应用道具到角色
- `AttachSMD()` - 将SMD模型绑定到角色
- `DGraphicAcquireSMD()` - 加载SMD模型文件

## 总结

通过分析`LoadItemFile`函数，我们获得了以下重要信息：

1. **BML是二进制XML**：可以被解码为标准的XML格式
2. **XML结构清晰**：包含channel、character、object等节点
3. **道具信息简单**：只包含类型、模型文件、纹理文件
4. **物理参数缺失**：BML中没有物理模拟相关字段

**核心结论**:
- 动态发型的物理效果**不是**由BML文件控制
- 物理参数可能存储在SMD模型文件中
- 需要深入分析SMD文件格式和加载逻辑

---

**文档创建时间**: 2026-02-09
**下一步**: 研究SMD模型文件加载代码和格式
