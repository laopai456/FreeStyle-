# 阶段三：VEH 异常捕获方案

> 目标：当硬件断点命中时，捕获 #DB 异常，记录寄存器快照，让线程继续运行。
>
> 思路：向目标进程注入一个 DLL，注册 VectoredExceptionHandler 来接管 STATUS_SINGLE_STEP。
>
> Apollo 拦截的是 `SetThreadContext` / `WaitForDebugEvent` 这类调试 API，但不管 VEH——VEH 是进程内部异常分发的正常路径。

> **⚠️ 2025-07-04 实测修正：** 共享内存名不能用 `Global\` 前缀。目标进程（非管理员）没有 SeCreateGlobalPrivilege，`CreateFileMappingW` 会静默失败，DLL 虽加载但共享内存不可用。已改为 session-local 名 `HwBpVEHSharedMem`，Python 客户端同步。

---

## 一、整体架构

```
FreeStyle.exe (目标进程)
┌─────────────────────────────────────────┐
│                                         │
│  VEH_Hook.dll (注入的 DLL)               │
│    ├── DllMain → AddVectoredExceptionHandler   │
│    ├── VexHandler ← 捕获 STATUS_SINGLE_STEP    │
│    └── 写入共享内存                             │
│                                         │
├─────────────────────────────────────────┤
│  HwBpDriver.sys (内核驱动)              │
│    └── 设置 DR 寄存器到各线程             │
└─────────────────────────────────────────┘
        ▲                        ▲
        │ IOCTL                  │ 读取共享内存
        ▼                        ▼
┌─────────────────────────────────────────┐
│  Python 客户端                           │
│    ├── 发送 IOCTL_SET_BP                │
│    └── 读取共享内存获取断点命中记录        │
└─────────────────────────────────────────┘
```

---

## 二、开发 VEH DLL

### 2.1 项目结构

```
veh_hook/
├── veh_hook.c         ← DLL 主代码
├── veh_hook.def       ← 导出定义（可选）
└── compile_dll.ps1    ← 编译脚本
```

### 2.2 DLL 代码

[veh_hook.c](file:///D:\py\反编译\FreeStyle\apollo_dump\veh_hook\veh_hook.c)

```c
#include <windows.h>
#include <intrin.h>

#pragma warning(disable: 4100 4201)

#define MAX_HIT_RECORDS 200

#pragma pack(push, 1)
typedef struct _BP_HIT_INFO {
    ULONG HitCount;
    ULONG64 TriggerAddress;
    ULONG64 HitAddress;
    ULONG DrIndex;
    ULONGLONG Timestamp;
    ULONG ThreadId;
    ULONG64 Rax;
    ULONG64 Rbx;
    ULONG64 Rcx;
    ULONG64 Rdx;
    ULONG64 Rbp;
    ULONG64 Rsp;
    ULONG64 Rsi;
    ULONG64 Rdi;
    ULONG64 R8;
    ULONG64 R9;
} BP_HIT_INFO, *PBP_HIT_INFO;

typedef struct _SHARED_HIT_DATA {
    volatile LONG HitCount;
    BP_HIT_INFO Records[MAX_HIT_RECORDS];
    volatile LONG Initialized;
} SHARED_HIT_DATA, *PSHARED_HIT_DATA;
#pragma pack(pop)

// ⚠️ 不能用 Global\ 前缀，目标进程非管理员时 CreateFileMappingW 会静默失败
#define SHARED_MEM_NAME L"HwBpVEHSharedMem"
#define VEH_BP_INFO_SIZE sizeof(BP_HIT_INFO)
#define SHARED_DATA_SIZE sizeof(SHARED_HIT_DATA)

PSHARED_HIT_DATA g_SharedData = NULL;
HANDLE g_SharedFile = NULL;
PVOID g_VeHandle = NULL;
CRITICAL_SECTION g_Cs;

