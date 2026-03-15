using System;
using System.Collections.Generic;
using System.Windows;
using System.Windows.Media;
using System.Windows.Media.Animation;
using System.IO;
using System.Linq;
using System.Diagnostics;
using System.ComponentModel;
using System.Text;
using System.Windows.Controls;
using System.Windows.Input;
using System.Runtime.InteropServices;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Win32;
using FS服装搭配专家v1._0.UI.Windows;
using FS服装搭配专家v1._0.Core.Services;
using FS服装搭配专家v1._0.Core.Models;
using FS服装搭配专家v1._0.Core.Config;

namespace FS服装搭配专家v1._0
{
    public partial class MainWindow : Window
    {
        private int currentSkinIndex = 0;
        private readonly SolidColorBrush[] skinColors = new[]
        {
            new SolidColorBrush(Color.FromRgb(109, 195, 255)), // 蓝色
            new SolidColorBrush(Color.FromRgb(232, 192, 243)), // 粉色
            new SolidColorBrush(Color.FromRgb(173, 216, 230)), // 浅蓝色
            new SolidColorBrush(Color.FromRgb(255, 182, 193)), // 浅红色
        };

        // 皮肤管理器
        private SkinManager skinManager;

        // 核心变量
        private List<FS服装搭配专家v1._0.ItemshopM> list = new List<FS服装搭配专家v1._0.ItemshopM>();
        private string cookiename = AppConfig.Directories.Cookies;
        private string oftenitemcode = AppConfig.Files.OftenItemCode;
        private string strInstallDirectory = "";
        private string pakIconNum = "";
        private string pngItemCode = "";
        private string pakItemNum = "";
        private string bmlItemCode = "";
        private string numEffectCode = "";
        private string strItemName = "";
        private string strBeforeEffCode = "";
        private string strAfterEffCode = "";
        private bool thisIsbefore = false;
        private string thisOtherIconPng = "";
        private string thisOtherPropName = "";
        private bool iseffok = false;

        // 变更前和变更后的服装列表
        private List<ItemshopM> beforeItems = new List<ItemshopM>();
        private List<ItemshopM> afterItems = new List<ItemshopM>();
        
        // 特效列表
        private List<ItemshopM> effectList = new List<ItemshopM>();
        private ItemshopM selectedEffect = null;

        // 后台工作线程
        private BackgroundWorker bwMain;
        private BackgroundWorker bwLoadImg;
        private BackgroundWorker bwLast;
        
        // 搜索优化
        private System.Windows.Threading.DispatcherTimer? _searchDebounceTimer;
        private CancellationTokenSource? _searchCts;
        private readonly object _searchLock = new object();

        // 性能监控
        private Stopwatch perfStopwatch = new Stopwatch();
        private Dictionary<string, long> perfCounters = new Dictionary<string, long>();
        
        // 加载动画
        private Storyboard _bounceStoryboard;
        private bool _isAnimationPlaying = false;

        public MainWindow()
        {
            try
            {
                Console.WriteLine("=== 主窗口初始化开始 ===");
                
                // 记录初始化前的状态
                Console.WriteLine("开始InitializeComponent()...");
                InitializeComponent();
                Console.WriteLine("InitializeComponent()完成");
                
                // 从配置文件加载窗口尺寸
                LoadWindowSize();
                
                // 注册窗口尺寸变化事件
                this.SizeChanged += MainWindow_SizeChanged;
                
                // 初始化控制台开关状态
                UpdateConsoleToggleState();
                
                // 强制设置窗口属性
                Console.WriteLine("设置窗口属性...");
                this.Width = 1440;
                this.Height = 768;
                this.WindowStartupLocation = WindowStartupLocation.CenterScreen;
                this.WindowState = WindowState.Normal;
                this.Visibility = Visibility.Visible;
                
                // 记录设置后的状态
                Console.WriteLine($"窗口宽度: {this.Width}");
                Console.WriteLine($"窗口高度: {this.Height}");
                Console.WriteLine($"窗口启动位置: {this.WindowStartupLocation}");
                Console.WriteLine($"窗口状态: {this.WindowState}");
                Console.WriteLine($"窗口可见性: {this.Visibility}");
                
                // 确保窗口激活和焦点
                Console.WriteLine("激活窗口并获取焦点...");
                this.Activate();
                this.Focus();
                
                // 显示初始化提示
                this.Dispatcher.Invoke(() =>
                {
                    labErrorMsg.Text = "欢迎使用 FreeStyle 服装搭配专家\n请按照以下步骤操作:\n1. 点击'加载图片'按钮获取服装图标\n2. 在服装列表中选择要预览的服装\n3. 设置当前装备和目标装备\n4. 点击'更新搭配'完成操作"; 
                    labErrorMsg.Visibility = Visibility.Visible;
                });
                
                // 初始化皮肤管理器
                Console.WriteLine("初始化皮肤管理器...");
                skinManager = new SkinManager();
                Console.WriteLine("皮肤管理器初始化完成");
                
                // 应用保存的主题
                ApplyCurrentTheme();
                
                // 初始化服装列表数据
                Console.WriteLine("初始化服装列表数据...");
                InitializeItemList();
                Console.WriteLine("服装列表数据初始化完成");
                
                // 再次确认窗口状态
                Console.WriteLine($"最终窗口状态: {this.WindowState}");
                Console.WriteLine($"最终窗口可见性: {this.Visibility}");
                Console.WriteLine($"最终窗口大小: {this.Width}, {this.Height}");
                Console.WriteLine("=== 主窗口初始化完成 ===");
                
                // 写入日志文件
                string logFilePath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "mainwindow.log");
                using (StreamWriter writer = new StreamWriter(logFilePath))
                {
                    writer.WriteLine($"=== 主窗口初始化日志 ===");
                    writer.WriteLine($"初始化时间: {DateTime.Now}");
                    writer.WriteLine($"窗口宽度: {this.Width}");
                    writer.WriteLine($"窗口高度: {this.Height}");
                    writer.WriteLine($"窗口状态: {this.WindowState}");
                    writer.WriteLine($"窗口可见性: {this.Visibility}");
                    writer.WriteLine("=== 初始化完成 ===");
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"主窗口初始化出错: {ex.Message}");
                Console.WriteLine($"堆栈跟踪: {ex.StackTrace}");
                
                // 写入错误日志
                string logFilePath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "mainwindow.log");
                using (StreamWriter writer = new StreamWriter(logFilePath, true))
                {
                    writer.WriteLine($"初始化出错: {ex.Message}");
                    writer.WriteLine($"堆栈跟踪: {ex.StackTrace}");
                    writer.WriteLine("=== 初始化失败 ===");
                }
                
