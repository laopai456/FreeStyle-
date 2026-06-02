---
name: "memory-patch"
description: "FreeStyle 游戏内存补丁助手。当用户需要修改游戏运行时内存、WriteProcessMemory、堆数据修改、Code Cave注入、CreateRemoteThread时调用此技能。"
auto_load: true
---

# FreeStyle 内存补丁助手

## 核心约束

### APOLLO 反作弊限制

| 禁止的操作 | 允许的操作 |
|-----------|-----------|
| ❌ 修改代码段（.text） | ✅ 只修改堆上数据字段 |
| ❌ 附加调试器（x64dbg attach） | ✅ Python OpenProcess + Read/WriteProcessMemory |
| ❌ 大范围频繁内存扫描 | ✅ 精确扫描、快速完成 |

### 安全的补丁方式

```
✅ WriteProcessMemory 写入堆内存（Heap） → APOLLO 不检测
❌ WriteProcessMemory 写入代码段（.text） → APOLLO 检测 CRC → 杀进程
⚠️ Code Cave 在堆上分配内存写入代码 → 需验证 APOLLO 是否扫描
```

## 内存布局

| 区域 | 范围 | 说明 |
|------|------|------|
| 游戏基址 | 0x400000 | PE 基址 |
| 代码段 | 0x401000 - 0x2C00000 | ~40MB，运行时已解压 |
| APOLLO | 0x2C00000 - 0x2CDA000 | 反作弊模块 |
| d9winglib.dll | 0x3430000 - 0x3460000 | |
| d3dx9_30.dll | 0x34C0000 - 0x3710000 | |
| wingman.dll | 0x3760000 - 0x37D8000 | |
| d3d8.dll | 0x3850000 - 0x3902000 | |

## 补丁方案记录

### 方案 1：Code Cave 注入（已被 APOLLO 杀）

- 写入 `.text` 段 → APOLLO CRC 检测 → 杀进程
- 工具：`dynamic_hair_patch.py`, `dynamic_hair_patch_v2.py`

### 方案 3：纯数据补丁（安全但找不到对象）

- 只修改堆数据 → 安全
- 但堆上不存在 DStaticActor/DDynamicActor 对象
- 工具：`apollo_kill_patch.py`

### 方案 5：Code Cave + DynamicInit 调用（切换频道崩溃）

- 补丁位置：DStaticActor 构造函数 0x236B998
- 崩溃原因：DStaticActor 和 DDynamicActor 基类构造不同
- 工具：`dynamic_hair_patch.py`（最新版）

## Python 补丁模板

```python
import ctypes
import struct

kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_VM_OPERATION = 0x0008
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_CREATE_THREAD = 0x0002

def open_process(pid):
    access = PROCESS_VM_READ | PROCESS_VM_WRITE | PROCESS_VM_OPERATION | PROCESS_QUERY_INFORMATION | PROCESS_CREATE_THREAD
    h = kernel32.OpenProcess(access, False, pid)
    if not h:
        raise RuntimeError(f"OpenProcess failed: {ctypes.get_last_error()}")
    return h

def read_mem(handle, addr, size):
    buf = ctypes.create_string_buffer(size)
    read = ctypes.c_size_t()
    kernel32.ReadProcessMemory(handle, ctypes.c_void_p(addr), buf, size, ctypes.byref(read))
    return buf.raw

def write_mem(handle, addr, data):
    written = ctypes.c_size_t()
    return kernel32.WriteProcessMemory(handle, ctypes.c_void_p(addr), data, len(data), ctypes.byref(written))
```

## 下一步方向

### 优先级 1：修复 Code Cave 崩溃

- [ ] 对比 DStaticActor 基类构造(0x0236B9F0) vs DDynamicActor 基类构造(0x02299BD0)
- [ ] 尝试保守方案：只替换 vtable 不调用 DynamicInit
- [ ] 尝试延迟补丁：在对象完全构造后修改

### 优先级 2：备选方案

- [ ] Hook 工厂函数(0x021C1F00)，替换创建的对象类型
- [ ] Hook CharacterMotion 解析(0x21B46E0)，修改 Type 值
- [ ] Hook SetMotionType(0x02297810)，强制写入 Dynamic 类型

## 可用脚本

| 脚本 | 功能 |
|------|------|
| `dynamic_hair_patch.py` | Code Cave 补丁（最新） |
| `dynamic_hair_patch_v2.py` | Code Cave + 调试反馈 |
| `apollo_kill_patch.py` | 纯数据补丁（v5） |
| `auto_patch_v4.py` | 自动等待进程 + 补丁 |
| `scan_dynamic.py` | 内存扫描/对比工具 |
| `verify_game.py` | 验证游戏内存布局 |
| `mem_reader.py` | 纯内存读取工具 |