LONG WINAPI VexHandler(PEXCEPTION_POINTERS ExceptionInfo) {
    PEXCEPTION_RECORD er = ExceptionInfo->ExceptionRecord;
    PCONTEXT ctx = ExceptionInfo->ContextRecord;

    if (er->ExceptionCode != STATUS_SINGLE_STEP &&
        er->ExceptionCode != STATUS_BREAKPOINT) {
        return EXCEPTION_CONTINUE_SEARCH;
    }

    if (!g_SharedData) return EXCEPTION_CONTINUE_SEARCH;

    EnterCriticalSection(&g_Cs);

    LONG idx = g_SharedData->HitCount;
    if (idx < MAX_HIT_RECORDS) {
        PBP_HIT_INFO info = &g_SharedData->Records[idx];
        info->HitCount = idx + 1;
        info->TriggerAddress = er->ExceptionAddress;
        info->HitAddress = er->ExceptionInformation[1];
        info->DrIndex = ctx->Dr6 & 0xF;
        info->Timestamp = GetTickCount64();
        info->ThreadId = GetCurrentThreadId();
        info->Rax = ctx->Rax;
        info->Rbx = ctx->Rbx;
        info->Rcx = ctx->Rcx;
        info->Rdx = ctx->Rdx;
        info->Rbp = ctx->Rbp;
        info->Rsp = ctx->Rsp;
        info->Rsi = ctx->Rsi;
        info->Rdi = ctx->Rdi;
        info->R8 = ctx->R8;
        info->R9 = ctx->R9;

        g_SharedData->HitCount = idx + 1;
    }

    LeaveCriticalSection(&g_Cs);

    ctx->Dr6 = 0;

    return EXCEPTION_CONTINUE_EXECUTION;
}

BOOL InitSharedMemory() {
    g_SharedFile = CreateFileMappingW(
        INVALID_HANDLE_VALUE, NULL,
        PAGE_READWRITE, 0, SHARED_DATA_SIZE,
        SHARED_MEM_NAME
    );
    if (!g_SharedFile) return FALSE;

    g_SharedData = (PSHARED_HIT_DATA)MapViewOfFile(
        g_SharedFile, FILE_MAP_ALL_ACCESS, 0, 0, SHARED_DATA_SIZE
    );
    if (!g_SharedData) {
        CloseHandle(g_SharedFile);
        g_SharedFile = NULL;
        return FALSE;
    }

    g_SharedData->HitCount = 0;
    g_SharedData->Initialized = 1;

    return TRUE;
}

BOOL APIENTRY DllMain(HMODULE hModule, DWORD reason, LPVOID lpReserved) {
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(hModule);
        InitializeCriticalSection(&g_Cs);

        if (!InitSharedMemory()) return TRUE;

        g_VeHandle = AddVectoredExceptionHandler(1, VexHandler);
        if (g_VeHandle) {
            OutputDebugStringW(L"[VEH_Hook] VEH registered OK");
        } else {
            OutputDebugStringW(L"[VEH_Hook] VEH register FAILED");
        }
    } else if (reason == DLL_PROCESS_DETACH) {
        if (g_VeHandle) RemoveVectoredExceptionHandler(g_VeHandle);
        if (g_SharedData) UnmapViewOfFile(g_SharedData);
        if (g_SharedFile) CloseHandle(g_SharedFile);
        DeleteCriticalSection(&g_Cs);
    }
    return TRUE;
}
```

### 2.3 编译脚本

[compile_dll.ps1](file:///D:\py\反编译\FreeStyle\apollo_dump\veh_hook\compile_dll.ps1)

```powershell
# compile_dll.ps1
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$VS = "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools"
$MSVC = Get-ChildItem "$VS\VC\Tools\MSVC" -Directory | Sort-Object Name -Descending | Select-Object -First 1
$cl = "$MSVC\bin\Hostx64\x64\cl.exe"
$link = "$MSVC\bin\Hostx64\x64\link.exe"
$SDK = "C:\Program Files (x86)\Windows Kits\10"
$SDK_VER = "10.0.22621.0"

$OutDir = "$ScriptDir\bin"
New-Object -TypeName System.IO.DirectoryInfo -ArgumentList $OutDir | ForEach-Object { if(!$_.Exists){$_.Create()} }

$IncFlags = "/I`"$SDK\Include\$SDK_VER\um`" /I`"$SDK\Include\$SDK_VER\shared`" /I`"$MSVC\include`""
$LibFlags = "/LIBPATH:`"$SDK\Lib\$SDK_VER\um\x64`" /LIBPATH:`"$MSVC\lib\x64`""

# 编译
& $cl /nologo /c /O1 /Zi /GS- "$ScriptDir\veh_hook.c" /Fo"$OutDir\veh_hook.obj" $IncFlags /D_WIN64 /D_AMD64_ /DWIN32 /D_WINDOWS
if ($LASTEXITCODE -ne 0) { Write-Host "COMPILE FAILED" -ForegroundColor Red; exit 1 }
Write-Host "Compile OK" -ForegroundColor Green

