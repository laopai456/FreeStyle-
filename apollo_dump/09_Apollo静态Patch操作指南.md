# Apollo.sys 静态 Patch 操作指南

> 本文档详细说明如何通过静态 Patch Apollo.sys 绕过 Apollo 保护，使硬件断点可用。
> 适用于 FreeStyle 街头篮球游戏。

---

## 一、目标

**绕过 Apollo 的 DR 寄存器清零机制**，使硬件断点可以正常设置，从而能够：
1. 追踪练习场阶段的 ItemCode 读取来源
2. Hook 练习场专用的加载路径
3. 实现练习场阶段的发型替换

---

## 二、Apollo 保护机制回顾

### 2.1 三层架构

| 层级 | 组件 | 保护机制 | 当前状态 |
|------|------|----------|----------|
| L0 | Apollo.sys 内核驱动 | DR 清零、反调试 | `sc stop` 可停，但运行时仍会干扰 |
| L1 | ApolloCT.dll | CRC 检查线程 | 已 patch 废掉 |
| L2 | FreeStyle.exe 内嵌 | .text 页属性扫描、API hook | 无法直接绕过 |

### 2.2 DR 清零机制

Apollo.sys 中的 `DR_clear_area` 函数会定期清零调试寄存器（DR0-DR3），导致硬件断点失效。

**关键函数**：
```
DR_clear_area @ VA 0x140001986
  └── 调用 FUN_140063780 (真正的 DR 处理逻辑)
```

**Patch 目标**：让 `DR_clear_area` 直接返回，不执行清零操作。

---

## 三、技术路线

```
┌─────────────────────────────────────────────────────────────┐
│ 步骤 1: 备份原始 Apollo.sys                                  │
├─────────────────────────────────────────────────────────────┤
│ 步骤 2: 解压 UPX（Apollo.sys 是 UPX 压缩的）                  │
├─────────────────────────────────────────────────────────────┤
│ 步骤 3: 计算文件偏移（VA → 文件偏移）                          │
├─────────────────────────────────────────────────────────────┤
│ 步骤 4: Patch DR_clear_area 入口为 RET                       │
├─────────────────────────────────────────────────────────────┤
│ 步骤 5: 开启 Windows 测试模式                                 │
├─────────────────────────────────────────────────────────────┤
│ 步骤 6: 替换系统驱动文件                                       │
├─────────────────────────────────────────────────────────────┤
│ 步骤 7: 重启系统，验证效果                                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 四、详细步骤

### 步骤 1：备份原始 Apollo.sys

```powershell
# 创建工作目录
mkdir D:\Apollo_Patch
cd D:\Apollo_Patch

# 备份原始文件
copy "C:\Windows\System32\drivers\Apollo.sys" "Apollo.sys.original"

# 复制一份用于修改
copy "C:\Windows\System32\drivers\Apollo.sys" "Apollo.sys.patched"
```

**重要**：保留原始文件备份，以便回滚。

---

### 步骤 2：解压 UPX

Apollo.sys 是 UPX 压缩的，需要先解压才能修改。

```powershell
# 下载 UPX
# https://github.com/upx/upx/releases
# 下载 upx-x.xx.x-win64.zip，解压到 D:\upx

# 解压 Apollo.sys
D:\upx\upx.exe -d Apollo.sys.patched
```

**验证解压成功**：
```powershell
# 检查文件大小变化（解压后会变大）
dir Apollo.sys.*
```

---

### 步骤 3：计算文件偏移

**VA 到文件偏移的转换**：

```
目标 VA: 0x140001986
基址:    0x140000000
RVA:     0x1986 (VA - 基址)
```

**需要分析 PE 节表**：

| 节名 | VA 范围 | 文件偏移范围 |
|------|---------|-------------|
| .text | 0x1000 - 0x1FFF | 0x400 - 0x15FF |
| .rdata | 0x3000 - 0x3FFF | 0x1600 - 0x1BFF |
| ... | ... | ... |

**计算公式**：
```
文件偏移 = RVA - 节.VA + 节.文件偏移
```

**对于 DR_clear_area (RVA 0x1986)**：
- 落在 .text 节（VA 0x1000 开始）
- 文件偏移 = 0x1986 - 0x1000 + 0x400 = 0xD86

**实际操作**：运行 `python patch_apollo_sys.py` 自动计算。

---

### 步骤 4：Patch DR_clear_area

**目标**：将函数入口改为 `RET`，使其直接返回。

**原始字节**（可能）：
```
41 55        push r13
...
```

**Patch 后**：
```
C3           ret
```

**方法 1：使用 Python 脚本**

```powershell
python D:\py\反编译\FreeStyle\apollo_dump\patch_apollo_sys.py
```

**方法 2：使用 HxD / 010 Editor 手动修改**

1. 打开 `Apollo.sys.patched`
2. 跳转到偏移 `0xD86`（或脚本计算的偏移）
3. 将第一个字节改为 `C3`
4. 保存文件

---

### 步骤 5：开启 Windows 测试模式

Patch 后驱动签名失效，需要开启测试模式才能加载。

```powershell
# 管理员 PowerShell
bcdedit /set testsigning on

# 验证
bcdedit /enum
# 应看到 "testsigning Yes"
```

**注意**：开启测试模式后，桌面右下角会显示"测试模式"水印。

---

### 步骤 6：替换系统驱动文件

```powershell
# 管理员 PowerShell

# 1. 停止 Apollo 服务
sc stop ApolloProtect

