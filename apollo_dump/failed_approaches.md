# FreeStyle 逆向 — 全部失败方案明细

> 汇总 2026-05-18 ~ 2026-05-24 所有尝试过的方案。
> 来源: progress/progress_20260518~0522.md, apollo_killplan.md, archive/plan_v2.md, acquire_hook_log.txt
>
> 标记说明:
> - ❌ = 彻底失败，根因明确，重试无意义
> - ⚠️ = 有限成功 / 有条件可用
> - 🔁 = 未走完，有继续的可能

---

## 一、换装（外观替换）路线

### 1.1 ReadFile SMD 数据替换 ❌
- **迭代**: v3→v11 (8 轮)
- **方法**: Hook kernel32.ReadFile，检测 SSKF header，在 onLeave 替换 buffer 为目标 SMD 数据
- **结果**: 每次都崩溃或冻结
- **根因**: .pak 文件句柄被所有文件共用 → 多线程并发 ReadFile 同一句柄 → SMD 内部纹理/骨骼引用断裂（2.8MB vs 3.6MB 大小不匹配）→ 非 SMD 的 .pak 读取被污染
- **来源**: progress_20260522 §34.8, apollo_killplan §11.1 #1

### 1.2 改包 payload B[0:1] 替换 ❌
- **方法**: 拦截 WSASend，替换加密 payload 的 B[0:1] 字节改变外观
- **结果**: 不可行
- **根因**: b0/b1 是全局计数器+属性的动态混合，每包变化；无法建立 ItemCode→b0/b1 静态映射
- **来源**: progress_20260521 §26.4, plan_v2 §1.2 #9

### 1.3 装备数组 +0xE34 修改 ❌
- **方法**: 修改装备槽偏移 +0xE34 处的 ItemCode 内存值
- **结果**: 外观无变化
- **根因**: 客户端渲染不读此值；模型在渲染管线中已缓存
- **来源**: progress_20260522 §27.2, §27.6 #2

### 1.4 背包结构 ItemCode 修改 ❌
- **方法**: 修改内存背包数据结构中的 ItemCode（二进制和 ASCII）
- **结果**: 外观无变化
- **根因**: 装备时游戏重新查表，不从背包结构读 ItemCode
- **来源**: progress_20260521 §26.14, progress_20260522 §27.6 #3

### 1.5 暴力全量 ItemCode 修改 ❌
- **方法**: 将内存中所有 10 处 ItemCode 替换为目标值
- **结果**: 外观无变化
- **根因**: 渲染管线使用缓存的模型数据；改 ItemCode 不影响已加载模型
- **来源**: progress_20260522 §27.2.3, §27.6 #4

### 1.6 Inline patch call site ❌
- **迭代**: 3 轮
- **方法**: Memory.patchCode 修改装备函数 call site，临时改 +0xE34
- **结果**: 崩溃（__chkstk 0x2020 字节栈帧）或无效
- **根因**: Frida Interceptor 破坏 SEH 异常链；目标函数 0x1922720 只发 msgID=0x17BE + 4 字节零，不是真正装备函数
- **来源**: progress_20260521 §26.11, progress_20260522 §27.6 #5

### 1.7 商城描述符 patch ⚠️
- **方法**: patch_itemcode.py 50ms 轮询，发现描述符立即改 ItemCode
- **结果**: ✅ 仅商城试用预览有效；❌ 退出商城恢复原发型，不影响大厅/游戏内
- **限制**: 背包装备不创建描述符；是临时预览
- **来源**: progress_20260522 §27.1, §27.4

### 1.8 离线 .pak 修改 ❌
- **迭代**: 2 轮
- **方法**: 修改 .pak 中的 BML 文件，替换 mesh 路径
- **结果**: 光头（SMD 加载失败）或无变化
- **根因**: 动态/静态发型是不同 C++ 类（DDynamicActor vs DStaticActor），跨 .pak 引用断裂
- **来源**: progress_20260522 §27.8.2