# 链接
& $link /NOLOGO /DLL /MACHINE:X64 /OUT:"$OutDir\veh_hook.dll" "$OutDir\veh_hook.obj" $LibFlags kernel32.lib user32.lib
if ($LASTEXITCODE -ne 0) { Write-Host "LINK FAILED" -ForegroundColor Red; exit 1 }
Write-Host "Link OK" -ForegroundColor Green

if (Test-Path "$OutDir\veh_hook.dll") {
    $size = (Get-Item "$OutDir\veh_hook.dll").Length
    Write-Host "=== BUILD SUCCESS ===" -ForegroundColor Green
    Write-Host "Output: $OutDir\veh_hook.dll ($([math]::Round($size/1024,1)) KB)" -ForegroundColor Cyan
}
```

---

## 三、DLL 注入

### 方法 A：用户态注入（先试这个，简单）

[inject_dll.exe](file:///D:\py\反编译\FreeStyle\apollo_dump\veh_hook\inject_dll.c)

```c
#include <windows.h>
#include <stdio.h>
#include <tlhelp32.h>

DWORD FindProcessId(const wchar_t* name) {
    HANDLE snap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (snap == INVALID_HANDLE_VALUE) return 0;
    PROCESSENTRY32W pe = { sizeof(pe) };
    DWORD pid = 0;
    if (Process32FirstW(snap, &pe)) {
        do {
            if (wcsicmp(pe.szExeFile, name) == 0) { pid = pe.th32ProcessID; break; }
        } while (Process32NextW(snap, &pe));
    }
    CloseHandle(snap);
    return pid;
}

int wmain(int argc, wchar_t* argv[]) {
    if (argc < 3) {
        wprintf(L"Usage: inject_dll.exe <pid> <dll_path>\n");
        wprintf(L"   or: inject_dll.exe /name <process_name> <dll_path>\n");
        return 1;
    }

    DWORD pid;
    wchar_t* dllPath;

    if (wcscmp(argv[1], L"/name") == 0) {
        pid = FindProcessId(argv[2]);
        dllPath = argv[3];
        if (!pid) { wprintf(L"Process not found: %s\n", argv[2]); return 1; }
        wprintf(L"Found PID: %d\n", pid);
    } else {
        pid = _wtoi(argv[1]);
        dllPath = argv[2];
    }

    HANDLE hProcess = OpenProcess(PROCESS_ALL_ACCESS, FALSE, pid);
    if (!hProcess) { wprintf(L"OpenProcess failed: %d\n", GetLastError()); return 1; }

    SIZE_T pathSize = (wcslen(dllPath) + 1) * sizeof(wchar_t);
    PVOID remoteMem = VirtualAllocEx(hProcess, NULL, pathSize, MEM_COMMIT, PAGE_READWRITE);
    if (!remoteMem) { wprintf(L"VirtualAllocEx failed: %d\n", GetLastError()); CloseHandle(hProcess); return 1; }

    WriteProcessMemory(hProcess, remoteMem, dllPath, pathSize, NULL);

    HMODULE kernel32 = GetModuleHandleW(L"kernel32.dll");
    LPTHREAD_START_ROUTINE loadLib = (LPTHREAD_START_ROUTINE)GetProcAddress(kernel32, "LoadLibraryW");

    HANDLE hThread = CreateRemoteThread(hProcess, NULL, 0, loadLib, remoteMem, 0, NULL);
    if (!hThread) {
        wprintf(L"CreateRemoteThread failed: %d\n", GetLastError());
        VirtualFreeEx(hProcess, remoteMem, 0, MEM_RELEASE);
        CloseHandle(hProcess);
        return 1;
    }

    wprintf(L"Injecting... ");
    WaitForSingleObject(hThread, INFINITE);

    DWORD exitCode;
    GetExitThreadCode(hThread, &exitCode);
    if (exitCode != 0) {
        wprintf(L"OK (LoadLibrary returned 0x%x)\n", exitCode);
    } else {
        wprintf(L"FAILED (LoadLibrary returned NULL)\n");
    }

    VirtualFreeEx(hProcess, remoteMem, 0, MEM_RELEASE);
    CloseHandle(hThread);
    CloseHandle(hProcess);
    return 0;
}
```

编译 inject_dll:
```powershell
cl.exe /nologo /O1 inject_dll.c /Feinject_dll.exe kernel32.lib
```

### 方法 B：驱动 APC 注入（方法 A 被 Apollo 拦截时用）

如果 `CreateRemoteThread` 被 Apollo 拦截，就在驱动中添加一个 IOCTL 来注入 DLL。原理：

```
IOCTL_INJECT_DLL
  → AttachToProcess(target_pid)
  → VirtualAllocEx 分配内存（zwAllocateVirtualMemory）
  → 写入 DLL 路径
  → KeInitializeApc + KeInsertQueueApc
  → APC 在目标线程上下文执行 LdrLoadDll
