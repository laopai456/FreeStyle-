# BML文件格式分析报告

## 关键发现

通过逆向分析源代码`FileSys.cpp`，发现BML文件实际上是**XML文件**，有两种存储格式：

1. **XOR加密格式**：每个字节与0xFF进行XOR运算
2. **纯文本XML格式**：直接存储的XML文本

## 源代码分析

### LoadBinaryXML函数（FileSys.cpp:78-133）

```cpp
bool CFileSys::LoadBinaryXML(IXMLDOMDocument2Ptr &pDoc, FILE *fIn, DWORD dwSize)
{
    pDoc.CreateInstance(__uuidof(DOMDocument40));

    // 读取BML文件数据
    if(dwSize>0)
    {
        char *pBuffer;
        pBuffer = new char [dwSize + 1];
        memset(pBuffer, 0, dwSize+1);

        fread(pBuffer, sizeof(char), dwSize, fIn);

        // 关键：每个字节与0xFF进行XOR解密
        for(int i=0; i<dwSize; i++)
        {
            pBuffer[i] = pBuffer[i] ^ 0xff;
        }

        strXML = pBuffer;
        delete [] pBuffer;
    }

    // 加载为XML DOM
    pDoc->loadXML(strXML);
    return true;
}
```

**解密算法**：
```cpp
解密后字节 = 原字节 XOR 0xFF
```

## 实际测试结果

### 动态发型：i50125031.bml（破坏者超赛发型）

**文件大小**: 1582 bytes

**格式**: 纯文本XML（无需解密）

**XML内容**:
```xml
<?xml version="1.0"?>
<root>
   <channel>1</channel>
   
   <character type="1">
      <object>
         <type>normal</type>
         <mesh>res764\i50125031_MT.smd</mesh>
         <texture>res764\i50125031.png</texture>
      </object>
      <object type="2">
         <type>normal</type>
         <mesh>res764\i50125031_ms.smd</mesh>
         <texture>res764\i50125031.png</texture>
      </object>
   </character>
   
   <character type="2">
      <object>
         <type>normal</type>
         <mesh>res764\i50125031_MN.smd</mesh>
         <texture>res764\i50125031.png</texture>
      </object>
   </character>
   
   <!-- type=3,4,5,6... -->
</root>
```

### 静态发型：i50125001.bml（可爱加倍发型）

**文件大小**: 1605 bytes

**格式**: XOR加密XML（需要用0xFF解密）

**解密后的XML内容**:
```xml
<root>
   <channel>1</channel>
   <character type="1">
      <object>
         <type>normal</type>
         <mesh>res764\i50125001_MT.smd</mesh>
         <texture>res764\i50125001_M.png</texture>
      </object>
      <object type="2">
         <type>normal</type>
         <mesh>res764\i50125001_MS.smd</mesh>
         <texture>res764\i50125031.png</texture>
      </object>
   </character>
   
   <character type="2">
      <object>
         <type>normal</type>
         <mesh>res764\i50125001_MN.smd</mesh>
         <texture>res764\i50125001_M.png</texture>
      </object>
   </character>
   
   <!-- type=3,4,5,6... -->
</root>
```

## BML文件XML结构分析

### 完整结构

```xml
<?xml version="1.0"?>
<root>
    <!-- 道具的channel信息（位掩码） -->
    <!-- 用于确定道具可以装备在哪些位置 -->
    <channel>1</channel>
    
    <!-- 按角色类型分组 -->
    <!-- type="1,2,3,4,5,6" 对应不同的角色模型 -->
    <character type="1">
        <!-- 每个道具可以有多个object（网格组件） -->
        <!-- 最多5个object -->
        <object>
            <!-- 网格类型 -->
            <type>normal</type>  <!-- normal/fskin/uskin/lskin -->
            
            <!-- SMD模型文件 -->
            <mesh>res764\i50125031_MT.smd</mesh>
            
            <!-- 纹理文件 -->
            <texture>res764\i50125031.png</texture>
        </object>
        
        <object type="2">
            <type>normal</type>
            <mesh>res764\i50125031_ms.smd</mesh>
            <texture>res764\i50125031.png</texture>
        </object>
        
        <!-- 最多5个object... -->
    </character>
    
    <character type="2">
        <!-- 同样的结构，适配不同的角色类型 -->
    </character>
    
    <character type="3">
        ...
    </character>
    
    <!-- ... -->
</root>
```

### XML节点说明

| 节点 | 含义 | 示例 | 说明 |
|------|------|------|------|
| `root` | 根节点 | `<root>` | XML文档根节点 |
| `channel` | 道具channel | `<channel>1</channel>` | 装备位掩码，用于检测道具冲突 |
| `character` | 角色适配数据 | `<character type="1">` | 按角色类型分组 |
| `object` | 网格组件 | `<object>` | 3D模型组件，最多5个 |
| `type` | 网格类型 | `<type>normal</type>` | normal/fskin/uskin/lskin |
| `mesh` | SMD模型文件 | `<mesh>res764\xxx.smd</mesh>` | 骨骼模型文件 |
| `texture` | 纹理文件 | `<texture>res764\xxx.png</texture>` | 模型纹理图片 |

### 网格类型说明

| 类型值 | 英文 | 中文 | 说明 |
|--------|------|------|------|
| `normal` | Normal | 普通 | 普通道具，独立渲染 |
| `fskin` | Face Skin | 面部皮肤 | 贴合面部皮肤 |
| `uskin` | Upper Skin | 上身皮肤 | 贴合上身皮肤 |
| `lskin` | Lower Skin | 下身皮肤 | 贴合下身皮肤 |

