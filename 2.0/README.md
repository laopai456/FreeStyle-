# FS服装搭配专家 v2.0

街头篮球（FreeStyle）实时装备搭配工具。通过 Frida Hook 游戏进程内存，在不修改游戏文件的前提下实时替换角色外观装备。

## 功能

- **读取当前穿搭** — Hook `MSVCR100.dll!sprintf`，自动收集角色当前 8 个装备位（上衣/下衣/鞋子/饰品/装饰/发型/特殊装饰/手套）
- **实时装备替换** — Hook sprintf + strcpy + DWORD 内存扫描，运行时替换道具编码，支持跨 PAK
- **道具搜索** — 从 ~15000 条 itemshop 数据库中按名称/编码模糊搜索
- **图标展示** — 自动解包游戏 icon PAK，4×2 网格展示各装备位道具图标
- **暗色主题 UI** — WPF 深色界面，Tab 分类列表，全宽搜索栏

## 架构

```
┌─────────────────────┐        TCP :18731        ┌──────────────────────┐
│   WPF 前端 (C#)      │◄──────────────────────►│   Python 后端         │
│   .NET 8.0           │     JSON over TCP       │   Frida + psutil     │
│                      │                         │                      │
│   MainWindow.xaml    │   CONNECT               │   server.py          │
│   FridaBridge.cs     │   READ_CURRENT          │   hook_manager.py    │
│   ItemshopService    │   REPLACE               │   itemshop_db.py     │
└─────────────────────┘   RESTORE                └──────────────────────┘
                          SEARCH                        │ frida attach
                                                        ▼
                                                ┌──────────────────────┐
                                                │  FreeStyle.exe       │
                                                │  MSVCR100.dll        │
                                                │  sprintf / strcpy    │
                                                └──────────────────────┘
```

前端启动时自动拉起 `engine/server.py` 子进程，通过 TCP JSON 协议通信。Python 端用 Frida attach 到游戏进程，注入 JS Hook 脚本。

## 目录结构

```
2.0/
├── Program.cs                        # 入口（单实例锁 + Encoding 注册）
├── FS服装搭配专家v2.0.csproj          # .NET 8.0 WPF 项目
│
├── Core/
│   ├── Models/
│   │   ├── ItemshopM.cs              # 道具数据模型
│   │   ├── SlotConfigM.cs            # 装备位配置模型
│   │   └── SkinTheme.cs              # 主题模型
│   ├── Services/
│   │   ├── FridaBridge.cs            # TCP 通信桥（启动 Python / 收发命令）
│   │   ├── SkinManager.cs            # 主题管理
│   │   ├── ThemeLoader.cs            # 主题加载
│   │   └── ThemeApplier.cs           # 主题应用
│   ├── Config/
│   │   ├── AppConfig.cs              # 常量定义
│   │   └── ConfigService.cs          # 游戏路径自动检测
│   └── Utilities/
│       └── conmon.cs                 # 通用工具
│
├── UI/
│   ├── App.xaml(.cs)                 # WPF 应用入口
│   ├── Resources/
│   │   └── Styles.xaml               # 全局样式
│   └── Windows/
│       ├── MainWindow.xaml(.cs)      # 主窗口（暗色主题，4×2 装备网格）
│       ├── ItemSearchDialog.xaml(.cs)# 道具搜索弹窗
│       └── SkinWindow.xaml(.cs)      # 换肤窗口
│
├── engine/                            # Python 后端
│   ├── server.py                     # TCP 服务器（端口 18731）
│   ├── hook_manager.py               # Frida JS Hook 生成器
│   ├── itemshop_db.py                # itemshop.json 查询封装
│   └── requirements.txt              # Python 依赖声明（首次自动安装）
│
├── data/
│   ├── slot_config.json              # 10 个装备位定义
│   └── itemshop.json                 # 道具数据库（~15000 条）
│
├── pack/resources.exe                # icon PAK 解包工具
├── skins/galaxy/                     # 示例主题
└── icon/favicon.ico                  # 应用图标
```

## 装备位

游戏角色共 10 个装备位，其中 2 个为隐藏基础模型，工具展示 8 个：

