# FreeStyle 装备搭配专家 v2.0 — 架构与机制速查

> 街头篮球(FreeStyle)装备外观/特效替换工具。v2.0 改用 Frida hook 方案(v1.0 在 `1.0/`,已归档)。
> 本文供快速理解项目,定位 bug 时先读这里。

## 三层架构

```
┌─────────────────┐   TCP 18731   ┌──────────────────────┐   Frida   ┌──────────────┐
│  C# WPF 主程序   │ ────────────► │  Python engine       │ ────────► │ FreeStyle.exe│
│  (UI + 启动引擎) │ ◄──────────── │  server.py           │ ◄──────── │ (游戏 PID)   │
└─────────────────┘               └──────────────────────┘           └──────────────┘
        ▲                                   ▲
        │ TCP 18731 (多客户端)              │ stdio (MCP 协议)
        │                                   │
┌─────────────────┐               ┌──────────────────────┐
│  MCP server      │ ────────────► │  (同一个 engine)      │
│ freestyle_mcp_   │ ◄──────────── │                      │
│ server.py        │               └──────────────────────┘
└─────────────────┘
```

- **C# WPF 主程序**(`2.0/UI`, `2.0/Core`):UI、按钮状态机、启动/管理 engine 进程(`FridaBridge.cs`)、TCP 客户端。
- **Python engine**(`2.0/engine/server.py`):TCP server(端口 **18731**,多客户端,每连接一线程)、Frida attach、Windows API 内存扫描。**运行中缓存的 `create_js` 只有重启 engine 才会更新**。
- **MCP server**(`2.0/freestyle_mcp_server.py`):供 Claude 调用,是 engine TCP 的**薄封装**(每次 `_send_cmd` 新建 TCP 连接,无状态)。同时含本地 PAK/BML/SSKF 解析工具。

## 关键文件

| 文件 | 作用 |
|---|---|
| `2.0/engine/hook_manager.py` | `create_js()` 生成 Frida JS 脚本(模板字符串)。**改 JS 逻辑改这里**。 |
| `2.0/engine/server.py` | engine 主体:TCP server、命令分发、`native_dword_scan`/`native_brute_scan`/`native_restore_shop`(Windows API 扫描)、`on_message`(JS→Python 日志)。 |
| `2.0/engine/optimized_scanner.js` | 旧版扫描器(当前 hook_manager.py 内嵌 CModule,这个文件疑似未用)。 |
| `2.0/freestyle_mcp_server.py` | MCP 工具定义(frida_connect/status、read/replace/restore/recollect_outfit、dword_scan、get_hook_log、pak 解析等)。 |
| `2.0/UI/Windows/MainWindow.xaml(.cs)` | 主界面、装备槽、按钮状态机、呼吸灯特效。 |
| `2.0/UI/Resources/Styles.xaml` | 按钮样式 + VisualStateManager 动画。 |
| `2.0/Core/Services/FridaBridge.cs` | C# 端 engine 进程管理 + TCP 通信。 |

## engine 的三个副本(重要!)

源代码与构建输出并存,**改代码后要同步到运行目录**:

- `2.0/engine/` — 源(改这里)
- `2.0/bin/Debug/net8.0-windows/engine/` — **Debug 运行目录(engine 实际从这里启动)**
- `2.0/bin/Release/net8.0-windows/engine/` — Release 副本(较旧)

改 `2.0/engine/` 后,务必 `cp` 覆盖到 `bin/Debug/.../engine/`,否则 engine 加载的还是旧文件。改完 **必须重启 engine 进程**(Python import 缓存),仅 `replace_outfit`/重连不够。

## 装备替换核心机制

### 数据结构
- **属性表条目标志**:道具 ItemCode 在内存中是一个 DWORD,其后 `+0x04 == 0x00010000` 表示这是"属性表条目"(装备定义)。商城/背包数据没有此标志。
- **特效槽**:属性表条目的 `+0x08` = 特效 ID,`+0x0C == 0x00010000` 表示下一条是特效条目。

