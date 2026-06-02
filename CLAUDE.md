# FreeStyle 逆向工程 — 项目导航

> 街头篮球 (FreeStyle) 20年老游戏，Apollo 反作弊 + 自制引擎
> 目标: 运行时替换角色3D模型(发型/服装)，绕过 Apollo 4层保护
> **最后更新**: 2026-05-27
> **MD文档总数**: 40 个（全部已索引，零遗漏）

---

## 一、路径速查

```
项目根         D:\py\反编译\FreeStyle\
  分析文档      apollo_dump\                     # 全部 .md / .py / .js
    进度        apollo_dump\progress\progress_*.md (7篇)
    存档        apollo_dump\archive\*.md (6篇)
  早期GUI工程   D:\py\反编译\FS服装搭配专家v5.3.6\  # WPF服装搭配工具(旧)
  游戏源码v1.1  game_source_v1.1\                # 官方泄漏源码(参考用)
  lib工具       lib\
  ghidra_tools  D:\py\反编译\ghidra_tools\       # GhidrAssistMCP 仓库
  ghidra安装    D:\py\反编译\ghidra_12.0.1_PUBLIC\
  ghidra项目    D:\ghidra_projects\
  x32dbg        D:\py\release\x32\x32dbg.exe
  docs          docs\                             # 早期文档(8个子目录, 24篇MD)
```

---

## 二、完整文档索引 (40/40)

### 2.0 核心战略文档 (apollo_dump 根目录)

