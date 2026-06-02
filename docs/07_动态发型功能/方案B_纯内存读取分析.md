# 方案B：纯内存读取定位失败原因

## 核心思路

不 attach 调试器（不触发 Apollo），用 `OpenProcess` + `ReadProcessMemory` 读取游戏进程内存。通过已知字符串地址定位关键函数，搞清楚动态发型 SMD 加载失败的**确切原因**。

## 为什么需要这一步

方案A（SMD注入）假设失败原因是"角色骨骼树缺少物理骨骼"。但这只是推测，实际可能是：
1. AcquireSMD 读取 SSKF 文件时就失败了（格式校验不通过）
2. 骨骼数量超限
3. 文件名大小写问题（BML 写 `i50125031_MT.smd`，pak 里可能是小写）
4. 跨 pak 引用问题（角色在 item767，SMD 在 res764）
5. CtrlPoints 骨骼名不匹配

**不知道确切原因就盲目修改 SMD，可能白费功夫。**

## 实施步骤

### 第1步：用 Python 连接游戏进程读内存

```python
import ctypes
from ctypes import wintypes

kernel32 = ctypes.windll.kernel32

PROCESS_VM_READ = 0x0010
PROCESS_QUERY_INFORMATION = 0x0400

def read_memory(pid, address, size):
    handle = kernel32.OpenProcess(
        PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, 
        False, pid
    )
    buf = ctypes.create_string_buffer(size)
    bytesRead = ctypes.c_size_t()
    kernel32.ReadProcessMemory(
        handle, ctypes.c_void_p(address), 
        buf, size, ctypes.byref(bytesRead)
    )
    kernel32.CloseHandle(handle)
    return buf.raw
```

这不会触发 Apollo——`ReadProcessMemory` 走的是 `NtReadVirtualMemory`，不在 Apollo 监控的调试 API 链上。

### 第2步：定位关键函数

已知字符串地址（来自调试总结）：

| 地址 | 字符串 | 用途 |
|------|--------|------|
| `0x28405CC` | `"strSMD is none in AcquireSMD(SFullName) = [%s]"` | AcquireSMD 失败时的日志 |
| `0x283F732` | `"HB ExitPhysics()"` | 物理系统退出 |

**操作**：
1. 在代码段 (`0x401000 - 0x2C00000`) 搜索引用 `0x28405CC` 的指令
2. 搜索模式：`push 0x28405CC`（x86 传参通常是 push 地址）
3. 找到引用点 → 往前回溯就是 AcquireSMD 函数体
4. 读函数体分析分支逻辑

### 第3步：定位 AttachSMD 中的骨骼查找逻辑

AttachSMD 核心逻辑（来自源码）：
```cpp
// 遍历 CtrlPoints
for(nCPoint=0; nCPoint<pObject->CtrlPoints.Num(); ++nCPoint) {
    if(pCPoint->ParentBone < 0)
        AddCtrlPointGrp(name, pos, quat, NONE);
    else
        AddCtrlPointGrp(name, pos, quat, 
            pObject->Skeleton.Bones[pCPoint->ParentBone].Name);
}
```

**操作**：
1. 在内存中搜索 `AddCtrlPointGrp` 相关的字符串引用
2. 或搜索 "GDynamicActor::AttachSMD has invalid handle" 字符串定位 AttachSMD 函数
3. 分析 AddCtrlPointGrp 的实现——当骨骼名找不到时会发生什么？

### 第4步：读游戏运行时的 SMD 数据

当角色装备动态发型时：
1. AcquireSMD 返回的 Handle 指向 DProgressiveMesh 对象
2. 读这个对象的内存：
   - Skeleton.Bones 数组 → 看有哪些骨骼
   - CtrlPoints 数组 → 看控制点引用了哪些骨骼
   - 对比角色基础骨骼 → 找到缺失的骨骼名

### 第5步：定位 DLogWriteSystem 输出

源码里有大量 `DLogWriteSystem` 调用，游戏崩溃日志没价值，但：
1. 找到 DLogWriteSystem 函数实现
2. 看它写到哪个文件/输出目标
3. 可能有非崩溃的日志记录了 AcquireSMD 的失败信息

## 关键难点

| 难点 | 说明 | 解决思路 |
|------|------|---------|
| 代码段已解压但无符号 | 只有裸地址，没有函数名 | 用已知字符串地址做锚点，反向搜索引用 |
| 代码段 ~40MB | 全量搜索耗时 | 缩小范围，只搜索关键字符串附近的引用 |
| 内存中的对象地址不确定 | Handle.pObject 指向哪里需要追踪 | 从 Character.cpp 的全局变量入手 |
| Apollo 虽然不拦截 ReadMemory | 但可能做进程句柄监控 | OpenProcess 用最小权限 |

## 风险

- **低**：ReadProcessMemory 不触发 Apollo 反调试链
- **中等**：代码段没有符号，需要靠字符串锚点定位，可能找不到
- **中等**：即使找到失败原因，可能需要配合方案A或方案C才能解决

## 优势

- **最安全**：完全绕开 Apollo
- **能确定根本原因**：不再猜测，用数据说话
- 为方案A和方案C提供精确的技术指导

## 与其他方案的关系

方案B 是**诊断手段**，不是最终解决方案。它告诉你"为什么失败"，然后：
- 如果是骨骼缺失 → 回到方案A（注入骨骼到SMD）
- 如果是函数级校验 → 走方案C（Hook绕过）
- 如果是文件路径问题 → 直接修BML路径即可解决
