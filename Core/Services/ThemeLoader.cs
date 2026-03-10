using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using FS服装搭配专家v1._0.Core.Models;

namespace FS服装搭配专家v1._0.Core.Services
{
    public class ThemeLoader
    {
        private static readonly string SkinsFolderName = "skins";
        private static readonly string ThemeFileName = "theme.json";
        private static readonly string SkinsConfigFileName = "skins.json";

        private readonly string _skinsPath;
        private readonly string _skinsConfigPath;

        public ThemeLoader()
        {
            string appPath = AppDomain.CurrentDomain.BaseDirectory;
            _skinsPath = Path.Combine(appPath, "skins");
            _skinsConfigPath = Path.Combine(appPath, "skins.json");
            
            EnsureDirectoriesExist();
        }

        private void EnsureDirectoriesExist()
        {
            if (!Directory.Exists(_skinsPath))
            {
                Directory.CreateDirectory(_skinsPath);
            }
        }

        public List<SkinTheme> LoadAllThemes()
        {
            List<SkinTheme> themes = new List<SkinTheme>();

            themes.Add(GetDefaultTheme());

            try
            {
                if (Directory.Exists(_skinsPath))
                {
                    foreach (var themeDir in Directory.GetDirectories(_skinsPath))
                    {
                        string themeFile = Path.Combine(themeDir, ThemeFileName);
                        if (File.Exists(themeFile))
                        {
                            try
                            {
                                string json = File.ReadAllText(themeFile);
                                var theme = JsonSerializer.Deserialize<SkinTheme>(json, new JsonSerializerOptions
                                {
                                    PropertyNameCaseInsensitive = true
                                });
                                
                                if (theme != null && !string.IsNullOrEmpty(theme.Id) && theme.Id != "default")
                                {
                                    themes.Add(theme);
                                }
                            }
                            catch (Exception ex)
                            {
                                Console.WriteLine($"加载主题文件失败: {themeFile}, 错误: {ex.Message}");
                            }
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"扫描主题目录失败: {ex.Message}");
            }

            return themes;
        }

        public SkinTheme? LoadTheme(string themeId)
        {
            if (themeId == "default")
            {
                return GetDefaultTheme();
            }

            try
            {
                string themeDir = Path.Combine(_skinsPath, themeId);
                string themeFile = Path.Combine(themeDir, ThemeFileName);
                
                if (File.Exists(themeFile))
                {
                    string json = File.ReadAllText(themeFile);
                    return JsonSerializer.Deserialize<SkinTheme>(json, new JsonSerializerOptions
                    {
                        PropertyNameCaseInsensitive = true
                    });
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"加载主题失败: {themeId}, 错误: {ex.Message}");
            }

            return null;
        }

        public void SaveTheme(SkinTheme theme)
        {
            try
            {
                string themeDir = Path.Combine(_skinsPath, theme.Id);
                if (!Directory.Exists(themeDir))
                {
                    Directory.CreateDirectory(themeDir);
                }

                string themeFile = Path.Combine(themeDir, ThemeFileName);
                var options = new JsonSerializerOptions
                {
                    WriteIndented = true,
                    PropertyNamingPolicy = JsonNamingPolicy.CamelCase
                };
                
                string json = JsonSerializer.Serialize(theme, options);
                File.WriteAllText(themeFile, json);
            }
            catch (Exception ex)
            {
                Console.WriteLine($"保存主题失败: {theme.Id}, 错误: {ex.Message}");
            }
        }

        public void DeleteTheme(string themeId)
        {
            if (themeId == "default")
            {
                return;
            }

            try
            {
                string themeDir = Path.Combine(_skinsPath, themeId);
                if (Directory.Exists(themeDir))
                {
                    Directory.Delete(themeDir, true);
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"删除主题失败: {themeId}, 错误: {ex.Message}");
            }
        }

        public string GetSkinsPath()
        {
            return _skinsPath;
        }

        public SkinTheme GetDefaultTheme()
        {
            return new SkinTheme
            {
                Id = "default",
                Name = "默认玻璃拟态",
                Author = "Developer",
                Version = "1.0",
                Description = "默认的玻璃拟态风格主题",
                Styles = new ThemeStyles
                {
                    Window = new WindowStyle
                    {
                        Background = new BackgroundStyle
                        {
                            Type = "gradient",
                            Colors = new List<string> { "#6a85b6", "#bac8e0", "#f0c9e8" },
                            Angle = 135
                        }
                    },
                    Card = new CardStyle
                    {
                        Background = "#15FFFFFF",
                        BorderColor = "#20FFFFFF",
                        ContentPanelBackground = "#0DFFFFFF",
                        CornerRadius = 16,
                        Shadow = new ShadowStyle
                        {
                            BlurRadius = 40,
                            ShadowDepth = 12,
                            Opacity = 0.15,
                            Color = "#000000"
                        }
                    },
                    Button = new ButtonStyle
                    {
                        Background = "#25FFFFFF",
                        HoverBackground = "#40FFFFFF",
                        PressedBackground = "#40FFFFFF",
                        BorderColor = "#20FFFFFF",
                        CornerRadius = 16,
                        Foreground = "#FFFFFFFF",
                        Shadow = new ShadowStyle
                        {
                            BlurRadius = 16,
                            ShadowDepth = 4,
                            Opacity = 0.1,
                            Color = "#000000"
                        }
                    },
                    Text = new TextStyle
                    {
                        Primary = "#FFFFFFFF",
                        Secondary = "#FF666666",
                        Title = "#FFFFFFFF",
                        Body = "#E6FFFFFF"
                    },
                    ListItem = new ListItemStyle
                    {
                        Background = "#1AFFFFFF",
                        HoverBackground = "#33FFFFFF",
                        SelectedBackground = "#33FFFFFF",
                        BorderColor = "#33FFFFFF",
                        CornerRadius = 12
                    },
                    Tab = new TabStyle
                    {
                        Background = "transparent",
                        SelectedBackground = "#40FFFFFF",
                        HoverBackground = "#25FFFFFF",
                        BorderColor = "#20FFFFFF",
                        SelectedForeground = "#FFFFFFFF",
                        CornerRadius = 8
                    },
                    TextBox = new TextBoxStyle
                    {
                        Background = "#20FFFFFF",
                        BorderColor = "#4DFFFFFF",
                        Foreground = "#FFFFFFFF",
                        CornerRadius = 8
                    },
                    ScrollBar = new ScrollBarStyle
                    {
                        Background = "Transparent",
                        ThumbColor = "#4DFFFFFF",
                        Width = 6,
                        CornerRadius = 3
                    }
                }
            };
        }

        public SkinTheme GetDarkTheme()
        {
            return new SkinTheme
            {
                Id = "dark",
                Name = "暗黑霓虹",
                Author = "Developer",
                Version = "1.0",
                Description = "深色背景配霓虹色调主题",
                Styles = new ThemeStyles
                {
                    Window = new WindowStyle
                    {
                        Background = new BackgroundStyle
                        {
                            Type = "video",
                            VideoPath = "dark-background.mp4",
                            Volume = 0
                        }
                    },
                    Card = new CardStyle
                    {
                        Background = "#8CFFFFFF",
                        BorderColor = "#8CFFFFFF",
                        ContentPanelBackground = "#8CFFFFFF",
                        CornerRadius = 16,
                        Shadow = new ShadowStyle
                        {
                            BlurRadius = 30,
                            ShadowDepth = 8,
                            Opacity = 0.8,
                            Color = "#6DD5FA"
                        }
                    },
                    Button = new ButtonStyle
                    {
                        Background = "#30FFFFFF",
                        HoverBackground = "#50FFFFFF",
                        PressedBackground = "#60FFFFFF",
                        BorderColor = "#40FFFFFF",
                        CornerRadius = 16,
                        Foreground = "#E6000000",
                        Shadow = new ShadowStyle
                        {
                            BlurRadius = 20,
                            ShadowDepth = 4,
                            Opacity = 0.2,
                            Color = "#667EEA"
                        }
                    },
                    Text = new TextStyle
                    {
                        Primary = "#E6000000",
                        Secondary = "#B0000000",
                        Title = "#E6000000",
                        Body = "#E0000000",
                        FontFamily = "Source Han Sans SC",
                        FontWeight = "Bold"
                    },
                    ListItem = new ListItemStyle
                    {
                        Background = "#25FFFFFF",
                        HoverBackground = "#40FFFFFF",
                        SelectedBackground = "#50FFFFFF",
                        BorderColor = "#40FFFFFF",
                        CornerRadius = 12,
                        Foreground = "#E6000000"
                    },
                    Tab = new TabStyle
                    {
                        Background = "transparent",
                        SelectedBackground = "#50FFFFFF",
                        HoverBackground = "#30FFFFFF",
                        BorderColor = "#40FFFFFF",
                        SelectedForeground = "#E6000000",
                        CornerRadius = 8
                    },
                    TextBox = new TextBoxStyle
                    {
                        Background = "#25FFFFFF",
                        BorderColor = "#50FFFFFF",
                        Foreground = "#E6000000",
                        CornerRadius = 8
                    },
                    ScrollBar = new ScrollBarStyle
                    {
                        Background = "Transparent",
                        ThumbColor = "#667EEA",
                        Width = 6,
                        CornerRadius = 3
                    }
                }
            };
        }

        public void EnsureDefaultThemesExist()
        {
            SaveTheme(GetDarkTheme());
        }
    }
}