| # | 文件 | 内容 | 行数 |
|---|------|------|------|
| 1 | [apollo_killplan.md](file:///d:/py/反编译/FreeStyle/apollo_dump/apollo_killplan.md) | **战略总纲** — Apollo 4层拆除计划, Phase1-4, 所有测试路线记录, x32dbg MCP, Apollo组件反编译 | ~2106 |
| 2 | [failed_approaches.md](file:///d:/py/反编译/FreeStyle/apollo_dump/failed_approaches.md) | **失败路线全集** — 16种改发方案的详细分析+死因(必须先读) | ~1200+ |
| 3 | [街头篮球PAK文件功能说明.md](file:///d:/py/反编译/FreeStyle/apollo_dump/街头篮球PAK文件功能说明.md) | PAK包文件结构分析 | ~200 |

### 2.1 进度日志 (progress/)

| # | 文件 | 日期 | 核心内容 | 关键发现 |
|---|------|------|---------|---------|
| 4 | [progress_20260518.md](file:///d:/py/反编译/FreeStyle/apollo_dump/progress/progress_20260518.md) | 05-18 | 项目启动，PAK格式分析 | 确认Apollo 4层架构，PAK=PGFN魔数 |
| 5 | [progress_20260519.md](file:///d:/py/反编译/FreeStyle/apollo_dump/progress/progress_20260519.md) | 05-19 | TCP协议+ApolloCRC | XOR key=4db8a854, f12(seq)完全破解, CRC2/2 patch |
| 6 | [progress_20260520.md](file:///d:/py/反编译/FreeStyle/apollo_dump/progress/progress_20260520.md) | 05-20 | 改包/加包注入+ItemCode | 加包失败(seq冲突), b0/b1全动态 |
| 7 | [progress_20260521.md](file:///d:/py/反编译/FreeStyle/apollo_dump/progress/progress_20260521.md) | 05-21 | 渲染管线+SSKF+Apollo诊断 | DGraphicAcquireSMD核心函数, ApolloCT=0线程 |
| 8 | [progress_20260522.md](file:///d:/py/反编译/FreeStyle/apollo_dump/progress/progress_20260522.md) | 05-22 | GhidrAssistMCP安装, 16条失败路线 | GhidrAssistMCP对FreeStyle.exe分析完成(185s) |
| 9 | [progress_20260525.md](file:///d:/py/反编译/FreeStyle/apollo_dump/progress/progress_20260525.md) | 05-25 | SSKF二进制验证, 骨骼映射 | "flag字节"分类无效, ItemSubtype=+0x058 |
| 10 | [progress_20260526.md](file:///d:/py/反编译/FreeStyle/apollo_dump/progress/progress_20260526.md) | 05-26 | 源码验证SSKF全格式, PAK逆向 | 加载管线零校验, PAK头不统一(20B vs 16B) |

### 2.2 存档文档 (archive/)

| # | 文件 | 内容 |
|---|------|------|
| 11 | [plan_v2.md](file:///d:/py/反编译/FreeStyle/apollo_dump/archive/plan_v2.md) | 早期v2计划，含渲染管线、ItemCode链 |
| 12 | [plan_udp_crypto.md](file:///d:/py/反编译/FreeStyle/apollo_dump/archive/plan_udp_crypto.md) | UDP AES加密分析计划 |
| 13 | [apollo_input_filter_analysis.md](file:///d:/py/反编译/FreeStyle/apollo_dump/archive/apollo_input_filter_analysis.md) | Apollo输入过滤分析(API监控清单) |
| 14 | [xor_decoder_说明.md](file:///d:/py/反编译/FreeStyle/apollo_dump/archive/xor_decoder_说明.md) | TCP XOR解码器使用说明 |
| 15 | [CODE_WIKI.md](file:///d:/py/反编译/FreeStyle/apollo_dump/archive/CODE_WIKI.md) | 旧版WPF服装搭配工具代码存档 |
| 16 | [开发文档.md](file:///d:/py/反编译/FreeStyle/apollo_dump/archive/开发文档.md) | 旧版开发文档 |

### 2.3 早期工程文档 (docs/)

#### 01_项目基础
| # | 文件 | 内容 |
|---|------|------|
| 17 | [目录结构说明.md](file:///d:/py/反编译/FreeStyle/docs/01_项目基础/目录结构说明.md) | FS服装搭配专家 v5.3.6 工程结构 |
| 18 | [项目快速上手指南.md](file:///d:/py/反编译/FreeStyle/docs/01_项目基础/项目快速上手指南.md) | 开发环境搭建+代码逻辑学习路径 |
| 19 | [核心代码文件索引.md](file:///d:/py/反编译/FreeStyle/docs/01_项目基础/核心代码文件索引.md) | FrmMain.cs方法/变量索引表 |

#### 02_服装变更功能
| # | 文件 | 内容 |
|---|------|------|
| 20 | [服装变更逻辑分析.md](file:///d:/py/反编译/FreeStyle/docs/02_服装变更功能/服装变更逻辑分析.md) | **最详细** — pak复制/解包/替换/重打包全流程, itemshop.txt特效修改, res.pak规则 |

#### 03_批量变更功能
| # | 文件 | 内容 |
|---|------|------|
| 21 | [批量变更需求文档.md](file:///d:/py/反编译/FreeStyle/docs/03_批量变更功能/批量变更需求文档.md) | 批量变更的7个设计问题+决策(已确认方案A/B) |
| 22 | [批量变更实现说明.md](file:///d:/py/反编译/FreeStyle/docs/03_批量变更功能/批量变更实现说明.md) | **核心技术细节** — EnsurePakUnpacked, RunCmd防卡死, 路径引号修复, BatchSelectFrm列复制 |

#### 04_地图切换功能
| # | 文件 | 内容 |
|---|------|------|
| 23 | [地图切换功能需求文档.md](file:///d:/py/反编译/FreeStyle/docs/04_地图切换功能/地图切换功能需求文档.md) | stage02.pak替换方案, MapM数据模型, 完整的UI/代码设计 |
| 24 | [地图切换功能开发进度.md](file:///d:/py/反编译/FreeStyle/docs/04_地图切换功能/地图切换功能开发进度.md) | ✅功能完成, 已修复8个bug(ContextMenuStrip/DataGridView等) |

#### 05_背景切图功能
| # | 文件 | 内容 |
|---|------|------|
| 25 | [背景切图功能开发进度.md](file:///d:/py/反编译/FreeStyle/docs/05_背景切图功能/背景切图功能开发进度.md) | 1366x768→512x512切图, 补充字节(FillBytesFrm), u_background.pak, 项目DLL引用优化 |

#### 06_技术工具类
| # | 文件 | 内容 |
|---|------|------|
| 26 | [常见问题FAQ.md](file:///d:/py/反编译/FreeStyle/docs/06_技术工具类/常见问题FAQ.md) | resources.exe被杀软删, 卡死进程(taskkill), 编译命令 |
| 27 | [完整操作逻辑梳理.md](file:///d:/py/反编译/FreeStyle/docs/06_技术工具类/完整操作逻辑梳理.md) | 核心变量数据流转, 7阶段代码入口, itemshop.txt特效替换 |
| 28 | [调试监听器说明.md](file:///d:/py/反编译/FreeStyle/docs/06_技术工具类/调试监听器说明.md) | OperationDebugger日志格式+示例, 9种日志类型 |

#### 07_动态发型功能 (11篇 — 最重要)
| # | 文件 | 内容 |
|---|------|------|
| 29 | [动态发型功能开发进度.md](file:///d:/py/反编译/FreeStyle/docs/07_动态发型功能/动态发型功能开发进度.md) | 研究时间线: BML→SMD→物理, 工具安装指导(HxD/Blender/SMD插件) |
| 30 | [动态发型功能需求文档.md](file:///d:/py/反编译/FreeStyle/docs/07_动态发型功能/动态发型功能需求文档.md) | EffectCode无关论, 静态/动态样本定义, 5阶段开发计划 |
| 31 | [调试总结.md](file:///d:/py/反编译/FreeStyle/docs/07_动态发型功能/调试总结.md) | **最全面的技术分析(599行)** — DDynamicActor/DStaticActor类, FName系统, vtable, 物理初始化, CharacterMotion.bml, 方案A/B/C, 补丁实测崩溃分析 |
| 32 | [方案A_SMD注入物理骨骼.md](file:///d:/py/反编译/FreeStyle/docs/07_动态发型功能/方案A_SMD注入物理骨骼.md) | SMD文件级修改: 把物理骨骼(Bone01-11)注入静态SMD, 纯文件操作绕Apollo |
| 33 | [方案A实测失败分析.md](file:///d:/py/反编译/FreeStyle/docs/07_动态发型功能/方案A实测失败分析.md) | PAK内动态SMD也只有59骨! 物理不是靠SMD骨骼触发的. BML ItemCode≠mesh名. SMD后缀含义(MN/MS/MT/FN/FS/FT) |
| 34 | [方案B_纯内存读取分析.md](file:///d:/py/反编译/FreeStyle/docs/07_动态发型功能/方案B_纯内存读取分析.md) | ReadProcessMemory绕过Apollo, 通过字符串锚点定位函数, 诊断手段而非解决方案 |
| 35 | [方案C_DLL注入运行时Hook.md](file:///d:/py/反编译/FreeStyle/docs/07_动态发型功能/方案C_DLL注入运行时Hook.md) | Hook AddCtrlPointGrp, 动态创建Bone01-11. 包含变体C1(外部进程操控) C2(改pak配置) C3(改网络包) |
| 36 | [SSKF文件格式文档.md](file:///d:/py/反编译/FreeStyle/docs/07_动态发型功能/SSKF文件格式文档.md) | 从DSkin.cpp提取的**完整SSKF二进制规范**: SPackHeader, SBone(含v≤1 Scale 12B), SCtrlPoint, SMaterial, STexturedVertex, SSkinTriangle, SBoneInfluence(32B each), TArray格式, AcquireSMD加载流程, 源码文件索引 |
| 37 | [BML文件格式分析报告.md](file:///d:/py/反编译/FreeStyle/docs/07_动态发型功能/BML文件格式分析报告.md) | BML=XOR 0xFF加密的XML. 编码解码工具(bml_decoder.py). XML结构(根→channel→character→object→type/mesh/texture). 物理参数不存在于BML |
| 38 | [LoadItemFile函数分析.md](file:///d:/py/反编译/FreeStyle/docs/07_动态发型功能/LoadItemFile函数分析.md) | CCharacter::LoadItemFile完整源码级分析: LoadBinaryXML, aItemResource[MAX_MESH_COMP=5], channel/dwChannel, 道具信息加载流程 |
| 39 | [测试失败总结.md](file:///d:/py/反编译/FreeStyle/docs/07_动态发型功能/测试失败总结.md) | 第12块局部替换失败→完整BML替换失败(光头)→结论: 模型结构不兼容. 3个已否定方向(不要再走) |

#### 08_UI美化功能
| # | 文件 | 内容 |
|---|------|------|
| 40 | [Discord风格梦幻效果实现.md](file:///d:/py/反编译/FreeStyle/docs/08_UI美化功能/Discord风格梦幻效果实现.md) | NeonButton/GlassPanel/NeonLabel自定义控件, MaterialSkin集成, 渐变背景, 几何装饰 |

---

## 三、架构总览

### Apollo 4层保护 (更新于2026-05-22诊断)

```
L0: Apollo.sys         内核驱动, sc stop ApolloProtect 可停
L1: ApolloCT.dll       用户态 (6.7MB, VMProtect), ❌ 0保护线程(已死!)
L2: FreeStyle.exe 内嵌  启动时解密.text后退出, 含反调试(PEB/NtQIP/INT3/rdtsc)
L3: .text 段            40MB, 运行时解密, TrID识为 UPX
```

### 当前阻塞 (更新于2026-05-27)

| 阻塞 | 根因 | 状态 |
|------|------|------|
| DGraphicAcquireSMD入口未知 | 11种Frida盲搜全失败, SSKF在数据区非函数体 | ❌ |
| .text dump | ✅ **已完成** Pymem dump 40MB, 熵6.24 | ✅ |
| x32dbg附加即崩 | FreeStyle.exe本身内建反调试(非Apollo) | ❌放弃,用Frida |
| 改包/加包注入 | b0/b1全动态, seq冲突 | ⏸️放弃 |
| PAK离线修改 | 动态/静态类不兼容, 跨pak引用断裂, 大小不匹配 | ⚠️部分 |
| BML替换→光头 | SMD内部引用断裂/骨骼缺失 | ❌ |
| **动态/静态分支点** | **已定位!** cmp @ 0x021B4F57 | ✅ |

### 三重协议

```
TCP 443:    登录/控制, magic=43d58b80, XOR key=4db8a854, f12(seq)完全破解
UDP 18417:  游戏实时数据, C2S magic=907f, AES加密(key未破), S2C 93B包占63%
```

---

## 四、当前状态 (2026-05-27)

| 研究方向 | 状态 | 备注 |
|---------|------|------|
| Apollo 拆除 | ✅ 4层全部可控 | L0可停, L1 0线程, L2内建反调试(x32dbg仍被阻), L3可rwx |
| f12 校验 | ✅ 100% 破解 | 算法+delta+seed全通 |
| TCP XOR 解密 | ✅ 可用 | key=4db8a854 |
| TCP 改包注入 | ⏸️ 放弃 | b0/b1全动态, 无意义 |
| UDP AES 解密 | ❌ 未破 | 算法已知AES, key未找到 |
| DGraphicAcquireSMD定位 | ⚠️ 进展 | SSKF push xref 找到 5 处引用，函数入口待确认 |
| .text dump | ✅ **已完成** | Pymem dump 40MB, 熵6.24, dump/dump_text.bin |
| PAK离线修改 | ⚠️ 部分 | 大小不匹配/类不兼容 |
| CharacterMotion.bml | ❌ 不可修改 | 服务器下发, 不在本地PAK中 |
| ItemCode→b0/b1映射 | ⚠️ 少量验证 | 待批量导出 |
| DDynamicActor/DStaticActor | ✅ 已完整分析 | vtable, 构造函数, 物理初始化地址全已知 |
| **动态/静态分支点** | ⚠️ 已纠正 | 构造函数通过 new+placement 间接调用，无直接 E8 caller |
| **运行时Actor追踪** | ⚠️ 进行中 | Frida Hook崩溃(CRC), VEH+DR部分工作, Pymem堆扫描VirtualQueryEx bug待修 |

---

## 五、脚本索引

### Apollo拆除/诊断
| 脚本 | 作用 | 用法 |
|------|------|------|
| [x64dbg_enabler.py](file:///d:/py/反编译/FreeStyle/apollo_dump/x64dbg_enabler.py) | Frida注入: NtQVM欺骗+CRC patch+.text unlock+anti-debug | `py x64dbg_enabler.py` |
| [x64dbg_enabler.js](file:///d:/py/反编译/FreeStyle/apollo_dump/x64dbg_enabler.js) | Frida侧注入脚本 | 自动加载 |
| [verify_level2.py](file:///d:/py/反编译/FreeStyle/apollo_dump/verify_level2.py) | 验证L2欺骗是否生效 | `py verify_level2.py` |
| [decompile_apollo_sys.py](file:///d:/py/反编译/FreeStyle/apollo_dump/decompile_apollo_sys.py) | Apollo.sys反编译输出加载(1514函数) | |

### AcquireSMD 定位
| 脚本 | 作用 | 状态 |
|------|------|------|
| [locate_acquiresmd.py](file:///d:/py/反编译/FreeStyle/apollo_dump/locate_acquiresmd.py) | Frida扫描SSKF→回搜序言→hook验证 | ✅ SSKF@0x244B9C4(数据区) |
| [acquire_smd_hook.py](file:///d:/py/反编译/FreeStyle/apollo_dump/acquire_smd_hook.py) | Hook AcquireSMD | ❌ 入口未知 |
| [smd_redirect_v12.py](file:///d:/py/反编译/FreeStyle/apollo_dump/smd_redirect_v12.py) | SMD重定向 | ❌ 内部引用断裂 |

### ItemCode/背包扫描
| 脚本 | 作用 | 状态 |
|------|------|------|
| [scan_itemcode.py](file:///d:/py/反编译/FreeStyle/apollo_dump/scan_itemcode.py) | 内存扫描ItemCode | ✅ |
| [scan_descriptor_hair.py](file:///d:/py/反编译/FreeStyle/apollo_dump/scan_descriptor_hair.py) | 扫描发型描述符 | ✅ 商城预览有效 |
| [patch_itemcode.py](file:///d:/py/反编译/FreeStyle/apollo_dump/patch_itemcode.py) | ItemCode patch注入 | ✅ 商城, 退出恢复 |
| [patch_source.py](file:///d:/py/反编译/FreeStyle/apollo_dump/patch_source.py) | 源码级patch | ❌ |
| [inline_patch_equip.py](file:///d:/py/反编译/FreeStyle/apollo_dump/inline_patch_equip.py) | 内联patch装备 | ❌ SEH链崩溃 |

### BML/SMD hook
| 脚本 | 作用 | 状态 |
|------|------|------|
| [hook_bml.py](file:///d:/py/反编译/FreeStyle/apollo_dump/hook_bml.py) | BML ReadFile拦截 | ❌ BML已缓存 |
| [hook_smd_v1.py](file:///d:/py/反编译/FreeStyle/apollo_dump/hook_smd_v1.py) | SMD ReadFile拦截 | ❌ 不走ReadFile |

### 网络协议
| 脚本 | 作用 | 状态 |
|------|------|------|
| [analyze_game_f12.py](file:///d:/py/反编译/FreeStyle/apollo_dump/analyze_game_f12.py) | f12校验算法分析 | ✅ 完全破解 |
| [udp_key_crack.py](file:///d:/py/反编译/FreeStyle/apollo_dump/udp_key_crack.py) | UDP key暴力破解 | ❌ 4个版本全部失败 |

### x32dbg 工具链
| 脚本 | 作用 |
|------|------|
| [x32dbg_search.py](file:///d:/py/反编译/FreeStyle/apollo_dump/x32dbg_search.py) | x32dbg参数搜索/配置 |
| [check_plugin.py](file:///d:/py/反编译/FreeStyle/apollo_dump/check_plugin.py) | x32dbg插件检查 |

### 动态发型工具 (FreeStyle\ 根目录)
| 脚本 | 作用 |
|------|------|
| [sskf_tool.py](file:///d:/py/反编译/FreeStyle/sskf_tool.py) | SSKF二进制格式解析/序列化 |
| [inject_physics_bones.py](file:///d:/py/反编译/FreeStyle/inject_physics_bones.py) | 物理骨骼注入(方案A) |
| [repack_pak.py](file:///d:/py/反编译/FreeStyle/repack_pak.py) | PGFN PAK打包/验证/对比(方案A) |
| [dynamic_hair_patch.py](file:///d:/py/反编译/FreeStyle/dynamic_hair_patch.py) | WriteProcessMemory Code Cave补丁(调试总结§11.1) |

### Actor 运行时追踪
| 脚本 | 作用 | 状态 |
|------|------|------|
| [scan_actor_objects.py](file:///d:/py/反编译/FreeStyle/apollo_dump/scan_actor_objects.py) | Pymem 堆扫描 vtable, baseline/diff | ⚠️ VirtualQueryEx bug |
| [trace_actors.py](file:///d:/py/反编译/FreeStyle/apollo_dump/trace_actors.py) | Frida Interceptor hook 构造函数 | ❌ 崩溃(写.text) |
| [trace_actors_veh.py](file:///d:/py/反编译/FreeStyle/apollo_dump/trace_actors_veh.py) | Frida VEH + DR 硬件断点 | ❌ Apollo INT3干扰 |
| [trace_actors_dr.py](file:///d:/py/反编译/FreeStyle/apollo_dump/trace_actors_dr.py) | Pymem SetThreadContext DR 断点 | ❌ 需调试器配合 |

---

## 六、已确认失败路线

> **开始任何新工作前，先读 [failed_approaches.md](file:///d:/py/反编译/FreeStyle/apollo_dump/failed_approaches.md)**

关键失败根因 (16条):
1. **b0/b1全动态** — 改包 payload 无效
2. **模型已缓存(m_ItemCharArray)** — 改内存ItemCode无效
3. **不走文件API** — 自定义PAK I/O, hook CreateFileW/ReadFile无效
4. **不走CRT** — hook sprintf/printf/strcpy无效
5. **SEH链破坏** — inline patch崩溃
6. **SMD内部引用断裂** — 直接替换SMD骨骼/材质引用错乱
7. **动态/静态C++类不兼容** — DDynamicActor vs DStaticActor不同类
8. **AcquireSMD序言不在SSKF附近** — SSKF在数据区(字符串池)
9. **BML没有物理参数** — XOR 0xFF解码后是纯XML, 只含mesh/texture路径
10. **CharacterMotion.bml服务器下发** — 本地无法修改
11. **PAK中动态SMD也只有59骨** — 没有物理骨骼! 骨骼数≠文件大小
12. **物理不是靠SMD骨骼触发的** — 由C++类(vtable)决定
13. **Ghidra看的是加密.text** — 31009个"函数"是假阳性
14. **x32dbg附加被阻** — FreeStyle.exe内建反调试, 不是Apollo
15. **补丁动态初始化崩溃** — vtable替换+DynamicInit在构造中执行导致SEH失败
16. **加包注入失败** — seq/f12冲突导致游戏卡死

---

## 七、当前阻塞点 + 下一步方向

### 阻塞 #1: DGraphicAcquireSMD入口未知
- **方案**: Frida dump解密后的.text → Ghidra离线分析 → xrefs定位
- **操作**: 先dump `.text`(40MB), 再导入Ghidra重分析

### 阻塞 #2: .text静态分析无效
- **根因**: ApolloShell加密磁盘中的.exe .text段
- **方案**: Frida运行时dump → Ghidra离线分析

### 阻塞 #3: x32dbg附加即崩
- **根因**: FreeStyle.exe本体内建反调试(非Apollo)
- **方案**: 全用Frida调试(Frida能附加且不触发检测), 放弃x32dbg

### 阻塞 #4: 物理效果激活
- **已知路径**: SetMotionType(0x02297810) + vtable替换(0x284E0B4→0x284A9EC) + DynamicPhysicsInit(0x0229C2D0)
- **已知地址**: DDynamicActor真构造(0x229AE80), DStaticActor真构造(0x24C5520), DynamicInit(0x229B1D0)
- **上次尝试**: Code Cave补丁在构造中执行崩溃(SEH不匹配)
- **下一步**: 延迟补丁(不在构造中改, 在对象构造完成后再修改), 或 Hook工厂(0x021C1F00)

---

## 八、关键常量速查

| 常量 | 值 | 说明 |
|------|-----|------|
| FreeStyle.exe base | 0x400000 | |
| .text RVA | 0x1000 | size=40MB(0x280A000) |
| SSKF运行时地址 | 0x284B9C4 | base+0x244B9C4, **数据区字符串** |
| ApolloCT.dll | 0x69000000 (运行时变) | 6.7MB, **0保护线程** |
| TCP XOR key | 4DB8A854 | 4字节循环 |
| f12 seed | 登录时变 | 每次会话变化 |
| TCP magic | 43D58B80 | 12B头 |
| UDP C2S magic | 0x907F | |
| DDynamicActor 真vtable | 0x0284A9EC | COL@0x02897EC4, 7项验证PASS |
| DStaticActor 真vtable | 0x0284E0B4 | COL@0x02898AD8, 7项验证PASS |
| ~~DDynamicActor vftable~~ | ~~0x284AA4C~~ | 子表，非主vtable |
| ~~DStaticActor vftable~~ | ~~0x284E114~~ | 子表，非主vtable |
| DDynamicActor真构造 | 0x0229AE80 | vtable write @ 0x0229AEAB, 0个E8 caller |
| DStaticActor真构造 | 0x024C5520 | vtable write @ 0x024C5532, 0个E8 caller |
| ~~DDynamicActor构造~~ | ~~0x229B0B0~~ | 函数中间，非入口 |
| ~~DStaticActor构造~~ | ~~0x236B8A0~~ | 函数中间，非入口 |
| DynamicInit | 0x0229B1D0 | call [vtable+0x10], 物理参数初始化 |
| DynamicPhysicsInit | 0x0229C2D0 | 未重新验证 |
| SetMotionType | 0x02297810 | |
| CharacterMotion解析 | 0x21B46E0 | |
| 对象工厂 | 0x021C1F00 | |
| SSKF加载器 | 0x22ECCD0 | |
| CharacterMotion解析 | 0x021B42D0 | 4153B, 1 caller |
| **动态/静态分支点** | **0x021B4ED2** | **je (Type比较), 非分支选择** |
| CreateDynamicActor (步骤) | 0x021C0F00 | 943B, 与0x021C0F40顺序执行 |
| CreateStaticActor (步骤) | 0x021C0F40 | 879B, 与0x021C0F00顺序执行 |
| DDynamicActor 真正构造 | 0x0229AE80 | vtable write @ 0x0229AEAB |
| DStaticActor 真正构造 | 0x024C5520 | vtable write @ 0x024C5532 |
| DDynamicActor 真正vtable | 0x0284A9EC | COL @ 0x02897EC4 |
| DStaticActor 真正vtable | 0x0284E0B4 | COL @ 0x02898AD8 |
| DynamicInit | 0x0229B1D0 | call [vtable+0x10], 物理参数初始化 |
| DStaticActor 创建wrapper | 0x0236B340 | call 0x024C5520 + 字段初始化 |

---

## 九、常用命令速查

```powershell
# subst映射(每次重启后执行, 避免中文路径问题)
subst X: "D:\py\反编译"

# 扫描游戏进程
Get-Process FreeStyle

# 停Apollo驱动
sc.exe stop ApolloProtect
sc.exe config ApolloProtect start=disabled

# 启动Ghidra headless (需先subst + cd实体路径)
& "X:\ghidra_12.0.1_PUBLIC\support\analyzeHeadless.bat" ^
  "D:\ghidra_projects" "FreeStyleProject" -process ^
  -scriptPath "C:\Users\w\.ghidra\.ghidra_12.0.1_PUBLIC\Extensions\GhidrAssistMCP\ghidra_scripts" ^
  -preScript StartMCPServer.java ^
  -postScript BlockForeverScript.java

# 跑Frida脚本
cd D:\py\反编译\FreeStyle\apollo_dump
python x64dbg_enabler.py

# 编译FS服装搭配专家
cd "D:\py\反编译\FS服装搭配专家v5.3.6"
msbuild FS服装搭配专家v5.3.6.csproj /p:Configuration=Debug /p:Platform=x86

# 清理卡死的resources.exe
taskkill /F /IM resources.exe
```

---

## 十、新会话启动步骤

1. **读本文件** (CLAUDE.md) — 了解整体结构
2. **读 [failed_approaches.md](file:///d:/py/反编译/FreeStyle/apollo_dump/failed_approaches.md)** — 避免重复已失败路线
3. **读最新进度** `progress/progress_20260526.md` — 了解最新进展
4. **参考核心分析**: [调试总结.md](file:///d:/py/反编译/FreeStyle/docs/07_动态发型功能/调试总结.md) (DDynamicActor/DStaticActor)
5. **参考核心分析**: [SSKF文件格式文档.md](file:///d:/py/反编译/FreeStyle/docs/07_动态发型功能/SSKF文件格式文档.md) (SSKF二进制格式)
6. **参考战略总纲**: [apollo_killplan.md](file:///d:/py/反编译/FreeStyle/apollo_dump/apollo_killplan.md)
7. **确认交叉引用关系**: failed_approaches ↔ killplan ↔ progress ↔ 调试总结
8. **总结当前阻塞点**后再开始工作