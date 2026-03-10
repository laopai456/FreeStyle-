using System;
using System.Collections.Generic;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Effects;
using FS服装搭配专家v1._0.Core.Models;

namespace FS服装搭配专家v1._0.Core.Services
{
    public class ThemeApplier
    {
        public void ApplyThemeToWindow(Window window, SkinTheme theme)
        {
            if (window == null || theme == null) return;

            ApplyBackground(window, theme.Styles.Window.Background);
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
            }
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

            UpdateAllVisualChildren(window, theme);
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
