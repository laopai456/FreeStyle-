using System;
using System.Collections.Generic;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Effects;
using FS服装搭配专家.Core.Models;

namespace FS服装搭配专家.Core.Services
{
    public class ThemeApplier
    {
        public void ApplyThemeToWindow(Window window, SkinTheme theme)
        {
            if (window == null || theme == null) return;

            if (theme.Styles.Window.Background?.Type?.ToLower() == "video")
            {
                window.Background = new SolidColorBrush(Colors.Black);
            }

            ApplyBackground(window, theme.Styles.Window.Background);
            ApplyResources(window, theme);
        }

        /// <summary>
        /// 只更新资源字典（颜色/字体等），不替换 Window/Grid Background。
        /// 用于 MainWindow 等需要保留 XAML 定义背景的场景。
        /// </summary>
        public void ApplyResourcesOnly(Window window, SkinTheme theme)
        {
            if (window == null || theme == null) return;

            // 不设置 window.Background —— MainWindow 自己管理背景（bgBrush 动画 / 视频透明）

            ApplyResources(window, theme);
        }

        public void ApplyThemeToUserControl(UserControl userControl, SkinTheme theme)
        {
            if (userControl == null || theme == null) return;

            ApplyResourcesToUserControl(userControl, theme);
        }

        public void ApplyThemeToGrid(Grid grid, SkinTheme theme)
        {
            if (grid == null || theme == null) return;

            ApplyBackgroundToGrid(grid, theme.Styles.Window.Background);
        }

        private void ApplyBackground(Window window, BackgroundStyle bgStyle)
        {
            if (bgStyle?.Type?.ToLower() != "video")
            {
                window.Background = new SolidColorBrush(Colors.White);
            }

            if (window.Content is Grid rootGrid)
            {
                ApplyBackgroundToGrid(rootGrid, bgStyle);
            }
        }

        private void ApplyBackgroundToGrid(Grid grid, BackgroundStyle bgStyle)
        {
            switch (bgStyle.Type.ToLower())
            {
                case "gradient":
                    var gradient = new LinearGradientBrush
                    {
                        StartPoint = new Point(0, 0),
                        EndPoint = new Point(1, 1)
                    };
                    
                    if (bgStyle.Colors != null && bgStyle.Colors.Count > 0)
                    {
                        for (int i = 0; i < bgStyle.Colors.Count; i++)
                        {
                            gradient.GradientStops.Add(new GradientStop(
                                ParseColor(bgStyle.Colors[i]),
                                i / (double)(bgStyle.Colors.Count - 1)));
                        }
                    }
                    grid.Background = gradient;
                    break;

                case "solid":
                    if (bgStyle.Colors != null && bgStyle.Colors.Count > 0)
                    {
                        grid.Background = new SolidColorBrush(ParseColor(bgStyle.Colors[0]));
                    }
                    break;

                case "image":
                    if (!string.IsNullOrEmpty(bgStyle.ImagePath))
                    {
                        var brush = new ImageBrush
                        {
                            ImageSource = new System.Windows.Media.Imaging.BitmapImage(
                                new Uri(bgStyle.ImagePath, UriKind.RelativeOrAbsolute)),
                            Stretch = Stretch.UniformToFill
                        };
                        grid.Background = brush;
                    }
                    break;

                case "video":
                    grid.Background = new SolidColorBrush(Colors.Transparent);
                    break;
            }
        }

        public bool IsVideoBackground(BackgroundStyle bgStyle)
        {
            return bgStyle?.Type?.ToLower() == "video";
        }

        public string? GetVideoPath(BackgroundStyle bgStyle)
        {
            if (IsVideoBackground(bgStyle) && !string.IsNullOrEmpty(bgStyle.VideoPath))
            {
                string videosDir = System.IO.Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "videos");
                return System.IO.Path.Combine(videosDir, bgStyle.VideoPath);
            }
            return null;
        }