```

> **先用方法 A 试。** Apollo 拦截的是调试相关 API（SetThreadContext、DebugActiveProcess），不一定拦 CreateRemoteThread。如果方法 A 不行，再扩展驱动加 APC 注入。

---

## 四、验证方法

### 验证 1：VehHandler 是否能捕获单步异常（独立测试）

不依赖驱动，先验证 VEH DLL 本身能工作。

**测试程序** [test_veh.c](file:///D:\py\反编译\FreeStyle\apollo_dump\veh_hook\test_veh.c)：

```c
#include <windows.h>
#include <stdio.h>

typedef struct {  // 与 DLL 中的定义一致
    volatile LONG HitCount;
    BYTE Records[200 * 80];  // BP_HIT_INFO * 200
    volatile LONG Initialized;
} SHARED_HIT_DATA;

// ⚠️ 必须与 DLL 中的名字一致（不能用 Global\ 前缀）
#define SHARED_MEM_NAME L"HwBpVEHSharedMem"

int main() {
    // 1. 验证共享内存是否存在
    printf("[1] Checking shared memory...\n");
    HANDLE hMap = OpenFileMappingW(FILE_MAP_READ, FALSE, SHARED_MEM_NAME);
    if (!hMap) {
        printf("    NOT FOUND - VEH DLL not injected yet\n");
        printf("    Run: inject_dll.exe <test_pid> veh_hook.dll\n");
        return 1;
    }

    SHARED_HIT_DATA* data = (SHARED_HIT_DATA*)MapViewOfFile(hMap, FILE_MAP_READ, 0, 0, sizeof(SHARED_HIT_DATA));
    if (!data) { printf("    MapViewOfFile failed: %d\n", GetLastError()); CloseHandle(hMap); return 1; }

    printf("    Found! Initialized=%d\n", data->Initialized);

    // 2. 检查是否有命中记录
    printf("\n[2] Checking hit records...\n");
    LONG count = data->HitCount;
    printf("    HitCount = %d\n", count);

    if (count > 0) {
        printf("\n=== Hit Records ===\n");
        for (LONG i = 0; i < count && i < 10; i++) {
            // 注意：这里简化输出，完整结构需定义 BP_HIT_INFO
            printf("  [%d] triggered at PID=%d\n", i, GetCurrentProcessId());
        }
    }

    UnmapViewOfFile(data);
    CloseHandle(hMap);
    return 0;
}
```

**测试步骤：**

```powershell
# 1. 编译 DLL
cd D:\py\反编译\FreeStyle\apollo_dump\veh_hook
powershell -File compile_dll.ps1

# 2. 启动记事本作为测试目标
notepad.exe
# 记下 PID

# 3. 注入 DLL
inject_dll.exe <notepad_pid> bin\veh_hook.dll
# 输出: Injecting... OK (LoadLibrary returned 0x...)

# 4. 验证共享内存
test_veh.exe
# 输出: Found! Initialized=1, HitCount=0

# 5. 手动触发测试（用 CE 给 notepad 设个断点，或直接跑驱动设断点）
# 然后再次运行 test_veh.exe 看 HitCount 是否增加
```

---

### 验证 2：与驱动联调

**完整测试流程：**

```powershell
# 1. 确保驱动已运行
sc.exe query HwBpDriver
# → STATE: RUNNING

# 2. 启动目标进程（先用 calc.exe 或 notepad.exe 测试，别直接上游戏）
calc.exe

# 3. 注入 VEH DLL
inject_dll.exe /name calc.exe D:\py\反编译\FreeStyle\apollo_dump\veh_hook\bin\veh_hook.dll
# → Injecting... OK

# 4. 打开 Python 客户端
python D:\py\反编译\FreeStyle\apollo_dump\hwbp_driver\hwbp_driver_client.py

# 5. 获取 calc.exe PID → 设置断点
#    找一个 calc.exe 中一定会执行的地址（如 MessageBoxW）
#    或直接用 CE 找一个函数地址

