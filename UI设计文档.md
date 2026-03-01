# FreeStyle 应用程序 UI 设计文档

## 整体布局

### 1. 窗口结构
- **窗口大小**：1440x1080
- **窗口样式**：无边框，透明背景
- **背景**：蓝粉紫渐变背景
- **视觉风格**：玻璃拟态（Glassmorphism）设计，具有半透明、模糊背景和柔和阴影

### 2. 顶部标题栏
- **位置**：窗口顶部
- **内容**：
  - 左侧：应用程序标题 "FreeStyle"，白色加粗字体
  - 右侧：窗口管理按钮（最小化、最大化、关闭），玻璃拟态风格
  - 换肤图标：带有流动渐变效果的背心图标
- **样式**：透明背景，与主窗口融为一体

### 3. 标签页导航
- **位置**：标题栏下方
- **内容**：三个标签页按钮
  - "服装道具"（Clothing Items）
  - "地图切换"（Map Switch）
  - "常用工具"（Common Tools）
- **样式**：玻璃拟态风格，选中状态有高亮效果

### 4. 主内容区域
- **位置**：标签页下方，占据窗口主要空间
- **样式**：玻璃拟态面板，圆角 16px，半透明背景，柔和阴影

## 标签页内容

### 1. 服装道具标签页
- **布局**：左右两栏
  - **左侧**：服装列表
    - 搜索框：玻璃拟态风格，圆角8px
    - 服装项目列表，每个项目为玻璃拟态卡片
    - 交互：点击项目可在右侧预览
  - **右侧**：预览区域
    - 变更前/变更后列表
    - 预览效果显示
    - 操作按钮（确认变更、清空所有）

### 2. 地图切换标签页
- **顶部**：地图库路径设置（选择路径、刷新按钮）
- **左侧**：地图列表（搜索框 + 列表）
- **右侧**：地图预览区域（预览图 + 地图名称 + 应用按钮）
- **底部**：状态栏

### 3. 常用工具标签页
- **内容**：占位文本
- **状态**：功能待实现

## 视觉元素

### 1. 颜色方案
- **背景**：蓝粉紫渐变
  - 起始色：#6a85b6
  - 中间色：#bac8e0
  - 结束色：#f0c9e8
- **文本**：
  - 标题：#FFFFFFFF（白色）
  - 正文：#E6FFFFFF（半透明白色）
  - 状态文本：#FFCCCCCC
- **玻璃拟态**：
  - 卡片背景：#15FFFFFF
  - 边框：#4DFFFFFF
  - 高光：#20FFFFFF
  - 按钮：#25FFFFFF

### 2. 交互元素
- **按钮**：玻璃拟态风格，悬停时有霓虹渐变文字效果
- **列表项**：玻璃拟态卡片，悬停时有背景透明度变化
- **文本框**：玻璃拟态风格，圆角6-8px
- **滚动条**：自定义玻璃拟态风格，半透明背景

### 3. 动画效果
- **按钮悬停**：背景透明度变化，文字变为霓虹渐变色
- **窗口拖动**：平滑拖动效果，支持从最大化状态恢复
- **换肤图标**：流动渐变动画效果

## UI 元素编号与命名

### 1. 窗口级别元素
| 编号 | 元素名称 | 位置描述 |
|------|---------|----------|
| W1 | 主窗口 | 整个应用程序窗口 |
| W2 | 背景渐变 | 窗口背景，蓝粉紫渐变 |
| W3 | 主容器 | 包含所有内容的玻璃拟态面板 |

### 2. 标题栏元素
| 编号 | 元素名称 | 位置描述 |
|------|---------|----------|
| T1 | 标题栏容器 | 顶部标题栏区域 |
| T2 | 应用标题 | 左侧 "FreeStyle" 文本 |
| T3 | 窗口管理按钮组 | 右侧按钮集合 |
| T3-1 | 最小化按钮 | 窗口管理按钮组左侧 |
| T3-2 | 最大化按钮 | 窗口管理按钮组中间 |
| T3-3 | 关闭按钮 | 窗口管理按钮组右侧 |
| T4 | 换肤图标 | 标题栏右侧，流动渐变效果 |

