using System;
using System.ComponentModel;
using System.IO;
using System.Windows;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Animation;
using Microsoft.Win32;
using FS服装搭配专家.Core.Models;
using FS服装搭配专家.Core.Services;

namespace FS服装搭配专家
{
    public partial class SkinWindow : Window
    {
        private SkinManager skinManager;
        private SkinTheme selectedTheme;
        private ThemeApplier themeApplier;
        private bool _isClosing = false;

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

            // 弹出动画：淡入
            this.Opacity = 0;
            this.Loaded += (s, e) =>
            {
                var fadeIn = new DoubleAnimation(0, 1, TimeSpan.FromSeconds(0.4))
                {
                    EasingFunction = new QuadraticEase { EasingMode = EasingMode.EaseOut }
                };
                this.BeginAnimation(Window.OpacityProperty, fadeIn);
            };
        }

        protected override void OnClosing(CancelEventArgs e)
        {
            if (_isClosing) { base.OnClosing(e); return; }
            e.Cancel = true;
            _isClosing = true;

            var fadeOut = new DoubleAnimation(1, 0, TimeSpan.FromSeconds(0.15));
            fadeOut.Completed += (s, _) => Dispatcher.Invoke(Close);
            this.BeginAnimation(Window.OpacityProperty, fadeOut);
        }