# 2. 取得文件所有权
takeown /f "C:\Windows\System32\drivers\Apollo.sys"

# 3. 获取完全控制权限
icacls "C:\Windows\System32\drivers\Apollo.sys" /grant Administrators:F

# 4. 替换文件
copy /Y "D:\Apollo_Patch\Apollo.sys.patched" "C:\Windows\System32\drivers\Apollo.sys"

# 5. 验证文件已替换
dir "C:\Windows\System32\drivers\Apollo.sys"
```

---

### 步骤 7：重启系统并验证

```powershell
# 重启
shutdown /r /t 0

# 重启后验证
# 1. 检查测试模式水印
# 2. 运行硬件断点测试
python D:\py\反编译\FreeStyle\apollo_dump\test_64bit_setcontext.py
```

**成功标志**：
```
验证: DR0=0x... DR7=0x...  ← 非零值
✅ 成功！硬件断点已设置
```

---

## 五、验证流程

### 5.1 硬件断点测试

```powershell
# 64 位 Python 运行
python test_64bit_setcontext.py
```

**预期输出**：
```
当前: EIP=0x... DR0=0x0
设置: DR0=0x... DR7=0xffff0055
验证: DR0=0x... DR7=0xffff0055  ← 成功！
```

### 5.2 游戏运行测试

1. 启动游戏
2. 检查是否正常运行（Apollo 可能检测到修改）
3. 如果游戏崩溃，说明 Patch 位置不对或有其他检测

---

## 六、回滚方案

如果 Patch 失败或游戏无法运行：

```powershell
# 管理员 PowerShell

# 1. 恢复原始驱动
copy /Y "D:\Apollo_Patch\Apollo.sys.original" "C:\Windows\System32\drivers\Apollo.sys"

# 2. 关闭测试模式
bcdedit /set testsigning off

# 3. 重启
shutdown /r /t 0
```

---

## 七、风险提示

| 风险 | 说明 |
|------|------|
| **游戏封号** | 修改反作弊驱动可能导致封号 |
| **系统不稳定** | 测试模式允许未签名驱动，可能影响系统稳定性 |
| **Apollo 更新** | 游戏更新后 Apollo.sys 可能变化，需要重新 Patch |
| **检测绕过失败** | Apollo 可能有其他检测机制（L2 内嵌） |

---

## 八、后续工作（Patch 成功后）

### 8.1 追踪练习场 ItemCode 来源

```powershell
# 设置硬件断点监控 ItemCode 地址
python trace_itemcode_reader.py
```

### 8.2 Hook 练习场加载路径

找到练习场获取 ItemCode 的函数后：
1. 分析函数调用链
2. 找到安全的 hook 点（系统 DLL 或非保护区域）
3. 实现 ItemCode 替换

---

## 九、文件清单

| 文件 | 路径 | 用途 |
|------|------|------|
| Apollo.sys.original | D:\Apollo_Patch\ | 原始备份 |
| Apollo.sys.patched | D:\Apollo_Patch\ | Patch 后的驱动 |
| patch_apollo_sys.py | apollo_dump\ | 自动 Patch 脚本 |
| test_64bit_setcontext.py | apollo_dump\ | 硬件断点测试脚本 |
| trace_itemcode_reader.py | apollo_dump\ | ItemCode 追踪脚本 |

---

## 十、常见问题

### Q: UPX 解压失败？

**原因**：Apollo 可能使用了自定义 UPX 或其他壳。

**解决**：
1. 尝试不同版本的 UPX
2. 使用专业脱壳工具（如 PE-bear, x64dbg 脱壳插件）
3. 直接在运行时 dump 解压后的内存

### Q: Patch 后游戏崩溃？

**原因**：
1. Patch 偏移错误
2. Apollo 有完整性自检
3. L2 内嵌检测

**解决**：
1. 重新计算偏移
2. 尝试 Patch 其他位置
3. 分析崩溃日志定位问题

### Q: 硬件断点仍然失败？

**原因**：
1. Patch 未生效（驱动未加载修改后的版本）
2. L2 内嵌了额外的保护机制

**解决**：
1. 验证驱动文件确实被替换
2. 检查是否有多个 Apollo 组件需要 Patch

---

## 十一、技术细节补充

### 11.1 DR_clear_area 函数分析

```c
// 反编译结果
void FUN_140001986(undefined8 param_1) {
  FUN_140063780(param_1);  // 调用真正的 DR 处理逻辑
  return;
}
```

**Patch 策略**：
- 方案 A：入口 NOP (`90 90`)
- 方案 B：入口 RET (`C3`) ← 推荐，直接返回

### 11.2 PE 节表结构

```
节名      VA       大小     文件偏移   原始大小
.text    0x1000   0x1200   0x400     0x1200
.rdata   0x3000   0x600    0x1600    0x600
.data    0x4000   0x400    0x1C00    0x400
.pdata   0x5000   0x200    0x2000    0x200
.INIT    0x6000   0x400    0x2200    0x400
.UPX0    0x7000   0x233A00 0x2600    0x233A00  ← UPX 压缩数据
.reloc   0x23B000 0x200    0x236000  0x200
```

### 11.3 测试模式说明

```
bcdedit /set testsigning on
```

**效果**：
- 允许加载未签名/签名无效的驱动
- 桌面显示"测试模式"水印
- 不影响 Windows 更新

**关闭**：
```
bcdedit /set testsigning off
```

---

> 更新时间：2026-06-01
> 状态：待验证
> 下一步：执行步骤 1-7，验证硬件断点是否可用