        private void ApplyResources(Window window, SkinTheme theme)
        {
            var resources = window.Resources;

            resources["GlassCardColor"] = CreateBrush(theme.Styles.Card.Background);
            resources["GlassBorderColor"] = CreateBrush(theme.Styles.Card.BorderColor);
            resources["GlassHighlightColor"] = CreateBrush(theme.Styles.Card.BorderColor);
            resources["GlassCardHoverColor"] = CreateBrush(theme.Styles.ListItem.HoverBackground);
            resources["ContentPanelBackgroundColor"] = CreateBrush(theme.Styles.Card.ContentPanelBackground);

            resources["TextColor"] = CreateBrush(theme.Styles.Text.Primary);
            resources["PreviewTextColor"] = CreateBrush(theme.Styles.Text.Primary);
            resources["StatusTextColor"] = CreateBrush(theme.Styles.Text.Secondary);
            resources["TitleTextColor"] = CreateBrush(theme.Styles.Text.Title);
            resources["BodyTextColor"] = CreateBrush(theme.Styles.Text.Body);

            if (!string.IsNullOrEmpty(theme.Styles.Text.FontFamily))
            {
                resources["ThemeFontFamily"] = new FontFamily(theme.Styles.Text.FontFamily);
            }
            else
            {
                resources["ThemeFontFamily"] = new FontFamily("Microsoft YaHei");
            }

            if (!string.IsNullOrEmpty(theme.Styles.Text.FontWeight))
            {
                resources["ThemeFontWeight"] = ParseFontWeight(theme.Styles.Text.FontWeight);
            }
            else
            {
                resources["ThemeFontWeight"] = FontWeights.Normal;
            }

            if (!string.IsNullOrEmpty(theme.Styles.ListItem.Foreground))
            {
                resources["ListItemForegroundColor"] = CreateBrush(theme.Styles.ListItem.Foreground);
            }
            else
            {
                resources["ListItemForegroundColor"] = CreateBrush(theme.Styles.Text.Primary);
            }

            resources["ButtonGlassColor"] = CreateBrush(theme.Styles.Button.Background);
            resources["ButtonGlassPressedColor"] = CreateBrush(theme.Styles.Button.PressedBackground);
            resources["ButtonForegroundColor"] = CreateBrush(theme.Styles.Button.Foreground);

            resources["HoverBackgroundColor"] = CreateBrush(theme.Styles.Button.HoverBackground);
            resources["PressedBackgroundColor"] = CreateBrush(theme.Styles.Button.PressedBackground);
            resources["ListItemBackgroundColor"] = CreateBrush(theme.Styles.ListItem.Background);
            resources["ListItemHoverBackgroundColor"] = CreateBrush(theme.Styles.ListItem.HoverBackground);
            resources["ListItemSelectedBackgroundColor"] = CreateBrush(theme.Styles.ListItem.SelectedBackground);
            resources["TabSelectedBackgroundColor"] = CreateBrush(theme.Styles.Tab.SelectedBackground);
            resources["TabHoverBackgroundColor"] = CreateBrush(theme.Styles.Tab.HoverBackground);
            resources["TabSelectedForegroundColor"] = CreateBrush(theme.Styles.Tab.SelectedForeground);

            // 新增资源键
            resources["PanelBackgroundColor"] = CreateBrush(theme.Styles.Card.Background);
            resources["HeaderBackgroundColor"] = CreateBrush(theme.Styles.Card.ContentPanelBackground);
            resources["WindowBackgroundColor"] = CreateBrush(theme.Styles.Window.Background?.Type?.ToLower() == "video" ? "#000000" : theme.Styles.Window.Background?.Colors?.FirstOrDefault() ?? "#1E1E1E");
            resources["LogBackgroundColor"] = CreateBrush(theme.Styles.Card.LogBackgroundColor);
            resources["AccentColor"] = CreateBrush(theme.Styles.Text.AccentColor);
            resources["ScrollBarThumbColor"] = CreateBrush(theme.Styles.ScrollBar.ThumbColor);
            resources["TabUnselectedForegroundColor"] = CreateBrush(theme.Styles.Tab.BorderColor);
            resources["CardBorderColor"] = CreateBrush(theme.Styles.Card.BorderColor);
            resources["SlotCardBackgroundColor"] = CreateBrush(theme.Styles.Button.Background);
            resources["SlotIconBackgroundColor"] = CreateBrush(theme.Styles.Card.Background);
            resources["SlotEmptyTextColor"] = CreateBrush(theme.Styles.Text.Body);
            resources["SlotCategoryTextColor"] = CreateBrush(theme.Styles.Text.Secondary);
            resources["SlotItemNameTextColor"] = CreateBrush(theme.Styles.Text.Primary);
            resources["SlotEffectTextColor"] = CreateBrush(theme.Styles.Text.Body);
            resources["SlotSelectedBorderColor"] = CreateBrush(theme.Styles.ListItem.SelectedBackground);
            resources["InfoMessageColor"] = CreateBrush(theme.Styles.Text.AccentColor);
            resources["TextBoxBackgroundColor"] = CreateBrush(theme.Styles.TextBox.Background);
            resources["TextBoxBorderColor"] = CreateBrush(theme.Styles.TextBox.BorderColor);
            resources["TextBoxForegroundColor"] = CreateBrush(theme.Styles.TextBox.Foreground);

            // 视频背景模式：面板需要半透明深色底色，确保内容在视频上可读
            if (theme.Styles.Window.Background?.Type?.ToLower() == "video")
            {
                var panelBg = new SolidColorBrush(Color.FromArgb(0xAA, 0x1A, 0x1A, 0x2E));
                var headerBg = new SolidColorBrush(Color.FromArgb(0xAA, 0x12, 0x12, 0x22));
                var cardBg = new SolidColorBrush(Color.FromArgb(0xAA, 0x1A, 0x1A, 0x2E));
                var slotBg = new SolidColorBrush(Color.FromArgb(0xBB, 0x2A, 0x2A, 0x4E));
                var slotIconBg = new SolidColorBrush(Color.FromArgb(0xBB, 0x1A, 0x1A, 0x3E));
                var borderClr = new SolidColorBrush(Color.FromArgb(0xCC, 0x4A, 0x4A, 0x7A));
                var logBg = new SolidColorBrush(Color.FromArgb(0xAA, 0x0A, 0x0A, 0x1F));
                var listItemBg = new SolidColorBrush(Color.FromArgb(0x99, 0x1A, 0x1A, 0x2E));
                var listItemHoverBg = new SolidColorBrush(Color.FromArgb(0xBB, 0x2A, 0x2A, 0x4E));
                var listItemSelBg = new SolidColorBrush(Color.FromArgb(0xCC, 0x3D, 0x3D, 0x6B));
                var tabSelBg = new SolidColorBrush(Color.FromArgb(0xBB, 0x1A, 0x1A, 0x3E));
                var tabHoverBg = new SolidColorBrush(Color.FromArgb(0xBB, 0x2A, 0x2A, 0x4E));
                var btnBg = new SolidColorBrush(Color.FromArgb(0xBB, 0x2A, 0x2A, 0x5E));
                var btnHoverBg = new SolidColorBrush(Color.FromArgb(0xCC, 0x3D, 0x3D, 0x7A));
                var btnPressedBg = new SolidColorBrush(Color.FromArgb(0xBB, 0x1A, 0x1A, 0x4E));
                var txtBoxBg = new SolidColorBrush(Color.FromArgb(0xBB, 0x1A, 0x1A, 0x3E));

                resources["PanelBackgroundColor"] = panelBg;
                resources["HeaderBackgroundColor"] = headerBg;
                resources["WindowBackgroundColor"] = new SolidColorBrush(Colors.Black);
                resources["LogBackgroundColor"] = logBg;
                resources["GlassCardColor"] = cardBg;
                resources["ContentPanelBackgroundColor"] = headerBg;
                resources["SlotCardBackgroundColor"] = slotBg;
                resources["SlotIconBackgroundColor"] = slotIconBg;
                resources["CardBorderColor"] = borderClr;
                resources["TextBoxBackgroundColor"] = txtBoxBg;
                resources["TextBoxBorderColor"] = borderClr;

                // 列表项必须半透明，不能是 Transparent
                resources["ListItemBackgroundColor"] = listItemBg;
                resources["ListItemHoverBackgroundColor"] = listItemHoverBg;
                resources["ListItemSelectedBackgroundColor"] = listItemSelBg;
                resources["GlassCardHoverColor"] = listItemHoverBg;

                // Tab 必须半透明
                resources["TabSelectedBackgroundColor"] = tabSelBg;
                resources["TabHoverBackgroundColor"] = tabHoverBg;

                // 按钮必须半透明
                resources["ButtonGlassColor"] = btnBg;
                resources["ButtonGlassPressedColor"] = btnPressedBg;
                resources["HoverBackgroundColor"] = btnHoverBg;
                resources["PressedBackgroundColor"] = btnPressedBg;
            }

            UpdateAllVisualChildren(window, theme);
        }