### 1.9 BML ReadFile 拦截 ❌
- **方法**: Hook ReadFile 拦截 BML 内容，替换 mesh 路径
- **结果**: ReadFile 上零 BML 流量
- **根因**: DFileGPack 启动时将 BML 缓存到内存，不走 ReadFile
- **来源**: progress_20260522 §36.2

### 1.10 全量 ItemCode 替换 (破坏性) ❌
- **方法**: 替换内存中所有 ItemCode 出现位置
- **结果**: "物品加载失败"，破坏索引表
- **根因**: 盲替换破坏了其他系统使用的索引/库存表
- **来源**: progress_20260521 §26.6

### 1.11 仅 vtable 过滤描述符 ❌
- **方法**: 仅 patch 匹配描述符 vtable 的 ItemCode
- **结果**: 背包物品 0 命中
- **根因**: 背包物品不创建描述符
- **来源**: progress_20260521 §26.6

---

## 二、AcquireSMD 定位路线

### 2.1 AcquireSMD backtrace 定位 (acquire_hook v1) ❌
- **方法**: 从 ReadFile SSKF 触发做 backtrace，选最深 level 候选
- **结果**: 选错函数，args=(0,1)，是文件 I/O 层不是 AcquireSMD
- **根因**: 10 帧 backtrace 只到 DFileGPack.Read；AcquireSMD 在第 8 帧以上
- **来源**: acquire_hook_log.txt, apollo_killplan §11.1 #14

