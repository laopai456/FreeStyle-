# 硬编码优化规范文档

## 项目概述

**项目名称**：FS服装搭配专家v1.0 硬编码优化  
**创建日期**：2026年3月11日  
**优先级**：中等  

## 背景分析

### 当前状态
项目中存在大量硬编码值，主要分布在：

| 类别 | 数量 | 影响范围 |
|------|------|----------|
| 尺寸值 (Width/Height/FontSize) | ~100处 | UI布局一致性 |
| 颜色值 (#十六进制) | ~100处 | 主题切换、维护成本 |
| 字符串 | 10个文件 | 国际化、统一管理 |

### 问题影响
1. **维护困难**：修改尺寸需要逐个文件查找替换
2. **主题不统一**：颜色分散在各文件，切换主题时容易遗漏
3. **可扩展性差**：难以支持多语言、多分辨率适配

## 优化目标

### 主要目标
1. 将尺寸值集中到 Styles.xaml 资源字典
2. 将颜色值整合到主题系统
3. 将字符串移到 Strings.xaml 资源文件

### 预期收益
- 减少 80% 以上的硬编码值
- 统一 UI 元素尺寸规范
- 便于主题切换和维护
- 为多语言支持打下基础

## 优化范围

### 包含内容
1. **尺寸优化**
   - 窗口尺寸（已在配置文件中）
   - 按钮高度/宽度
   - 字体大小
   - 图标尺寸
   - 边距/间距

2. **颜色优化**
   - 玻璃效果颜色
   - 文字颜色
   - 边框颜色
   - 背景颜色
   - 交互状态颜色

3. **字符串优化**
   - 提示文本（已在 Strings.xaml）
   - 错误消息
   - 窗口标题
   - 按钮文字

### 不包含内容
- 业务逻辑相关的动态值
- 第三方库的配置
- 运行时计算的值

## 技术方案

### 尺寸常量定义
在 Styles.xaml 中添加：

```xml
<!-- 尺寸常量 -->
<sys:Double x:Key="FontSize_Title">18</sys:Double>
<sys:Double x:Key="FontSize_Subtitle">16</sys:Double>
<sys:Double x:Key="FontSize_Body">14</sys:Double>
<sys:Double x:Key="FontSize_Small">12</sys:Double>
<sys:Double x:Key="FontSize_Tiny">11</sys:Double>

<sys:Double x:Key="ButtonHeight_Large">44</sys:Double>
<sys:Double x:Key="ButtonHeight_Medium">36</sys:Double>
<sys:Double x:Key="ButtonHeight_Small">32</sys:Double>

<sys:Double x:Key="ButtonWidth_Action">160</sys:Double>
<sys:Double x:Key="ButtonWidth_Dialog">100</sys:Double>

<sys:Double x:Key="IconSize_Large">48</sys:Double>
<sys:Double x:Key="IconSize_Medium">24</sys:Double>
<sys:Double x:Key="IconSize_Small">16</sys:Double>
```

### 颜色整合方案
颜色值已在 MainWindow.xaml 的资源字典中定义，需要：
1. 将颜色定义移到统一的 Colors.xaml
2. 各窗口通过 DynamicResource 引用
3. 主题切换时更新颜色资源

### 字符串资源化
Strings.xaml 已创建基础框架，需要：
1. 补充更多提示文本
2. 在代码中通过资源查找使用
3. 统一错误消息格式

## 风险评估

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|----------|
| 样式引用错误 | 中 | 高 | 逐步替换，每步验证 |
| 主题切换异常 | 低 | 高 | 保留默认值作为后备 |
| 编译错误 | 低 | 中 | 完整编译测试 |

## 验收标准

1. 所有尺寸值通过资源引用
2. 所有颜色值通过 DynamicResource 引用
3. 用户可见字符串在 Strings.xaml 中定义
4. 应用正常编译运行
5. 主题切换功能正常
6. 开发文档已更新

## 时间估算

| 阶段 | 预计时间 |
|------|----------|
| 尺寸优化 | 1小时 |
| 颜色优化 | 1小时 |
| 字符串优化 | 30分钟 |
| 测试验证 | 30分钟 |
| 文档更新 | 15分钟 |
| **总计** | **3小时15分钟** |
