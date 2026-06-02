---
name: "game-debugging"
description: "FreeStyle 游戏调试助手(x64dbg MCP)。当用户需要用x64dbg调试游戏、设断点、单步执行、内存搜索、反汇编分析时调用此技能。"
auto_load: true
---

# FreeStyle 游戏调试助手 (x64dbg MCP)

## 调试环境

### 工具链

| 工具 | 路径 | 用途 |
|------|------|------|
| x32dbg-unsigned | `D:\py\release\x32\x32dbg-unsigned.exe` | 32位调试器 |
| x64dbg-automate MCP | pip 安装，MCP 配置 | Trae IDE 远程控制 |
| ScyllaHide | x32dbg 插件 | 反反调试 |
| resources.exe | `d:\py\反编译\FreeStyle\pack\resources.exe` | PAK 解包/打包 |

### MCP 配置

文件：`d:\py\反编译\.trae\mcp.json`
```json
{
  "mcpServers": {
    "x64dbg": {
      "command": "cmd",
      "args": ["/c", "npx", "-y", "x64dbg-mcp-server"],
      "timeout": 1800,
      "disabled": false
    }
  }
}
```

### 使用步骤

1. 以**管理员身份**运行 `D:\py\release\x32\x32dbg-unsigned.exe`
2. Options → Preferences → Engine → 勾选 Enable Debug Privilege
3. **异常设置**：Options → Preferences → 异常标签 → 把所有异常移到右侧（忽略）
4. File → Attach → 选 FreeStyle.exe
5. 按 F9 运行（可能需要多次）
6. Trae 里通过 MCP 连接：`mcp_x64dbg_connect_to_session`

## MCP 命令速查

### 连接

| 命令 | 说明 |
|------|------|
| `list_sessions` | 列出可用的 x32dbg 实例 |
| `connect_to_session(pid)` | 连接到已有实例 |

### 调试控制

| 命令 | 说明 |
|------|------|
| `get_debugger_status` | 查看调试状态 |
| `go(pass/swallow_exceptions)` | 继续运行 |
| `pause()` | 暂停 |
| `step_into(count)` | 单步进入 |
| `step_over(count)` | 单步越过 |

### 内存操作

| 命令 | 说明 |
|------|------|
| `read_memory(address, size)` | 读内存 |
| `write_memory(address, hex_data)` | 写内存 |
| `get_memory_map()` | 内存映射 |
| `allocate_memory(size)` | 分配内存 |

### 断点

| 命令 | 说明 |
|------|------|
| `set_breakpoint(address, bp_type)` | 设断点 |
| `clear_breakpoint(address, bp_type)` | 删断点 |
| `list_breakpoints(bp_type)` | 列出断点 |

### 搜索与分析

| 命令 | 说明 |
|------|------|
| `disassemble(address, count)` | 反汇编 |
| `eval_expression(expression)` | 求值表达式 |
| `execute_command("find ADDR, HEX")` | 搜索字节 |
| `execute_command("findall ADDR, HEX")` | 搜索所有匹配 |

## APOLLO 注意事项

- APOLLO 在 `0x2C00000 - 0x2CDA000`
- attach 后 APOLLO 会循环设断点导致游戏暂停
- ScyllaHide 已安装但**不足以绕过 APOLLO**
- `swallow_exceptions=true` 可临时绕过 APOLLO 中断
- 内存断点按 4KB 页生效，在代码段设内存断点会导致频繁暂停

## 典型调试场景

### 场景 1：定位函数引用

```
1. 已知字符串地址（如 0x28405CC）
2. execute_command("find 401000, 68CC052802")  // push 0x028405CC
3. 找到引用 → disassemble(ref_addr, 20) 反汇编上下文
```

### 场景 2：跟踪对象创建

```
1. set_breakpoint(0x021C1F00, "software")  // 工厂函数
2. go()  // 继续运行
3. 断到后 get_all_registers() 看参数
4. step_over() 跟踪返回值
```

### 场景 3：内存搜索 vtable

```
1. execute_command("findall 400000, 4CA18402")  // 搜索 0x0284AA4C (DDynamicActor vtable)
2. 过滤结果：排除 .rdata 段的（那是 vtable 表本身）
3. 剩余的就是 DDynamicActor 对象实例
```

### 场景 4：对比基类构造函数

```
1. disassemble(0x02299BD0, 50)  // DDynamicActor 基类构造
2. disassemble(0x0236B9F0, 50)  // DStaticActor 基类构造
3. 对比两者初始化的字段差异
```

## 注意事项

- `findallmem` 对字符串参数会失败，必须用十六进制
- `write_memory` 写代码段会触发 APOLLO
- 调试会话断开后游戏可正常运行
- 建议：先暂停分析（只读），确认安全后再写
