# 方案C：DLL注入运行时 Hook

## 核心思路

写一个 DLL 注入到游戏进程中，Hook 关键函数，在运行时**动态创建缺失的物理骨骼**。当游戏加载动态发型 SMD 并尝试 AttachSMD 时，Hook 拦截骨骼查找逻辑，让它在角色骨骼树中"凭空出现" Bone01-11。

## 问题根因

```
AttachSMD → CtrlPoints[i].ParentBone → Skeleton.Bones[index].Name
→ AddCtrlPointGrp(name, pos, quat, boneName)
→ 在角色骨骼树中查找 boneName → 找不到 Bone01 → 失败
```

如果我们在 `AddCtrlPointGrp` 里做手脚：当查找 Bone01-11 失败时，自动创建这些骨骼并插入角色骨骼树，就能让 AttachSMD 成功。

## 实施步骤

### 第1步：定位目标函数

用方案B的内存读取方法，找到以下函数在当前版本游戏中的地址：

| 函数 | 定位方法 |
|------|---------|
| `AddCtrlPointGrp` | 搜索 "GDynamicActor::AttachSMD has invalid handle" 字符串 → 定位 AttachSMD → 内部调用就是 AddCtrlPointGrp |
| `DActor::AssignSkel` | 搜索 "DActor::AssignSkel" 日志字符串 |
| `DActor::BuildBoneIndex` | 在 AssignSkel 附近查找 |

或者用更简单的方法：
- 搜索 `apolloct.dll` 以外的所有内存区域
- 用模式匹配找函数序言（`push ebp; mov ebp, esp`）

### 第2步：编写 Hook DLL

```cpp
// hook.dll - 简化逻辑

// 原始 AddCtrlPointGrp 函数指针
typedef bool (*fn_AddCtrlPointGrp)(void* thisPtr, SName name, SVector pos, SQuat quat, SName boneName);
fn_AddCtrlPointGrp original_AddCtrlPointGrp = NULL;

// Hook 后的 AddCtrlPointGrp
bool hooked_AddCtrlPointGrp(void* thisPtr, SName name, SVector pos, SQuat quat, SName boneName) {
    // 调用原始函数
    bool result = original_AddCtrlPointGrp(thisPtr, name, pos, quat, boneName);
    
    if (!result && boneName != NONE) {
        // 骨骼查找失败 → 可能是物理骨骼不存在
        // 检查 boneName 是否以 "Bone" 开头
        const char* boneStr = boneName.GetString();
        if (strncmp(boneStr, "Bone", 4) == 0) {
            // 动态创建骨骼并插入角色骨骼树
            InjectPhysicsBone(thisPtr, boneName);
            // 重试
            result = original_AddCtrlPointGrp(thisPtr, name, pos, quat, boneName);
        }
    }
    return result;
}

BOOL APIENTRY DllMain(HMODULE hModule, DWORD reason, LPVOID) {
    if (reason == DLL_PROCESS_ATTACH) {
        // 1. 定位 AddCtrlPointGrp 地址
        // 2. 用 MinHook / Detours 安装 Hook
        InstallHook(ADDCTRLPOINT_ADDR, hooked_AddCtrlPointGrp, &original_AddCtrlPointGrp);
    }
}
```

### 第3步：注入方式

有两种注入方式：

**方式1：CreateRemoteThread 注入**
```python
import ctypes
kernel32 = ctypes.windll.kernel32

pid = 找到 FreeStyle.exe 的 PID
handle = kernel32.OpenProcess(0x1F0FFF, False, pid)  # PROCESS_ALL_ACCESS

# 分配内存写入 DLL 路径
path_addr = kernel32.VirtualAllocEx(handle, 0, len(dll_path), 0x3000, 0x40)
kernel32.WriteProcessMemory(handle, path_addr, dll_path, len(dll_path), None)

# CreateRemoteThread 调用 LoadLibrary
loadlib = kernel32.GetProcAddress(kernel32.GetModuleHandleA("kernel32.dll"), b"LoadLibraryA")
kernel32.CreateRemoteThread(handle, None, 0, loadlib, path_addr, 0, None)
```

**方式2：注册表 AppInit_DLLs（持久化）**
```
HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Windows\AppInit_DLLs
```
游戏启动时自动加载 DLL。

### 第4步：Hook 策略

| Hook 点 | 目的 |
|---------|------|
| `AddCtrlPointGrp` | 当骨骼查找失败时动态注入物理骨骼 |
| `DActor::AssignSkel` | 在角色骨骼赋值时追加物理骨骼到骨骼数组 |
| `AcquireSMD` 返回值检查 | 确保 Handle 有效 |

## 关键难点

| 难点 | 说明 | 解决思路 |
|------|------|---------|
| 定位函数地址 | 没有符号表 | 用方案B的字符串锚点法 |
| Apollo 可能监控 DLL 注入 | CreateRemoteThread 可能被拦截 | 改用注册表方式，或用 Process Hollowing |
| SName 字符串比较 | 引擎内部的 SName 可能是 hash 比较而非字符串比较 | 需要确认 SName 的内存布局 |
| 物理骨骼的初始数据 | 不知道 Bone01-11 的初始 Pos/Quat 值 | 从动态发型 SMD 文件中提取 |
| 反作弊完整性校验 | Apollo 可能检测代码段被修改 | 用硬件断点 Hook 或 VEH Hook 代替 Inline Hook |

## 风险

- **高**：Apollo 反作弊可能检测 DLL 注入行为
- **高**：Inline Hook 修改代码段可能被完整性校验发现
- **中等**：函数地址在不同版本游戏中会变，每次更新都要重新定位
- **高**：可能导致封号

## 优势

- **最直接**：直接在运行时解决问题，不需要修改任何文件
- **最灵活**：可以动态调整，实时测试
- 可以让任意角色穿任意发型

## 降低风险的变体

### 变体C1：不注入 DLL，用外部进程操控

不注入 DLL 到游戏进程，而是用外部 Python 进程：
1. `ReadProcessMemory` 读取角色骨骼数据
2. `WriteProcessMemory` 直接往骨骼数组里写入 Bone01-11
3. 然后触发发型切换

这样没有任何 DLL 在游戏内部，降低被检测风险。

### 变体C2：修改游戏的 pak 文件中的角色骨骼定义

角色的基础骨骼可能定义在某个 pak 里的配置文件中（不是 SMD）。如果能找到这个文件，直接把 Bone01-11 加进去，就不需要运行时 Hook。

## 与其他方案的关系

```
方案B（诊断）→ 确定失败原因
  ├── 原因是骨骼缺失 → 方案A（改SMD文件）或 方案C（运行时注入骨骼）
  ├── 原因是文件路径 → 直接修BML
  └── 原因是函数校验 → 方案C（Hook绕过）
```