        /// <summary>
        /// 视频模式：用统一 alpha 重设所有覆盖层颜色（保持 RGB 不变）。
        /// 滑块拖动时实时调用，不需要完整主题重载。
        /// </summary>
        public void ApplyVideoOverlayAlpha(Window window, byte alpha)
        {
            if (window == null) return;
            var res = window.Resources;

            // 覆盖色定义：(resourceKey, R, G, B)
            var overlayColors = new (string key, byte r, byte g, byte b)[]
            {
                ("PanelBackgroundColor",               0x1A, 0x1A, 0x2E),
                ("HeaderBackgroundColor",               0x12, 0x12, 0x22),
                ("ContentPanelBackgroundColor",          0x12, 0x12, 0x22),
                ("GlassCardColor",                      0x1A, 0x1A, 0x2E),
                ("GlassCardHoverColor",                 0x2A, 0x2A, 0x4E),
                ("SlotCardBackgroundColor",              0x2A, 0x2A, 0x4E),
                ("SlotIconBackgroundColor",              0x1A, 0x1A, 0x3E),
                ("CardBorderColor",                     0x4A, 0x4A, 0x7A),
                ("ListItemBackgroundColor",              0x1A, 0x1A, 0x2E),
                ("ListItemHoverBackgroundColor",         0x2A, 0x2A, 0x4E),
                ("ListItemSelectedBackgroundColor",      0x3D, 0x3D, 0x6B),
                ("TabSelectedBackgroundColor",           0x1A, 0x1A, 0x3E),
                ("TabHoverBackgroundColor",              0x2A, 0x2A, 0x4E),
                ("ButtonGlassColor",                    0x2A, 0x2A, 0x5E),
                ("ButtonGlassPressedColor",              0x1A, 0x1A, 0x4E),
                ("HoverBackgroundColor",                0x3D, 0x3D, 0x7A),
                ("PressedBackgroundColor",               0x1A, 0x1A, 0x4E),
                ("LogBackgroundColor",                  0x0A, 0x0A, 0x1F),
                ("TextBoxBackgroundColor",               0x1A, 0x1A, 0x3E),
                ("TextBoxBorderColor",                  0x4A, 0x4A, 0x7A),
            };

            foreach (var (key, r, g, b) in overlayColors)
            {
                res[key] = new SolidColorBrush(Color.FromArgb(alpha, r, g, b));
            }
        }

