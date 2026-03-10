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
            skinManager = manager;
            themeApplier = new ThemeApplier();
            ApplyCurrentThemeFont();
            InitializeThemeList();
        }

        private void ApplyCurrentThemeFont()
        {
            if (skinManager.CurrentTheme != null)
            {
                var theme = skinManager.CurrentTheme;
                
                if (!string.IsNullOrEmpty(theme.Styles.Text.FontFamily))
                {
                    Resources["ThemeFontFamily"] = new FontFamily(theme.Styles.Text.FontFamily);
                }
                
                if (!string.IsNullOrEmpty(theme.Styles.Text.FontWeight))
                {
                    Resources["ThemeFontWeight"] = ParseFontWeight(theme.Styles.Text.FontWeight);
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
            previewGrid.Background = themeApplier.GetBackgroundBrush(theme.Styles.Window.Background);
            
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
    }
}