# 6. 触发断点（在 calc 上点按钮等操作）

# 7. 读取共享内存确认是否捕获
test_veh.exe
# → HitCount > 0 表示成功
```

---

### 验证 3：Python 客户端集成读取共享内存

在 [hwbp_driver_client.py](file:///D:\py\反编译\FreeStyle\apollo_dump\hwbp_driver\hwbp_driver_client.py) 中增加直接读共享内存的功能：

```python
import mmap
import ctypes

SHARED_MEM_NAME = "HwBpVEHSharedMem"
SHARED_DATA_SIZE = 4 + 200 * 80 + 4  # 对应 SHARED_HIT_DATA

class BPHitInfo(ctypes.Structure):
    _fields_ = [
        ("HitCount", ctypes.c_uint32),
        ("TriggerAddress", ctypes.c_uint64),
        ("HitAddress", ctypes.c_uint64),
        ("DrIndex", ctypes.c_uint32),
        ("Timestamp", ctypes.c_uint64),
        ("ThreadId", ctypes.c_uint32),
        ("Rax", ctypes.c_uint64),
        ("Rbx", ctypes.c_uint64),
        ("Rcx", ctypes.c_uint64),
        ("Rdx", ctypes.c_uint64),
        ("Rbp", ctypes.c_uint64),
        ("Rsp", ctypes.c_uint64),
        ("Rsi", ctypes.c_uint64),
        ("Rdi", ctypes.c_uint64),
        ("R8", ctypes.c_uint64),
        ("R9", ctypes.c_uint64),
    ]

def read_veh_hits():
    try:
        mmf = mmap.mmap(-1, SHARED_DATA_SIZE, SHARED_MEM_NAME)
        hit_count = ctypes.c_uint32.from_buffer(mmf, 0)
        print(f"VEH HitCount: {hit_count.value}")
        if hit_count.value > 0:
            for i in range(min(hit_count.value, 10)):
                offset = 4 + i * ctypes.sizeof(BPHitInfo)
                info = BPHitInfo.from_buffer(mmf, offset)
                print(f"  [{i}] RIP=0x{info.TriggerAddress:016x} "
                      f"Thread={info.ThreadId} "
                      f"DR{info.DrIndex}")
        mmf.close()
    except Exception as e:
        print(f"Shared memory not available: {e}")
        print("VEH DLL may not be injected yet")
```

---

## 五、如果注入失败怎么办

| 现象 | 原因 | 解决 |
|------|------|------|
| `OpenProcess` 拒绝访问 | 权限不够 | 以管理员身份运行 |
| `CreateRemoteThread` 返回 5 (拒绝访问) | Apollo 拦截了远程线程创建 | 换方法 B：驱动 APC 注入 |
| `LoadLibrary` 返回 NULL | DLL 依赖问题 | 检查 DLL 是否在目标可访问的路径，用 Dependency Walker 检查依赖 |
| VEH 注册成功但断点不触发 | 断点没设对 | 确认驱动确实写入了 DR 寄存器（驱动有回读验证） |
| VEH 触发但进程崩溃 | VEH 返回了错误值 | 确认 VEH 返回 `EXCEPTION_CONTINUE_EXECUTION`，确认清空了 Dr6 |

---

## 六、方案优劣总结

```
VEH 注入方案
├── 优点
│   ├── 不需要内核异常回调（避免蓝屏风险）
│   ├── Apollo 不管 VEH（管的是调试器路径）
│   ├── 实现简单 ≈ 100 行代码
│   └── 崩溃只影响目标进程，不会蓝屏
│
└── 缺点
    ├── 需要注入 DLL（可能被检测）
    ├── VEH 在用户态，可能被 L2 的扫描发现
    └── 共享内存通信相对脆弱
```

如果 VEH 方案被 Apollo 检测到（概率较低），再退回到内核异常回调方案（KeRegisterExceptionCallback 等）。

---

## 七、验证检查清单

```
□ DLL 编译通过（veh_hook.dll）
□ DLL 注入进测试进程（notepad / calc）
□ test_veh 能读到共享内存（Initialized=1）
□ 驱动设置断点到测试进程
□ VEH 捕获到断点（HitCount > 0）
□ Python 客户端能通过共享内存读取命中记录
□ 目标进程在断点触发后没有崩溃
□ 在 FreeStyle.exe 上复现以上全部步骤
```