        private void ApplyResourcesToUserControl(UserControl userControl, SkinTheme theme)
        {
            var resources = userControl.Resources;

            resources["GlassCardColor"] = CreateBrush(theme.Styles.Card.Background);
            resources["GlassBorderColor"] = CreateBrush(theme.Styles.Card.BorderColor);
            resources["GlassHighlightColor"] = CreateBrush(theme.Styles.Card.BorderColor);
            resources["GlassCardHoverColor"] = CreateBrush(theme.Styles.ListItem.HoverBackground);
            resources["ContentPanelBackgroundColor"] = CreateBrush(theme.Styles.Card.ContentPanelBackground);

            resources["TextColor"] = CreateBrush(theme.Styles.Text.Primary);
            resources["PreviewTextColor"] = CreateBrush(theme.Styles.Text.Primary);
            resources["StatusTextColor"] = CreateBrush(theme.Styles.Text.Secondary);
            resources["TitleTextColor"] = CreateBrush(theme.Styles.Text.Title);
            resources["BodyTextColor"] = CreateBrush(theme.Styles.Text.Body);

            if (!string.IsNullOrEmpty(theme.Styles.Text.FontFamily))
            {
                resources["ThemeFontFamily"] = new FontFamily(theme.Styles.Text.FontFamily);
            }
            else
            {
                resources["ThemeFontFamily"] = new FontFamily("Microsoft YaHei");
            }

            if (!string.IsNullOrEmpty(theme.Styles.Text.FontWeight))
            {
                resources["ThemeFontWeight"] = ParseFontWeight(theme.Styles.Text.FontWeight);
            }
            else
            {
                resources["ThemeFontWeight"] = FontWeights.Normal;
            }

            if (!string.IsNullOrEmpty(theme.Styles.ListItem.Foreground))
            {
                resources["ListItemForegroundColor"] = CreateBrush(theme.Styles.ListItem.Foreground);
            }
            else
            {
                resources["ListItemForegroundColor"] = CreateBrush(theme.Styles.Text.Primary);
            }

            resources["ButtonGlassColor"] = CreateBrush(theme.Styles.Button.Background);
            resources["ButtonGlassPressedColor"] = CreateBrush(theme.Styles.Button.PressedBackground);
            resources["ButtonForegroundColor"] = CreateBrush(theme.Styles.Button.Foreground);

            resources["HoverBackgroundColor"] = CreateBrush(theme.Styles.Button.HoverBackground);
            resources["PressedBackgroundColor"] = CreateBrush(theme.Styles.Button.PressedBackground);
            resources["ListItemBackgroundColor"] = CreateBrush(theme.Styles.ListItem.Background);
            resources["ListItemHoverBackgroundColor"] = CreateBrush(theme.Styles.ListItem.HoverBackground);
            resources["ListItemSelectedBackgroundColor"] = CreateBrush(theme.Styles.ListItem.SelectedBackground);

            // 新增资源键
            resources["PanelBackgroundColor"] = CreateBrush(theme.Styles.Card.Background);
            resources["HeaderBackgroundColor"] = CreateBrush(theme.Styles.Card.ContentPanelBackground);
            resources["WindowBackgroundColor"] = CreateBrush(theme.Styles.Window.Background?.Type?.ToLower() == "video" ? "#000000" : theme.Styles.Window.Background?.Colors?.FirstOrDefault() ?? "#1E1E1E");
            resources["LogBackgroundColor"] = CreateBrush(theme.Styles.Card.LogBackgroundColor);
            resources["AccentColor"] = CreateBrush(theme.Styles.Text.AccentColor);
            resources["ScrollBarThumbColor"] = CreateBrush(theme.Styles.ScrollBar.ThumbColor);
            resources["TabUnselectedForegroundColor"] = CreateBrush(theme.Styles.Tab.BorderColor);
            resources["CardBorderColor"] = CreateBrush(theme.Styles.Card.BorderColor);
            resources["SlotCardBackgroundColor"] = CreateBrush(theme.Styles.Button.Background);
            resources["SlotIconBackgroundColor"] = CreateBrush(theme.Styles.Card.Background);
            resources["SlotEmptyTextColor"] = CreateBrush(theme.Styles.Text.Body);
            resources["SlotCategoryTextColor"] = CreateBrush(theme.Styles.Text.Secondary);
            resources["SlotItemNameTextColor"] = CreateBrush(theme.Styles.Text.Primary);
            resources["SlotEffectTextColor"] = CreateBrush(theme.Styles.Text.Body);
            resources["SlotSelectedBorderColor"] = CreateBrush(theme.Styles.ListItem.SelectedBackground);
            resources["InfoMessageColor"] = CreateBrush(theme.Styles.Text.AccentColor);
            resources["TextBoxBackgroundColor"] = CreateBrush(theme.Styles.TextBox.Background);
            resources["TextBoxBorderColor"] = CreateBrush(theme.Styles.TextBox.BorderColor);
            resources["TextBoxForegroundColor"] = CreateBrush(theme.Styles.TextBox.Foreground);

            // 视频背景模式：面板需要半透明深色底色，确保内容在视频上可读
            if (theme.Styles.Window.Background?.Type?.ToLower() == "video")
            {
                var panelBg = new SolidColorBrush(Color.FromArgb(0xAA, 0x1A, 0x1A, 0x2E));
                var headerBg = new SolidColorBrush(Color.FromArgb(0xAA, 0x12, 0x12, 0x22));
                var cardBg = new SolidColorBrush(Color.FromArgb(0xAA, 0x1A, 0x1A, 0x2E));
                var slotBg = new SolidColorBrush(Color.FromArgb(0xBB, 0x2A, 0x2A, 0x4E));
                var slotIconBg = new SolidColorBrush(Color.FromArgb(0xBB, 0x1A, 0x1A, 0x3E));
                var borderClr = new SolidColorBrush(Color.FromArgb(0xCC, 0x4A, 0x4A, 0x7A));
                var logBg = new SolidColorBrush(Color.FromArgb(0xAA, 0x0A, 0x0A, 0x1F));
                var listItemBg = new SolidColorBrush(Color.FromArgb(0x99, 0x1A, 0x1A, 0x2E));
                var listItemHoverBg = new SolidColorBrush(Color.FromArgb(0xBB, 0x2A, 0x2A, 0x4E));
                var listItemSelBg = new SolidColorBrush(Color.FromArgb(0xCC, 0x3D, 0x3D, 0x6B));
                var tabSelBg = new SolidColorBrush(Color.FromArgb(0xBB, 0x1A, 0x1A, 0x3E));
                var tabHoverBg = new SolidColorBrush(Color.FromArgb(0xBB, 0x2A, 0x2A, 0x4E));
                var btnBg = new SolidColorBrush(Color.FromArgb(0xBB, 0x2A, 0x2A, 0x5E));
                var btnHoverBg = new SolidColorBrush(Color.FromArgb(0xCC, 0x3D, 0x3D, 0x7A));
                var btnPressedBg = new SolidColorBrush(Color.FromArgb(0xBB, 0x1A, 0x1A, 0x4E));
                var txtBoxBg = new SolidColorBrush(Color.FromArgb(0xBB, 0x1A, 0x1A, 0x3E));

                resources["PanelBackgroundColor"] = panelBg;
                resources["HeaderBackgroundColor"] = headerBg;
                resources["WindowBackgroundColor"] = new SolidColorBrush(Colors.Black);
                resources["LogBackgroundColor"] = logBg;
                resources["GlassCardColor"] = cardBg;
                resources["ContentPanelBackgroundColor"] = headerBg;
                resources["SlotCardBackgroundColor"] = slotBg;
                resources["SlotIconBackgroundColor"] = slotIconBg;
                resources["CardBorderColor"] = borderClr;
                resources["TextBoxBackgroundColor"] = txtBoxBg;
                resources["TextBoxBorderColor"] = borderClr;

                // 列表项必须半透明，不能是 Transparent
                resources["ListItemBackgroundColor"] = listItemBg;
                resources["ListItemHoverBackgroundColor"] = listItemHoverBg;
                resources["ListItemSelectedBackgroundColor"] = listItemSelBg;
                resources["GlassCardHoverColor"] = listItemHoverBg;

                // Tab 必须半透明
                resources["TabSelectedBackgroundColor"] = tabSelBg;
                resources["TabHoverBackgroundColor"] = tabHoverBg;

                // 按钮必须半透明
                resources["ButtonGlassColor"] = btnBg;
                resources["ButtonGlassPressedColor"] = btnPressedBg;
                resources["HoverBackgroundColor"] = btnHoverBg;
                resources["PressedBackgroundColor"] = btnPressedBg;
            }

            UpdateAllVisualChildren(userControl, theme);
        }

