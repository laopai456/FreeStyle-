using System;
using System.Collections.Generic;
using System.Windows;
using System.Windows.Media;
using System.IO;
using System.Linq;
using System.Diagnostics;
using System.ComponentModel;
using System.Text;
using System.Windows.Controls;
using System.Windows.Input;

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
        private string cookiename = "cookies";
        private string oftenitemcode = "oftenitemcode.ini";
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

        // 后台工作线程
        private BackgroundWorker bwMain;
        private BackgroundWorker bwLoadImg;
        private BackgroundWorker bwLast;

        public MainWindow()
        {
            try
            {
                Console.WriteLine("=== 主窗口初始化开始 ===");
                
                // 记录初始化前的状态
                Console.WriteLine("开始InitializeComponent()...");
                InitializeComponent();
                Console.WriteLine("InitializeComponent()完成");
                
                // 强制设置窗口属性
                Console.WriteLine("设置窗口属性...");
                this.Width = 1440;
                this.Height = 1080;
                this.WindowStartupLocation = WindowStartupLocation.CenterScreen;
                this.WindowState = WindowState.Maximized;
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
        
        private void btnSkin_Click(object sender, RoutedEventArgs e)
        {
            // 简单的换肤功能
            Console.WriteLine("换肤按钮点击");
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
            // 实时搜索功能
            Search();
        }

        private void Search()
        {
            try
            {
                string searchText = "";
                this.Dispatcher.Invoke(() =>
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
                    this.Dispatcher.Invoke(() =>
                    {
                        lstClothing.ItemsSource = this.list;
                    });
                    return;
                }
                
                var filteredList = this.list.Where(item =>
                    (item.ItemCode != null && item.ItemCode.IndexOf(searchText, StringComparison.OrdinalIgnoreCase) >= 0) ||
                    (item.PakNum != null && item.PakNum.IndexOf(searchText, StringComparison.OrdinalIgnoreCase) >= 0) ||
                    (item.EffectCode != null && item.EffectCode.IndexOf(searchText, StringComparison.OrdinalIgnoreCase) >= 0) ||
                    (item.ItemName != null && item.ItemName.IndexOf(searchText, StringComparison.OrdinalIgnoreCase) >= 0) ||
                    (item.Comment != null && item.Comment.IndexOf(searchText, StringComparison.OrdinalIgnoreCase) >= 0) ||
                    (item.ItemType != null && item.ItemType.IndexOf(searchText, StringComparison.OrdinalIgnoreCase) >= 0)
                ).ToList();
                
                this.Dispatcher.Invoke(() =>
                {
                    lstClothing.ItemsSource = filteredList;
                    labErrorMsg.Text = string.Format("找到 {0} 个结果", filteredList.Count);
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
                dialog.Owner = this;
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
                        
                        File.AppendAllText("dopaklog.ini", logEntry, Encoding.Default);
                        
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
            string beforePakNum = beforeItem.PakNum.Replace("*", "").Replace(".pak", "");
            string afterPakNum = afterItem.PakNum.Replace("*", "").Replace(".pak", "");
            
            string beforeModFile = string.Format("i{0}.bml", beforeItem.ItemCode);
            string afterModFile = string.Format("i{0}.bml", afterItem.ItemCode);
            
            string beforePakDir = Path.Combine(Environment.CurrentDirectory, cookiename, "item" + beforePakNum + "_pak");
            string afterPakDir = Path.Combine(Environment.CurrentDirectory, cookiename, "item" + afterPakNum + "_pak");
            
            string sourceModPath = Path.Combine(afterPakDir, afterModFile);
            string destModPath = Path.Combine(beforePakDir, beforeModFile);
            
            if (File.Exists(sourceModPath))
            {
                Directory.CreateDirectory(Path.GetDirectoryName(destModPath));
                File.Copy(sourceModPath, destModPath, true);
            }
            
            string beforePakName = string.IsNullOrEmpty(beforePakNum) ? "item.pak" : string.Format("item{0}.pak", beforePakNum);
            string pakPath = Path.Combine(strInstallDirectory, beforePakName);
            
            string cmd = "pack\\resources -file2pak \"" + beforePakDir + "\" \"" + pakPath + "\"";
            conmon.RunCmd(cmd);
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
                // 显示加载提示
                this.Dispatcher.Invoke(() =>
                {
                    labErrorMsg.Text = "正在准备加载图片...请稍候";
                    labErrorMsg.Visibility = Visibility.Visible;
                    picLoding.Visibility = Visibility.Visible;
                });
                
                // 启动后台线程加载图片
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
                    picLoding.Visibility = Visibility.Collapsed;
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
            
            // 显示初始化状态
            this.Dispatcher.Invoke(() =>
            {
                labErrorMsg.Text = "正在初始化服装数据...";
                labErrorMsg.Visibility = Visibility.Visible;
                picLoding.Visibility = Visibility.Visible;
            });
            
            Console.WriteLine("开始后台线程加载服装数据...");
            bwMain.RunWorkerAsync();
        }

        // 核心业务逻辑方法

        // 加载服装数据
        public void GetNewItem()
        {
            Console.WriteLine("=== 开始加载服装数据 ===");
            
            try
            {
                
                this.Dispatcher.Invoke(() =>
                {
                    picLoding.Visibility = Visibility.Visible;
                    labErrorMsg.Visibility = Visibility.Collapsed;
                    labErrorMsg.Text = "";
                });
                
                if (this.list != null && this.list.Count > 0)
                {
                    Console.WriteLine("数据已加载，跳过加载步骤");
                    return;
                }
                
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
                        picLoding.Visibility = Visibility.Collapsed;
                    });
                    return;
                }
                
                string sourceFileName = Path.Combine(this.strInstallDirectory, "item_text.pak");
                Console.WriteLine("源文件路径: " + sourceFileName);
                
                string currentDir = Environment.CurrentDirectory;
                string cookiesPath = Path.Combine(currentDir, this.cookiename);
                string pakPath = Path.Combine(cookiesPath, "item_text.pak");
                string destFileName = pakPath;
                
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
                            picLoding.Visibility = Visibility.Collapsed;
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
                        picLoding.Visibility = Visibility.Collapsed;
                    });
                    return;
                }
                
                string itemshopPath = Path.Combine(cookiesPath, "item_text_pak", "itemshop.txt");
                if (File.Exists(itemshopPath))
                {
                    Console.WriteLine("cookies目录中已有解包后的itemshop.txt文件，直接使用");
                }
                else
                {
                    try
                    {
                        File.Copy(sourceFileName, pakPath, true);
                        Console.WriteLine("复制文件成功");
                        destFileName = pakPath;
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine("复制文件失败: " + ex.Message);
                        destFileName = sourceFileName;
                    }
                }
                Console.WriteLine("使用的pak文件路径: " + destFileName);
                
                if (!File.Exists(destFileName))
                {
                    Console.WriteLine("文件不存在，无法解包: " + destFileName);
                    this.Dispatcher.Invoke(() =>
                    {
                        labErrorMsg.Text = "文件不存在，无法解包: " + destFileName;
                        labErrorMsg.Visibility = Visibility.Visible;
                        picLoding.Visibility = Visibility.Collapsed;
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
                            picLoding.Visibility = Visibility.Collapsed;
                        });
                        return;
                    }
                }
                
                string resourcesExePath = Path.Combine(currentDir, "..", "..", "..", "pack", "resources.exe");
                Console.WriteLine("resources.exe路径: " + resourcesExePath);
                
                if (!File.Exists(resourcesExePath))
                {
                    resourcesExePath = Path.Combine(Path.GetDirectoryName(System.Reflection.Assembly.GetExecutingAssembly().Location), "..", "..", "..", "pack", "resources.exe");
                    Console.WriteLine("尝试resources.exe路径: " + resourcesExePath);
                    
                    if (!File.Exists(resourcesExePath))
                    {
                        Console.WriteLine("resources.exe不存在: " + resourcesExePath);
                        this.Dispatcher.Invoke(() =>
                        {
                            labErrorMsg.Text = "resources.exe不存在: " + resourcesExePath;
                            labErrorMsg.Visibility = Visibility.Visible;
                            picLoding.Visibility = Visibility.Collapsed;
                        });
                        return;
                    }
                }
                Console.WriteLine("resources.exe存在");
                
                if (File.Exists(itemshopPath))
                {
                    Console.WriteLine("itemshop.txt文件已经存在，跳过解包步骤");
                }
                else
                {
                    Console.WriteLine("开始执行解包命令");
                    try
                    {
                        ProcessStartInfo processStartInfo = new ProcessStartInfo();
                        processStartInfo.FileName = resourcesExePath;
                        processStartInfo.Arguments = $"\"{destFileName}\" -all";
                        processStartInfo.UseShellExecute = true;
                        processStartInfo.CreateNoWindow = true;
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
                        string dopaklogPath = Path.Combine(Environment.CurrentDirectory, "dopaklog.ini");
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
                    
                    // 更新UI
                    this.Dispatcher.Invoke(() =>
                    {
                        try
                        {
                            lstClothing.ItemsSource = null;
                            lstClothing.ItemsSource = list;
                            lstClothing.DisplayMemberPath = "ItemName";
                            
                            labErrorMsg.Text = "服装数据加载成功，共 " + list.Count + " 件服装";
                            labErrorMsg.Visibility = Visibility.Visible;
                            
                            CheckAndLoadImages();
                        }
                        catch (Exception ex)
                        {
                            Console.WriteLine("UI更新失败: " + ex.Message);
                            labErrorMsg.Text = "UI更新失败: " + ex.Message;
                            labErrorMsg.Visibility = Visibility.Visible;
                        }
                    });
                }
                else
                {
                    Console.WriteLine("解析后的服装数据文件不存在: " + itemshopPath);
                    this.Dispatcher.Invoke(() =>
                    {
                        labErrorMsg.Text = "解析后的服装数据文件不存在: " + itemshopPath;
                        labErrorMsg.Visibility = Visibility.Visible;
                        picLoding.Visibility = Visibility.Collapsed;
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
                this.Dispatcher.Invoke(() =>
                {
                    picLoding.Visibility = Visibility.Collapsed;
                });
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
                
                bool hasUnpackedIconDir = false;
                string[] directories = Directory.GetDirectories(cookiesDir);
                foreach (string dir in directories)
                {
                    string dirName = Path.GetFileName(dir);
                    if (dirName.StartsWith("icon") && dirName.EndsWith("_pak"))
                    {
                        hasUnpackedIconDir = true;
                        break;
                    }
                }
                
                if (!hasUnpackedIconDir && this.list.Count > 0)
                {
                    Console.WriteLine("检测到没有解包的icon目录，自动开始加载");
                    this.Dispatcher.Invoke(() =>
                    {
                        labErrorMsg.Text = "检测到没有图片文件，正在自动加载...";
                        labErrorMsg.Visibility = Visibility.Visible;
                        picLoding.Visibility = Visibility.Visible;
                    });
                    
                    bwLoadImg = new BackgroundWorker();
                    bwLoadImg.WorkerSupportsCancellation = true;
                    bwLoadImg.DoWork += bw_DoWorkAllIcon;
                    bwLoadImg.RunWorkerCompleted += bw_CompletedWorkAllIcon;
                    bwLoadImg.RunWorkerAsync();
                }
                else
                {
                    Console.WriteLine("已存在解包的icon目录，跳过自动加载");
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
                    picLoding.Visibility = Visibility.Visible;
                    labErrorMsg.Text = "正在加载图片...";
                    labErrorMsg.Visibility = Visibility.Visible;
                });
                
                string cookiesDir = Path.Combine(Environment.CurrentDirectory, this.cookiename);
                string currentDir = Environment.CurrentDirectory;
                
                // 查找resources.exe
                string resourcesExePath = Path.Combine(currentDir, "pack", "resources.exe");
                if (!File.Exists(resourcesExePath))
                {
                    resourcesExePath = Path.Combine(currentDir, "..", "..", "..", "pack", "resources.exe");
                }
                if (!File.Exists(resourcesExePath))
                {
                    resourcesExePath = Path.Combine(Path.GetDirectoryName(System.Reflection.Assembly.GetExecutingAssembly().Location), "..", "..", "..", "pack", "resources.exe");
                }
                
                Console.WriteLine("resources.exe路径: " + resourcesExePath);
                
                if (!File.Exists(resourcesExePath))
                {
                    this.Dispatcher.Invoke(() =>
                    {
                        labErrorMsg.Text = "找不到resources.exe: " + resourcesExePath;
                        labErrorMsg.Visibility = Visibility.Visible;
                        picLoding.Visibility = Visibility.Collapsed;
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
                            labErrorMsg.Text = string.Format("正在解包图片... {0}/{1}", finalCurrentCount, totalCount);
                        });
                    }
                    
                    string pakNum = itemshopM.PakNum.Replace("*", "");
                    string iconDirName = "icon" + pakNum.Replace(".", "_");
                    string iconDir = Path.Combine(cookiesDir, iconDirName);
                    string iconPakName = "icon" + pakNum;
                    
                    if (!Directory.Exists(iconDir))
                    {
                        try
                        {
                            string sourcePath = Path.Combine(this.strInstallDirectory, iconPakName);
                            string destPath = Path.Combine(cookiesDir, iconPakName);
                            
                            if (File.Exists(sourcePath))
                            {
                                if (!File.Exists(destPath))
                                {
                                    File.Copy(sourcePath, destPath, true);
                                }
                                
                                // 直接执行resources.exe解包
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
                    else
                    {
                        skipCount++;
                    }
                }
                
                this.Dispatcher.Invoke(() =>
                {
                    labErrorMsg.Text = string.Format("图片加载完成！成功: {0}, 跳过: {1}", successCount, skipCount);
                    labErrorMsg.Visibility = Visibility.Visible;
                    picLoding.Visibility = Visibility.Collapsed;
                });
            }
            catch (Exception ex)
            {
                this.Dispatcher.Invoke(() =>
                {
                    labErrorMsg.Text = "加载图片失败: " + ex.Message;
                    labErrorMsg.Visibility = Visibility.Visible;
                    picLoding.Visibility = Visibility.Collapsed;
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
                
                // 尝试从多个位置读取配置文件
                string[] configPaths = new string[]
                {
                    Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "config.ini"),
                    Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "..", "..", "..", "config.ini"), // 项目根目录
                    Path.Combine(Environment.CurrentDirectory, "config.ini")
                };
                
                bool configFound = false;
                foreach (string configPath in configPaths)
                {
                    Console.WriteLine("尝试读取配置文件: " + configPath);
                    if (File.Exists(configPath))
                    {
                        Console.WriteLine("配置文件存在");
                        StreamReader streamReader = new StreamReader(configPath, Encoding.Default);
                        string text;
                        while ((text = streamReader.ReadLine()) != null)
                        {
                            this.strInstallDirectory = text.ToString().Trim();
                            Console.WriteLine("读取到游戏目录: " + this.strInstallDirectory);
                        }
                        streamReader.Close();
                        configFound = true;
                        break; // 找到配置文件后退出循环
                    }
                    else
                    {
                        Console.WriteLine("配置文件不存在: " + configPath);
                    }
                }
                
                // 检查路径是否为空
                if (string.IsNullOrEmpty(this.strInstallDirectory))
                {
                    Console.WriteLine("游戏目录为空");
                    
                    // 显示错误消息
                    this.Dispatcher.Invoke(() =>
                    {
                        labErrorMsg.Text = "请先设置游戏安装目录。\n在config.ini文件中添加游戏目录路径。";
                        labErrorMsg.Visibility = Visibility.Visible;
                    });
                }
                else
                {
                    Console.WriteLine("游戏目录: " + this.strInstallDirectory);
                    
                    // 检查游戏目录是否存在
                    if (!Directory.Exists(this.strInstallDirectory))
                    {
                        Console.WriteLine("游戏目录不存在: " + this.strInstallDirectory);
                        
                        // 显示错误消息
                        this.Dispatcher.Invoke(() =>
                        {
                            labErrorMsg.Text = "游戏目录不存在: " + this.strInstallDirectory;
                            labErrorMsg.Visibility = Visibility.Visible;
                        });
                    }
                    else
                    {
                        // 检查item_text.pak文件是否存在
                        string itemTextPakPath = Path.Combine(this.strInstallDirectory, "item_text.pak");
                        if (!File.Exists(itemTextPakPath))
                        {
                            Console.WriteLine("item_text.pak文件不存在: " + itemTextPakPath);
                            
                            // 显示错误消息
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
                // 不检查路径有效性，因为用户确认路径正确
                
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

        // 后台工作线程方法
        private void bwMain_DoLoadList(object sender, DoWorkEventArgs e)
        {
            try
            {
                Console.WriteLine("=== 开始加载服装数据 ===");
                
                // 记录当前工作目录
                Console.WriteLine("当前工作目录: " + Environment.CurrentDirectory);
                
                // 初始化配置
                Console.WriteLine("开始初始化配置...");
                InitializeConfig();
                Console.WriteLine("配置初始化完成，游戏目录: " + this.strInstallDirectory);
                
                // 加载服装数据
                Console.WriteLine("开始加载服装数据...");
                GetNewItem();
                Console.WriteLine("服装数据加载完成，共加载 " + this.list.Count + " 件服装");
                
                Console.WriteLine("=== 服装数据加载流程完成 ===");
            }
            catch (Exception ex)
            {
                Console.WriteLine("加载服装数据时出错: " + ex.Message);
                Console.WriteLine("堆栈跟踪: " + ex.StackTrace);
                
                // 显示错误消息
                this.Dispatcher.Invoke(() =>
                {
                    labErrorMsg.Text = "加载服装数据时出错: " + ex.Message;
                    labErrorMsg.Visibility = Visibility.Visible;
                    picLoding.Visibility = Visibility.Collapsed;
                });
            }
        }

        private void bwMain_CompletedLoadList(object sender, RunWorkerCompletedEventArgs e)
        {
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