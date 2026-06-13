# FreeStyle 装备搭配专家 — 项目说明 (Claude 必读)

街头篮球(FreeStyle)装备外观/特效内存替换工具。
- **v2.0**(活跃,Frida hook 方案):`2.0/`
- **v1.0**(已归档):`1.0/`

> 详细架构/机制见 [`2.0/ARCHITECTURE.md`](2.0/ARCHITECTURE.md)。本文件只放**每次会话必须记住**的关键规则与坑。

## 工程纪律

1. **非平凡改动先 Plan**：改 engine JS（`hook_manager.py` 模板）/ C# 多文件 / 不确定影响范围时，先用 plan 模式梳理调用链与影响范围，确认后再动手；小修（单行 / 明确）可直接改。
2. **日志带固定关键词**：关键事件用固定短词打日志（见下方「调试入口」的关键事件清单），便于事后 `grep` 排查，而非逐行翻 `engine.log`。

## 三层架构(速记)

```
C# WPF 主程序 ──TCP 18731──► Python engine(server.py)──Frida──► FreeStyle.exe
                              ▲
MCP server(freestyle_mcp_server.py)是 engine 的无状态薄封装(每次 _send_cmd 新建 TCP 连接)
```

## ⚠️ 最易踩的坑(务必遵守)

1. **engine 有三份副本,改完必须同步 + 重启**
   - 源:`2.0/engine/`(在这里改)
   - 实际运行目录:**`2.0/bin/Debug/net8.0-windows/engine/`**(engine 从这里启动)
   - Release 副本:较旧
   - 改 `2.0/engine/*.py` 后:① 覆盖到 `bin/Debug/.../engine/`;② **重启 engine 进程**(Python import 缓存,`replace_outfit`/重连都不够)。
   - 改 `hook_manager.py` 的 JS 模板尤其要重启——`create_js()` 被 import 缓存。
   - `FreeStyle.exe` 的 PID 不随 engine 重启变化,重启 engine 不影响游戏。

2. **改 JS 替换/收集逻辑** → 改 `2.0/engine/hook_manager.py` 的 `create_js()`(JS 是模板字符串,不是独立 .js 文件)。`optimized_scanner.js` 疑似废弃,当前用的是内嵌 CModule。

3. **WPF 按钮特效:VisualStateManager 动画 HoldEnd 会压制代码设的属性**
   - `Styles.xaml` 的 GlassButton 模板里,VSM 用 `ObjectAnimationUsingKeyFrames` 改模板内 `ButtonBorder.Background`(HoldEnd 持有)。
   - 经 `TemplateBinding` 由代码设 `btn.Background` 会被**动画值压制**(WPF 优先级:动画值 > local value)→ 表现为"特效只生效一次"。
   - 修复套路:先 `btn.ApplyTemplate()` + `FindName("ButtonBorder")` + `BeginAnimation(prop, null)` 清除持有;复用单个 `LinearGradientBrush`(每帧改 GradientStops)+ 单例 `DispatcherTimer`,别每次 new。

## 内存布局标志

- **属性表条目**:ItemCode 是个 DWORD,其后 `+0x04 == 0x00010000` 表示这是装备定义条目;商城/背包数据**无此标志**。
- **特效槽**:属性表条目的 `+0x08` = 特效 ID,`+0x0C == 0x00010000` 表示下一条是特效条目。
- **三种扫描**:`native_dword_scan`(房间,有 flag 检查)、`native_brute_scan`(练习场,无 flag 检查)、JS 内嵌 CModule(正向 src→dst,**缺 dst→src 反向恢复**)。
- **两套替换路径**:房间场景(sprintf hook,命中 REPLACE_MAP 改栈 + dwordScan);练习场场景(strcpy hook + bruteDwordScan)。

## CRC 反作弊 patch

`launch_game`:CREATE_SUSPENDED 启动游戏 → patch RVA `0x001A3C54` & `0x001BE222` → 写 `xor eax,eax; ret`(字节 `33 C0 C3`)→ 恢复主线程。

## 调试入口

- **engine 日志**:`2.0/bin/Debug/.../engine/engine.log`(运行目录下,带时间戳,1MB 截断)
- **MCP 工具**:`frida_status`(连接/替换映射/收集数)、`get_hook_log`(200 条循环,可按 keyword 过滤)
- **关键事件**:`sprintf_hit/miss`、`brute_scan_done`、`dword_scan_done`、`batch_reset`(角色切换隔离)、`scene_change`(lobby/room/practice)、`anomaly[too_many_miss]`(映射可能失效)

## 收集机制要点

- JS 全局:`collected`(append-only,key=collectIndex)、`seenCodes`(去重)、`currentCharCcode`(当前角色)。
- `read_current_outfit` 不清 JS 端,只把 `collected` 拉到 Python。
- **角色隔离(2026-06-13 已修)**:sprintf hook 收到 `c%d.xml` 且 c-code 变化时,自动清空 `collected`/`seenCodes`/`consecutiveMiss` 并发 `batch_reset(reason='char_switch')`,消除跨角色数据污染。

## 已知待修(非本次范围,动到再说)

- `bruteDwordScan` CModule 不做 dst→src 反向恢复 → 反复进练习场可能内存残留。
- `need_restore_shop` 在 `server.py` 被禁用("避免光头")→ 退出练习场恢复链路断裂。

## 构建

```bash
dotnet build "D:/py/反编译/FreeStyle/2.0/FS服装搭配专家v2.0.csproj" -c Debug
```