| ID | Key | 名称 | ItemCode 前缀 | 示例 |
|----|------|------|---------------|------|
| 0 | base1 | 角色基础1 | c | c800 (隐藏) |
| 1 | base2 | 角色基础2 | c | c801 (隐藏) |
| 2 | top | 上衣 | 504 | 50421031 |
| 3 | bottom | 下衣 | 505 | 50519561 |
| 4 | shoes | 鞋子 | 506 | 50623371 |
| 5 | glasses | 饰品 | 509 | 50914721 |
| 6 | deco1 | 装饰 | 515 | 51514521 |
| 7 | hair | 发型 | 501 | 50125461 |
| 8 | deco2 | 特殊装饰 | 516 | 51616261 |
| 9 | gloves | 手套 | 512 | 51213111 |

## 使用流程

```
1. 启动游戏 → 进入大厅
2. 启动 FS服装搭配专家 v2.0
3. 点击「🔗 连接游戏」→ 自动检测 FreeStyle.exe 并 Frida attach
4. 进一次房间（触发 sprintf 收集当前穿搭）
5. 回到工具，点击「🔄 刷新穿搭」→ 右侧 4×2 网格显示当前装备
6. 点击目标装备位（蓝色高亮）
7. 左侧列表搜索/选择替换道具
8. 点击「✅ 确认变更」→ Frida 注入替换 Hook
9. 再进房间/练习场 → 看到新外观
10. 点击「↩ 还原」→ 清除 Hook，恢复原装
```

## TCP 协议

前端与 Python 后端通过 TCP JSON 通信（每条消息以 `\n` 分隔）：

| 命令 | 请求 | 响应 |
|------|------|------|
| CONNECT | `{"cmd":"CONNECT"}` | `{"status":"ok","pid":1234}` |
| READ_CURRENT | `{"cmd":"READ_CURRENT"}` | `{"status":"ok","slots":{...},"hint":""}` |
| REPLACE | `{"cmd":"REPLACE","map":{"7":"50125711"}}` | `{"status":"ok","map":{...}}` |
| RESTORE | `{"cmd":"RESTORE"}` | `{"status":"ok"}` |
| STATUS | `{"cmd":"STATUS"}` | `{"status":"ok","connected":true,...}` |
| SEARCH | `{"cmd":"SEARCH","keyword":"超赛"}` | `{"status":"ok","results":[...]}` |

## Hook 原理

核心 Hook 点为 `MSVCR100.dll` 导出函数：

1. **sprintf** — 游戏构建装备路径时调用（如 `item/501/50125461`），从中提取道具编码并按 slot 归类。替换模式下拦截并改写目标编码。

2. **strcpy** — 练习场场景加载装备路径时调用，配合 sprintf Hook 实现练习场装备替换。

3. **DWORD 内存扫描** — 对已加载到内存的道具编码直接扫描替换，覆盖 sprintf 未触发的场景。

## 环境要求

- **操作系统**: Windows 10/11
- **运行时**: .NET 8.0 Runtime
- **Python**: 3.10+，安装时勾选 "Add to PATH"
- **游戏**: 街头篮球（FreeStyle）已安装且运行中

首次启动时工具会自动执行 `pip install -r engine/requirements.txt` 安装 frida 和 psutil，无需手动操作。

## 构建

```bash
cd "D:\py\反编译\FreeStyle\2.0"
dotnet build -c Debug
```

输出目录 `bin\Debug\net8.0-windows\` 包含：
- `FS服装搭配专家v2.exe` — 主程序
- `engine\` — Python 后端（自动启动）
- `data\` — 道具数据库 + 装备位配置
- `cookies\` — icon 素材缓存（首次需解包）

## 图标素材

首次使用需解包游戏 icon PAK：

1. 点击「📷 加载图片」
2. 工具调用 `pack/resources.exe` 解包 `icon*.pak` 到 `cookies/icon*_pak/` 目录
3. 图标路径模板：`cookies/icon{pakNum}_pak/u{itemCode}.png`

## 与 v1.0 的区别

| | v1.0 | v2.0 |
|---|------|------|
| 替换方式 | BML 文件替换（改 PAK） | Frida 内存 Hook（不碰文件） |
| 场景 | 仅房间 | 房间 + 练习场 |
| 跨 PAK | ❌ | ✅ |
| 装备位 | 发型为主 | 全部 8 装备位 |
| 架构 | 纯 C# WPF | C# WPF + Python Frida |
| UI | 浅色主题 | 暗色主题，4×2 网格 |