### 3. 标签页导航元素
| 编号 | 元素名称 | 位置描述 |
|------|---------|----------|
| N1 | 标签页控制 | 标题栏下方的标签页控件 |
| N1-1 | 服装道具标签 | 左侧第一个标签 |
| N1-2 | 地图切换标签 | 中间标签 |
| N1-3 | 常用工具标签 | 右侧标签 |

### 4. 服装道具标签页内容
| 编号 | 元素名称 | 位置描述 |
|------|---------|----------|
| C1 | 服装道具内容区 | 标签页内容区域 |
| C2 | 服装列表容器 | 左侧服装列表区域 |
| C2-1 | 搜索框 | 玻璃拟态风格，圆角 |
| C2-2 | 服装列表控件 | 服装项目列表 |
| C3 | 预览区域容器 | 右侧预览区域 |
| C3-1 | 变更前列表 | 变更前服装列表 |
| C3-2 | 变更后列表 | 变更后服装列表 |
| C3-3 | 操作按钮区 | 确认变更、清空所有按钮 |

### 5. 地图切换标签页内容
| 编号 | 元素名称 | 位置描述 |
|------|---------|----------|
| M1 | 地图库设置区 | 顶部路径设置区域 |
| M2 | 地图列表区 | 左侧地图列表 |
| M2-1 | 搜索框 | 地图搜索框 |
| M2-2 | 地图列表控件 | 地图项目列表 |
| M3 | 地图预览区 | 右侧预览区域 |
| M3-1 | 预览图 | 地图预览图片 |
| M3-2 | 地图名称 | 当前选中地图名称 |
| M3-3 | 应用按钮 | 应用地图按钮 |
| M4 | 状态栏 | 底部状态显示 |

## 技术实现要点

### 玻璃拟态效果
```xaml
<Border Background="#15FFFFFF"
        BorderBrush="#4DFFFFFF"
        BorderThickness="1"
        CornerRadius="16">
    <Border.Effect>
        <DropShadowEffect BlurRadius="40"
                          ShadowDepth="12"
                          Opacity="0.15" />
    </Border.Effect>
</Border>
```

### 渐变背景
```xaml
<LinearGradientBrush StartPoint="0,0" EndPoint="1,1">
    <GradientStop Color="#6a85b6" Offset="0" />
    <GradientStop Color="#bac8e0" Offset="0.5" />
    <GradientStop Color="#f0c9e8" Offset="1" />
</LinearGradientBrush>
```

### 霓虹渐变文字
```xaml
<LinearGradientBrush x:Key="NeonGradient" StartPoint="0,0" EndPoint="1,1">
    <GradientStop Color="#FF667EEA" Offset="0" />
    <GradientStop Color="#FF6DD5FA" Offset="0.5" />
    <GradientStop Color="#FFC58AF9" Offset="1" />
</LinearGradientBrush>
```

### 圆角文本框
```xaml
<Style x:Key="GlassTextBox" TargetType="TextBox">
    <Setter Property="Background" Value="#20FFFFFF" />
    <Setter Property="Foreground" Value="White" />
    <Setter Property="BorderBrush" Value="#4DFFFFFF" />
    <Setter Property="BorderThickness" Value="1" />
    <Setter Property="Template">
        <Setter.Value>
            <ControlTemplate TargetType="TextBox">
                <Border CornerRadius="8"
                        Background="{TemplateBinding Background}"
                        BorderBrush="{TemplateBinding BorderBrush}"
                        BorderThickness="{TemplateBinding BorderThickness}">
                    <ScrollViewer x:Name="PART_ContentHost"
                                  Margin="12,8"
                                  VerticalAlignment="Center" />
                </Border>
            </ControlTemplate>
        </Setter.Value>
    </Setter>
</Style>
```

## 可修改的元素

1. **窗口样式**：窗口大小、背景渐变颜色、圆角半径
2. **标题栏**：标题文本、窗口管理按钮样式
3. **标签页**：标签页数量、名称、样式
4. **内容区域**：各标签页的布局和功能
5. **视觉效果**：颜色方案、阴影效果、动画效果
