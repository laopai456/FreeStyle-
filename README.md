# FS服装搭配专家 v1.0 — 街头篮球道具修改工具

> 基于 WPF (.NET 8) 的 FreeStyle 街头篮球逆向辅助工具  
> 编译运行：`dotnet build` → 运行 `bin/Debug/net8.0-windows/FS服装搭配专家v1.0.exe`

---

## 快速上手

1. **启动**：第一次运行会弹出“选择游戏目录”，选到街头篮球安装文件夹（如 `C:\Program Files (x86)\T2CN\街头篮球`）
2. **搜索道具**：顶部搜索框输入道具名或 ItemCode，列表自动过滤
3. **变更道具**：左键添加到“变更前”，`Ctrl + 左键` 添加到“变更后”，点击“确认变更”执行
4. **换肤**：右上角 🎨 按钮打开皮肤窗口，可选默认玻璃拟态 / Galaxy / 暗黑视频背景
5. **常用工具**：支持背景切图、补充 PAK 字节

---

## 当前功能

| 模块 | 说明 |
|------|------|
| 服装道具 | 解析 `item_text.pak`，搜索服装/特效，解包 item/icon pak，替换 BML 并重打包 |
| 地图切换 | 扫描地图资源，预览并替换地图文件 |
| 背景切图 | 上传静态图片，缩放到 1366x768，按游戏背景规则切块 |
| 补充字节 | PAK 重打包后按参考大小补齐字节，降低游戏读取异常概率 |
| 主题换肤 | 读取 `skins/*/theme.json`，支持渐变、纯色、图片、视频背景 |
| 视频动态背景 | 通过 LibVLCSharp 解码视频帧，渲染到主窗口底层 |

---

## 主题换肤系统

右上角 🎨 按钮打开 `SkinWindow`。

### 内置主题

| 主题 | 效果 | 说明 |
|------|------|------|
| 默认玻璃拟态 | 半透明毛玻璃面板 + 渐变背景 | `ThemeLoader.GetDefaultTheme()` 内置 |
| Galaxy | 浅色亮丽风格 | 从 `skins/galaxy/theme.json` 加载 |
| 暗黑霓虹 | 深色背景 + 视频动态背景 | 运行时生成 `skins/dark/theme.json`，播放 `videos/dark-background.mp4` |

### 主题模型

每个主题是一个 `theme.json`：

```json
{
  "id": "my-theme",
  "name": "我的主题",
  "author": "作者名",
  "version": "1.0",
  "description": "描述",
  "styles": {
    "window": {
      "background": {
        "type": "video",
        "videoPath": "my-video.mp4",
        "volume": 0
      }
    },
    "card": { "background": "#66FFFFFF", "borderColor": "#20FFFFFF", "cornerRadius": 16 },
    "button": { "background": "#66FFFFFF", "cornerRadius": 16 },
    "text": { "primary": "#FFFFFFFF", "fontFamily": "Microsoft YaHei" }
  }
}
```

**背景类型**：

- `gradient` — 渐变色（`colors` + `angle`）
- `solid` — 纯色背景
- `image` — 图片背景（`imagePath`）
- `video` — 视频背景（`videoPath`，文件放 `videos/` 目录）

---

## 动态视频背景实现

暗黑主题使用 **LibVLCSharp** 播放视频作为窗口背景。

### 工作原理

```text
用户选择视频主题
  → ThemeLoader 读取 skins/{主题ID}/theme.json
  → ThemeApplier.GetVideoPath() 拼接 {程序目录}/videos/{videoPath}
  → MainWindow.ApplyVideoBackground()
  → LibVLC 解码视频帧
  → WriteableBitmap 渲染到 VideoBackgroundImage 控件
  → 窗口背景显示为动态视频
```

### 相关代码

| 文件 | 作用 |
|------|------|
| `Core/Models/SkinTheme.cs` | 定义 `BackgroundStyle.Type` / `VideoPath` / `Volume` |
| `Core/Services/ThemeLoader.cs` | 扫描 `skins/`，生成暗黑主题 |
| `Core/Services/ThemeApplier.cs` | 判断视频背景，拼接视频路径 |
| `UI/Windows/MainWindow.xaml` | `VideoBackgroundImage` 视频背景层 |
| `UI/Windows/MainWindow.xaml.cs` | LibVLC 初始化、解码、循环播放、主题切换 |
| `UI/Windows/SkinWindow.xaml.cs` | 主题选择与应用入口 |

### 当前限制

- 目前只能手动把视频放入 `videos/` 并手写 `theme.json`
- `SkinWindow` 尚未提供“导入视频/上传动态背景”按钮
- 新增主题后通常需要重新打开皮肤窗口或重启程序才能看到

### 待开发：动态主题背景上传

目标：用户选择本地视频文件后，工具自动复制视频并生成主题。

建议流程：

```text
皮肤窗口点击“导入动态背景”
  → OpenFileDialog 选择 .mp4
  → 复制到 {程序目录}/videos/custom_时间戳.mp4
  → 创建 skins/custom_video_时间戳/theme.json
  → skinManager.LoadThemes()
  → 刷新主题列表并选中新主题
  → 点击“应用”即可欣赏动态背景
```

实现建议：

1. 在 `SkinWindow.xaml` 增加“导入动态背景”按钮
2. 在 `SkinWindow.xaml.cs` 增加导入逻辑
3. 复用 `ThemeLoader.SaveTheme(SkinTheme theme)` 生成 `theme.json`
4. 复制视频时使用异步任务，避免大文件卡 UI
5. 主题 ID 和视频文件名使用时间戳，避免覆盖旧文件
6. 导入成功后刷新 `skinManager.Themes` 和 `lstSkins.ItemsSource`

---

## 项目结构

```text
FreeStyle/
├── Program.cs
├── FS服装搭配专家v1.0.csproj
├── Core/
│   ├── Config/                 # AppConfig / ConfigService
│   ├── Models/                 # ItemshopM / MapM / SkinTheme 等
│   ├── Services/               # SkinManager / ThemeLoader / ThemeApplier
│   └── Utilities/              # conmon / OperationDebugger
├── UI/
│   ├── App.xaml(.cs)
│   ├── Resources/              # 字符串和样式资源
│   └── Windows/
│       ├── MainWindow.xaml(.cs)
│       ├── SkinWindow.xaml(.cs)
│       ├── BgCropWindow.xaml(.cs)
│       ├── FillBytesWindow.xaml(.cs)
│       ├── MapControl.xaml(.cs)
│       └── TeamSelectionWindow.xaml(.cs)
├── skins/                      # 主题配置
├── videos/                     # 视频背景资源
└── pack/resources.exe          # PAK 解包/打包工具
```

---

## 开发 / 编译

```bash
# 构建
dotnet build -c Debug

# 发布
dotnet publish -c Release -o publish

# 运行
./bin/Debug/net8.0-windows/FS服装搭配专家v1.0.exe
```

---

## 备注

- 工具修改的是游戏客户端本地文件，不影响服务器数据
- PAK 操作依赖 `pack/resources.exe`
- 操作日志在 `logs/operation_debug.log`
- 动态视频背景依赖 `LibVLCSharp` 和 `libvlc/` 原生库