                // 显示错误消息
                this.Dispatcher.Invoke(() =>
                {
                    MessageBox.Show($"主窗口初始化失败: {ex.Message}", "初始化错误", MessageBoxButton.OK, MessageBoxImage.Error);
                });
            }
        }

        private void Minimize_Click(object sender, RoutedEventArgs e)
        {
            this.WindowState = WindowState.Minimized;
        }

        private void Maximize_Click(object sender, RoutedEventArgs e)
        {
            if (this.WindowState == WindowState.Normal)
            {
                this.WindowState = WindowState.Maximized;
            }
            else
            {
                this.WindowState = WindowState.Normal;
            }
        }

        private void Close_Click(object sender, RoutedEventArgs e)
        {
            this.Close();
        }

        private void TitleBar_MouseLeftButtonDown(object sender, System.Windows.Input.MouseButtonEventArgs e)
        {
            // 开始拖动窗口
            if (this.WindowState == WindowState.Maximized)
            {
                // 如果窗口是最大化状态，先恢复到正常状态
                this.WindowState = WindowState.Normal;
                
                // 计算鼠标位置，使窗口在拖动时位置合理
                var point = e.GetPosition(this);
                this.Left = point.X;
                this.Top = point.Y;
            }
            
            this.DragMove();
        }

        private void ChangeSkin_Click(object sender, RoutedEventArgs e)
        {
            // 切换到下一个皮肤颜色
            currentSkinIndex = (currentSkinIndex + 1) % skinColors.Length;
            
            // 更新按钮颜色
            var button = sender as System.Windows.Controls.Button;
            if (button != null)
            {
                button.Background = skinColors[currentSkinIndex];
            }
            
            Console.WriteLine($"切换到皮肤 {currentSkinIndex + 1}");
        }
        
        private void StartLoadingAnimation()
        {
            if (_isAnimationPlaying) return;
            
            Dispatcher.Invoke(() =>
            {
                loadingAnimationGrid.Visibility = Visibility.Visible;
                _bounceStoryboard = loadingAnimationGrid.Resources["BounceAnimation"] as Storyboard;
                if (_bounceStoryboard != null)
                {
                    _isAnimationPlaying = true;
                    _bounceStoryboard.Begin();
                }
            });
        }
        
        private void StopLoadingAnimation()
        {
            Dispatcher.Invoke(() =>
            {
                if (_bounceStoryboard != null && _isAnimationPlaying)
                {
                    _bounceStoryboard.Stop();
                    _isAnimationPlaying = false;
                }
                loadingAnimationGrid.Visibility = Visibility.Collapsed;
            });
        }
        
        private void ConsoleToggle_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
        {
            Program.ToggleConsole();
            UpdateConsoleToggleState();
        }
        
        private void UpdateConsoleToggleState()
        {
            bool isOn = App.ConsoleVisible;
            var grid = ConsoleToggleGrid;
            var onStoryboard = grid.Resources["ToggleOnStoryboard"] as Storyboard;
            var offStoryboard = grid.Resources["ToggleOffStoryboard"] as Storyboard;
            
            if (isOn && onStoryboard != null)
            {
                onStoryboard.Begin();
            }
            else if (!isOn && offStoryboard != null)
            {
                offStoryboard.Begin();
            }
        }
        
        private void btnSkin_Click(object sender, RoutedEventArgs e)
        {
            Console.WriteLine("换肤按钮点击");
            
            var skinWindow = new SkinWindow(skinManager);
            skinWindow.Owner = this;
            skinWindow.ThemeApplied += OnThemeApplied;
            skinWindow.ShowDialog();
        }

        private void OnThemeApplied(object? sender, SkinTheme theme)
        {
            ApplyCurrentTheme();
        }

        private void ApplyCurrentTheme()
        {
            if (skinManager?.CurrentTheme != null)
            {
                var applier = new ThemeApplier();
                applier.ApplyThemeToWindow(this, skinManager.CurrentTheme);
                applier.ApplyThemeToUserControl(mapControl, skinManager.CurrentTheme);
                
                ApplyVideoBackground(skinManager.CurrentTheme);
                
                Console.WriteLine($"已应用主题: {skinManager.CurrentTheme.Name}");
            }
        }

        private void ApplyVideoBackground(SkinTheme theme)
        {
            var applier = new ThemeApplier();
            var bgStyle = theme.Styles.Window.Background;
            
            if (applier.IsVideoBackground(bgStyle))
            {
                string? videoPath = applier.GetVideoPath(bgStyle);
                if (!string.IsNullOrEmpty(videoPath) && File.Exists(videoPath))
                {
                    VideoBackground.Source = new Uri(videoPath);
                    VideoBackground.Visibility = Visibility.Visible;
                    VideoBackground.Volume = bgStyle.Volume;
                    VideoBackground.Play();
                    Console.WriteLine($"播放视频背景: {videoPath}");
                }
                else
                {
                    Console.WriteLine($"视频文件不存在: {videoPath}");
                    VideoBackground.Visibility = Visibility.Collapsed;
                }
            }
            else
            {
                VideoBackground.Stop();
                VideoBackground.Visibility = Visibility.Collapsed;
            }
        }

        private void VideoBackground_MediaEnded(object sender, RoutedEventArgs e)
        {
            VideoBackground.Position = TimeSpan.Zero;
            VideoBackground.Play();
        }

        private void btnBgCrop_Click(object sender, System.Windows.Input.MouseButtonEventArgs e)
        {
            var window = new BgCropWindow(strInstallDirectory);
            window.Owner = this;
            window.ShowDialog();
        }

        private void btnFillBytes_Click(object sender, System.Windows.Input.MouseButtonEventArgs e)
        {
            var window = new FillBytesWindow(strInstallDirectory);
            window.Owner = this;
            window.ShowDialog();
        }
        
        private void ApplySkin(SolidColorBrush skinColor)
        {
            // 简单的皮肤应用方法
            Console.WriteLine("应用皮肤颜色");
        }
        
        private void ApplySkinToVisualTree(DependencyObject parent, SolidColorBrush skinColor)
        {
            // 简单的皮肤应用到视觉树方法
            Console.WriteLine("应用皮肤到视觉树");
        }
        
        private Color GetContrastColor(Color color)
        {
            // 简单的对比度颜色计算方法
            return Colors.White;
        }
        
        // 搜索按钮点击事件
        private void btnSearch_Click(object sender, RoutedEventArgs e)
        {
            // 简化版搜索功能
            try
            {
                // 获取搜索文本
                string searchText = "";
                this.Dispatcher.Invoke(() =>
                {
                    // 显示搜索状态
                    labErrorMsg.Visibility = Visibility.Collapsed;
                    labErrorMsg.Text = "";
                    searchText = txtSearch.Text.Trim();
                });
                
                // 显示搜索结果
                this.Dispatcher.Invoke(() =>
                {
                    labErrorMsg.Text = string.Format("搜索功能已简化，当前搜索文本: {0}", searchText);
                    labErrorMsg.Visibility = Visibility.Visible;
                });
            }
            catch (Exception ex)
            {
                Console.WriteLine("搜索失败: " + ex.Message);
                this.Dispatcher.Invoke(() =>
                {
                    labErrorMsg.Text = "搜索失败: " + ex.Message;
                    labErrorMsg.Visibility = Visibility.Visible;
                });
            }
        }

        private void txtSearch_TextChanged(object sender, TextChangedEventArgs e)
        {
            if (_searchDebounceTimer == null)
            {
                _searchDebounceTimer = new System.Windows.Threading.DispatcherTimer();
                _searchDebounceTimer.Interval = TimeSpan.FromMilliseconds(200);
                _searchDebounceTimer.Tick += async (s, args) =>
                {
                    _searchDebounceTimer.Stop();
                    await SearchAsync();
                };
            }
            
            _searchDebounceTimer.Stop();
            _searchDebounceTimer.Start();
        }

        private async Task SearchAsync()
        {
            lock (_searchLock)
            {
                _searchCts?.Cancel();
                _searchCts = new CancellationTokenSource();
            }
            
            var token = _searchCts.Token;
            
            try
            {
                string searchText = "";
                await this.Dispatcher.InvokeAsync(() =>
                {
                    labErrorMsg.Visibility = Visibility.Collapsed;
                    labErrorMsg.Text = "";
                    searchText = txtSearch.Text.Trim();
                });
                
                if (this.list == null || this.list.Count == 0)
                {
                    return;
                }
                
                if (string.IsNullOrEmpty(searchText))
                {
                    await this.Dispatcher.InvokeAsync(() =>
                    {
                        lstClothing.ItemsSource = this.list;
                        lstEffect.ItemsSource = this.effectList;
                    });
                    return;
                }
                
                var filteredClothingList = await Task.Run(() =>
                {
                    return this.list.Where(item =>
                        (item.ItemCode != null && item.ItemCode.IndexOf(searchText, StringComparison.OrdinalIgnoreCase) >= 0) ||
                        (item.PakNum != null && item.PakNum.IndexOf(searchText, StringComparison.OrdinalIgnoreCase) >= 0) ||
                        (item.EffectCode != null && item.EffectCode.IndexOf(searchText, StringComparison.OrdinalIgnoreCase) >= 0) ||
                        (item.ItemName != null && item.ItemName.IndexOf(searchText, StringComparison.OrdinalIgnoreCase) >= 0) ||
                        (item.Comment != null && item.Comment.IndexOf(searchText, StringComparison.OrdinalIgnoreCase) >= 0) ||
                        (item.ItemType != null && item.ItemType.IndexOf(searchText, StringComparison.OrdinalIgnoreCase) >= 0)
                    ).ToList();
                }, token);
                
                var filteredEffectList = await Task.Run(() =>
                {
                    return this.effectList.Where(item =>
                        (item.ItemCode != null && item.ItemCode.IndexOf(searchText, StringComparison.OrdinalIgnoreCase) >= 0) ||
                        (item.EffectCode != null && item.EffectCode.IndexOf(searchText, StringComparison.OrdinalIgnoreCase) >= 0) ||
                        (item.ItemName != null && item.ItemName.IndexOf(searchText, StringComparison.OrdinalIgnoreCase) >= 0)
                    ).ToList();
                }, token);
                
                if (token.IsCancellationRequested)
                {
                    return;
                }
                
                await this.Dispatcher.InvokeAsync(() =>
                {
                    lstClothing.ItemsSource = filteredClothingList;
                    lstEffect.ItemsSource = filteredEffectList;
                    labErrorMsg.Text = string.Format("找到服装 {0} 个，特效 {1} 个", filteredClothingList.Count, filteredEffectList.Count);
                    labErrorMsg.Visibility = Visibility.Visible;
                });
            }
            catch (OperationCanceledException)
            {
            }
            catch (Exception ex)
            {
                Console.WriteLine("搜索失败: " + ex.Message);
                await this.Dispatcher.InvokeAsync(() =>
                {
                    labErrorMsg.Text = "搜索失败: " + ex.Message;
                    labErrorMsg.Visibility = Visibility.Visible;
                });
            }
        }

        private void Search()
        {
            _ = SearchAsync();
        }

        private void lstClothing_Loaded(object sender, RoutedEventArgs e)
        {
            // 确保ListBox加载完成后滚动到顶部
            ScrollListBoxToTop();
        }
        
        private void ScrollListBoxToTop()
        {
            if (lstClothing.Items.Count > 0)
            {
                this.Dispatcher.BeginInvoke(new Action(() =>
                {
                    lstClothing.ScrollIntoView(lstClothing.Items[0]);
                    var scrollViewer = GetScrollViewer(lstClothing);
                    if (scrollViewer != null)
                    {
                        scrollViewer.UpdateLayout();
                        scrollViewer.ScrollToVerticalOffset(0);
                    }
                }), System.Windows.Threading.DispatcherPriority.Render);
            }
        }

        private void lstClothing_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            try
            {
                if (lstClothing.SelectedItem == null) return;
                
                ItemshopM selectedItem = lstClothing.SelectedItem as ItemshopM;
                if (selectedItem == null) return;
                
                if (Keyboard.Modifiers == ModifierKeys.Control)
                {
                    AddToAfterList(selectedItem);
                }
                else if (Keyboard.Modifiers == ModifierKeys.Alt)
                {
                    // Alt+左键：选中变更后服装（用于特效添加）
                    SelectAfterItemForEffect(selectedItem);
                }
                else
                {
                    AddToBeforeList(selectedItem);
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine("选择服装失败: " + ex.Message);
                labErrorMsg.Text = "选择服装失败: " + ex.Message;
                labErrorMsg.Visibility = Visibility.Visible;
            }
        }
        
        private void lstEffect_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            try
            {
                if (lstEffect.SelectedItem == null) return;
                
                ItemshopM selectedEffectItem = lstEffect.SelectedItem as ItemshopM;
                if (selectedEffectItem == null) return;
                
                selectedEffect = selectedEffectItem;
                
                // 提取特效代码
                string effectCode = selectedEffectItem.EffectCode;
                if (effectCode.StartsWith("特效代码:"))
                {
                    effectCode = effectCode.Replace("特效代码:", "");
                }
                
                Console.WriteLine($"选中特效: {selectedEffectItem.ItemName}, 特效代码: {effectCode}");
                labErrorMsg.Text = $"已选中特效: {selectedEffectItem.ItemName} (代码: {effectCode})";
                labErrorMsg.Visibility = Visibility.Visible;
            }
            catch (Exception ex)
            {
                Console.WriteLine("选择特效失败: " + ex.Message);
                labErrorMsg.Text = "选择特效失败: " + ex.Message;
                labErrorMsg.Visibility = Visibility.Visible;
            }
        }
        
        private void SelectAfterItemForEffect(ItemshopM item)
        {
            // 检查是否已在变更后列表中
            var existingItem = afterItems.FirstOrDefault(x => x.ItemCode == item.ItemCode);
            if (existingItem == null)
            {
                // 如果不在变更后列表，先添加
                AddToAfterList(item);
                existingItem = afterItems.FirstOrDefault(x => x.ItemCode == item.ItemCode);
            }
            
            if (selectedEffect != null)
            {
                // 提取特效代码
                string effectCode = selectedEffect.EffectCode;
                if (effectCode.StartsWith("特效代码:"))
                {
                    effectCode = effectCode.Replace("特效代码:", "");
                }
                
                // 更新变更后服装的特效代码
                existingItem.EffectCode = "特效代码:" + effectCode;
                
                Console.WriteLine($"已将特效 {selectedEffect.ItemName} (代码: {effectCode}) 添加到服装 {item.ItemName}");
                labErrorMsg.Text = $"已将特效 [{selectedEffect.ItemName}] 添加到服装 [{item.ItemName}]";
                labErrorMsg.Visibility = Visibility.Visible;
                
                UpdateAfterPanel();
            }
            else
            {
                labErrorMsg.Text = "请先在特效列表中选择一个特效";
                labErrorMsg.Visibility = Visibility.Visible;
            }
        }

        private void AddToBeforeList(ItemshopM item)
        {
            if (beforeItems.Any(x => x.ItemCode == item.ItemCode))
            {
                labErrorMsg.Text = "该服装已在变更前列表中";
                labErrorMsg.Visibility = Visibility.Visible;
                return;
            }
            
            UnpackItemPak(item.PakNum);
            
            beforeItems.Add(item);
            UpdateBeforePanel();
            UpdatePairStatus();
            
            labErrorMsg.Text = string.Format("已添加 [{0}] 到变更前", item.ItemName);
            labErrorMsg.Visibility = Visibility.Visible;
        }

        private void AddToAfterList(ItemshopM item)
        {
            if (afterItems.Any(x => x.ItemCode == item.ItemCode))
            {
                labErrorMsg.Text = "该服装已在变更后列表中";
                labErrorMsg.Visibility = Visibility.Visible;
                return;
            }
            
            UnpackItemPak(item.PakNum);
            
            afterItems.Add(item);
            UpdateAfterPanel();
            UpdatePairStatus();
            
            labErrorMsg.Text = string.Format("已添加 [{0}] 到变更后", item.ItemName);
            labErrorMsg.Visibility = Visibility.Visible;
        }
        
        private void UnpackItemPak(string pakNum)
        {
            try
            {
                string pakName = "item" + pakNum.Replace("*", "");
                string itemDir = Path.Combine(Environment.CurrentDirectory, cookiename, pakName.Replace(".", "_"));
                
                if (Directory.Exists(itemDir) && Directory.GetFiles(itemDir, "*.bml").Length > 0)
                {
                    return;
                }
                
                string sourcePath = Path.Combine(strInstallDirectory, pakName);
                string destPath = Path.Combine(Environment.CurrentDirectory, cookiename, pakName);
                
                if (File.Exists(sourcePath) && !File.Exists(destPath))
                {
                    File.Copy(sourcePath, destPath, true);
                }
                
                if (File.Exists(destPath))
                {
                    string cmd = "pack\\resources \"" + destPath + "\" -all";
                    conmon.RunCmd(cmd);
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine("解包item pak失败: " + ex.Message);
            }
        }

        private void UpdateBeforePanel()
        {
            try
            {
                if (beforeWrapPanel == null) return;
                
                beforeWrapPanel.Children.Clear();
                
                foreach (var item in beforeItems)
                {
                    var border = new Border
                    {
                        Width = 70,
                        Height = 70,
                        Margin = new Thickness(5),
                        Background = new SolidColorBrush(Color.FromArgb(30, 255, 255, 255)),
                        BorderBrush = new SolidColorBrush(Color.FromArgb(80, 255, 255, 255)),
                        BorderThickness = new Thickness(1),
                        CornerRadius = new CornerRadius(8),
                        Cursor = Cursors.Hand,
                        Tag = item
                    };
                    
                    var grid = new Grid();
                    
                    var image = new Image
                    {
                        Width = 60,
                        Height = 60,
                        Stretch = Stretch.Uniform,
                        HorizontalAlignment = HorizontalAlignment.Center,
                        VerticalAlignment = VerticalAlignment.Center
                    };
                    
                    if (File.Exists(item.ImgPath))
                    {
                        try
                        {
                            var bitmap = new System.Windows.Media.Imaging.BitmapImage();
                            bitmap.BeginInit();
                            bitmap.UriSource = new Uri(item.ImgPath, UriKind.Absolute);
                            bitmap.CacheOption = System.Windows.Media.Imaging.BitmapCacheOption.OnLoad;
                            bitmap.EndInit();
                            image.Source = bitmap;
                        }
                        catch
                        {
                        }
                    }
                    
                    var tooltip = new ToolTip
                    {
                        Content = item.ItemName ?? item.ItemCode
                    };
                    ToolTipService.SetToolTip(border, tooltip);
                    
                    grid.Children.Add(image);
                    border.Child = grid;
                    
                    border.MouseLeftButtonDown += (s, e) =>
                    {
                        var borderItem = s as Border;
                        var itemData = borderItem?.Tag as ItemshopM;
                        if (itemData != null)
                        {
                            beforeItems.Remove(itemData);
                            UpdateBeforePanel();
                            UpdatePairStatus();
                        }
                    };
                    
                    beforeWrapPanel.Children.Add(border);
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine("更新变更前面板失败: " + ex.Message);
            }
        }

        private void UpdateAfterPanel()
        {
            try
            {
                if (afterWrapPanel == null) return;
                
                afterWrapPanel.Children.Clear();
                
                foreach (var item in afterItems)
                {
                    var border = new Border
                    {
                        Width = 70,
                        Height = 70,
                        Margin = new Thickness(5),
                        Background = new SolidColorBrush(Color.FromArgb(30, 255, 255, 255)),
                        BorderBrush = new SolidColorBrush(Color.FromArgb(80, 255, 255, 255)),
                        BorderThickness = new Thickness(1),
                        CornerRadius = new CornerRadius(8),
                        Cursor = Cursors.Hand,
                        Tag = item
                    };
                    
                    var grid = new Grid();
                    
                    var image = new Image
                    {
                        Width = 60,
                        Height = 60,
                        Stretch = Stretch.Uniform,
                        HorizontalAlignment = HorizontalAlignment.Center,
                        VerticalAlignment = VerticalAlignment.Center
                    };
                    
                    if (File.Exists(item.ImgPath))
                    {
                        try
                        {
                            var bitmap = new System.Windows.Media.Imaging.BitmapImage();
                            bitmap.BeginInit();
                            bitmap.UriSource = new Uri(item.ImgPath, UriKind.Absolute);
                            bitmap.CacheOption = System.Windows.Media.Imaging.BitmapCacheOption.OnLoad;
                            bitmap.EndInit();
                            image.Source = bitmap;
                        }
                        catch
                        {
                        }
                    }
                    
                    var tooltip = new ToolTip
                    {
                        Content = item.ItemName ?? item.ItemCode
                    };
                    ToolTipService.SetToolTip(border, tooltip);
                    
                    grid.Children.Add(image);
                    border.Child = grid;
                    
                    border.MouseLeftButtonDown += (s, e) =>
                    {
                        var borderItem = s as Border;
                        var itemData = borderItem?.Tag as ItemshopM;
                        if (itemData != null)
                        {
                            afterItems.Remove(itemData);
                            UpdateAfterPanel();
                            UpdatePairStatus();
                        }
                    };
                    
                    afterWrapPanel.Children.Add(border);
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine("更新变更后面板失败: " + ex.Message);
            }
        }

        private void UpdatePairStatus()
        {
            int pairCount = Math.Min(beforeItems.Count, afterItems.Count);
            txtPairStatus.Text = string.Format("已配对 {0} 件服装", pairCount);
        }

        private T FindVisualChild<T>(DependencyObject parent) where T : DependencyObject
        {
            for (int i = 0; i < System.Windows.Media.VisualTreeHelper.GetChildrenCount(parent); i++)
            {
                DependencyObject child = System.Windows.Media.VisualTreeHelper.GetChild(parent, i);
                if (child is T typedChild)
                {
                    return typedChild;
                }
                T result = FindVisualChild<T>(child);
                if (result != null)
                {
                    return result;
                }
            }
            return null;
        }

        private void btnConfirm_Click(object sender, RoutedEventArgs e)
        {
            try
            {
                if (beforeItems.Count == 0 || afterItems.Count == 0)
                {
                    labErrorMsg.Text = "请先添加变更前和变更后的服装";
                    labErrorMsg.Visibility = Visibility.Visible;
                    return;
                }
                
                if (beforeItems.Count != afterItems.Count)
                {
                    labErrorMsg.Text = string.Format("变更前({0})和变更后({1})数量不一致，请配对后再确认", beforeItems.Count, afterItems.Count);
                    labErrorMsg.Visibility = Visibility.Visible;
                    return;
                }
                
                string msg = string.Format("确认要将 {0} 件服装进行变更吗？\n\n注意：一定要先关闭游戏！", beforeItems.Count);
                var dialog = new ConfirmDialog(msg);
                
                // 定位在确认变更按钮下方
                var buttonPos = btnConfirm.PointToScreen(new Point(0, btnConfirm.ActualHeight));
                dialog.Left = buttonPos.X;
                dialog.Top = buttonPos.Y + 4;
                
                dialog.ShowDialog();
                
                if (!dialog.Result)
                {
                    return;
                }
                
                labErrorMsg.Text = "正在执行服装变更...";
                labErrorMsg.Visibility = Visibility.Visible;
                
                int successCount = 0;
                int failCount = 0;
                List<string> errorMessages = new List<string>();
                
                for (int i = 0; i < beforeItems.Count; i++)
                {
                    var beforeItem = beforeItems[i];
                    var afterItem = afterItems[i];
                    
                    try
                    {
                        ExecuteClothingChange(beforeItem, afterItem);
                        
                        string logEntry = string.Format("{0}#{1}#{2}\r\n",
                            beforeItem.ItemCode,
                            afterItem.ItemCode,
                            DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss"));
                        
                        File.AppendAllText(AppConfig.Files.DopakLog, logEntry, Encoding.Default);
                        
                        successCount++;
                    }
                    catch (Exception ex)
                    {
                        failCount++;
                        errorMessages.Add(string.Format("{0} -> {1}: {2}", beforeItem.ItemName, afterItem.ItemName, ex.Message));
                    }
                }
                
                string resultMsg = string.Format("变更完成！成功: {0}, 失败: {1}", successCount, failCount);
                if (errorMessages.Count > 0)
                {
                    resultMsg += "\n失败详情:\n" + string.Join("\n", errorMessages.Take(5));
                    if (errorMessages.Count > 5)
                    {
                        resultMsg += string.Format("\n...还有 {0} 个错误", errorMessages.Count - 5);
                    }
                }
                
                labErrorMsg.Text = resultMsg;
                labErrorMsg.Visibility = Visibility.Visible;
                
                beforeItems.Clear();
                afterItems.Clear();
                UpdateBeforePanel();
                UpdateAfterPanel();
                UpdatePairStatus();
            }
            catch (Exception ex)
            {
                labErrorMsg.Text = "确认变更失败: " + ex.Message;
                labErrorMsg.Visibility = Visibility.Visible;
            }
        }
        
        private void ExecuteClothingChange(ItemshopM beforeItem, ItemshopM afterItem)
        {
            Console.WriteLine("=== 开始执行服装变更 ===");
            
            string beforePakNum = beforeItem.PakNum.Replace("*", "").Replace(".pak", "");
            string afterPakNum = afterItem.PakNum.Replace("*", "").Replace(".pak", "");
            Console.WriteLine($"变更前PakNum: {beforePakNum}, 变更后PakNum: {afterPakNum}");
            
            string beforeModFile = string.Format("i{0}.bml", beforeItem.ItemCode);
            string afterModFile = string.Format("i{0}.bml", afterItem.ItemCode);
            Console.WriteLine($"变更前模型文件: {beforeModFile}, 变更后模型文件: {afterModFile}");
            
            string beforePakDir = Path.Combine(Environment.CurrentDirectory, cookiename, "item" + beforePakNum + "_pak");
            string afterPakDir = Path.Combine(Environment.CurrentDirectory, cookiename, "item" + afterPakNum + "_pak");
            Console.WriteLine($"变更前目录: {beforePakDir}");
            Console.WriteLine($"变更后目录: {afterPakDir}");
            
            string sourceModPath = Path.Combine(afterPakDir, afterModFile);
            string destModPath = Path.Combine(beforePakDir, beforeModFile);
            Console.WriteLine($"源模型路径: {sourceModPath}");
            Console.WriteLine($"目标模型路径: {destModPath}");
            
            Console.WriteLine($"检查源文件是否存在: {File.Exists(sourceModPath)}");
            if (File.Exists(sourceModPath))
            {
                Console.WriteLine("源文件存在，开始复制...");
                Directory.CreateDirectory(Path.GetDirectoryName(destModPath));
                File.Copy(sourceModPath, destModPath, true);
                Console.WriteLine($"复制完成: {sourceModPath} -> {destModPath}");
            }
            else
            {
                Console.WriteLine($"警告: 源文件不存在: {sourceModPath}");
            }
            
            string beforePakName = string.IsNullOrEmpty(beforePakNum) ? "item.pak" : string.Format("item{0}.pak", beforePakNum);
            string pakPath = Path.Combine(strInstallDirectory, beforePakName);
            Console.WriteLine($"目标pak路径: {pakPath}");
            
            string cmd = "pack\\resources -file2pak \"" + beforePakDir + "\" \"" + pakPath + "\"";
            Console.WriteLine($"执行命令: {cmd}");
            conmon.RunCmd(cmd);
            Console.WriteLine("命令执行完成");
            
            // 处理特效写入 itemshop.txt
            string afterEffectCode = "";
            if (afterItem.EffectCode != null && afterItem.EffectCode != "无" && afterItem.EffectCode.StartsWith("特效代码:"))
            {
                afterEffectCode = afterItem.EffectCode.Replace("特效代码:", "");
            }
            
            if (!string.IsNullOrEmpty(afterEffectCode))
            {
                Console.WriteLine($"开始处理特效写入: afterEffectCode: {afterEffectCode}");
                
                string itemshopPath = Path.Combine(Environment.CurrentDirectory, cookiename, "item_text_pak", "itemshop.txt");
                Console.WriteLine($"itemshop.txt 路径: {itemshopPath}");
                
                if (File.Exists(itemshopPath))
                {
                    try
                    {
                        Encoding.RegisterProvider(CodePagesEncodingProvider.Instance);
                        var lines = File.ReadAllLines(itemshopPath, Encoding.GetEncoding("GB2312"));
                        bool found = false;
                        
                        for (int i = 0; i < lines.Length; i++)
                        {
                            if (lines[i].StartsWith(beforeItem.ItemCode + "\t"))
                            {
                                string[] parts = lines[i].Split('\t');
                                if (parts.Length >= 3)
                                {
                                    parts[2] = afterEffectCode;
                                    lines[i] = string.Join("\t", parts);
                                    found = true;
                                    Console.WriteLine($"已更新第 {i + 1} 行的特效代码为: {afterEffectCode}");
                                    break;
                                }
                            }
                        }
                        
                        if (found)
                        {
                            File.WriteAllLines(itemshopPath, lines, Encoding.GetEncoding("GB2312"));
                            Console.WriteLine("itemshop.txt 已保存");
                            
                            // 重新打包 item_text.pak
                            string itemTextPakPath = Path.Combine(strInstallDirectory, AppConfig.Files.ItemTextPak);
                            string packTextCmd = "pack\\resources -file2pak \"" + Path.Combine(Environment.CurrentDirectory, cookiename, "item_text_pak") + "\" \"" + itemTextPakPath + "\"";
                            Console.WriteLine($"重新打包 item_text.pak: {packTextCmd}");
                            conmon.RunCmd(packTextCmd);
                            Console.WriteLine("item_text.pak 打包完成");
                        }
                        else
                        {
                            Console.WriteLine($"未找到服装代码 {beforeItem.ItemCode} 在 itemshop.txt");
                        }
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine($"写入特效失败: {ex.Message}");
                    }
                }
            }
            
            Console.WriteLine("=== 服装变更结束 ===");
        }

        private void btnClear_Click(object sender, RoutedEventArgs e)
        {
            try
            {
                beforeItems.Clear();
                afterItems.Clear();
                UpdateBeforePanel();
                UpdateAfterPanel();
                UpdatePairStatus();
                
                labErrorMsg.Text = "已清空所有服装";
                labErrorMsg.Visibility = Visibility.Visible;
            }
            catch (Exception ex)
            {
                labErrorMsg.Text = "清空失败: " + ex.Message;
                labErrorMsg.Visibility = Visibility.Visible;
            }
        }
        
        // 加载图片按钮点击事件
        private void btnLoadImg_Click(object sender, RoutedEventArgs e)
        {
            try
            {
                this.Dispatcher.Invoke(() =>
                {
                    labErrorMsg.Text = "正在准备加载图片...请稍候";
                    labErrorMsg.Visibility = Visibility.Visible;
                });
                
                bwLoadImg = new BackgroundWorker();
                bwLoadImg.WorkerSupportsCancellation = true;
                bwLoadImg.DoWork += bw_DoWorkAllIcon;
                bwLoadImg.RunWorkerCompleted += bw_CompletedWorkAllIcon;
                bwLoadImg.RunWorkerAsync();
            }
            catch (Exception ex)
            {
                Console.WriteLine("加载图片按钮点击事件出错: " + ex.Message);
                this.Dispatcher.Invoke(() =>
                {
                    labErrorMsg.Text = "加载图片失败: " + ex.Message;
                    labErrorMsg.Visibility = Visibility.Visible;
                });
            }
        }
        
        // 更新搭配按钮点击事件
        private void btnUpdate_Click(object sender, RoutedEventArgs e)
        {
            try
            {
                labErrorMsg.Visibility = Visibility.Collapsed;
                labErrorMsg.Text = "";
                
                // 简化版更新搭配功能
                labErrorMsg.Text = "更新搭配功能已简化，将在后续版本实现";
                labErrorMsg.Visibility = Visibility.Visible;
            }
            catch (Exception ex)
            {
                Console.WriteLine("更新搭配失败: " + ex.Message);
                labErrorMsg.Text = "更新搭配失败: " + ex.Message;
                labErrorMsg.Visibility = Visibility.Visible;
            }
        }
        
        // 执行搭配更新
        private void bw_DoWorkLast(object sender, DoWorkEventArgs e)
        {
            try
            {
                // 简化版执行搭配更新
                Console.WriteLine("执行搭配更新功能已简化");
            }
            catch (Exception ex)
            {
                Console.WriteLine("执行搭配更新失败: " + ex.Message);
                throw;
            }
        }
        
        // 搭配更新完成
        private void bw_CompletedWorkLast(object sender, RunWorkerCompletedEventArgs e)
        {
            try
            {
                labErrorMsg.Text = "";
                labErrorMsg.Visibility = Visibility.Collapsed;
                
                if (e.Error != null)
                {
                    MessageBox.Show("更新失败: " + e.Error.Message, "错误", MessageBoxButton.OK, MessageBoxImage.Error);
                    return;
                }
                
                // 显示成功消息
                MessageBox.Show("更新成功，请重新打开游戏去查看效果！", "成功", MessageBoxButton.OK, MessageBoxImage.Information);
                
                // 清理
                bwLast.Dispose();
            }
            catch (Exception ex)
            {
                Console.WriteLine("搭配更新完成处理失败: " + ex.Message);
            }
        }
        
        private void InitializeItemList()
        {
            // 初始化后台工作线程
            bwMain = new BackgroundWorker();
            bwMain.WorkerSupportsCancellation = true;
            bwMain.DoWork += bwMain_DoLoadList;
            bwMain.RunWorkerCompleted += bwMain_CompletedLoadList;
            
            // 显示初始化状态和动画
            this.Dispatcher.Invoke(() =>
            {
                labErrorMsg.Text = "正在初始化服装数据...";
                labErrorMsg.Visibility = Visibility.Visible;
                StartLoadingAnimation();
            });
            
            Console.WriteLine("开始后台线程加载服装数据...");
            bwMain.RunWorkerAsync();
        }

        // 核心业务逻辑方法

        // 加载服装数据
        public void GetNewItem()
        {
            var totalSw = Stopwatch.StartNew();
            Console.WriteLine("=== 开始加载服装数据 ===");
            
            try
            {
                
                this.Dispatcher.Invoke(() =>
                {
                    labErrorMsg.Visibility = Visibility.Collapsed;
                    labErrorMsg.Text = "";
                    labLoadingStatus.Visibility = Visibility.Visible;
                    labLoadingStatus.Text = "正在初始化...";
                });
                
                if (this.list != null && this.list.Count > 0)
                {
                    Console.WriteLine("数据已加载，跳过加载步骤");
                    return;
                }
                
                var sw = Stopwatch.StartNew();
                this.list = new List<ItemshopM>();
                Console.WriteLine("创建服装列表成功");
                
                if (string.IsNullOrEmpty(this.strInstallDirectory))
                {
                    Console.WriteLine("游戏目录为空，无法加载服装数据");
                    // 使用Dispatcher.Invoke确保UI操作在主线程执行
                    this.Dispatcher.Invoke(() =>
                    {
                        labErrorMsg.Text = "游戏目录为空，请在config.ini文件中设置游戏目录路径";
                        labErrorMsg.Visibility = Visibility.Visible;
                    });
                    return;
                }
                
                string sourceFileName = Path.Combine(this.strInstallDirectory, AppConfig.Files.ItemTextPak);
                Console.WriteLine("源文件路径: " + sourceFileName);
                
                UpdateLoadingStatus("正在检查游戏目录文件...");
                
                string currentDir = Environment.CurrentDirectory;
                string cookiesPath = Path.Combine(currentDir, this.cookiename);
                string pakPath = Path.Combine(cookiesPath, AppConfig.Files.ItemTextPak);
                string destFileName = pakPath;
                
                sw.Stop();
                Console.WriteLine($"[性能] GetNewItem - 初始化路径: {sw.ElapsedMilliseconds}ms");
                sw.Restart();
                
                if (!Directory.Exists(cookiesPath))
                {
                    Console.WriteLine("创建目标目录: " + cookiesPath);
                    try
                    {
                        Directory.CreateDirectory(cookiesPath);
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine("创建目录失败: " + ex.Message);
                        this.Dispatcher.Invoke(() =>
                        {
                            labErrorMsg.Text = "创建目录失败: " + ex.Message;
                            labErrorMsg.Visibility = Visibility.Visible;
                        });
                        return;
                    }
                }
                
                if (!File.Exists(sourceFileName))
                {
                    Console.WriteLine("源文件不存在: " + sourceFileName);
                    this.Dispatcher.Invoke(() =>
                    {
                        labErrorMsg.Text = "源文件不存在: " + sourceFileName;
                        labErrorMsg.Visibility = Visibility.Visible;
                    });
                    return;
                }
                
                string itemshopPath = Path.Combine(cookiesPath, "item_text_pak", "itemshop.txt");
                
                bool needUnpackItemText = false;
                
                DateTime sourceTime = File.GetLastWriteTime(sourceFileName);
                DateTime destTime = File.Exists(pakPath) ? File.GetLastWriteTime(pakPath) : DateTime.MinValue;
                
                if (!File.Exists(itemshopPath))
                {
                    needUnpackItemText = true;
                    Console.WriteLine("itemshop.txt不存在，需要解包");
                }
                else if (sourceTime > destTime)
                {
                    needUnpackItemText = true;
                    Console.WriteLine("游戏目录的item_text.pak已更新，需要重新解包");
                }
                
                if (needUnpackItemText)
                {
                    try
                    {
                        UpdateLoadingStatus("正在复制 item_text.pak...");
                        File.Copy(sourceFileName, pakPath, true);
                        Console.WriteLine("复制item_text.pak成功");
                        destFileName = pakPath;
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine("复制文件失败: " + ex.Message);
                        destFileName = sourceFileName;
                    }
                }
                else
                {
                    Console.WriteLine("itemshop.txt已存在且未更新，直接使用");
                }
                Console.WriteLine("使用的pak文件路径: " + destFileName);
                
                if (!File.Exists(destFileName))
                {
                    Console.WriteLine("文件不存在，无法解包: " + destFileName);
                    this.Dispatcher.Invoke(() =>
                    {
                        labErrorMsg.Text = "文件不存在，无法解包: " + destFileName;
                        labErrorMsg.Visibility = Visibility.Visible;
                    });
                    return;
                }
                Console.WriteLine("文件存在，开始解包");
                
                if (!Directory.Exists(cookiesPath))
                {
                    Console.WriteLine("创建cookies目录: " + cookiesPath);
                    try
                    {
                        Directory.CreateDirectory(cookiesPath);
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine("创建cookies目录失败: " + ex.Message);
                        this.Dispatcher.Invoke(() =>
                        {
                            labErrorMsg.Text = "创建cookies目录失败: " + ex.Message;
                            labErrorMsg.Visibility = Visibility.Visible;
                        });
                        return;
                    }
                }
                
                string resourcesExePath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, AppConfig.Directories.Pack, AppConfig.Files.ResourcesExe);
                Console.WriteLine("resources.exe路径: " + resourcesExePath);
                
                if (!File.Exists(resourcesExePath))
                {
                    Console.WriteLine("resources.exe不存在: " + resourcesExePath);
                    this.Dispatcher.Invoke(() =>
                    {
                        labErrorMsg.Text = "resources.exe不存在，请确保pack目录下有resources.exe";
                        labErrorMsg.Visibility = Visibility.Visible;
                    });
                    return;
                }
                Console.WriteLine("resources.exe存在");
                
                if (!needUnpackItemText)
                {
                    Console.WriteLine("itemshop.txt已存在且未更新，跳过解包步骤");
                }
                else
                {
                    Console.WriteLine("开始执行解包命令");
                    UpdateLoadingStatus("正在解包 item_text.pak...");
                    try
                    {
                        if (Directory.Exists(Path.Combine(cookiesPath, "item_text_pak")))
                        {
                            try
                            {
                                Directory.Delete(Path.Combine(cookiesPath, "item_text_pak"), true);
                                Console.WriteLine("删除旧的item_text_pak目录");
                            }
                            catch { }
                        }
                        
                        ProcessStartInfo processStartInfo = new ProcessStartInfo();
                        processStartInfo.FileName = resourcesExePath;
                        processStartInfo.Arguments = $"\"{destFileName}\" -all";
                        processStartInfo.UseShellExecute = false;
                        processStartInfo.CreateNoWindow = true;
                        processStartInfo.WindowStyle = ProcessWindowStyle.Hidden;
                        processStartInfo.RedirectStandardOutput = true;
                        processStartInfo.RedirectStandardError = true;
                        processStartInfo.WorkingDirectory = currentDir;
                        
                        Console.WriteLine("执行解包命令: " + processStartInfo.FileName + " " + processStartInfo.Arguments);
                        
                        Process process = Process.Start(processStartInfo);
                        Console.WriteLine("进程启动成功，等待退出");
                        
                        bool exited = process.WaitForExit(15000);
                        if (exited)
                        {
                            Console.WriteLine("解包命令执行完成，退出码: " + process.ExitCode);
                        }
                        else
                        {
                            Console.WriteLine("解包命令执行超时，强制关闭进程");
                            process.Kill();
                        }
                        process.Close();
                        
                        Console.WriteLine("解包命令处理完成");
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine("执行解包命令失败: " + ex.Message);
                        this.Dispatcher.Invoke(() =>
                        {
                            labErrorMsg.Text = "执行解包命令时出现错误: " + ex.Message;
                            labErrorMsg.Visibility = Visibility.Visible;
                        });
                    }
                }
                
                Console.WriteLine("解包命令执行完成，开始检查解包结果");
                Console.WriteLine("检查解析后的文件: " + itemshopPath);
                UpdateLoadingStatus("正在解析服装数据...");
                
                if (!Directory.Exists(cookiesPath))
                {
                    Console.WriteLine("cookies目录不存在: " + cookiesPath);
                }
                else
                {
                    Console.WriteLine("cookies目录存在");
                    string itemTextPakPath = Path.Combine(cookiesPath, "item_text_pak");
                    if (!Directory.Exists(itemTextPakPath))
                    {
                        Console.WriteLine("item_text_pak目录不存在: " + itemTextPakPath);
                    }
                    else
                    {
                        Console.WriteLine("item_text_pak目录存在");
                        try
                        {
                            string[] files = Directory.GetFiles(itemTextPakPath);
                            Console.WriteLine("item_text_pak目录中的文件数量: " + files.Length);
                        }
                        catch (Exception ex)
                        {
                            Console.WriteLine("列出文件失败: " + ex.Message);
                        }
                    }
                }
                
                if (File.Exists(itemshopPath))
                {
                    sw.Stop();
                    Console.WriteLine($"[性能] GetNewItem - 准备解析文件: {sw.ElapsedMilliseconds}ms");
                    sw.Restart();
                    
                    int itemCount = 0;
                    try
                    {
                        Encoding.RegisterProvider(CodePagesEncodingProvider.Instance);
                        using (FileStream fileStream = new FileStream(itemshopPath, FileMode.Open, FileAccess.Read))
                        using (StreamReader streamReader = new StreamReader(fileStream, Encoding.GetEncoding("GB2312")))
                        {
                            string text;
                            while ((text = streamReader.ReadLine()) != null)
                            {
                                string text2 = text.ToString();
                                
                                if (text2.IndexOf("ItemCode") == -1)
                                {
                                    string[] array = text2.Split(new string[] { "\t" }, StringSplitOptions.None);
                                    
                                    if (array.Length >= 5)
                                    {
                                        if (array[3] != "" && array[3] != "--")
                                        {
                                            this.list.Add(new ItemshopM
                                            {
                                                ItemCode = array[0],
                                                PakNum = "*" + ((array[1] == "1") ? "" : array[1]) + ".pak",
                                                ImgPath = string.Concat(new string[]
                                                {
                                                    currentDir,
                                                    "\\",
                                                    this.cookiename,
                                                    "\\icon",
                                                    (array[1] == "1") ? "" : array[1],
                                                    "_pak\\u",
                                                    array[0],
                                                    ".png"
                                                }),
                                                EffectCode = ((array[2] == "") ? "无" : ("特效代码:" + array[2])),
                                                ItemName = array[3],
                                                Comment = array[4]
                                            });
                                            itemCount++;
                                        }
                                    }
                                    else if (array.Length == 4)
                                    {
                                        if (array[3] != "" && array[3] != "--")
                                        {
                                            this.list.Add(new ItemshopM
                                            {
                                                ItemCode = array[0],
                                                PakNum = "*" + ((array[1] == "1") ? "" : array[1]) + ".pak",
                                                ImgPath = string.Concat(new string[]
                                                {
                                                    currentDir,
                                                    "\\",
                                                    this.cookiename,
                                                    "\\icon",
                                                    (array[1] == "1") ? "" : array[1],
                                                    "_pak\\u",
                                                    array[0],
                                                    ".png"
                                                }),
                                                ItemName = array[2],
                                                Comment = array[3]
                                            });
                                            itemCount++;
                                        }
                                    }
                                }
                            }
                        }
                        
                        sw.Stop();
                        Console.WriteLine($"[性能] GetNewItem - 解析文件({itemCount}条): {sw.ElapsedMilliseconds}ms");
                        sw.Restart();
                        
                        Console.WriteLine("解析完成，共加载 " + itemCount + " 件服装");
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine("解析文件失败: " + ex.Message);
                    }
                    
                    // 加载常用物品颜色配置
                    List<string> colorList = new List<string>();
                    try
                    {
                        string oftenitemcodePath = Path.Combine(Environment.CurrentDirectory, this.oftenitemcode);
                        if (File.Exists(oftenitemcodePath))
                        {
                            StreamReader streamReader2 = new StreamReader(oftenitemcodePath, Encoding.Default);
                            string text3;
                            while ((text3 = streamReader2.ReadLine()) != null)
                            {
                                colorList.Add(text3.ToString());
                            }
                            streamReader2.Close();
                        }
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine("加载常用物品颜色配置失败: " + ex.Message);
                    }
                    
                    // 加载修改记录
                    List<string> modifyList = new List<string>();
                    try
                    {
                        string dopaklogPath = Path.Combine(Environment.CurrentDirectory, AppConfig.Files.DopakLog);
                        if (File.Exists(dopaklogPath))
                        {
                            StreamReader streamReader2 = new StreamReader(dopaklogPath, Encoding.Default);
                            string text4;
                            while ((text4 = streamReader2.ReadLine()) != null)
                            {
                                modifyList.Add(text4.ToString());
                            }
                            streamReader2.Close();
                        }
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine("加载修改记录失败: " + ex.Message);
                    }
                    
                    // 更新物品属性
                    foreach (ItemshopM item in this.list)
                    {
                        item.RowBackColor = (from o in colorList
                                            where o.IndexOf(item.ItemCode) != -1
                                            select o).FirstOrDefault<string>();
                        
                        string text5 = (from o in modifyList
                                        where o.IndexOf(item.ItemCode + "#") != -1
                                        select o).FirstOrDefault<string>();
                        if (text5 != null)
                        {
                            if (text5.IndexOf("#") != -1)
                            {
                                item.EditNewCode = text5.Split(new char[] { '#' })[1];
                            }
                        }
                    }
                    
                    sw.Stop();
                    Console.WriteLine($"[性能] GetNewItem - 加载配置和处理属性: {sw.ElapsedMilliseconds}ms");
                    sw.Restart();
                    
                    // 更新UI
                    this.Dispatcher.Invoke(() =>
                    {
                        try
                        {
                            // 反转列表顺序，让最新的服装显示在顶部
                            list.Reverse();
                            lstClothing.ItemsSource = null;
                            lstClothing.ItemsSource = list;
                            
                            // 加载特效列表（筛选有特效的服装）
                            effectList = list.Where(item => item.EffectCode != "无" && !string.IsNullOrEmpty(item.EffectCode)).ToList();
                            lstEffect.ItemsSource = null;
                            lstEffect.ItemsSource = effectList;
                            
                            sw.Stop();
                            Console.WriteLine($"[性能] GetNewItem - 更新UI绑定: {sw.ElapsedMilliseconds}ms");
                            
                            labErrorMsg.Text = "服装数据加载成功，共 " + list.Count + " 件服装，其中 " + effectList.Count + " 件有特效";
                            labErrorMsg.Visibility = Visibility.Visible;
                            labLoadingStatus.Text = "加载完成！";
                            labLoadingStatus.Visibility = Visibility.Visible;
                            
                            var timer = new System.Windows.Threading.DispatcherTimer();
                            timer.Interval = TimeSpan.FromSeconds(2);
                            timer.Tick += (s, e) =>
                            {
                                labErrorMsg.Visibility = Visibility.Collapsed;
                                labLoadingStatus.Visibility = Visibility.Collapsed;
                                timer.Stop();
                            };
                            timer.Start();
                            
                            CheckAndLoadImages();
                        }
                        catch (Exception ex)
                        {
                            Console.WriteLine("UI更新失败: " + ex.Message);
                            labErrorMsg.Text = "UI更新失败: " + ex.Message;
                            labErrorMsg.Visibility = Visibility.Visible;
                        }
                    });
                    
                    totalSw.Stop();
                    Console.WriteLine($"[性能] GetNewItem - 总耗时: {totalSw.ElapsedMilliseconds}ms");
                    
                    // 延迟滚动到顶部，确保ListBox已完成布局
                    this.Dispatcher.BeginInvoke(new Action(() =>
                    {
                        ScrollListBoxToTop();
                    }), System.Windows.Threading.DispatcherPriority.Render);
                }
                else
                {
                    Console.WriteLine("解析后的服装数据文件不存在: " + itemshopPath);
                    this.Dispatcher.Invoke(() =>
                    {
                        labErrorMsg.Text = "解析后的服装数据文件不存在: " + itemshopPath;
                        labErrorMsg.Visibility = Visibility.Visible;
                    });
                    return;
                }
            }
            catch (Exception ex)
            {
                string errorMessage = "加载服装数据失败: " + ex.Message;
                Console.WriteLine(errorMessage);
                
                this.Dispatcher.Invoke(() =>
                {
                    MessageBox.Show(errorMessage, "错误", MessageBoxButton.OK, MessageBoxImage.Error);
                    
                    // 更新错误状态
                    labErrorMsg.Text = "加载失败: " + ex.Message;
                    labErrorMsg.Visibility = Visibility.Visible;
                });
            }
            finally
            {
            }
        }
        
        // 检查并加载图片
        private void CheckAndLoadImages()
        {
            try
            {
                string cookiesDir = Path.Combine(Environment.CurrentDirectory, this.cookiename);
                
                if (!Directory.Exists(cookiesDir))
                {
                    Console.WriteLine("cookies目录不存在，无法检查图片");
                    return;
                }
                
                bool hasUnpackedIconFiles = false;
                string[] directories = Directory.GetDirectories(cookiesDir);
                foreach (string dir in directories)
                {
                    string dirName = Path.GetFileName(dir);
                    if (dirName.StartsWith("icon") && dirName.EndsWith("_pak"))
                    {
                        if (Directory.GetFiles(dir).Length > 0)
                        {
                            hasUnpackedIconFiles = true;
                            break;
                        }
                    }
                }
                
                if (!hasUnpackedIconFiles && this.list.Count > 0)
                {
                    Console.WriteLine("检测到没有图片文件，自动开始加载");
                    this.Dispatcher.Invoke(() =>
                    {
                        labErrorMsg.Text = "检测到没有图片文件，正在自动加载...";
                        labErrorMsg.Visibility = Visibility.Visible;
                    });
                    
                    bwLoadImg = new BackgroundWorker();
                    bwLoadImg.WorkerSupportsCancellation = true;
                    bwLoadImg.DoWork += bw_DoWorkAllIcon;
                    bwLoadImg.RunWorkerCompleted += bw_CompletedWorkAllIcon;
                    bwLoadImg.RunWorkerAsync();
                }
                else
                {
                    Console.WriteLine("已存在解包的icon文件，跳过自动加载");
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine("检查图片文件失败: " + ex.Message);
            }
        }

        // 加载图片
        private void LoadImages()
        {
            try
            {
                this.Dispatcher.Invoke(() =>
                {
                    labLoadingStatus.Text = "正在加载图片...";
                    labLoadingStatus.Visibility = Visibility.Visible;
                    labErrorMsg.Visibility = Visibility.Collapsed;
                });
                
                string cookiesDir = Path.Combine(Environment.CurrentDirectory, this.cookiename);
                
                // 查找resources.exe
                string resourcesExePath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, AppConfig.Directories.Pack, AppConfig.Files.ResourcesExe);
                
                Console.WriteLine("resources.exe路径: " + resourcesExePath);
                
                if (!File.Exists(resourcesExePath))
                {
                    this.Dispatcher.Invoke(() =>
                    {
                        labErrorMsg.Text = "找不到resources.exe，请确保pack目录下有resources.exe";
                        labErrorMsg.Visibility = Visibility.Visible;
                        labLoadingStatus.Visibility = Visibility.Collapsed;
                    });
                    return;
                }
                
                if (this.list == null || this.list.Count == 0)
                {
                    throw new InvalidOperationException("服装列表为空，请先加载服装数据");
                }
                
                List<FS服装搭配专家v1._0.ItemshopM> distinctList = this.list.Distinct(new ItemshopMComparer()).ToList<FS服装搭配专家v1._0.ItemshopM>();
                int totalCount = distinctList.Count;
                int currentCount = 0;
                int successCount = 0;
                int skipCount = 0;
                
                foreach (FS服装搭配专家v1._0.ItemshopM itemshopM in distinctList)
                {
                    currentCount++;
                    
                    if (currentCount % 50 == 0)
                    {
                        int finalCurrentCount = currentCount;
                        this.Dispatcher.Invoke(() =>
                        {
                            labLoadingStatus.Text = string.Format("正在解包图片... {0}/{1}", finalCurrentCount, totalCount);
                        });
                    }
                    
                    string pakNum = itemshopM.PakNum.Replace("*", "");
                    string iconDirName = "icon" + pakNum.Replace(".", "_");
                    string iconDir = Path.Combine(cookiesDir, iconDirName);
                    string iconPakName = "icon" + pakNum;
                    
                    // 检查目录是否存在且有文件
                    if (Directory.Exists(iconDir) && Directory.GetFiles(iconDir).Length > 0)
                    {
                        skipCount++;
                        continue;
                    }
                    
                    string sourcePath = Path.Combine(this.strInstallDirectory, iconPakName);
                    string destPath = Path.Combine(cookiesDir, iconPakName);
                    
                    try
                    {
                        if (File.Exists(sourcePath))
                        {
                            File.Copy(sourcePath, destPath, true);
                            
                            string cmd = "pack\\resources \"" + destPath + "\" -byname .+\\.png";
                            conmon.RunCmd(cmd);
                            
                            successCount++;
                        }
                        else
                        {
                            skipCount++;
                        }
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine("加载图片失败: " + ex.Message);
                    }
                }
                
                this.Dispatcher.Invoke(() =>
                {
                    labErrorMsg.Text = string.Format("图片加载完成！新加载: {0}, 跳过: {1}", successCount, skipCount);
                    labErrorMsg.Visibility = Visibility.Visible;
                });
            }
            catch (Exception ex)
            {
                this.Dispatcher.Invoke(() =>
                {
                    labErrorMsg.Text = "加载图片失败: " + ex.Message;
                    labErrorMsg.Visibility = Visibility.Visible;
                });
            }
        }
        
        // 预览服装图片
        private void PreviewItemImage(ItemshopM item)
        {
            try
            {
                this.Dispatcher.Invoke(() =>
                {
                    if (item == null)
                    {
                        labErrorMsg.Text = "请选择一件服装进行预览";
                        labErrorMsg.Visibility = Visibility.Visible;
                        return;
                    }
                    
                    // 显示预览加载状态
                    labErrorMsg.Text = "正在加载预览图片...";
                    labErrorMsg.Visibility = Visibility.Visible;
                });
                
                // 构建图片路径
                string imagePath = item.ImgPath;                
                // 检查图片是否存在
                if (File.Exists(imagePath))
                {
                    try
                    {
                        // 加载图片
                        var bitmap = new System.Windows.Media.Imaging.BitmapImage();
                        bitmap.BeginInit();
                        bitmap.UriSource = new Uri(imagePath);
                        bitmap.CacheOption = System.Windows.Media.Imaging.BitmapCacheOption.OnLoad;
                        bitmap.EndInit();
                        
                        // 设置预览图片
                        this.Dispatcher.Invoke(() =>
                        {
                            labErrorMsg.Text = "预览图片: " + item.ItemName;
                            labErrorMsg.Visibility = Visibility.Visible;
                        });
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine("加载图片失败: " + ex.Message);
                        this.Dispatcher.Invoke(() =>
                        {
                            labErrorMsg.Text = "加载图片失败: " + ex.Message;
                            labErrorMsg.Visibility = Visibility.Visible;
                        });
                    }
                }
                else
                {
                    // 图片不存在
                    this.Dispatcher.Invoke(() =>
                    {
                        // 提示用户加载图片
                        labErrorMsg.Text = "图片不存在，请点击'加载图片'按钮";
                        labErrorMsg.Visibility = Visibility.Visible;
                    });
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine("预览图片失败: " + ex.Message);
                this.Dispatcher.Invoke(() =>
                {
                    labErrorMsg.Text = "预览图片失败: " + ex.Message;
                    labErrorMsg.Visibility = Visibility.Visible;
                });
            }
        }

        // 刷新控件
        private void RefreshControl(string otherIconPng, bool isbefore)
        {
            try
            {
                this.thisOtherIconPng = otherIconPng;
                this.thisIsbefore = isbefore;
                this.thisOtherPropName = otherIconPng;
                
                // 这里可以添加图片预览逻辑
            }
            catch (Exception ex)
            {
                Console.WriteLine("刷新控件失败: " + ex.Message);
            }
        }

        // 初始化配置
        private void InitializeConfig()
        {
            try
            {
                Console.WriteLine("=== 开始初始化配置 ===");
                
                this.strInstallDirectory = ConfigService.Instance.GameInstallDirectory;
                Console.WriteLine("从 ConfigService 读取游戏目录: " + this.strInstallDirectory);
                
                bool needsSetup = ConfigService.Instance.NeedsGamePathSetup();
                
                if (needsSetup)
                {
                    Console.WriteLine("游戏目录需要设置");
                    bool pathSet = false;
                    
                    string? detectedPath = ConfigService.Instance.AutoDetectGamePath();
                    
                    if (!string.IsNullOrEmpty(detectedPath))
                    {
                        this.Dispatcher.Invoke(() =>
                        {
                            var result = MessageBox.Show(
                                $"检测到游戏安装目录：\n{detectedPath}\n\n是否使用此路径？",
                                "游戏目录检测",
                                MessageBoxButton.YesNo,
                                MessageBoxImage.Question);
                            
                            if (result == MessageBoxResult.Yes)
                            {
                                this.strInstallDirectory = detectedPath;
                                ConfigService.Instance.SetGameInstallDirectory(detectedPath);
                                pathSet = true;
                                Console.WriteLine("用户确认使用检测到的路径: " + detectedPath);
                            }
                        });
                    }
                    
                    if (!pathSet)
                    {
                        pathSet = ShowFolderDialog();
                    }
                    
                    if (!pathSet)
                    {
                        this.Dispatcher.Invoke(() =>
                        {
                            labErrorMsg.Text = "请选择游戏安装目录后重新启动程序。";
                            labErrorMsg.Visibility = Visibility.Visible;
                        });
                        return;
                    }
                }
                
                if (!string.IsNullOrEmpty(this.strInstallDirectory))
                {
                    Console.WriteLine("游戏目录: " + this.strInstallDirectory);
                    
                    if (!Directory.Exists(this.strInstallDirectory))
                    {
                        Console.WriteLine("游戏目录不存在: " + this.strInstallDirectory);
                        
                        this.Dispatcher.Invoke(() =>
                        {
                            labErrorMsg.Text = "游戏目录不存在: " + this.strInstallDirectory;
                            labErrorMsg.Visibility = Visibility.Visible;
                        });
                    }
                    else
                    {
                        string itemTextPakPath = Path.Combine(this.strInstallDirectory, AppConfig.Files.ItemTextPak);
                        if (!File.Exists(itemTextPakPath))
                        {
                            Console.WriteLine("item_text.pak文件不存在: " + itemTextPakPath);
                            
                            this.Dispatcher.Invoke(() =>
                            {
                                labErrorMsg.Text = "item_text.pak文件不存在: " + itemTextPakPath;
                                labErrorMsg.Visibility = Visibility.Visible;
                            });
                        }
                        else
                        {
                            Console.WriteLine("item_text.pak文件存在: " + itemTextPakPath);
                        }
                    }
                }
                
                // 创建必要的目录
                if (!Directory.Exists(this.cookiename))
                {
                    Console.WriteLine("创建cookies目录: " + this.cookiename);
                    Directory.CreateDirectory(this.cookiename);
                }
                else
                {
                    Console.WriteLine("cookies目录已存在: " + this.cookiename);
                }
                
                Console.WriteLine("=== 配置初始化完成 ===");
            }
            catch (Exception ex)
            {
                Console.WriteLine("初始化配置时出错: " + ex.Message);
                Console.WriteLine("堆栈跟踪: " + ex.StackTrace);
                
                // 显示错误消息
                this.Dispatcher.Invoke(() =>
                {
                    labErrorMsg.Text = "初始化配置时出错: " + ex.Message;
                    labErrorMsg.Visibility = Visibility.Visible;
                });
            }
        }

        private bool ShowFolderDialog()
        {
            bool result = false;
            
            this.Dispatcher.Invoke(() =>
            {
                var dialog = new OpenFolderDialog
                {
                    Title = "请选择街头篮球游戏安装目录",
                    InitialDirectory = @"C:\Program Files (x86)"
                };
                
                if (dialog.ShowDialog() == true)
                {
                    string selectedPath = dialog.FolderName;
                    
                    if (ConfigService.Instance.IsValidGamePath(selectedPath))
                    {
                        this.strInstallDirectory = selectedPath;
                        ConfigService.Instance.SetGameInstallDirectory(selectedPath);
                        labErrorMsg.Visibility = Visibility.Collapsed;
                        result = true;
                        Console.WriteLine("用户选择的游戏目录: " + selectedPath);
                    }
                    else
                    {
                        MessageBox.Show(
                            "所选目录不是有效的游戏安装目录。\n请选择包含 item_text.pak 文件的目录。",
                            "路径无效",
                            MessageBoxButton.OK,
                            MessageBoxImage.Warning);
                        result = ShowFolderDialog();
                    }
                }
                else
                {
                    result = false;
                }
            });
            
            return result;
        }

        private void btnSettings_Click(object sender, RoutedEventArgs e)
        {
            ShowFolderDialog();
        }

        // 后台工作线程方法
        private void bwMain_DoLoadList(object sender, DoWorkEventArgs e)
        {
            try
            {
                Console.WriteLine("=== 开始加载服装数据 ===");
                
                UpdateLoadingStatus("正在初始化配置...");
                Console.WriteLine("当前工作目录: " + Environment.CurrentDirectory);
                
                Console.WriteLine("开始初始化配置...");
                InitializeConfig();
                Console.WriteLine("配置初始化完成，游戏目录: " + this.strInstallDirectory);
                
                UpdateLoadingStatus("正在加载服装数据...");
                Console.WriteLine("开始加载服装数据...");
                GetNewItem();
                Console.WriteLine("服装数据加载完成，共加载 " + this.list.Count + " 件服装");
                
                UpdateLoadingStatus("加载完成！");
                Console.WriteLine("=== 服装数据加载流程完成 ===");
            }
            catch (Exception ex)
            {
                Console.WriteLine("加载服装数据时出错: " + ex.Message);
                Console.WriteLine("堆栈跟踪: " + ex.StackTrace);
                
                this.Dispatcher.Invoke(() =>
                {
                    labErrorMsg.Text = "加载服装数据时出错: " + ex.Message;
                    labErrorMsg.Visibility = Visibility.Visible;
                    labLoadingStatus.Visibility = Visibility.Collapsed;
                });
            }
        }

        private void UpdateLoadingStatus(string status)
        {
            this.Dispatcher.Invoke(() =>
            {
                labLoadingStatus.Text = status;
                labLoadingStatus.Visibility = Visibility.Visible;
            });
            Console.WriteLine("[状态] " + status);
        }

        private void bwMain_CompletedLoadList(object sender, RunWorkerCompletedEventArgs e)
        {
            StopLoadingAnimation();
            
            if (e.Error != null)
            {
                MessageBox.Show("加载数据失败: " + e.Error.Message);
            }
            else
            {
                bwMain.Dispose();
            }
        }

        private void bw_DoWorkAllIcon(object sender, DoWorkEventArgs e)
        {
            LoadImages();
        }

        private ScrollViewer? GetScrollViewer(DependencyObject parent)
        {
            if (parent == null) return null;

            for (int i = 0; i < VisualTreeHelper.GetChildrenCount(parent); i++)
            {
                var child = VisualTreeHelper.GetChild(parent, i);
                if (child is ScrollViewer scrollViewer)
                {
                    return scrollViewer;
                }
                var result = GetScrollViewer(child);
                if (result != null)
                {
                    return result;
                }
            }
            return null;
        }

        private void bw_CompletedWorkAllIcon(object sender, RunWorkerCompletedEventArgs e)
        {
            if (e.Error != null)
            {
                MessageBox.Show("加载图片失败: " + e.Error.Message);
            }
            else
            {
                bwLoadImg.Dispose();
            }
            
            this.Dispatcher.Invoke(() =>
            {
                labLoadingStatus.Visibility = Visibility.Collapsed;
            });
        }

        /// <summary>
        /// 从配置文件加载窗口尺寸
        /// </summary>
        private void LoadWindowSize()
        {
            try
            {
                var configService = Core.Config.ConfigService.Instance;
                this.Width = configService.MainWindowWidth;
                this.Height = configService.MainWindowHeight;
                Console.WriteLine($"[MainWindow] 从配置文件加载窗口尺寸: {Width}x{Height}");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[MainWindow] 加载窗口尺寸失败: {ex.Message}");
            }
        }

        /// <summary>
        /// 窗口尺寸变化事件处理
        /// </summary>
        private void MainWindow_SizeChanged(object sender, SizeChangedEventArgs e)
        {
            try
            {
                // 只在窗口正常状态下保存尺寸
                if (this.WindowState == WindowState.Normal)
                {
                    var configService = Core.Config.ConfigService.Instance;
                    configService.MainWindowWidth = this.ActualWidth;
                    configService.MainWindowHeight = this.ActualHeight;
                    Console.WriteLine($"[MainWindow] 窗口尺寸已保存: {ActualWidth}x{ActualHeight}");
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[MainWindow] 保存窗口尺寸失败: {ex.Message}");
            }
        }
    }
}

// 物品比较器
public class ItemshopMComparer : IEqualityComparer<FS服装搭配专家v1._0.ItemshopM>
{
    public bool Equals(FS服装搭配专家v1._0.ItemshopM x, FS服装搭配专家v1._0.ItemshopM y)
    {
        return x.PakNum == y.PakNum;
    }

    public int GetHashCode(FS服装搭配专家v1._0.ItemshopM obj)
    {
        return obj.PakNum.GetHashCode();
    }
}