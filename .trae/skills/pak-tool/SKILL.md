---
name: "pak-tool"
description: "FreeStyle 游戏 PAK 文件操作助手。当用户需要解包/打包 PAK 文件、修改 BML、替换 SMD、验证 PAK 完整性时调用此技能。"
auto_load: true
---

# FreeStyle PAK 文件操作助手

## 文件格式

### PGFN Pak 格式

- 魔数：`PGFN`
- item pak 和 res pak 都是此格式
- 块结构：`[16字节头部][null结尾文件名][加密数据]`
  - 头部[+0x00]：文件名长度
  - 头部[+0x04]：数据起始偏移
  - 头部[+0x08]：数据大小
  - 头部[+0x0C]：下一块偏移
- 块之间通过 next_block 指针链接

### BML 文件格式

- XOR 0xFF 加密的 XML
- 解密：每个字节 ^ 0xFF
- 包含 mesh 路径（SMD）和 texture 路径（PNG）

### SMD/SSKF 文件格式

- 魔数：`SSKF`，版本 `01 00 00 00`
- 静态发型：~44 个标准 Bip01 骨骼，~919KB
- 动态发型：额外包含 Bone01-Bone11 物理骨骼（共~55个），~353KB

## 可用工具

| 工具 | 命令 | 说明 |
|------|------|------|
| resources.exe | `pack\resources <pak路径> -all` | 解包 PAK |
| resources.exe | `pack\resources -file2pak "<目录>" "<pak路径>"` | 打包 PAK |
| repack_pak.py | `py repack_pak.py --pak <path> --verify` | 验证 PAK |
| repack_pak.py | `py repack_pak.py --pak <path> --list` | 列出文件 |
| repack_pak.py | `py repack_pak.py --pak <path> --file <name> --checksum` | 查看文件 MD5 |
| repack_pak.py | `py repack_pak.py --pak <path> --file <name> --input <file> --mode rebuild` | 替换文件 |
| inject_physics_bones.py | `py inject_physics_bones.py` | 注入物理骨骼 |
| sskf_tool.py | `py sskf_tool.py` | SSKF 解析工具 |

## 标准操作流程（SOP）

### 阶段 0：准备

- 确认原始 PAK 已备份（`.bak` 存在）
- 确认 PAK 可打开：`py repack_pak.py --pak <path> --list`
- 记录原始 PAK 的 MD5

### 阶段 1：注入物理骨骼

```powershell
cd /d d:\py\反编译\FreeStyle
py inject_physics_bones.py
```

验证项：骨骼总数=75、Bip01 Head children=2、16个物理骨骼名匹配、Round-trip 通过

### 阶段 2：PAK 打包前验证

```powershell
py repack_pak.py --pak "<pak_path>" --verify
py repack_pak.py --pak "<pak_path>" --file i50125001_MT.smd --checksum
```

### 阶段 3：打包

```powershell
# Dry-run 预览
py repack_pak.py --pak "<pak_path>" --file i50125001_MT.smd --input "<注入文件>" --mode rebuild --dry-run

# 实际替换
py repack_pak.py --pak "<pak_path>" --file i50125001_MT.smd --input "<注入文件>" --mode rebuild
```

### 阶段 4：部署

```powershell
py repack_pak.py --pak "<游戏目录>\res764.pak" --compare "<打包产物>"
copy "<打包产物>" "<游戏目录>\res764.pak"
```

### 阶段 5：游戏内测试

装备目标发型，检查：不崩溃、不光头、有物理效果

### 回滚

```powershell
copy "<游戏目录>\res764.pak.bak" "<游戏目录>\res764.pak"
```

## 关键文件位置

| 文件 | 位置 |
|------|------|
| 道具数据 | `cookies\item_text_pak\itemshop.txt` |
| PAK 文件 | `cookies\item764.pak`, `cookies\res764.pak` 等 |
| SMD 工作目录 | `cookies\res764_smd\` |
| 解包工具 | `pack\resources.exe` |

## 已验证的结论

- BML 替换（等大）→ 游戏不崩溃但发型不显示（光头）
- SMD 骨骼注入 → 发型正常显示但**无物理效果**
- 物理效果由运行时对象类型决定，不是由 SMD 骨骼驱动
