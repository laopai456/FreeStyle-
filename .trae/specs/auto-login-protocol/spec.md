# 自动登录 — 网络协议重放方案

> 状态: 实现中
> 创建: 2026-05-18
> 基于: apollo_launcher.py (已验证的启动+CRC绕过基础)

---

## 背景

### 为什么要自动登录

AI 大模型需要无人值守的循环调试工作流：启动游戏 → 自动登录 → 进练习场 → 注入修改 → 测试 → 崩了重启 → 自动登录 → ... 整个闭环不能依赖人类输入密码。

### 为什么 UI 路线走不通

Apollo 输入过滤发生在内核层 (Apollo.sys 引用 `\system32\win32k.sys`)，所有 SendInput/keybd_event/PostMessage 变体都被拦截。详见 `apollo_dump/archive/apollo_input_filter_analysis.md`。

### 为什么内存注入路线有风险

Apollo.sys 注册了 `PsSetCreateThreadNotifyRoutine` (监控所有线程创建) 和 `PsSetLoadImageNotifyRoutine` (监控 DLL 加载)。CRC patch 只解除 ApolloCT.dll 自身的代码完整性校验，内核驱动回调仍然活跃。`CreateRemoteThread` 可能触发检测。

### 基础能力 (已验证)

| 能力 | 脚本 | 状态 |
|------|------|------|
| CreateProcess SUSPENDED 启动游戏 | apollo_launcher.py | ✅ |
| 直连 42.193.73.163:10005 网络正常 | apollo_launcher.py | ✅ |
| CRC patch ApolloCT.dll (2处) | apollo_launcher.py | ✅ |
| ReadProcessMemory / WriteProcessMemory | apollo_launcher.py | ✅ |

---

## 方案：网络协议重放

整体路线：完全不碰游戏 UI，在 TCP 协议层完成登录。

### Phase 1: 协议捕获（一次性，手动配合一次）

**目标**: 获取登录 TCP 数据包的完整内容。

**方案**: WS2_32.connect inline hook → 透明重定向流量到本地代理 → 捕获。

```
正常:   游戏 ──connect──→ 42.193.73.163:10005

Hook后: 游戏 ──connect──→ 127.0.0.1:23001 ──转发──→ 42.193.73.163:10005
              ↑ hook改写了目标地址       ↑ 代理同时捕获两个方向的包
```

**为什么不用简单 hosts 文件**: 不依赖系统级修改，hook 在进程内完成，干净可控。

**为什么 hook connect 而不是 hook send**: connect 只调用一次 (建立连接)，hook 它需要的 shellcode 极少。且 connect hook 绕过了域名解析环节。

**输出**: `apollo_dump/login_packets.bin` — 包含登录阶段全部 TCP 双向数据。

### Phase 2: 协议分析

分析 `login_packets.bin`：
- 用户名/密码的编码方式
- 是否有加密 / 密钥交换
- 请求 → 响应的结构
- 登录成功 / 失败的标志位

**产出**: 协议文档，记录在 `docs/auto_login_protocol.md`。

### Phase 3: 纯 TCP 登录重放

在游戏启动前，直接用 Python socket 连 `42.193.73.163:10005`，重放登录包，验证能否成功登录。

如果协议有挑战-响应 (challenge-response) 或动态 token，需要进一步分析。

### Phase 4: 完整闭环脚本 `auto_login_complete.py`

```
1. 杀旧 FreeStyle.exe
2. 启动 TCP 连接到服务器，发送登录包
3. 接收登录响应，确认成功
4. 保持 TCP 连接 (session)
5. 启动游戏 (CRC 绕过)
6. 游戏检测到已有 session → 直接进入大厅
   (如果游戏不支持 session 共享，则需要额外步骤)
7. 监控进程存活 → 崩了自动回到步骤1
```

### 备选：如果协议无法重放

如果登录协议包含一次性 token / 时间戳 / 服务端挑战，无法纯 TCP 重放，则回到 Plan C：

**内存层调用登录函数** — 在游戏进程内定位登录提交函数，通过修改 EIP 或 hook 的方式触发。虽有一定内核检测风险，但作为最后手段。

---

## 文件结构

```
FreeStyle/
├── capture_login_protocol.py    # Phase 1: connect hook + proxy 捕获
├── auto_login_complete.py       # Phase 4: 全自动登录闭环
├── docs/
│   └── auto_login_protocol.md   # Phase 2 产出: 协议分析文档
├── apollo_dump/
│   ├── login_packets.bin        # 捕获的原始登录包
│   └── login_capture_log.txt    # 捕获日志
├── apollo_launcher.py           # 已有: 启动+CRC绕过 (Phase 4 依赖)
└── .trae/specs/auto-login-protocol/
    └── spec.md                  # 本文档
```

---

## 关键技术细节

### WS2_32.connect inline hook

- 在 WS2_32.dll 的 `connect` 函数入口写 `JMP <trampoline>` (5字节)
- Trampoline (shellcode): 检查 sockaddr 目标是 `42.193.73.163:10005` → 改写为 `127.0.0.1:23001`
- 非目标连接 → 直接透传，不影响游戏其他网络调用
- 连接关闭后自动恢复 hook，清理资源

### Hook 时机

```
1. CreateProcess SUSPENDED  # 进程创建但主线程未运行
2. ResumeThread             # 开始运行，加载 DLL
3. 等待 WS2_32.dll 加载    # 通常在 1-2 秒内
4. 等待 ApolloCT.dll 加载  # 通常 3-5 秒
5. CRC patch               # 解除 Apollo 代码保护
6. 写入 connect hook       # 在游戏首次调用 connect 之前
7. 游戏进入登录画面 → 首次 connect 被 hook 重定向
```

### 代理设计

- 单线程事件驱动 (select)，不做多线程复杂度
- 双向转发同时写入 .bin 文件
- 超时 120 秒自动退出
- 用户手动登录完毕后 Ctrl+C 或等待自然断开

---

## 成功标准

- [ ] Phase 1: 成功捕获一次完整的登录 TCP 双向数据包
- [ ] Phase 2: 分析出登录协议结构 (用户名/密码编码、加密方式)
- [ ] Phase 3: 用 Python socket 成功完成一次独立登录
- [ ] Phase 4: `auto_login_complete.py` 一键全自动登录 → 游戏在大厅就绪

---

## 风险与缓解

| 风险 | 概率 | 缓解 |
|------|------|------|
| connect hook 被 Apollo 检测 | 低 | hook 在 WS2_32.dll (系统DLL)，Apollo 不校验系统模块完整性 |
| 协议含动态挑战无法重放 | 中 | 备选 Plan C: 内存调用登录函数 |
| 游戏不支持已有 session | 中 | Phase 4 备选: hook 登录响应包注入到游戏进程 |
| 内核驱动检测到线程异常 | 低 | 不创建远程线程，仅做代码 patch |