using System;
using System.Windows;
using System.Windows.Input;
using System.Windows.Media;
using FS服装搭配专家v1._0.Core.Models;
using FS服装搭配专家v1._0.Core.Services;

namespace FS服装搭配专家v1._0
{
    public partial class SkinWindow : Window
    {
        private SkinManager skinManager;
        private SkinTheme selectedTheme;
        private ThemeApplier themeApplier;

        public event EventHandler<SkinTheme>? ThemeApplied;

        public SkinWindow(SkinManager manager)
        {
            InitializeComponent();
            LoadWindowSize();
            skinManager = manager;
            themeApplier = new ThemeApplier();
            ApplyCurrentTheme();
            InitializeThemeList();
            this.SizeChanged += SkinWindow_SizeChanged;
        }

        private void ApplyCurrentTheme()
        {
            if (skinManager.CurrentTheme != null)
            {
                var theme = skinManager.CurrentTheme;
                
                themeApplier.ApplyThemeToWindow(this, theme);
                
                if (!string.IsNullOrEmpty(theme.Styles.Text.FontFamily))
                {
                    Resources["ThemeFontFamily"] = new FontFamily(theme.Styles.Text.FontFamily);
                }
                else
                {
                    Resources["ThemeFontFamily"] = new FontFamily("Microsoft YaHei");
                }
                
                if (!string.IsNullOrEmpty(theme.Styles.Text.FontWeight))
                {
                    Resources["ThemeFontWeight"] = ParseFontWeight(theme.Styles.Text.FontWeight);
                }
                else
                {
                    Resources["ThemeFontWeight"] = FontWeights.Normal;
                }
                
                if (theme.Id == "dark")
                {
                    Resources["GlassCardColor"] = new SolidColorBrush(Color.FromArgb(0x33, 0x1A, 0x1A, 0x2E));
                    Resources["TextColor"] = new SolidColorBrush(Colors.White);
                    Resources["TitleTextColor"] = new SolidColorBrush(Color.FromRgb(0x6D, 0xD5, 0xFA));
                    Resources["StatusTextColor"] = new SolidColorBrush(Color.FromRgb(0xB0, 0xB0, 0xB0));
                    Resources["GlassBorderColor"] = new SolidColorBrush(Color.FromRgb(0x40, 0x40, 0x60));
                    Resources["GlassHighlightColor"] = new SolidColorBrush(Color.FromRgb(0x50, 0x50, 0x70));
                    Resources["ButtonForegroundColor"] = new SolidColorBrush(Colors.White);
                    Resources["ButtonGlassColor"] = new SolidColorBrush(Color.FromArgb(0x60, 0x40, 0x40, 0x60));
                    Resources["HoverBackgroundColor"] = new SolidColorBrush(Color.FromArgb(0x80, 0x50, 0x50, 0x70));
                    Resources["PressedBackgroundColor"] = new SolidColorBrush(Color.FromArgb(0x99, 0x60, 0x60, 0x80));
                }
                else if (theme.Id == "galaxy")
                {
                    Resources["GlassCardColor"] = new SolidColorBrush(Colors.White);
                    Resources["TextColor"] = new SolidColorBrush(Color.FromRgb(0x42, 0x42, 0x42));
                    Resources["TitleTextColor"] = new SolidColorBrush(Color.FromRgb(0x42, 0x42, 0x42));
                    Resources["StatusTextColor"] = new SolidColorBrush(Color.FromRgb(0x75, 0x75, 0x75));
                    Resources["GlassBorderColor"] = new SolidColorBrush(Color.FromRgb(0xE0, 0xE0, 0xE0));
                    Resources["GlassHighlightColor"] = new SolidColorBrush(Color.FromRgb(0xD0, 0xD0, 0xD0));
                    Resources["ButtonForegroundColor"] = new SolidColorBrush(Colors.White);
                }
                else
                {
                    Resources["GlassCardColor"] = new SolidColorBrush(Color.FromArgb(0xCC, 0xFF, 0xFF, 0xFF));
                    Resources["TextColor"] = new SolidColorBrush(Color.FromRgb(0x33, 0x33, 0x33));
                    Resources["TitleTextColor"] = new SolidColorBrush(Color.FromRgb(0x33, 0x33, 0x33));
                    Resources["StatusTextColor"] = new SolidColorBrush(Color.FromRgb(0x75, 0x75, 0x75));
                    Resources["GlassBorderColor"] = new SolidColorBrush(Color.FromRgb(0xE0, 0xE0, 0xE0));
                    Resources["GlassHighlightColor"] = new SolidColorBrush(Color.FromRgb(0xD0, 0xD0, 0xD0));
                    Resources["ButtonForegroundColor"] = new SolidColorBrush(Color.FromRgb(0x33, 0x33, 0x33));
                    Resources["ButtonGlassColor"] = new SolidColorBrush(Color.FromArgb(0xCC, 0xFF, 0xFF, 0xFF));
                }
            }
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

        private void InitializeThemeList()
        {
            lstSkins.ItemsSource = skinManager.Themes;
            
            if (lstSkins.Items.Count > 0)
            {
                for (int i = 0; i < skinManager.Themes.Count; i++)
                {
                    if (skinManager.Themes[i].Id == skinManager.CurrentTheme?.Id)
                    {
                        lstSkins.SelectedIndex = i;
                        break;
                    }
                }
                
                if (lstSkins.SelectedIndex < 0)
                {
                    lstSkins.SelectedIndex = 0;
                }
            }
        }

        private void TitleBar_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
        {
            if (this.WindowState == WindowState.Maximized)
            {
                this.WindowState = WindowState.Normal;
                var point = e.GetPosition(this);
                this.Left = point.X;
                this.Top = point.Y;
            }
            
            this.DragMove();
        }

        private void Close_Click(object sender, RoutedEventArgs e)
        {
            this.Close();
        }

        private void Cancel_Click(object sender, RoutedEventArgs e)
        {
            this.Close();
        }

        private void Apply_Click(object sender, RoutedEventArgs e)
        {
            if (selectedTheme != null)
            {
                skinManager.ApplyTheme(selectedTheme);
                ThemeApplied?.Invoke(this, selectedTheme);
                this.Close();
            }
        }

        private void lstSkins_SelectionChanged(object sender, System.Windows.Controls.SelectionChangedEventArgs e)
        {
            if (lstSkins.SelectedItem != null)
            {
                selectedTheme = lstSkins.SelectedItem as SkinTheme;
                if (selectedTheme != null)
                {
                    UpdatePreview(selectedTheme);
                    
                    txtSkinInfo.Text = $"主题名称: {selectedTheme.Name}\n" +
                                      $"作者: {selectedTheme.Author}\n" +
                                      $"版本: {selectedTheme.Version}\n" +
                                      $"描述: {selectedTheme.Description}";
                }
            }
        }

        private void UpdatePreview(SkinTheme theme)
        {
            if (theme.Styles.Window.Background.Type?.ToLower() == "video")
            {
                var gradient = new LinearGradientBrush
                {
                    StartPoint = new Point(0, 0),
                    EndPoint = new Point(1, 1)
                };
                gradient.GradientStops.Add(new GradientStop(Color.FromRgb(0x1A, 0x1A, 0x2E), 0));
                gradient.GradientStops.Add(new GradientStop(Color.FromRgb(0x16, 0x21, 0x3E), 0.5));
                gradient.GradientStops.Add(new GradientStop(Color.FromRgb(0x0F, 0x34, 0x60), 1));
                previewGrid.Background = gradient;
            }
            else
            {
                previewGrid.Background = themeApplier.GetBackgroundBrush(theme.Styles.Window.Background);
            }
            
            previewBorder.BorderBrush = new SolidColorBrush(ParseColor(theme.Styles.Card.BorderColor));
            
            foreach (var child in previewGrid.Children)
            {
                if (child is System.Windows.Controls.TextBlock textBlock)
                {
                    textBlock.Foreground = new SolidColorBrush(ParseColor(theme.Styles.Text.Primary));
                }
            }
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

        /// <summary>
        /// 从配置文件加载窗口尺寸
        /// </summary>
        private void LoadWindowSize()
        {
            try
            {
                var configService = Core.Config.ConfigService.Instance;
                this.Width = configService.SkinWindowWidth;
                this.Height = configService.SkinWindowHeight;
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[SkinWindow] 加载窗口尺寸失败: {ex.Message}");
            }
        }

        /// <summary>
        /// 窗口尺寸变化事件处理
        /// </summary>
        private void SkinWindow_SizeChanged(object sender, SizeChangedEventArgs e)
        {
            try
            {
                if (this.WindowState == WindowState.Normal)
                {
                    var configService = Core.Config.ConfigService.Instance;
                    configService.SkinWindowWidth = this.ActualWidth;
                    configService.SkinWindowHeight = this.ActualHeight;
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[SkinWindow] 保存窗口尺寸失败: {ex.Message}");
            }
        }
    }
}