### 2.2 逐级 probe 候选函数 args ❌
- **方法**: Interceptor.attach 9 个候选函数，probe args 中 SString
- **结果**: 全部 args[0..3] 不含 SString
- **根因**: SString 在 AcquireSMD 层被消费为 pack entry index
- **来源**: acquire_hook_log.txt (probes #0-#3), apollo_killplan §11.1 #15
- **备注**: **probe 到 #3 中断，#8 (0x01EEC130 = 真正的入口) 从未测试** 🔁

### 2.3 栈扫描找 .smd 文件名 ❌
- **方法**: ReadFile SSKF 触发时扫描 ESP 附近栈空间
- **结果**: 找到 c3000.smd 但文件已打开无法替换文件名
- **根因**: 文件句柄已用原始文件名打开
- **来源**: acquire_hook_log.txt, apollo_killplan §11.1 #16

### 2.4 格式字符串 xref 搜索 (Frida) ❌
- **方法**: 搜 push/mov/lea 引用 "AcquireSMD(SFullName)" 格式字符串
- **结果**: 13 个可执行段 + 16 个可读段，0 命中
- **根因**: 格式字符串是死代码或调试残留
- **来源**: progress_20260522 §27.10 methods #3-4
- **备注**: **Apollo 拆除后 Memory.scan 可能会有不同结果** 🔁

### 2.5 sprintf/printf hook ❌
- **迭代**: 2 轮 (msvcrt.dll → MSVCR100.dll)
- **结果**: "not a function" 或零输出
- **根因**: 游戏用 C++ string 类，不走 CRT 格式化函数
- **来源**: progress_20260522 §27.10 methods #5-6

### 2.6 strcpy/strcat hook ❌
- **结果**: 零输出
- **根因**: 游戏用 SString 内联操作
- **来源**: progress_20260522 §27.10 method #7

### 2.7 D3DXCreateTextureFromFileA hook ❌
- **结果**: 零输出
- **根因**: 纹理从内存加载，不走文件 API
- **来源**: progress_20260522 §27.10 method #8

### 2.8 Stalker 主线程 3s ❌
- **结果**: 268 个函数，0x22EC 区域不在其中
- **根因**: 3s 追踪窗口未覆盖 SMD 加载
- **来源**: progress_20260522 §27.10 method #9

### 2.9 Stalker 全线程 diff ❌
- **结果**: 游戏卡死
- **根因**: 32 线程 Stalker 太重
- **来源**: progress_20260522 §27.10 method #10

### 2.10 Stalker 主线程 diff ❌
- **结果**: 超时崩溃
- **根因**: Stalker 对此游戏不兼容
- **来源**: progress_20260522 §27.10 method #11

### 2.11 Hook 0x22EC130 (Apollo 拆除前) ❌
- **方法**: Interceptor.attach 最近函数入口 (CC+SEH prologue)
- **结果**: 不崩但**不触发**
- **根因**: 测试在 Apollo 拆除之前；Apollo 保护可能阻止了触发
- **来源**: progress_20260522 §27.9.2
- **备注**: **Apollo 拆除后 acquire_hook_log.txt backtrace 证明此函数在 SMD 加载时被调用，从未在拆除后重新测试 hook** 🔁

### 2.12 返回地址过滤 0x1eec93e/0x1eecba7 ❌
- **方法**: ESP 返回地址过滤 AcquireSMD 调用者
- **结果**: 0 个 ACQUIRE 命中
- **根因**: toInt32() 有符号值比较逻辑问题 / 或 ESP 被 Frida 修改 / 或调用是间接跳转
- **来源**: progress_20260522 §38.4

### 2.13 热函数 0x21e25b0 hook ❌
- **结果**: 游戏阻塞/崩溃
- **根因**: 通用字符串函数，80次/秒，hook 开销阻塞主循环
- **来源**: progress_20260522 §38.2

### 2.14 纯内存扫描找到 0x01EED020 ⚠️
- **方法**: 搜索字符串 "AcquireSMD"/"SSKF" 引用
- **结果**: 找到 push 指令位置，但**不是函数入口**
- **根因**: 0x01EED020 是函数体内部地址（push 字符串常量），真正入口是 **0x01EEC130**（偏移 0xEF0 字节前）
- **来源**: 本次会话新发现

---

## 三、Apollo 绕过路线

### 3.1 x64dbg 硬件断点 DR0-DR3 ❌
- **结果**: DR1-DR3 被清零，断点不触发
- **根因**: Apollo.sys 内核驱动清零调试寄存器
- **来源**: progress_20260519 §19 step 4
- **备注**: **sc stop ApolloProtect 后硬件断点可用** ⚠️

### 3.2 x32dbg 软件断点 ❌
- **结果**: EIP 跳转到 Apollo 加密代码段执行垃圾指令崩溃
- **根因**: L2 内嵌 Apollo 检测调试器
- **来源**: progress_20260519 §19 step 5

### 3.3 x32dbg 入口点清除 + 批量继续 ❌
- **结果**: 反复暂停在 DLL TLS 回调，最终崩溃
- **根因**: L2 内嵌 Apollo 加密代码检测调试器
- **来源**: progress_20260519 §19 steps 6-7

### 3.4 Interceptor.attach 游戏代码 (无保护) ❌
- **结果**: 立即崩溃
- **根因**: Apollo 检测页属性变化 (RX→RWX)
- **来源**: progress_20260522 §27.9

### 3.5 Memory.scan ❌
- **结果**: 始终返回 0
- **根因**: 此 Frida 版本 API 损坏
- **来源**: progress_20260522 §34.9
- **备注**: **Apollo 拆除后可能修复** 🔁

### 3.6 rwx + attach + 保持 rwx ❌
- **结果**: 几秒后崩溃
- **根因**: Apollo 定期扫描 .text 页属性
- **来源**: progress_20260522 §38.1

### 3.7 rwx + attach + 立刻恢复 rx ✅
- **结果**: 不崩
- **限制**: 只能 hook 极轻量函数（冷函数）；热函数必崩
- **来源**: progress_20260522 §38.1

### 3.8 挂起 ApolloCT 保护线程 ⚠️
- **结果**: 有效，但 1-2 分钟后服务器断连
- **根因**: 保护线程同时负责心跳/保活
- **来源**: apollo_killplan §9.2
- **备注**: **VirtualQuery 欺骗方案可替代（线程不挂起，让它看到假数据）** ⚠️

### 3.9 debug_inject.py CRC patch (独立) ❌
- **结果**: 只过完整性校验
- **根因**: 核心保护（代码段监控/线程检测）不受影响
- **来源**: progress_20260522 §37.1

### 3.10 诊断版大型内存读取 ❌
- **结果**: 游戏崩溃
- **根因**: 大量内存读冲破 Frida IPC 桥
- **来源**: progress_20260522 §38.5

---

## 四、静态分析路线

### 4.1 Ghidra 静态分析 FreeStyle.exe ❌
- **迭代**: 2 轮
- **结果**: API 成功但输出无用（swi/out/in 无意义）
- **根因**: .text 段加密（熵 7.23/8.0），Ghidra 强制反汇编加密垃圾字节，字符串 xref 率 0%
- **来源**: progress_20260522 §31.4

### 4.2 .text 段 XOR 解密 ❌
- **迭代**: 单字节 XOR (0x00-0xFF) + 4 字节 XOR (0x4db8a854)
- **结果**: 无有效函数序言
- **根因**: 非简单 XOR，推测流密码或块密码
- **来源**: progress_20260522 §31.6

### 4.3 r2ghidra (pdg) ❌
- **结果**: 不可用
- **根因**: core_r2ghidra.dll 是 Debug build，依赖 MSVCP140D.dll/VCRUNTIME140D.dll（系统无 Debug CRT）
- **来源**: apollo_killplan §13.1

---

## 五、网络/协议路线

### 5.1 入站数据包捕获 (12 条路径) ❌
- **方法**: recv hook, WSARecv hook, IOCP GetQueuedCompletionStatus, NtReadFile, AFD_RECV 等
- **结果**: 1267 个出站包，0 个真实入站包
- **根因**: 游戏通过 IOCP 零缓冲区模式接收；AFD_RECV 提交时 WSABUF.buf=NULL，内核自行分配，通过 IOCP 完成返回
- **来源**: progress_20260520 §3-11

### 5.2 Npcap/scapy 网卡层捕获 ❌
- **结果**: 仅 TLS 流量，无游戏数据
- **根因**: 游戏数据走 UDP，不走 TCP
- **来源**: progress_20260520 §15.4

### 5.3 UDP recv 验证 ❌
- **结果**: 17 个"入站"包全是假阳性（UTF-16LE 文本）
- **根因**: frida_udp.js 同时捕获 TCP 和 UDP socket 的 recv()
- **来源**: progress_20260520 §18.2

### 5.4 UDP 加密密钥破解 ❌
- **结果**: 确认 AES 强加密，无法破解
- **根因**: UDP 使用独立于 TCP 的 AES 加密
- **来源**: progress_20260520 §19

### 5.5 CryptEncrypt 运行时 hook ❌
- **结果**: 0 次加密调用
- **根因**: 游戏用内置 AES（.rdata 中 S-box），不走 Windows CryptoAPI
- **来源**: progress_20260520 §20.3

---

## 六、输入/DirectInput 路线

### 6.1 DirectInput 自动登录 (7 种方法) ❌
- **方法**: SendInput, PostMessage WM_CHAR, SendMessage WM_KEYDOWN, keybd_event, mouse_event 等
- **结果**: 全部被 DirectInput 忽略
- **根因**: DirectInput 直接从 HID 驱动读硬件输入，所有软件注入被绕过
- **来源**: progress_20260519 §14.1

### 6.2 DirectInput8Create 导出搜索 ❌
- **结果**: DLL 找到但导出不存在
- **根因**: 游戏的 DINPUT8.dll 是自定义版本
- **来源**: progress_20260519 §20.1

---

## 七、Frida 技术问题

### 7.1 Stalker 追踪 E2 内部指令 ❌
- **结果**: 零输出（JS 加载阶段静默失败）
- **根因**: 此 Frida 版本 Stalker API 可能不可用或签名不同
- **来源**: progress_20260519 §3.3

### 7.2 E2 CALL 指令级 Interceptor 二分法 ❌
- **迭代**: 2 轮
- **结果**: ACCESS_VIOLATION 崩溃 / 游戏无响应
- **根因**: 短 FF 指令被 Frida 5 字节跳转覆盖，破坏相邻代码；45 个 hook 性能问题
- **来源**: progress_20260519 §3.1

### 7.3 E2 CALL_E0 内部位置 hook ❌
- **迭代**: 3 轮（偏移量错误两次 + 偏移量正确但初始化阶段崩溃）
- **根因**: 函数体内 jmp 破坏代码；初始化阶段 E2 被调用时 hook 触发导致崩溃
- **来源**: progress_20260519 §3.2

### 7.4 NativeFunction 直接调用 E0/E2 ❌
- **方法**: cdecl/fastcall/thiscall 三种调用约定
- **结果**: 全部 ACCESS_VIOLATION (读 0x0 或 0x4)
- **根因**: E0/E2 依赖内部对象状态、TLS、前置计算结果，不能脱离上下文调用
- **来源**: progress_20260518 §2.1, progress_20260519 §4

### 7.5 XOR 密钥内存扫描 ❌
- **方法**: 搜代码段中 XOR 密钥常量 0x54A8B84D
- **结果**: 0 命中
- **根因**: 密钥不是代码中 4 字节常量，可能逐字节构造或通过数据段引用
- **来源**: progress_20260518 §2.3

### 7.6 描述符 1s 轮询 ❌
- **根因**: 游戏在微秒级创建并缓存描述符，外部轮询来不及拦截
- **来源**: progress_20260521 §26.6

### 7.7 描述符 50ms Frida 轮询 ❌
- **根因**: 同上，50ms 仍然太慢
- **来源**: progress_20260521 §26.6

### 7.8 描述符拷贝构造函数 hook ❌
- **结果**: 崩溃（SEH 冲突）
- **根因**: 拷贝构造函数有 SEH 序言，Frida Interceptor 破坏异常处理链
- **来源**: progress_20260521 §26.6

### 7.9 标准 field12 算法穷举 ❌
- **方法**: CRC32, Adler32, Fletcher32, XOR, SUM32 等 15 种算法
- **结果**: 38 个数据包上全 0 匹配
- **根因**: field12 使用自定义算法（后来破解：XOR 二进制计数器 + 周期 8 LEVEL 表）
- **来源**: progress_20260519 §3.4
- **备注**: **已破解，不再需要穷举** ✅

### 7.10 Interceptor 0x19247a0 (三级指针搜索) ❌
- **结果**: ItemCode 未找到
- **根因**: 函数接收坐标参数 (917.0, 484.0)，不是 ItemCode
- **来源**: progress_20260521 §26.11

---

## 八、CreateFileW / 文件 API 路线

### 8.1 CreateFileW hook 捕获资源访问 ❌
- **结果**: 零命中
- **根因**: 游戏用自定义 pak I/O 系统 (DFileGPack)
- **来源**: progress_20260522 §27.5.1

---

## 九、未走完的路线 (🔁 可继续)

| # | 方向 | 现状 | 为什么认为能继续 |
|---|------|------|-----------------|
| 1 | **Hook 0x01EEC130 (AcquireSMD 真入口)** | Apollo 拆除前测试不触发；拆除后 backtrace 证明它在 SMD 加载时被调用，但从未重新 hook 测试 | Apollo 拆除 + VirtualQuery 欺骗 + CRC patch 后环境完全不同 |
| 2 | **Memory.scan Apollo 拆除后重试** | 之前 API 损坏返回 0 | 可能是 Apollo 干扰导致，拆除后可能修复 |
| 3 | **x32dbg MCP 远程调试** | 工具全部就绪（.mcp.json, enabler, ScyllaHide），从未实际连接测试 | §12.7 有完整执行计划，从 0x01EEC130 设断点验证 |
| 4 | **增大 backtrace 深度到 20-30 帧** | 默认 10 帧不够，AcquireSMD 在第 8 帧以上 | Thread.backtrace 可指定深度参数 |
| 5 | **源码编译旧版客户端** | 有完整 V1.1 源码 + 无 Apollo 的原始 EXE (68KB) | 本地渲染外观不需要联机；协议差异可能有限 |

---

## 十、统计

| 类别 | 数量 |
|------|------|
| 彻底失败 ❌ | 44 |
| 有限成功 ⚠️ | 4 (商城描述符 patch, rwx+restore rx, 挂起线程, 纯内存扫描定位) |
| 未走完 🔁 | 5 |
| **总计** | **53** |