### 角色类型说明

| type值 | 角色类型 |
|--------|----------|
| 1 | 男性角色类型1 |
| 2 | 男性角色类型2 |
| 3 | 男性角色类型3 |
| 4 | 女性角色类型1 |
| 5 | 女性角色类型2 |
| 6 | 女性角色类型3 |

### 道具文件命名规则

**SMD模型文件**:
```
i{道具ID}_{角色类型}_{组件ID}.smd

示例：
- i50125031_MT.smd  - 男性角色T（可能是Main/Top）
- i50125031_ms.smd  - 男性角色s（可能是secondary/副模型）
- i50125031_MN.smd  - 男性角色N
- i50125031_MF.smd  - 男性角色F（可能是Fat）
- i50125031_FT.smd  - 女性角色T
- i50125031_FS.smd  - 女性角色S
- i50125031_FN.smd  - 女性角色N
```

**纹理文件**:
```
i{道具ID}.png
或
i{道具ID}_M.png  - 男性纹理
i{道具ID}_F.png  - 女性纹理
```

## BML文件解码工具

### Python实现（bml_decoder.py）

```python
def decode_bml(bml_path, output_xml_path=None):
    """解码BML文件为XML文件"""
    if output_xml_path is None:
        import os
        base_name = os.path.splitext(bml_path)[0]
        output_xml_path = base_name + '.xml'

    # 读取BML文件
    with open(bml_path, 'rb') as f:
        bml_data = f.read()

    # 解码：每个字节与0xFF进行XOR运算
    decoded_data = bytearray(len(bml_data))
    for i, byte in enumerate(bml_data):
        decoded_data[i] = byte ^ 0xFF

    # 写入XML文件
    with open(output_xml_path, 'wb') as f:
        f.write(decoded_data)

    return output_xml_path
```

### 使用方法

```bash
# 解码BML文件
python bml_decoder.py i50125001.bml

# 编码XML为BML文件
python bml_decoder.py i50125001.xml --encode
```

## 重要发现：BML中不包含物理参数

### 关键结论

通过分析XML结构，**BML文件只包含基本信息**：

1. ✅ channel信息（装备位掩码）
2. ✅ object类型（normal/fskin/uskin/lskin）
3. ✅ mesh文件（SMD模型路径）
4. ✅ texture文件（纹理路径）

**没有包含**：
- ❌ 物理模拟参数（重力、弹性、阻尼等）
- ❌ 骨骼绑定信息
- ❌ 动态效果标志位
- ❌ 物理模拟开关

### 推论

**物理模拟参数存储位置**：

1. **最可能**：SMD模型文件内部
   - SMD文件包含骨骼数据
   - 可能包含物理模拟参数

2. **可能**：外部配置文件
   - 单独的物理配置文件
   - 按道具ID或文件名映射

3. **可能**：游戏引擎硬编码
   - 某些道具ID被标记为动态
   - 在代码中硬编码配置

## 下一步研究方向

### 方向1：分析SMD模型文件（推荐）

**目标**：
- 解析SMD文件格式
- 对比动态发型和静态发型的SMD文件
- 查找物理模拟参数

**工具**：
- 十六进制编辑器
- SMD文件分析脚本
- 模型查看工具（如Blender）

### 方向2：搜索配置文件

**目标**：
- 搜索所有pak包中的配置文件
- 查找包含"physics"、"dynamic"关键词的文件
- 搜索道具ID配置文件

### 方向3：分析SMD加载代码

**目标**：
- 查找`DGraphicAcquireSMD`函数实现
- 理解SMD文件如何被加载
- 查找物理模拟参数如何被设置

**源代码位置**：
```
Scud/Graphic/Graphic.cpp
Scud/Graphic/Graphic.h
```

### 方向4：逆向分析游戏运行时

**目标**：
- 使用调试器追踪道具加载过程
- 观察动态发型和静态发型在加载时的差异
- 查找物理模拟参数的设置时机

## 总结

### BML文件格式总结

1. **本质**：XML文件（可能XOR加密）
2. **结构**：`root -> channel -> character[type] -> object[type, mesh, texture]`
3. **用途**：定义道具的基本信息和资源路径
4. **限制**：不包含物理模拟参数

### 动态发型功能研究现状

| 研究方向 | 状态 | 结论 |
|----------|------|------|
| BML文件字节级分析 | ❌ 已失败 | 无法通过修改BML实现动态效果 |
| BML文件XML结构分析 | ✅ 已完成 | BML不包含物理参数 |
| SMD模型文件分析 | 🔄 待开始 | **最可能的方向** |
| 外部配置文件搜索 | 🔄 待开始 | 可能发现物理配置 |
| 源代码物理系统分析 | 🔄 待开始 | 需要深入研究 |

### 核心发现

**BML解码只是第一步**：
- ✅ 成功解码BML为XML
- ✅ 理解了BML的完整结构
- ❌ 但BML中不包含物理参数

**真正的突破口在于SMD模型文件**：
- 物理模拟参数最可能存储在SMD文件中
- 需要深入分析SMD文件格式
- 可能需要找到或开发SMD编辑工具

---

**文档创建时间**: 2026-02-09
**文档状态**: 已完成BML分析，下一步分析SMD
**下一步**: 研究SMD模型文件格式和加载代码