        private void UpdateAllVisualChildren(DependencyObject parent, SkinTheme theme)
        {
            for (int i = 0; i < System.Windows.Media.VisualTreeHelper.GetChildrenCount(parent); i++)
            {
                var child = System.Windows.Media.VisualTreeHelper.GetChild(parent, i);
                UpdateAllVisualChildren(child, theme);
            }
        }

        private SolidColorBrush CreateBrush(string colorString)
        {
            return new SolidColorBrush(ParseColor(colorString));
        }

        private Color ParseColor(string colorString)
        {
            if (string.IsNullOrEmpty(colorString))
            {
                return Colors.Transparent;
            }

            colorString = colorString.Trim();

            if (colorString.ToLower() == "transparent")
            {
                return Colors.Transparent;
            }

            try
            {
                if (colorString.StartsWith("#"))
                {
                    string hex = colorString.Substring(1);
                    
                    if (hex.Length == 6)
                    {
                        return Color.FromRgb(
                            Convert.ToByte(hex.Substring(0, 2), 16),
                            Convert.ToByte(hex.Substring(2, 2), 16),
                            Convert.ToByte(hex.Substring(4, 2), 16));
                    }
                    else if (hex.Length == 8)
                    {
                        return Color.FromArgb(
                            Convert.ToByte(hex.Substring(0, 2), 16),
                            Convert.ToByte(hex.Substring(2, 2), 16),
                            Convert.ToByte(hex.Substring(4, 2), 16),
                            Convert.ToByte(hex.Substring(6, 2), 16));
                    }
                }

                return (Color)ColorConverter.ConvertFromString(colorString);
            }
            catch
            {
                return Colors.Transparent;
            }
        }