### 两套替换路径
1. **房间场景(sprintf hook)**:游戏 `sprintf` 格式化 `customize/.../item%d...` 路径时触发。命中 `REPLACE_MAP` 则改 `args[2]` + ebp 栈 + `dwordScan`(写特效,有 `+0x04` flag 检查)。
2. **练习场场景(strcpy hook)**:路径替换 + `bruteDwordScan`(暴力扫描,**无 flag 检查**,因为练习场数据无标志)。

### 内存扫描三种实现
- `native_dword_scan`(server.py):房间用,有 flag 检查,只替换属性表条目。
- `native_brute_scan`(server.py):练习场用,无 flag 检查。
- JS 内嵌 CModule(`hook_manager.py`):`_nativeScanFn` 单遍 src→dst。⚠️ **CModule 路径只做正向替换,不做 dst→src 反向恢复**(JS 降级路径有反向)。这是潜在内存残留隐患。

### 收集机制(本次修复重点)
- JS 全局:`collected`(append-only,key=collectIndex)、`seenCodes`(去重表)、`currentCharCcode`(当前角色)。
- `read_current_outfit` 不清 JS 端,只把 `collected` 拉到 Python。
- **角色隔离(2026-06-13 修复)**:sprintf hook 收到 `c%d.xml` 且 c-code 变化时,自动清空 `collected`/`seenCodes`/`consecutiveMiss`,发 `batch_reset(reason='char_switch')`。消除跨角色数据污染。之前必须手动 `recollect_outfit`。

## 进程拓扑

| 进程 | 启动者 | 作用 |
|---|---|---|
| `FreeStyle.exe` | 游戏启动器 / `launch_game` | 游戏本体,attach 目标 |
| `python .../engine/server.py` | C# 主程序(`FridaBridge`) | TCP server + Frida |
| `python .../freestyle_mcp_server.py` | Claude Code | MCP 工具 |
| C# WPF 主程序 | 用户 | UI + engine 管理 |

`FreeStyle.exe` PID 不随 engine 重启变化。engine 重启只 detach Frida(游戏不受影响),重连后恢复。

## 调试入口

- **engine.log**:`2.0/bin/Debug/.../engine/engine.log`(运行目录下,带时间戳,1MB 截断)。
- **hook 日志**:`get_hook_log`(MCP)/ `HOOK_LOG`(TCP),来自 `hook_log_buffer`(200 条循环)。
- **状态**:`frida_status` 看连接/替换映射/收集数;`get_hook_log keyword=异常` 看告警。
- 关键日志事件:`sprintf_hit/miss`、`brute_scan_done`、`dword_scan_done`、`batch_reset`(角色切换隔离)、`anomaly[too_many_miss]`(映射可能失效)、`scene_change`(lobby/room/practice)。

## 已知问题 & 修复记录

| 问题 | 状态 | 说明 |
|---|---|---|
| 切换角色收集数据污染 | ✅ 已修(2026-06-13) | `currentCharCcode` 自动隔离。改 `hook_manager.py` + `server.py`。 |
| `bruteDwordScan` CModule 不反向恢复 | ⚠️ 待修 | 切角色+反复进练习场可能内存残留。CModule 路径缺 dst→src 恢复。 |
| `need_restore_shop` 被禁用 | ⚠️ 待修 | `server.py:603` 退出练习场恢复被注释("避免光头"),恢复链路断裂。 |
| 按钮呼吸灯第二次循环失效 | ✅ 已修(2026-06-13) | VSM(MouseOver/Pressed)的 ObjectAnimation 用 HoldEnd 持有模板 `ButtonBorder.Background`,压制代码经 TemplateBinding 设的 `btn.Background`(WPF 优先级:动画值 > local value)。点过一次后流光失效。修复:`StartBtnBreathing` 先 `ApplyTemplate`+`FindName("ButtonBorder")`+`BeginAnimation(null)` 清除持有;复用单个 `LinearGradientBrush`(每帧改 GradientStops);单例 `DispatcherTimer`+命名 Tick;去掉缩放只留流光。改 `MainWindow.xaml.cs`。 |

## 启动 CRC patch

游戏有 Apollo 反作弊 CRC 校验。`launch_game` 以 CREATE_SUSPENDED 启动 → patch 两个 RVA(`0x001A3C54`, `0x001BE222` → `xor eax,eax; ret`)→ 恢复主线程。
