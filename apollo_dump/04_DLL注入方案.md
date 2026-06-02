# DLL注入方案 — 技术文档

> 最终目标：通过IAT hook sprintf替换发型ItemCode，让游戏加载紫色超赛发型(50125711)代替美丽梦想(50125461)
> 核心约束：Apollo反作弊会检测.text段代码修改和Frida注入，必须找到不被检测的注入方式

---

## 一、目标游戏信息

| 项目 | 值 |
|------|-----|
| 进程 | FreeStyle.exe (街头篮球) |
| 架构 | 32位 (i386), 基址 0x400000, 无ASLR |
| CRT | MSVCR100.dll |
| 反作弊 | Apollo (内核驱动 + 用户态 + 内嵌Shell) |
| 安装路径 | `C:\Program Files (x86)\T2CN\街头篮球\` |

---

## 二、Apollo反作弊架构

| 层 | 组件 | 状态 | 说明 |
|----|------|------|------|
| L0 | Apollo.sys | `sc.exe stop ApolloProtect` 可停 | 内核驱动 |
| L1 | ApolloCT.dll | 0保护线程（CRC patch点已知） | 用户态DLL，在进程内但已死 |
| **L2** | **ApolloShell** | **活跃** | 嵌入FreeStyle.exe .text加密段，登录后启动检测 |

### L2检测行为（已验证）
- 扫描.text段字节变化 → Frida JMP/INT3 inline hook被检测
- 扫描页属性变化 → RX→RWX被检测
- **扫描IAT完整性** → 检测IAT条目指向的地址是否在对应DLL范围内（v8d诊断确认）
- 杀进程方式：ntdll抛system类型异常，不走TerminateProcess
- **检测时机**：登录前也会检测IAT完整性（v8c测试确认，注入后未登录即崩）

### 已验证失败的Apollo对抗方案

| 方案 | 结果 |
|------|------|
| Frida Interceptor堵杀进程API | ❌ Apollo不走TerminateProcess |
| 页属性欺骗(NtQueryVirtualMemory) | ❌ |
| 隐藏调试端口 | ❌ 干扰游戏加载(光头) |
| 吞system异常 | ❌ Apollo杀失效但Frida本身导致光头 |
| 吞INT3 | ❌ 打断Frida自身机制 |
| Memory.patchCode静态补丁 | ❌ 登录即崩 |
| PEB BeingDebugged=0 | ❌ 仍光头 |
| **IAT hook（替换为非模块地址）** | **❌ v8c测试：未登录即崩** |

### v8d诊断实验（关键结论）

分步测试VirtualProtect和IAT写入，确认Apollo的具体检测机制：

| 测试 | 操作 | 结果 |
|------|------|------|
| test1 | VirtualProtect改页属性RW→RWX→恢复 | ✅ 不崩 |
| test2 | VP + 写回IAT原值（无变化） | ✅ 不崩 |
| v8c | VP + 替换IAT为hook_sprintf地址(0x220Fxxxx) | ❌ 即崩 |

**结论**：Apollo不检测页属性变化，不检测写入行为本身，**检测的是IAT条目指向的地址不在合法DLL范围内**。
- sprintf原始地址: `0x7A5B6051` (MSVCR100.dll范围内)
- hook_sprintf地址: `0x220Fxxxx` (manual map分配的匿名内存，不属于任何DLL)
- Apollo扫描IAT，发现sprintf条目指向非MSVCR100地址 → 杀进程

---

## 三、sprintf Hook方案（唯一成功渲染的方案）

### 原理
Hook MSVCR100.dll的sprintf，当格式串包含`i%d.xml`或`c%d.xml`时，将ItemCode从50125461替换为50125711。

### 效果链
```
sprintf("customize\\item\\i%d.xml", 50125461)
→ hook替换args为50125711
→ 输出 "i50125711.xml"
→ LoadItemFile收到iItemCode=50125711
→ SeekFile查找 i50125711.bml
→ Resource\item768\i50125711.bml (松散文件命中)
→ 解析BML → SMD路径 → AcquireSMD加载完整骨骼
→ 紫色超赛发型渲染成功 ✅
→ pItem->iItemCode仍为50125461 → 服务器无感
```

### 关键地址
| 名称 | RVA | 说明 |
|------|-----|------|
| sprintf调用点 | 0x1AE255E | CALL指令位置 |
| sprintf返回 | 0x1AE2563 | SetCharacterFeature内部 |
| LoadItemFile | 0x1ACE1C0 | 加载item BML |
| [ebp-0xD8] | 调用者栈帧 | iItemCode局部变量(需同步修复) |
| BML格式串 "i%d.xml" | 0x22A1680 | .rdata段 |
| BML格式串 "c%d.xml" | 0x22A1698 | .rdata段 |

### BML文件部署
- 路径: `Resource\item768\i50125711.bml`
- 格式: XOR 0xFF编码的XML
- Group机制: 游戏用`item`+pak编号查BML，SeekFile优先查松散文件
- 查找顺序: `Resource\{group}\{name}` → `{group}.pak` → `{group}_ext.pak`

### 已知限制
- 进练习场崩溃：美丽梦想(50125461)是DStaticActor，紫色超赛需要DDynamicActor的物理骨骼
- 只能替换同角色类型（男→男/女→女）的发型

---

## 四、DLL注入演进史

### v1: LoadLibraryA注入 → 崩溃
- injector.py + apollo_hook.c
- CreateRemoteThread(LoadLibraryA) 注入
- DllMain直接运行IAT遍历 → 崩溃在iat_hook()
- **问题**: DllMain在loader lock下运行，IAT遍历访问加壳EXE的异常导入表

### v2: Worker线程 + 全内存扫描 → 崩溃
- DllMain只创建线程，3秒后执行hook
- IAT遍历找到3个DLL（加壳重建的导入表），未找到MSVCR100
- fallback全进程内存搜索sprintf地址 → patch了2处（1处正确，1处误patch其他模块）
- **问题**: fallback扫描了全部进程内存，patch了其他模块的sprintf → 崩溃

### v3: 限制模块范围 → 崩溃
- fallback限制在FreeStyle.exe模块范围内
- 但DLL仍通过LoadLibraryA注册到PEB模块链表
- **问题**: Apollo模块枚举发现未知DLL → 登录后杀进程

### v4: Manual Map + 标准CRT → 不崩但DllMain不执行
- manual_map.py: 手动映射DLL，不走LoadLibraryA，不注册PEB
- 日志文件不存在 → DllMain从未执行
- **问题**: MinGW的`_DllMainCRTStartup`依赖PEB模块注册，CRT初始化失败静默跳过DllMain

### v5: --entry=DllMain跳过CRT → 立即崩溃
- 直接设置入口点为DllMain
- **问题**: DLL仍链接UCRT（api-ms-win-crt-*），42个CRT函数未解析 → 调用崩溃

### v6/v7: 零CRT + 手写声明 → ✅ 成功！
- 不包含windows.h，手动声明kernel32函数
- 编译参数: `-nostdlib -fno-stack-protector -fno-builtin -Wl,--entry=DllMain -lkernel32 -lgcc`
- 结果: 只import KERNEL32.dll
- Manual map: 重定位修复 + 导入解析，0失败
- **hook_alive.txt成功写入"ALIVE"** ✅

### v8: 完整IAT Hook DLL → log_fmt崩溃
- 加入wvsprintfA格式化、sprintf IAT扫描、hook_sprintf替换
- DllMain只写一行log就停（编译路径错误导致用了旧DLL）
- wvsprintfA首次调用时崩溃（log_fmt中的va_list构造问题）

### v8b: 修复编译路径 + worker诊断 → 文件锁问题
- 修复：bash路径`C:\tmp\`在zig中不生效，需用`/c/tmp/`
- DllMain写alive成功，但log文件被上次注入的worker线程持有写锁
- 新log文件名`apollo_hook_v8b.log`解决锁问题

### v8c: IAT Hook激活 → ❌ Apollo即杀
- 全raw_write诊断，手写hex转换替代wvsprintfA
- worker线程完整跑通：GetModuleHandle(NULL)=0x400000, MSVCR100=0x7A550000, sprintf=0x7A5B6051
- IAT entry at `0x0268F560`, 替换为hook_sprintf → HOOK ACTIVE
- **结果：游戏立即崩溃（未登录）**，Apollo检测到IAT值异常

### v8d: 诊断分步测试 → ✅ 确认检测机制
- test1: 只VirtualProtect改页属性再恢复 → 不崩
- test2: VP + 写回IAT原值 → 不崩
- **结论：Apollo检测IAT条目指向地址的合法性，不检测页属性变化**

---

## 五、Manual Map注入技术细节

### 编译命令
```bash
cd D:\py\反编译\FreeStyle\apollo_dump
python -m ziglang cc -target x86-windows-gnu -shared -nostdlib -fno-sanitize=undefined -fno-stack-protector -fno-builtin -Wl,--entry=DllMain -o /c/tmp/apollo_hook.dll apollo_hook.c -lkernel32 -lgcc
```

> **注意**：输出路径必须用`/c/tmp/`（Unix风格），Windows反斜杠在bash/zig中不生效！

### 注入流程
1. 解析DLL PE文件（本地）
2. VirtualAllocEx在目标分配SizeOfImage内存
3. 写入PE头 + 各节数据
4. 修复重定位表（delta = 实际基址 - 首选基址）
5. 解析导入表：本地解析SysWOW64/kernel32.dll导出RVA + 远程模块基址
6. 写shellcode: `push 0; push 1; push [esp+12]; mov eax, entry; call eax; ret 4`
7. CreateRemoteThread → shellcode(base) → DllMain(base, DLL_PROCESS_ATTACH, NULL)

### 关键代码: manual_map.py
- `parse_local_exports()`: 解析SysWOW64 DLL的PE导出表，获取函数RVA
- `resolve_import()`: 目标模块基址 + 本地RVA = 目标函数地址
- `PEFile`: DLL PE解析（节表、导入表、重定位表）

---

## 六、当前困境

### 核心矛盾
sprintf hook方案是唯一能成功渲染替换发型的方法，但Apollo现在已确认会检测IAT完整性：

| 层级 | 检测 | 状态 |
|------|------|------|
| .text代码段 | 字节完整性(CRC) | ❌ inline hook被杀 |
| 页属性 | RX→RWX变化 | ❌ 已知（但v8d确认VP改RW再恢复不触发） |
| **IAT** | **条目指向地址合法性** | **❌ v8d确认：指向非DLL地址即杀** |
| 模块枚举 | PEB模块链表 | ❌ LoadLibraryA注册的被发现 |
| 进程/线程 | CreateRemoteThread | ✅ v8d诊断：登录前不检测 |

### 检测逻辑推测
Apollo（可能是L2 Shell）定期扫描FreeStyle.exe的IAT：
1. 遍历导入表每个条目
2. 检查条目值指向的地址是否属于对应的DLL模块范围
3. 比如sprintf条目应指向MSVCR100.dll范围(`0x7A550000`附近)
4. 如果指向匿名内存(manual map分配)→ 杀进程
5. **检测频率**：持续扫描，登录前也会触发

### hook_sprintf为什么暴露
- hook函数位于manual map分配的内存(`0x220F0000`等)
- 这块内存不属于任何已注册模块
- 即使manual map不走PEB注册，Apollo通过VirtualQuery扫描也能发现这块RWX内存
- IAT条目从`0x7A5B6051`(MSVCR100)变成`0x220Fxxxx`(匿名) → 异常

---

## 七、下一步方向

### 方向A: 在MSVCR100内部做hook（让IAT值合法）
不替换IAT条目，而是直接修改MSVCR100.dll中sprintf函数的代码：
- **问题**：修改MSVCR100的.text段同样会被Apollo扫描到
- **变体**：MSVCR100不在Apollo的保护范围内？（需测试）
- **变体**：在MSVCR100的.data段放跳转代码？（绕过.text CRC）

### 方向B: VEH/Hardware Breakpoint hook
- 设置硬件断点(DR0-DR3)在sprintf入口，通过VEH(Structured Exception Handler)拦截
- 不修改任何代码，不改IAT
- **优势**：零代码修改，纯调试寄存器操作
- **风险**：Apollo可能检测DR寄存器状态；VEH链可能被监控

### 方向C: 代理DLL（DLL Sideloading）
- 创建一个假的`MSVCR100.dll`，转发所有函数到真正的MSVCR100
- 在假DLL的sprintf中做替换逻辑
- 放在游戏目录让游戏优先加载
- **问题**：Apollo可能验证DLL签名/Hash；游戏目录的DLL可能被完整性检查

### 方向D: 不hook，改数据文件路径
- 不做任何内存修改，纯文件系统层操作
- 让`i50125461.bml`指向`i50125711`的内容（文件系统重定向/Junction）
- **问题**：游戏代码用ItemCode直接拼文件名，无法在文件系统层区分来源

### 方向E: 内核层拦截
- 利用已停的Apollo.sys驱动能力
- 写自己的内核驱动做SSDT hook拦截NtReadFile
- 当读取`i50125461.bml`时返回`i50125711.bml`的内容
- **优势**：完全在内核层，用户态检测无感
- **风险**：需要签名驱动或测试模式；复杂度高

### 方向F: 修改游戏.rdata段（格式串替换）
- 不hook sprintf，改为修改`"i%d.xml"`格式串
- 但.rdata也在CRC保护范围内，与.text同命运

---

## 八、工具链

| 文件 | 用途 |
|------|------|
| `manual_map.py` | Manual map注入器（v2，带日志和IAT验证） |
| `injector.py` | LoadLibraryA注入器（已弃用） |
| `apollo_hook.c` | DLL源码（当前v8d诊断版本） |
| `item_lookup.py` | 物品代码→名称查询 |
| `search_itemshop.py` | 交互式物品搜索 |
| `hook_settings_crash.py` | 设置崩溃诊断 |
| `01_知识库.md` | 已确认知识汇总 |
| `02_试验记录.md` | 全部试验历史 |
| `03_常量地址表.md` | 已验证地址索引 |

### 编译DLL
```bash
cd D:\py\反编译\FreeStyle\apollo_dump
python -m ziglang cc -target x86-windows-gnu -shared -nostdlib -fno-sanitize=undefined -fno-stack-protector -fno-builtin -Wl,--entry=DllMain -o /c/tmp/apollo_hook.dll apollo_hook.c -lkernel32 -lgcc
```

### 注入
```bash
sc.exe stop ApolloProtect
python D:\py\反编译\FreeStyle\apollo_dump\manual_map.py
```

### 验证
```bash
type C:\tmp\manual_map.log      # 注入器日志
type C:\tmp\hook_alive.txt      # DLL执行证明
type C:\tmp\apollo_hook_v8d.log # DLL worker日志
```