        public Brush GetBackgroundBrush(BackgroundStyle bgStyle)
        {
            switch (bgStyle.Type.ToLower())
            {
                case "gradient":
                    var gradient = new LinearGradientBrush
                    {
                        StartPoint = new Point(0, 0),
                        EndPoint = new Point(1, 1)
                    };
                    
                    if (bgStyle.Colors != null && bgStyle.Colors.Count > 0)
                    {
                        for (int i = 0; i < bgStyle.Colors.Count; i++)
                        {
                            gradient.GradientStops.Add(new GradientStop(
                                ParseColor(bgStyle.Colors[i]),
                                i / (double)(bgStyle.Colors.Count - 1)));
                        }
                    }
                    return gradient;

                case "solid":
                    if (bgStyle.Colors != null && bgStyle.Colors.Count > 0)
                    {
                        return new SolidColorBrush(ParseColor(bgStyle.Colors[0]));
                    }
                    break;

                case "image":
                    if (!string.IsNullOrEmpty(bgStyle.ImagePath))
                    {
                        return new ImageBrush
                        {
                            ImageSource = new System.Windows.Media.Imaging.BitmapImage(
                                new Uri(bgStyle.ImagePath, UriKind.RelativeOrAbsolute)),
                            Stretch = Stretch.UniformToFill
                        };
                    }
                    break;
            }

            return new SolidColorBrush(Colors.Transparent);
        }

        public DropShadowEffect CreateShadowEffect(ShadowStyle? shadow)
        {
            if (shadow == null) return new DropShadowEffect();

            return new DropShadowEffect
            {
                BlurRadius = shadow.BlurRadius,
                ShadowDepth = shadow.ShadowDepth,
                Opacity = shadow.Opacity,
                Direction = 270,
                Color = ParseColor(shadow.Color)
            };
        }

        private FontWeight ParseFontWeight(string weight)
        {
            return weight?.ToLower() switch
            {
                "thin" => FontWeights.Thin,
                "extralight" => FontWeights.ExtraLight,
                "light" => FontWeights.Light,
                "normal" => FontWeights.Normal,
                "medium" => FontWeights.Medium,
                "semibold" => FontWeights.SemiBold,
                "bold" => FontWeights.Bold,
                "extrabold" => FontWeights.ExtraBold,
                "black" => FontWeights.Black,
                "ultralight" => FontWeights.UltraLight,
                "ultrabold" => FontWeights.UltraBold,
                _ => FontWeights.Normal
            };
        }
    }
}
