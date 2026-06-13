using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using FS服装搭配专家.Core.Models;

namespace FS服装搭配专家.Core.Services
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
            themes.Add(GetDarkTheme());
            themes.Add(GetGalaxyTheme());

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
                                
                                if (theme != null && !string.IsNullOrEmpty(theme.Id) && theme.Id != "default" && theme.Id != "dark" && theme.Id != "galaxy")
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
            if (themeId == "dark")
                return GetDarkTheme();
            if (themeId == "galaxy")
                return GetGalaxyTheme();

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
                Version = "2.0",
                Description = "浅冷紫渐变，悬浮卡片设计",
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
                        Background = "#B0FFFFFF",           // 半透明白（面板底色，浅紫上可见）
                        BorderColor = "#D1D7E8",            // 极浅灰边框（贴近面板底色）
                        ContentPanelBackground = "#90FFFFFF", // Tab 头等次级区域
                        LogBackgroundColor = "#A0FFFFFF",   // 日志区
                        CornerRadius = 12,
                        Shadow = new ShadowStyle
                        {
                            BlurRadius = 20,
                            ShadowDepth = 4,
                            Opacity = 0.1,
                            Color = "#6a85b6"
                        }
                    },
                    Button = new ButtonStyle
                    {
                        Background = "#C0FFFFFF",           // 淡白紫底
                        HoverBackground = "#D0FFFFFF",      // hover 更亮
                        PressedBackground = "#A0FFFFFF",    // pressed 更暗
                        BorderColor = "#D1D7E8",            // 极浅灰边框
                        CornerRadius = 8,
                        Foreground = "#4A536B",             // 二级正文色（按钮文字）
                        Shadow = new ShadowStyle
                        {
                            BlurRadius = 8,
                            ShadowDepth = 2,
                            Opacity = 0.08,
                            Color = "#6a85b6"
                        }
                    },
                    Text = new TextStyle
                    {
                        Primary = "#4A536B",               // 二级正文：中性灰（全界面主体）
                        Secondary = "#8892AB",              // 三级辅助：浅灰蓝（特效后缀、空字、勾选框）
                        Title = "#363E55",                  // 一级标题：深灰蓝（窗口标题、顶部按钮）
                        Body = "#8892AB",                   // 三级辅助：同 Secondary
                        AccentColor = "#D65565"             // 提示高亮：低饱和浅红（仅异常提示）
                    },
                    ListItem = new ListItemStyle
                    {
                        Background = "#10FFFFFF",           // 列表项：极淡白
                        HoverBackground = "#30FFFFFF",      // hover
                        SelectedBackground = "#8999BC",     // 选中边框：中度蓝灰
                        BorderColor = "#D1D7E8",
                        CornerRadius = 8,
                        Foreground = "#4A536B"              // 二级正文色
                    },
                    Tab = new TabStyle
                    {
                        Background = "transparent",
                        SelectedBackground = "#50FFFFFF",   // 选中 Tab
                        HoverBackground = "#30FFFFFF",
                        BorderColor = "#8892AB",
                        SelectedForeground = "#363E55",     // 一级标题色
                        CornerRadius = 8
                    },
                    TextBox = new TextBoxStyle
                    {
                        Background = "#D0FFFFFF",           // 输入框：更亮的白
                        BorderColor = "#D1D7E8",
                        Foreground = "#4A536B",             // 二级正文色
                        CornerRadius = 8
                    },
                    ScrollBar = new ScrollBarStyle
                    {
                        Background = "Transparent",
                        ThumbColor = "#996a85b6",           // 半透明紫
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
                Version = "2.0",
                Description = "优化对比度的深色主题",
                Styles = new ThemeStyles
                {
                    Window = new WindowStyle
                    {
                        Background = new BackgroundStyle
                        {
                            Type = "gradient",
                            Colors = new List<string> { "#111111", "#181828", "#0F0F1E" },
                            Angle = 135
                        }
                    },
                    Card = new CardStyle
                    {
                        Background = "#222222",          // 左右面板：深灰分层（vs 主背景 #111）
                        BorderColor = "#555555",          // 浅灰描边（替代亮蓝）
                        ContentPanelBackground = "#1A1A1A", // Tab 头/次级区域
                        LogBackgroundColor = "#0F0F0F",
                        CornerRadius = 6,
                        Shadow = new ShadowStyle { BlurRadius = 0, ShadowDepth = 0, Opacity = 0, Color = "#000000" }
                    },
                    Button = new ButtonStyle
                    {
                        Background = "#3A3A3A",           // 深灰底（替代 #333，更明显）
                        HoverBackground = "#505050",      // hover 提亮
                        PressedBackground = "#2A2A2A",
                        BorderColor = "#555555",
                        CornerRadius = 4,
                        Foreground = "#FFFFFF",           // 白色文字（替代灰底黑字）
                        Shadow = new ShadowStyle { BlurRadius = 0, ShadowDepth = 0, Opacity = 0, Color = "#000000" }
                    },
                    Text = new TextStyle
                    {
                        Primary = "#E8E8E8",              // 主文字：微提亮
                        Secondary = "#B0B0B0",            // 次要文字：从 #AAA 提亮到 #B0B0
                        Title = "#F0F0F0",                // 标题：更亮
                        Body = "#999999",                 // 正文：从 #8080 提亮到 #999
                        AccentColor = "#7EC8E3"           // 特效编号：浅青色（替代 #6DD5FA 蓝色）
                    },
                    ListItem = new ListItemStyle
                    {
                        Background = "Transparent",
                        HoverBackground = "#2E2E2E",      // 列表 hover：深灰（vs 面板 #222）
                        SelectedBackground = "#2A3A5A",   // 选中：柔和蓝灰（替代 #2b4266 亮蓝）
                        BorderColor = "#666666",
                        CornerRadius = 3,
                        Foreground = "#E8E8E8"
                    },
                    Tab = new TabStyle
                    {
                        Background = "Transparent",
                        SelectedBackground = "#222222",
                        HoverBackground = "#2E2E2E",
                        BorderColor = "#888888",
                        SelectedForeground = "#E8E8E8",
                        CornerRadius = 4
                    },
                    TextBox = new TextBoxStyle
                    {
                        Background = "#1E1E1E",           // 输入框：比面板深一点
                        BorderColor = "#555555",
                        Foreground = "#E0E0E0",
                        CornerRadius = 4
                    },
                    ScrollBar = new ScrollBarStyle
                    {
                        Background = "Transparent",
                        ThumbColor = "#555555",           // 滚动条：浅灰（替代 #666）
                        Width = 6,
                        CornerRadius = 3
                    }
                }
            };
        }

        public SkinTheme GetGalaxyTheme()
        {
            return new SkinTheme
            {
                Id = "galaxy",
                Name = "银河星空",
                Author = "Developer",
                Version = "2.0",
                Description = "银河星空主题，优化对比度",
                Styles = new ThemeStyles
                {
                    Window = new WindowStyle
                    {
                        Background = new BackgroundStyle
                        {
                            Type = "gradient",
                            Colors = new List<string> { "#0A0A1A", "#12122E", "#080820" },
                            Angle = 135
                        }
                    },
                    Card = new CardStyle
                    {
                        Background = "#1A1A3E",
                        BorderColor = "#4A4A7A",          // 提亮边框
                        ContentPanelBackground = "#10102A",
                        LogBackgroundColor = "#08081A",
                        CornerRadius = 8,
                        Shadow = new ShadowStyle { BlurRadius = 20, ShadowDepth = 4, Opacity = 0.3, Color = "#6DD5FA" }
                    },
                    Button = new ButtonStyle
                    {
                        Background = "#2A2A5E",
                        HoverBackground = "#3D3D7A",
                        PressedBackground = "#1A1A4E",
                        BorderColor = "#4A4A7A",
                        CornerRadius = 6,
                        Foreground = "#D0DDE8",           // 提亮按钮文字
                        Shadow = new ShadowStyle { BlurRadius = 10, ShadowDepth = 2, Opacity = 0.2, Color = "#6DD5FA" }
                    },
                    Text = new TextStyle
                    {
                        Primary = "#D0DDE8",              // 提亮主文字
                        Secondary = "#90A0B0",            // 提亮次要文字
                        Title = "#FFFFFF",
                        Body = "#708090",                 // 提亮正文
                        AccentColor = "#7EC8E3"           // 浅青色（与暗黑主题一致）
                    },
                    ListItem = new ListItemStyle
                    {
                        Background = "Transparent",
                        HoverBackground = "#2A2A5E",
                        SelectedBackground = "#3A3A8A",   // 提亮选中色
                        BorderColor = "#90A0B0",
                        CornerRadius = 4,
                        Foreground = "#D0DDE8"
                    },
                    Tab = new TabStyle
                    {
                        Background = "Transparent",
                        SelectedBackground = "#1A1A3E",
                        HoverBackground = "#2A2A5E",
                        BorderColor = "#90A0B0",
                        SelectedForeground = "#D0DDE8",
                        CornerRadius = 4
                    },
                    TextBox = new TextBoxStyle
                    {
                        Background = "#14142E",
                        BorderColor = "#4A4A7A",
                        Foreground = "#D0DDE8",
                        CornerRadius = 4
                    },
                    ScrollBar = new ScrollBarStyle
                    {
                        Background = "Transparent",
                        ThumbColor = "#4A4A7A",
                        Width = 6,
                        CornerRadius = 3
                    }
                }
            };
        }

        public void EnsureDefaultThemesExist()
        {
            SaveTheme(GetDarkTheme());
            SaveTheme(GetGalaxyTheme());
        }
    }
}
