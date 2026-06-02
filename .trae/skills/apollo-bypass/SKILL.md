---
name: "apollo-bypass"
description: "APOLLO 反作弊分析与绕过助手。当用户讨论 APOLLO 检测、反调试、CRC校验、需要绕过保护执行操作时调用此技能。"
auto_load: true
---

# APOLLO 反作弊分析与绕过助手

## APOLLO 基本信息

| 属性 | 值 |
|------|-----|
| 模块名 | apolloct.dll |
| 内存区域 | `0x2C00000 - 0x2CDA000` |
| 断点循环地址 | `0x694F21AB` |
| 运行层级 | 用户态（Ring 3） |

## APOLLO 检测能力

### 已确认的检测

| 检测项 | 触发条件 | 后果 |
|--------|---------|------|
| 代码段 CRC | WriteProcessMemory 写入 `.text` 段 | 杀进程 |
| 调试器检测 | x64dbg attach（即使有 ScyllaHide） | 下断暂停 |
| OpenProcess 锁定 | 频繁/高权限 OpenProcess | 拒绝访问 |

### 未确认的检测（待评估）

| 检测项 | 推测 | 需要验证 |
|--------|------|---------|
| 堆数据 CRC | 可能不检测 | v3-v5 补丁未触发 → 可能不检测 |
| CreateRemoteThread | 可能不检测 | v5 调用 DynamicInit 成功 |
| DLL 注入 | 可能检测 | 未尝试 |
| 内核层操作 | 无法检测 | 未尝试 |

## ScyllaHide 配置

已启用的 hook：
- KiUserExceptionDispatcherHook=1
- NtGetContextThreadHook=1
- NtSetContextThreadHook=1
- NtCloseHook=1
- NtQueryObjectHook=1
- NtQueryInformationProcessHook=1
- KillAntiAttach=1
- 所有 handleException*=1

**状态**：hook 注入成功但 APOLLO 使用了未覆盖的检测手段。

## 安全操作矩阵

| 操作 | 安全性 | 说明 |
|------|:------:|------|
| ReadProcessMemory（最小权限） | ✅ 安全 | 不在 APOLLO 监控链上 |
| WriteProcessMemory 写堆内存 | ✅ 安全 | v3-v5 验证通过 |
| WriteProcessMemory 写代码段 | ❌ 危险 | APOLLO CRC 检测 → 杀进程 |
| CreateRemoteThread | ⚠️ 待验证 | v5 使用成功 |
| x64dbg attach | ❌ 危险 | APOLLO 检测调试器 |
| 硬件断点 DR0-DR3 | ❌ 危险 | APOLLO 检测 |
| 内存断点 | ⚠️ 谨慎 | 按 4KB 页生效，代码段内危险 |
| 内核驱动读写 | ✅ 安全 | APOLLO 无法检测内核层 |

## 绕过方案

### 方案 A：纯数据补丁（当前可行）

```
✅ 只用 ReadProcessMemory + WriteProcessMemory
✅ 只修改堆上数据（flags、vtable 指针、motion type）
✅ 不修改任何代码段字节
❌ 问题：堆上找不到头发 actor 对象
```

### 方案 B：Code Cave + CRC 恢复

```
1. WriteProcessMemory 写入 code cave（堆上）
2. 修改代码段（写入 JMP 指令）
3. code cave 执行补丁逻辑
4. 恢复代码段原始字节
5. JMP 回原始代码流
⚠️ 风险：APOLLO CRC 检测有时间窗口
```

### 方案 C：内核驱动

```
✅ APOLLO 完全无法检测
✅ 可以读写任何内存
❌ 需要驱动签名
❌ 实现复杂度高
```

### 方案 D：DLL 注入

```
⚠️ APOLLO 可能检测 DLL 注入
⚠️ 需要验证
```

## 调试反馈机制（dynamic_hair_patch_v2.py 遗产）

即使被 APOLLO 杀进程，也有调试反馈：
- `--status`：从内存读取调试状态结构体（step、exception 等）
- `--monitor`：持续监控调试状态变化
- 内嵌 SEH handler：异常时记录 exception_code + exception_addr

## 下一步

- [ ] 评估 APOLLO CRC 检测的时间窗口（是否可以在检测间隔内完成修改+恢复）
- [ ] 验证 APOLLO 是否检测 CreateRemoteThread
- [ ] 验证 APOLLO 是否检测 DLL 注入
- [ ] 评估 APOLLO 是否使用 NtQueryVirtualMemory 检测内存属性变化

---
## 反作弊绕过方法论（来自 game-re-framework 集成）

> 来源: [lbh666/game-re-framework](https://github.com/lbh666/game-re-framework) — 应用到 ApolloCT 绕过

### 反作弊三层防护模型

```
层1: 页属性扫描（NtQueryVirtualMemory）
  └→ 应对: hook 返回虚假页属性（永远返回 ER）
层2: 保护恢复（NtProtectVirtualMemory）
  └→ 应对: hook 假成功（不实际修改）+ VP_DISABLED 窗口控制
层3: CRC 校验（直接读 .text 字节算 checksum）
  └→ 应对: patch CRC 函数入口 → xor eax,eax; ret
```

### 绕过 Hook 的完整性检查

每次安装 hook 前验证：

- [ ] 页属性欺骗已生效（NtQueryVirtualMemory hook onEnter/onLeave）
- [ ] 保护恢复欺骗已生效（NtProtectVirtualMemory hook）
- [ ] CRC 已 patch（所有 CRC 函数入口覆盖）
- [ ] 不挂起任何线程（Apollo 心跳不断）
- [ ] Hook 安装窗口内 VP_DISABLED=true → 保护线程被骗

### Frida 安全操作矩阵

| 操作 | 安全性 | 说明 |
|------|:------:|------|
| `Memory.scanSync` | ✅ 安全 | 只读，不触发 CRC |
| `Interceptor.attach`（前提：欺骗 hook active）| ✅ 安全 | 修改代码段但 Apollo 被骗 |
| `Memory.protect` + rwx + restore | ⚠️ 窗口 | 必须 VP_DISABLED=true 时段内完成 |
| `writeByteArray` / `writeUtf8String`（堆/数据段）| ✅ 安全 | Apollo 不检测数据变化 |
| `Memory.readByteArray` | ✅ 安全 | 纯读操作 |
