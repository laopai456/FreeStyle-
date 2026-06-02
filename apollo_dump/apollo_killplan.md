# Apollo 全盘拆除计划 — 为所欲为方案

> 目标: 完全解除 Apollo 全部4层保护，恢复游戏 .text 段读写权限，
>       使 Interceptor.attach、硬件断点、x32dbg 全部可用。

---

## 一、Apollo 保护架构 (诊断更新版 2026-05-22)

```
L0: Apollo.sys 内核驱动
    ├── KdDisableDebugger / DR清零 / CR0.WP / out 0x64,0xFE
    ├── PsSetCreateThreadNotify / PsSetLoadImageNotify
    └── DeviceIoControl(\\.\ApolloProtect)
    状态: sc stop 可停 ✅ （实际: 停服后 ApolloCT 仍加载但0线程）

L1: ApolloCT.dll 用户态 (6.7MB, VMProtect)
    ├── CRC32 patch ✓ (0x1A3C54, 0x1BE222)
    ├── 保护线程 → 定时扫描 .text 页属性
    └── 状态: **0 保护线程! DLL仅加载, 不运行**
    结论: L1 已死, 不需要欺骗

L2: FreeStyle.exe 内嵌 Apollo (ApolloShell)
    ├── 启动时解密 .text (40MB) → 设 ER
    ├── 内建反调试 (PEB/NtQIP/INT3扫描/rdtsc等)
    └── 状态: **x32dbg 附加仍被阻 — 根源在此** ⚠️

L3: 游戏 .text (40MB, ER)
    └── L1已死, 页属性随便改
```

---

## 二、诊断发现 (2026-05-22 实测)

通过 Frida 注入后 `diagnose()` 输出:

```
[DIAG] ApolloCT.dll: 已加载 @ 0x69000000 (7045120 bytes)
[DIAG] 总线程数: 38
[DIAG] ApolloCT 线程数: 0 （保护线程不存在!）
[DIAG] L2 线程数: 0
```

**关键结论**: ApolloCT 保护已死, 阻挡 x32dbg 的是 FreeStyle.exe 本身内建的反调试。

---

## 三、4 Phase 计划 (更新版)

### Phase 1: 停 L0（可选，建议保持开启以减小行为差异）
```powershell
sc stop ApolloProtect
sc config ApolloProtect start=disabled
```

### Phase 2: 绕过 L2 内建反调试（当前核心阻塞）
L2 反调试手段未知, 需 Frida 定位:
1. 用 Frida 逐步关闭已知反调试检测点
2. 每次关一个, 试 x32dbg 附加
3. 直到找到哪个检测导致的崩溃

### Phase 3: 通过 Frida 实现无调试器调试
不用 x32dbg, 用 Frida 的:
- Memory.scan → 搜 SSKF
- Interceptor.attach → hook 函数
- setHardwareBreakpoint → 硬件断点
- Thread.backtrace → 栈回溯

### Phase 4: Hook AcquireSMD → 替换发型

---

## 四、无 x32dbg 的 Frida 调试方案（当前唯一可行方案）

### 问题
x32dbg 附加即崩 → 不能靠调试器

### 方案: Frida 本身就是调试工具

| 调试需求 | Frida 方案 | 示例 |
|---------|-----------|------|
| 搜内存 | Memory.scan | `Memory.scan(base, size, "53 53 4B 46", cb)` 找 SSKF |
| 设断点 | Interceptor.attach | hook 任意函数入口 |
| 硬件断点 | setHardwareBreakpoint | `Process.setHardwareBreakpoint(addr, 'execute')` |
| 读上下文 | Thread.backtrace | 捕获调用栈 |
| 写内存 | addr.writeByteArray | patch 字节 |
| 调用函数 | NativeFunction | 调游戏函数验证 |
| 枚举线程/模块 | Process.enumerateThreads | 监控状态 |

### 步骤: 定位 AcquireSMD 入口

```
Step 1: Memory.scan(.text, "53 53 4B 46") → 找到 SSKF 位置 (已知 0x22ECCD0)
Step 2: 从 0x22ECCD0 往回 0x100 字节, 解析 x86 指令找函数序言 (push ebp / sub esp,XX)
Step 3: 找到序言后, 验证: hook 该地址, 看是否被调用
Step 4: hook 成功后, 拦截 SString 参数, 替换发型 ItemCode
```

### 验证钩子是否成功
```javascript
// 从 SSKF 命中地址往回搜函数序言
var sskfAddr = fsMod.base.add(0x22ECCD0);
// 典型 x86 函数序言: 55 8B EC ... 或 55 89 E5 ...
// 从 sskfAddr 往前读 0x200 字节, 找 0x55 (push ebp)
function findPrologue(endAddr) {
    var scanStart = endAddr.sub(0x200);
    var scanEnd = endAddr;
    // "55" = push ebp (最常用函数序言)
    Memory.scan(scanStart, 0x200, "55", {
        onMatch: function(address, size) {
            // 验证: 下一个常见指令是 8B EC 或 89 E5
            var next = address.add(1).readU8();
            if (next === 0x8B || next === 0x89) {
                send({t: 'DIAG', msg: '!!! 找到函数入口候选: ' + address + ' (push ebp found before SSKF)'});
            }
        },
        onComplete: function() {}
    });
}
```

---

## 五、Apollo 拆除状态总表

| 层 | 组件 | 状态 | 影响 |
|----|------|------|------|
| L0 | Apollo.sys | sc stop 可停 | DR/Debugger 保护消失 |
| L1 | ApolloCT.dll | 0 保护线程 (已死) | 页扫描/CRC 不运行 |
| L2 | FreeStyle.exe 内建 | ⚠️ 未绕过 | x32dbg 附加即崩 |
| L3 | .text 段 | 页属性可自由改 | 无限制 |

---

## 六、命令速查

```powershell
# 停驱动
sc stop ApolloProtect
sc config ApolloProtect start=disabled

# 注入诊断/保护
cd d:\py\反编译\FreeStyle\apollo_dump
py x64dbg_enabler.py

# x32dbg 路径
D:\py\release\x32\x32dbg.exe

# Ghidra 分析
subst X: "d:\py\反编译"
& "X:\ghidra_12.0.1_PUBLIC\support\analyzeHeadless.bat" ^
  "D:\ghidra_projects" "FreeStyleProject" ^
  -process ^
  -scriptPath "C:\Users\w\.ghidra\.ghidra_12.0.1_PUBLIC\Extensions\GhidrAssistMCP\ghidra_scripts" ^
  -preScript GAMCPStartServerScript.java "host=127.0.0.1" "port=8080"
```