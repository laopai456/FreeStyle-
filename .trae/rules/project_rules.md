# 项目规则

## 默认加载的 Skill

在处理此项目时，默认加载以下 skill：

- **fs**: FS服装搭配专家 UI开发助手
- **superpowers-zh**: Superpowers-ZH 中文增强技能框架

### 逆向工程 Skills

| Skill | 用途 | 触发条件 |
|-------|------|---------|
| reverse-engineering | 核心逆向分析（地址定位、RTTI、vtable、类继承） | 分析二进制格式、定位函数地址、理解类关系 |
| memory-patch | 内存补丁（WriteProcessMemory、堆数据修改） | 修改游戏运行时内存、Code Cave 注入 |
| game-debugging | 游戏调试（x64dbg MCP 远程控制） | 用 x64dbg 调试游戏、设断点、反汇编 |
| pak-tool | PAK 文件操作（解包/打包/验证） | 操作 PAK 文件、替换 SMD/BML |
| apollo-bypass | APOLLO 反作弊分析与绕过 | 讨论 APOLLO 检测、需要绕过保护 |

### 逆向方法论

每次逆向任务前，先回顾 `reverse-methodology.md` 中的核心原则（双路并行、特征指令预扫描、策略切换触发器、反模式）。这些规则基于 [lbh666/game-re-framework](https://github.com/lbh666/game-re-framework) 的实战经验提炼。

核心纪要：
- **双路并行**: 自顶向下（调用链）+ 自底向上（特征搜索）同时推进，任一路连续3轮无进展则切换
- **搜索参照物**: 搜 CODE 中引用 DATA 的指令（如 push offset），不搜数据字节本身
- **反模式**: 一条路卡住后死磕（如扫 SSKF 字节 16KB 无结果仍加大到 64KB，应立即切 ReadFile hook）

### Superpowers-ZH 已复制 Skills

| Skill | 用途 | 源码 |
|-------|------|------|
| brainstorming | 功能设计前的需求分析和方案探索 | mouyu |
| chinese-code-review | 中文代码审查规范（专业且有礼貌的反馈） | mouyu |
| chinese-commit-conventions | 中文 Commit Message 格式规范 | mouyu |
| executing-plans | 执行书面实现计划 | mouyu |
| requesting-code-review | 完成任务/合并前请求代码审查 | mouyu |
| subagent-driven-development | 子智能体驱动的并行开发（每个任务独立执行+双阶段审查） | mouyu |
| systematic-debugging | 系统化调试：根因分析→模式对比→假设验证→修复 | mouyu |
| test-driven-development | TDD 测试驱动开发（红-绿-重构循环） | mouyu |
| verification-before-completion | 宣称完成前必须先运行验证命令 | mouyu |
| writing-plans | 编写多步骤实现计划 | mouyu |

## 编译/验证命令

### Python 脚本验证
```powershell
py d:\py\反编译\FreeStyle\sskf_tool.py              # SSKF 解析回环测试
py d:\py\反编译\FreeStyle\inject_physics_bones.py    # 物理骨骼注入
py d:\py\反编译\FreeStyle\repack_pak.py --help        # PAK 重打包
```

### WPF 项目编译（fs skill）
```powershell
dotnet build   # 在 FS服装搭配专家 项目根目录下执行
```

## 设计先于编码

收到新功能/修改需求时，先使用 `brainstorming` skill 进行需求分析和方案探索，获得用户批准后再使用 `writing-plans` skill 创建实现计划。

## 测试先于实现

所有代码修改在实现前应先有验证手段：
- SSKF 解析：round_trip_test() 确保字节级一致
- 骨骼注入：verify() 函数校验骨骼层次
- PAK 打包：readback 验证完整性

## 验证先于完成

**宣称完成前必须运行验证命令** — 遵循 `verification-before-completion` skill 的铁律：没有新鲜的验证证据，不许宣称完成。

## Git 提交规范

commit message 使用中文，格式遵循 `chinese-commit-conventions` skill：
```
<type>(<scope>): <中文描述>
```
类型：feat / fix / docs / refactor / test / chore

---

## SMD 注入 → PAK 打包 → 游戏测试 标准化操作流程（SOP）

> **核心原则**：每一步都有可验证的 Memento（证据），每种异常都有对应的处理方式。

### 阶段 0：准备工作

- [ ] 确认原始 PAK 已备份（`res764.pak.bak` 存在，来源可靠）
- [ ] 确认 PAK 文件可打开：`py repack_pak.py --pak <pak_path> --list`
- [ ] 记录原始 PAK 的完整 MD5 — 替换后可以回滚
- [ ] 工作目录：`d:\py\反编译\FreeStyle\cookies\res764_smd\`

### 阶段 1：注入物理骨骼

**命令**：
```powershell
cd /d d:\py\反编译\FreeStyle
py inject_physics_bones.py
```

**验证项（脚本会自动输出）**：

| 验证点 | 预期输出 | 异常处理 |
|--------|----------|----------|
| 输入文件 MD5 显示 | 非空 MD5 值，与历史一致 | 文件可能被修改过，检查来源 |
| 输出文件 `i50125001_MT_static_injected.smd` 创建成功 | 文件大小 ≈ 940KB（与 static SMD 相近） | 注入失败，检查控制台报错 |
| 输出文件 MD5 | 非空值，记录到下方 |  |
| 骨骼总数 = 75 | `Bone count: 75 (expected 75)` | 骨骼数不对 → 中止，检查 dynamic SMD 的骨骼结构 |
| Bip01 Head num_children = 2 | `Bip01 Head: num_children=2 ✓` | 父骨骼关系错误 → 中止，检查索引映射 |
| Dummy_center parent=8, children=16 | 全部显示 ✓ | 层级错误 → 中止 |
| 16 个物理骨骼名称全部匹配 | `All 16 physics bones verified ✓` | 名称不匹配 → 中止，检查 physics bone indices |
| Round-trip 验证通过 | `Round-trip verification PASSED ✓` | 解析/序列化不一致 → 中止，检查 sskf_tool.py |
| 所有验证通过 | `All verifications PASSED!` | 有任何 FAILED → 中止，先排查 |

**用户自查方法**：
```powershell
# 单独跑验证（不重新注入）
py -c "exec(open('inject_physics_bones.py').read().split('if __name__')[0]);\
from inject_physics_bones import verify; verify()"
```

**异常处理**：
- 如果 round-trip 失败：表示 SSKF 解析器有 bug，不能用于打包
- 如果骨骼名不匹配：dynamic SMD 可能变了，需要重新确认骨索引

### 阶段 2：PAK 打包前验证

在打包之前，确认原始 PAK 和注入产物的状态。

**验证当前 pak 完整性**：
```powershell
py repack_pak.py --pak "<pak_path>" --verify
```
输出的每行应显示：
- 目标文件行（如 `i50125001_MT.smd`）显示 `InPak=✓` 且有 MD5 值
- 如果看到 `InPak=✗` → PAK 已损坏，不要继续，从备份恢复

**查看目标文件在当前 PAK 中的 MD5**：
```powershell
py repack_pak.py --pak "<pak_path>" --file i50125001_MT.smd --checksum
```

**记录现场**（复制保存以下信息）：
```
原始PAK路径: <pak_path>
原始PAK大小: <bytes>
原始PAK整体MD5: <通过 --verify 获取>
目标文件: i50125001_MT.smd
目标文件原始MD5: <通过 --checksum 获取>
注入文件MD5: <从阶段1的输出获取>
```

### 阶段 3：打包（写入 PAK）

**3A. 先做 DRY-RUN（预览，不实际修改）**：
```powershell
py repack_pak.py --pak "<pak_path>" --file i50125001_MT.smd --input "d:\py\反编译\FreeStyle\cookies\res764_smd\i50125001_MT_static_injected.smd" --mode rebuild --dry-run
```

**预期输出**：显示替换文件信息和大小变化，末尾显示 `DRY-RUN 完成，未做任何修改。`

**3B. 确认无误后执行实际替换**：
```powershell
py repack_pak.py --pak "<pak_path>" --file i50125001_MT.smd --input "d:\py\反编译\FreeStyle\cookies\res764_smd\i50125001_MT_static_injected.smd" --mode rebuild
```

**3C. 打包后验证**：

脚本会自动执行验证：
- 显示重建的 PAK 文件列表（前5个 + 后2个）
- 显示 `验证通过!` 和块数量
- 显示新 PAK 整体 MD5，并确认 `新pak MD5与原始不同`

**用户手动验证**：
```powershell
# 重新打开新pak并完整验证
py repack_pak.py --pak "<pak_path>" --verify
```
逐个检查：
| 验证点 | 预期 | 异常处理 |
|--------|------|----------|
| 魔数 | `✓ PGFN` | 文件可能坏了，从备份恢复 |
| 声明文件数 = 实际解析数 | 数字相等 | PAK 结构异常，需要从备份恢复 |
| 目标文件 InPak | `✓` | 文件丢失，可能是重建 bug |
| 目标文件 MD5 已变化 | 与阶段1记录的注入文件 MD5 一致 | 内容没有正确替换 → 重新打包 |
| 其他文件 MD5 **没有变化** | 与阶段2记录的原始值一致 | 打包工具 bug 影响了其他文件 |
| 整体 PAK MD5 已变化 | 与阶段2记录的原始 MD5 不同 | 说明确实被修改了 |

**异常处理**：
- 如果 `替换时出错 ValueError`：PAK 格式不兼容，用 `--output` 输出到单独文件
- 如果 `新pak MD5与原始相同`：内容没有实际修改，检查注入产物是否正确
- 如果其他文件的 MD5 变化了：打包工具 bug，**不要**将此 PAK 复制到游戏目录

### 阶段 4：部署到游戏目录

```powershell
# 先用 --compare 确认修改范围正确
py repack_pak.py --pak "<游戏目录>\res764.pak" --compare "<打包产物路径>"

# 如果备份不存在，先备份
copy "<游戏目录>\res764.pak" "<游戏目录>\res764.pak.bak"

# 复制修改后的 PAK
copy "<打包产物路径>" "<游戏目录>\res764.pak"
```

**验证点**：
- `--compare` 输出中只显示 `i50125001_MT.smd` 被修改，其他文件不变
- 如果显示多个文件被修改 → 打包过程有问题

### 阶段 5：游戏内测试

启动游戏，装备「可爱加倍发型」(ItemCode 50125001)，检查：

| 验证点 | 操作 | 预期 |
|--------|------|------|
| 游戏启动 | 正常启动 | 不崩溃，不闪退 |
| 角色显示 | 进入游戏，查看角色 | 发型正常显示（不是光头） |
| 物理效果 | 在游戏内移动/跳跃 | 头发有物理摆动效果（与动态发型一致） |

### 回滚方案

如果游戏测试失败，随时恢复备份：
```powershell
copy "<游戏目录>\res764.pak.bak" "<游戏目录>\res764.pak"
```
然后在阶段1排查问题：骨骼名异常 / round-trip 失败 / AIO 偏移错误 等。

### 每步证据留存清单（Memento）

完成一次完整流程后，应保留以下证据链：

```
日期: _________
原始PAK MD5: _________
注入前目标文件MD5: _________
注入后文件MD5: _________
打包后PAK MD5: _________
部署后对比结果: [仅目标文件变化 / 其他文件也变了]
游戏测试结果: [正常 / 光头 / 崩溃]
回滚操作: [是 / 否]
问题简述: _________
```