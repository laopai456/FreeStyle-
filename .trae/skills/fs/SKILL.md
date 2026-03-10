---
name: "fs"
description: "FS服装搭配专家 UI开发助手，自动检测项目位置。当用户需要修改WPF界面、主题系统、字体样式、颜色配置时调用此技能。"
auto_load: true
---

# FS服装搭配专家 UI 开发助手

## 项目识别

**自动检测规则**：
- 通过 `.csproj` 文件名识别：`FS服装搭配专家v1.0.csproj`
- 检测顺序：
  1. 当前工作目录
  2. 用户桌面下的 `py/UI/` 目录
  3. 用户打开的文件所在目录向上查找

**确认项目后**，所有路径使用相对路径。

## 项目架构

```
项目根目录/
├── Core/
│   ├── Models/
│   │   └── SkinTheme.cs          # 主题数据模型
│   └── Services/
│       ├── ThemeLoader.cs        # 主题加载器
│       └── ThemeApplier.cs       # 主题应用器
├── UI/Windows/
│   ├── MainWindow.xaml           # 主窗口
│   ├── MainWindow.xaml.cs
│   ├── MapControl.xaml           # 地图控件
│   ├── SkinWindow.xaml           # 皮肤设置窗口
│   ├── ConfirmDialog.xaml        # 确认对话框
│   ├── BgCropWindow.xaml         # 背景裁剪窗口
│   ├── FillBytesWindow.xaml      # 字节填充窗口
│   └── TeamSelectionWindow.xaml  # 队伍选择窗口
├── videos/                        # 视频背景目录
├── skins/                         # 主题配置目录
├── 开发文档.md                    # 开发文档
└── FS服装搭配专家v1.0.csproj
```

## 主题系统

### 数据流
```
SkinTheme.cs (模型)
    ↓
ThemeLoader.cs (加载配置)
    ↓
ThemeApplier.cs (应用到UI)
    ↓
MainWindow.xaml (显示)
```

### 核心类

**SkinTheme.cs** - 主题数据模型：
- `TextStyle`: FontFamily, FontWeight, Primary, Secondary, Title, Body
- `CardStyle`: Background, BorderColor, ContentPanelBackground, Shadow
- `BackgroundStyle`: Type, Colors, VideoPath, Volume
- `ListItemStyle`: Foreground

**ThemeLoader.cs** - 加载主题配置：
- `LoadDefaultTheme()` - 加载默认主题
- `LoadDarkTheme()` - 加载暗黑主题
- `LoadGalaxyTheme()` - 加载银河主题

**ThemeApplier.cs** - 应用主题到UI：
- `ApplyThemeToWindow()` - 应用到窗口
- `ApplyThemeToUserControl()` - 应用到用户控件
- `IsVideoBackground()` - 检测是否视频背景
- `GetVideoPath()` - 获取视频路径

## 编译命令

```bash
dotnet build
```

## 修改规范

### XAML 文件统一处理

所有 XAML 窗口需要统一处理以下内容：

1. **字体资源定义**：
```xml
<FontFamily x:Key="ThemeFontFamily">Microsoft YaHei</FontFamily>
<FontWeight x:Key="ThemeFontWeight">Normal</FontWeight>
```

2. **样式绑定**：
```xml
<Setter Property="FontFamily" Value="{DynamicResource ThemeFontFamily}" />
<Setter Property="FontWeight" Value="{DynamicResource ThemeFontWeight}" />
```

3. **颜色绑定**：
```xml
<Setter Property="Foreground" Value="{DynamicResource TextColor}" />
<Setter Property="Background" Value="{DynamicResource GlassCardColor}" />
```

### 修改检查清单

修改主题相关功能时，检查以下文件：

- [ ] `SkinTheme.cs` - 数据模型
- [ ] `ThemeLoader.cs` - 主题配置
- [ ] `ThemeApplier.cs` - 应用逻辑
- [ ] `MainWindow.xaml` - 主窗口
- [ ] `MapControl.xaml` - 地图控件
- [ ] `SkinWindow.xaml` - 皮肤设置
- [ ] `ConfirmDialog.xaml` - 确认对话框
- [ ] `BgCropWindow.xaml` - 背景裁剪
- [ ] `FillBytesWindow.xaml` - 字节填充
- [ ] `TeamSelectionWindow.xaml` - 队伍选择

## 自动工作流

### 修改代码后
1. 执行 `dotnet build` 编译验证
2. 检查是否有遗漏文件
3. 更新 `开发文档.md`

### 新增功能后
1. 在 `开发文档.md` 添加新章节
2. 更新最后修改时间

## 常见任务

### 修改主题颜色
1. 修改 `ThemeLoader.cs` 中的主题配置
2. 编译验证
3. 更新开发文档

### 添加新窗口
1. 创建 XAML 文件
2. 添加字体资源定义
3. 绑定 DynamicResource
4. 更新开发文档

### 修改字体
1. 修改 `ThemeLoader.cs` 中的 FontFamily/FontWeight
2. 确保所有 XAML 文件使用 DynamicResource
3. 编译验证

## 参考文档

详细修改历史请参考项目根目录的 `开发文档.md`。