        private void ApplyCurrentTheme()
        {
            if (skinManager.CurrentTheme != null)
            {
                var theme = skinManager.CurrentTheme;
                
                // SkinWindow 只应用颜色/字体，不应用视频背景
                // 否则视频模式下 SkinWindow 控件全透明，用户无法切换主题
                themeApplier.ApplyResourcesOnly(this, theme);
                
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

        private void Delete_Click(object sender, RoutedEventArgs e)
        {
            if (selectedTheme == null)
            {
                MessageBox.Show("请先选择要删除的主题", "提示", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            // 内置主题不允许删除
            if (selectedTheme.Id == "default" || selectedTheme.Id == "dark" || selectedTheme.Id == "galaxy")
            {
                MessageBox.Show("内置主题不可删除", "提示", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            var result = MessageBox.Show($"确定删除主题「{selectedTheme.Name}」？\n此操作不可撤销。", "确认删除",
                MessageBoxButton.YesNo, MessageBoxImage.Question);

            if (result == MessageBoxResult.Yes)
            {
                string deletedId = selectedTheme.Id;
                skinManager.DeleteCustomTheme(deletedId);

                // 如果删除的是当前正在使用的主题，回退到 default
                if (skinManager.CurrentTheme?.Id == deletedId)
                {
                    skinManager.ApplyTheme("default");
                }

                // 刷新列表
                lstSkins.ItemsSource = null;
                lstSkins.ItemsSource = skinManager.Themes;
                if (lstSkins.Items.Count > 0)
                {
                    lstSkins.SelectedIndex = 0;
                }
            }
        }

        private void AddVideoBackground_Click(object sender, RoutedEventArgs e)
        {
            var dialog = new OpenFileDialog
            {
                Title = "选择视频背景文件",
                Filter = "视频文件|*.mp4;*.avi;*.mkv;*.mov;*.wmv|所有文件|*.*",
                FilterIndex = 1
            };

            if (dialog.ShowDialog() == true)
            {
                try
                {
                    // 确保 videos 目录存在
                    string videosDir = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "videos");
                    if (!Directory.Exists(videosDir))
                        Directory.CreateDirectory(videosDir);

                    // 复制视频到 videos 目录
                    string fileName = Path.GetFileName(dialog.FileName);
                    string destPath = Path.Combine(videosDir, fileName);

                    if (dialog.FileName != destPath)
                    {
                        File.Copy(dialog.FileName, destPath, overwrite: true);
                    }

                    // 基于当前主题创建视频背景主题
                    string themeName = Path.GetFileNameWithoutExtension(fileName);
                    string themeId = "video_" + DateTime.Now.ToString("yyyyMMdd_HHmmss");

                    var videoTheme = new SkinTheme
                    {
                        Id = themeId,
                        Name = $"🎬 {themeName}",
                        Author = "自定义",
                        Version = "1.0",
                        Description = $"视频背景: {fileName}",
                        Styles = new ThemeStyles
                        {
                            Window = new Core.Models.WindowStyle
                            {
                                Background = new BackgroundStyle
                                {
                                    Type = "video",
                                    VideoPath = fileName,
                                    Volume = 0
                                }
                            },
                            Card = new CardStyle
                            {
                                Background = "#1A1A2E",
                                BorderColor = "#3D3D6B",
                                ContentPanelBackground = "#12122A",
                                LogBackgroundColor = "#0A0A1F",
                                CornerRadius = 8,
                                Shadow = new ShadowStyle { BlurRadius = 20, ShadowDepth = 4, Opacity = 0.3, Color = "#6DD5FA" }
                            },
                            Button = new ButtonStyle
                            {
                                Background = "#2A2A5E",
                                HoverBackground = "#3D3D7A",
                                PressedBackground = "#1A1A4E",
                                BorderColor = "#4D4D8A",
                                CornerRadius = 6,
                                Foreground = "#C8D6E5",
                                Shadow = new ShadowStyle { BlurRadius = 10, ShadowDepth = 2, Opacity = 0.2, Color = "#6DD5FA" }
                            },
                            Text = new TextStyle
                            {
                                Primary = "#C8D6E5",
                                Secondary = "#8395A7",
                                Title = "#FFFFFF",
                                Body = "#576574",
                                AccentColor = "#7EC8E3"
                            },
                            ListItem = new ListItemStyle
                            {
                                Background = "#BB1A1A2E",
                                HoverBackground = "#2A2A5E",
                                SelectedBackground = "#3D3D8A",
                                BorderColor = "#8395A7",
                                CornerRadius = 4,
                                Foreground = "#C8D6E5"
                            },
                            Tab = new TabStyle
                            {
                                Background = "Transparent",
                                SelectedBackground = "#1A1A3E",
                                HoverBackground = "#2A2A5E",
                                BorderColor = "#8395A7",
                                SelectedForeground = "#C8D6E5",
                                CornerRadius = 4
                            },
                            TextBox = new TextBoxStyle
                            {
                                Background = "#1A1A3E",
                                BorderColor = "#3D3D6B",
                                Foreground = "#C8D6E5",
                                CornerRadius = 4
                            },
                            ScrollBar = new ScrollBarStyle
                            {
                                Background = "Transparent",
                                ThumbColor = "#4D4D8A",
                                Width = 6,
                                CornerRadius = 3
                            }
                        }
                    };

                    // 保存主题
                    var loader = new ThemeLoader();
                    loader.SaveTheme(videoTheme);

                    // 添加到管理器并选中
                    skinManager.AddTheme(videoTheme);
                    lstSkins.Items.Refresh();

                    // 选中新添加的主题
                    for (int i = 0; i < skinManager.Themes.Count; i++)
                    {
                        if (skinManager.Themes[i].Id == themeId)
                        {
                            lstSkins.SelectedIndex = i;
                            break;
                        }
                    }

                    MessageBox.Show($"视频背景主题已创建：{themeName}\n点击\u201C应用\u201D即可使用", "成功", MessageBoxButton.OK, MessageBoxImage.Information);
                }
                catch (Exception ex)
                {
                    MessageBox.Show($"创建视频背景主题失败：{ex.Message}", "错误", MessageBoxButton.OK, MessageBoxImage.Error);
                }
            }
        }

        private void Apply_Click(object sender, RoutedEventArgs e)
        {
            if (selectedTheme != null)
            {
                Console.WriteLine($"[Theme] SkinWindow Apply_Click: selectedTheme={selectedTheme.Id}, name={selectedTheme.Name}, bgType={selectedTheme.Styles.Window.Background?.Type}");
                skinManager.ApplyTheme(selectedTheme);
                ThemeApplied?.Invoke(this, selectedTheme);
                this.Close();
            }
            else
            {
                Console.WriteLine("[Theme] SkinWindow Apply_Click: selectedTheme is null!");
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
