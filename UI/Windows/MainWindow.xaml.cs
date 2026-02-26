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
                this.Width = 1400;
                this.Height = 720;
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

        private void lstClothing_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
        {
            // 服装列表点击事件
            // 实现左键添加到变更前，Ctrl+左键添加到变更后
        }

        private void btnConfirm_Click(object sender, RoutedEventArgs e)
        {
            // 确认变更按钮点击事件
        }

        private void btnClear_Click(object sender, RoutedEventArgs e)
        {
            // 清空所有按钮点击事件
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
            // 确保日志文件路径正确
            string logPath = Path.Combine(Environment.CurrentDirectory, "debug.log");
            Console.WriteLine("日志文件路径: " + logPath);
            
            // 清空旧日志
            if (File.Exists(logPath))
            {
                Console.WriteLine("删除旧日志文件");
                File.Delete(logPath);
            }
            
            // 日志记录函数
            Action<string> Log = (message) =>
            {
                string logMessage = $"[{DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss")}] {message}";
                Console.WriteLine(logMessage);
                try
                {
                    File.AppendAllText(logPath, logMessage + "\n");
                }
                catch (Exception ex)
                {
                    Console.WriteLine("写入日志失败: " + ex.Message);
                }
            };
            
            Log("=== 开始加载服装数据 ===");
            Log("当前工作目录: " + Environment.CurrentDirectory);
            Log("应用程序基目录: " + AppDomain.CurrentDomain.BaseDirectory);
            Log("开始加载服装数据");
            
            try
            {
                
                // 使用Dispatcher.Invoke确保UI操作在主线程执行
                this.Dispatcher.Invoke(() =>
                {
                    // 显示加载状态
                    picLoding.Visibility = Visibility.Visible;
                    labErrorMsg.Visibility = Visibility.Collapsed;
                    labErrorMsg.Text = "";
                });
                
                this.list = new List<ItemshopM>();
                Log("创建服装列表成功，初始数量: " + this.list.Count);
                
                // 简化版本：只使用本地安装目录
                Log("当前strInstallDirectory: " + this.strInstallDirectory);
                
                // 检查strInstallDirectory是否为空
                if (string.IsNullOrEmpty(this.strInstallDirectory))
                {
                    Log("游戏目录为空，无法加载服装数据");
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
                Log("源文件路径: " + sourceFileName);
                string destFileName = Path.Combine(Environment.CurrentDirectory, this.cookiename, "item_text.pak");
                Log("目标文件路径: " + destFileName);
                
                // 确保目标目录存在
                string localCookiesPath = Path.Combine(Environment.CurrentDirectory, this.cookiename);
                Log("cookies目录路径: " + localCookiesPath);
                if (!Directory.Exists(localCookiesPath))
                {
                    Log("创建目标目录: " + localCookiesPath);
                    try
                    {
                        Directory.CreateDirectory(localCookiesPath);
                        Log("创建目录成功");
                    }
                    catch (Exception ex)
                    {
                        Log("创建目录失败: " + ex.Message);
                        // 使用Dispatcher.Invoke确保UI操作在主线程执行
                        this.Dispatcher.Invoke(() =>
                        {
                            labErrorMsg.Text = "创建目录失败: " + ex.Message;
                            labErrorMsg.Visibility = Visibility.Visible;
                            picLoding.Visibility = Visibility.Collapsed;
                        });
                        return;
                    }
                }
                else
                {
                    Log("目标目录已存在");
                }
                
                // 检查源文件是否存在
                if (!File.Exists(sourceFileName))
                {
                    Log("源文件不存在: " + sourceFileName);
                    // 使用Dispatcher.Invoke确保UI操作在主线程执行
                    this.Dispatcher.Invoke(() =>
                    {
                        labErrorMsg.Text = "源文件不存在: " + sourceFileName;
                        labErrorMsg.Visibility = Visibility.Visible;
                        picLoding.Visibility = Visibility.Collapsed;
                    });
                    return;
                }
                else
                {
                    Log("源文件存在，大小: " + new FileInfo(sourceFileName).Length + " 字节");
                }
                
                // 检查cookies目录中是否已经有解包后的itemshop.txt文件
                string itemshopPath = Path.Combine(cookiesPath, "item_text_pak", "itemshop.txt");
                if (File.Exists(itemshopPath))
                {
                    Log("cookies目录中已有解包后的itemshop.txt文件，直接使用");
                }
                else
                {
                    // 复制item_text.pak文件到cookies目录
                    Log("cookies目录中没有解包后的文件，开始复制item_text.pak");
                    try
                    {
                        File.Copy(sourceFileName, pakPath, true);
                        Log("复制文件成功: " + sourceFileName + " -> " + pakPath);
                        destFileName = pakPath; // 使用复制到cookies目录的文件
                    }
                    catch (Exception ex)
                    {
                        Log("复制文件失败: " + ex.Message);
                        Log("使用游戏目录中的文件作为备选");
                        destFileName = sourceFileName; // 使用游戏目录中的文件作为备选
                    }
                }
                Log("使用的pak文件路径: " + destFileName);
                
                // 验证文件是否存在
                if (!File.Exists(destFileName))
                {
                    Log("文件不存在，无法解包: " + destFileName);
                    // 使用Dispatcher.Invoke确保UI操作在主线程执行
                    this.Dispatcher.Invoke(() =>
                    {
                        labErrorMsg.Text = "文件不存在，无法解包: " + destFileName;
                        labErrorMsg.Visibility = Visibility.Visible;
                        picLoding.Visibility = Visibility.Collapsed;
                    });
                    return;
                }
                Log("文件存在，开始解包");
                
                // 使用当前工作目录作为基准路径，确保路径一致
                string currentDir = Environment.CurrentDirectory;
                Log("当前工作目录: " + currentDir);
                
                // 统一使用当前工作目录下的cookies目录
                string cookiesPath = Path.Combine(currentDir, this.cookiename);
                Log("统一cookies目录路径: " + cookiesPath);
                string pakPath = Path.Combine(cookiesPath, "item_text.pak");
                Log("统一pak文件路径: " + pakPath);
                
                // 确保cookies目录存在
                if (!Directory.Exists(cookiesPath))
                {
                    Log("创建cookies目录: " + cookiesPath);
                    try
                    {
                        Directory.CreateDirectory(cookiesPath);
                        Log("创建cookies目录成功");
                    }
                    catch (Exception ex)
                    {
                        Log("创建cookies目录失败: " + ex.Message);
                        // 使用Dispatcher.Invoke确保UI操作在主线程执行
                        this.Dispatcher.Invoke(() =>
                        {
                            labErrorMsg.Text = "创建cookies目录失败: " + ex.Message;
                            labErrorMsg.Visibility = Visibility.Visible;
                            picLoding.Visibility = Visibility.Collapsed;
                        });
                        return;
                    }
                }
                else
                {
                    Log("cookies目录已存在");
                }
                
                // 检查resources.exe是否存在
                string resourcesExePath = Path.Combine(currentDir, "..", "..", "..", "pack", "resources.exe");
                Log("resources.exe路径: " + resourcesExePath);
                
                if (!File.Exists(resourcesExePath))
                {
                    // 尝试其他可能的路径
                    resourcesExePath = Path.Combine(Path.GetDirectoryName(System.Reflection.Assembly.GetExecutingAssembly().Location), "..", "..", "..", "pack", "resources.exe");
                    Log("尝试resources.exe路径: " + resourcesExePath);
                    
                    if (!File.Exists(resourcesExePath))
                    {
                        Log("resources.exe不存在: " + resourcesExePath);
                        // 使用Dispatcher.Invoke确保UI操作在主线程执行
                        this.Dispatcher.Invoke(() =>
                        {
                            labErrorMsg.Text = "resources.exe不存在: " + resourcesExePath;
                            labErrorMsg.Visibility = Visibility.Visible;
                            picLoding.Visibility = Visibility.Collapsed;
                        });
                        return;
                    }
                }
                Log("resources.exe存在");
                
                // 检查itemshop.txt文件是否已经存在
                string itemshopPath = Path.Combine(cookiesPath, "item_text_pak", "itemshop.txt");
                if (File.Exists(itemshopPath))
                {
                    Log("itemshop.txt文件已经存在，跳过解包步骤");
                }
                else
                {
                    // 执行解包命令
                    Log("开始执行解包命令");
                    try
                    {
                        Log("创建ProcessStartInfo");
                        ProcessStartInfo processStartInfo = new ProcessStartInfo();
                        processStartInfo.FileName = resourcesExePath;
                        processStartInfo.Arguments = $"\"{destFileName}\" -all";
                        processStartInfo.UseShellExecute = true; // 使用ShellExecute，避免输出流阻塞
                        processStartInfo.CreateNoWindow = true;
                        processStartInfo.WorkingDirectory = currentDir; // 设置工作目录为当前工作目录
                        
                        Log("执行解包命令: " + processStartInfo.FileName + " " + processStartInfo.Arguments);
                        Log("工作目录: " + processStartInfo.WorkingDirectory);
                        
                        Log("启动进程");
                        Process process = Process.Start(processStartInfo);
                        Log("进程启动成功，等待退出");
                        
                        // 等待进程结束，最多等待15秒
                        bool exited = process.WaitForExit(15000);
                        if (exited)
                        {
                            int exitCode = process.ExitCode;
                            Log("解包命令执行完成，退出码: " + exitCode);
                        }
                        else
                        {
                            Log("解包命令执行超时，强制关闭进程");
                            process.Kill();
                        }
                        process.Close();
                        
                        Log("解包命令处理完成");
                    }
                    catch (Exception ex)
                    {
                        Log("执行解包命令失败: " + ex.Message);
                        Log("堆栈跟踪: " + ex.StackTrace);
                        // 即使解包命令执行失败，也继续尝试读取文件，因为可能已经成功解包
                        // 使用Dispatcher.Invoke确保UI操作在主线程执行
                        this.Dispatcher.Invoke(() =>
                        {
                            labErrorMsg.Text = "执行解包命令时出现错误，但将继续尝试读取解包结果: " + ex.Message;
                            labErrorMsg.Visibility = Visibility.Visible;
                        });
                    }
                }
                
                Log("解包命令执行完成，开始检查解包结果");
                
                // 检查解包结果
                Log("检查解析后的文件: " + itemshopPath);
                
                // 检查cookies目录是否存在
                if (!Directory.Exists(cookiesPath))
                {
                    Log("cookies目录不存在: " + cookiesPath);
                }
                else
                {
                    Log("cookies目录存在");
                    // 检查item_text_pak目录是否存在
                    string itemTextPakPath = Path.Combine(cookiesPath, "item_text_pak");
                    if (!Directory.Exists(itemTextPakPath))
                    {
                        Log("item_text_pak目录不存在: " + itemTextPakPath);
                    }
                    else
                    {
                        Log("item_text_pak目录存在");
                        // 列出item_text_pak目录中的文件
                        try
                        {
                            string[] files = Directory.GetFiles(itemTextPakPath);
                            Log("item_text_pak目录中的文件数量: " + files.Length);
                            foreach (string file in files)
                            {
                                Log("文件: " + Path.GetFileName(file));
                            }
                        }
                        catch (Exception ex)
                        {
                            Log("列出文件失败: " + ex.Message);
                        }
                    }
                }
                
                if (File.Exists(itemshopPath))
                {
                    Log("itemshop.txt文件存在，开始解析");
                    Log("itemshop.txt文件大小: " + new FileInfo(itemshopPath).Length + " 字节");
                    
                    int itemCount = 0;
                    int lineCount = 0;
                    try
                    {
                        StreamReader streamReader = new StreamReader(itemshopPath, Encoding.Default);
                        string text;
                        while ((text = streamReader.ReadLine()) != null)
                        {
                            lineCount++;
                            string text2 = text.ToString();
                            Log($"解析第 {lineCount} 行: {text2.Substring(0, Math.Min(50, text2.Length))}...");
                            
                            if (text2.IndexOf("ItemCode") == -1)
                            {
                                string[] array = text2.Split(new string[] { "\t" }, StringSplitOptions.None);
                                Log($"分割后数组长度: {array.Length}");
                                
                                if (array.Length >= 5)
                                {
                                    Log($"数组元素: [0]={array[0]}, [1]={array[1]}, [2]={array[2]}, [3]={array[3]}");
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
                                            Comment = array[3]
                                        });
                                        itemCount++;
                                        Log($"添加服装成功: {array[3]}");
                                    }
                                    else
                                    {
                                        Log($"跳过空名称或--的服装: {array[3]}");
                                    }
                                }
                                else if (array.Length == 4)
                                {
                                    Log($"数组元素: [0]={array[0]}, [1]={array[1]}, [2]={array[2]}, [3]={array[3]}");
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
                                        Log($"添加服装成功: {array[2]}");
                                    }
                                    else
                                    {
                                        Log($"跳过空名称或--的服装: {array[3]}");
                                    }
                                }
                                else
                                {
                                    Log($"跳过数组长度不足的行: {array.Length}");
                                }
                            }
                            else
                            {
                                Log("跳过表头行");
                            }
                        }
                        streamReader.Close();
                        
                        Log("解析完成，共加载 " + itemCount + " 件服装");
                        Log("服装列表总数量: " + this.list.Count);
                    }
                    catch (Exception ex)
                    {
                        Log("解析文件失败: " + ex.Message);
                        Log("堆栈跟踪: " + ex.StackTrace);
                        Log("当前处理到第 " + lineCount + " 行");
                    }
                    
                    // 加载常用物品颜色配置
                    List<string> colorList = new List<string>();
                    try
                    {
                        string oftenitemcodePath = Path.Combine(Environment.CurrentDirectory, this.oftenitemcode);
                        Log("加载常用物品颜色配置: " + oftenitemcodePath);
                        if (File.Exists(oftenitemcodePath))
                        {
                            StreamReader streamReader2 = new StreamReader(oftenitemcodePath, Encoding.Default);
                            string text3;
                            while ((text3 = streamReader2.ReadLine()) != null)
                            {
                                colorList.Add(text3.ToString());
                            }
                            streamReader2.Close();
                            Log("加载常用物品颜色配置成功，共 " + colorList.Count + " 条");
                        }
                        else
                        {
                            Log("常用物品颜色配置文件不存在: " + oftenitemcodePath);
                        }
                    }
                    catch (Exception ex)
                    {
                        Log("加载常用物品颜色配置失败: " + ex.Message);
                    }
                    
                    // 加载修改记录
                    List<string> modifyList = new List<string>();
                    try
                    {
                        string dopaklogPath = Path.Combine(Environment.CurrentDirectory, "dopaklog.ini");
                        Log("加载修改记录: " + dopaklogPath);
                        if (File.Exists(dopaklogPath))
                        {
                            StreamReader streamReader2 = new StreamReader(dopaklogPath, Encoding.Default);
                            string text4;
                            while ((text4 = streamReader2.ReadLine()) != null)
                            {
                                modifyList.Add(text4.ToString());
                            }
                            streamReader2.Close();
                            Log("加载修改记录成功，共 " + modifyList.Count + " 条");
                        }
                        else
                        {
                            Log("修改记录文件不存在: " + dopaklogPath);
                        }
                    }
                    catch (Exception ex)
                    {
                        Log("加载修改记录失败: " + ex.Message);
                    }
                    
                    // 更新物品属性
                    Log("更新物品属性");
                    foreach (ItemshopM item in this.list)
                    {
                        // 设置背景颜色
                        item.RowBackColor = (from o in colorList
                                            where o.IndexOf(item.ItemCode) != -1
                                            select o).FirstOrDefault<string>();
                        
                        // 设置修改后的代码
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
                    Log("更新UI，绑定服装数据到ListView");
                    Log("服装列表数量: " + list.Count);
                    Log("ListView控件是否为空: " + (lstClothing == null));
                    
                    this.Dispatcher.Invoke(() =>
                    {
                        try
                        {
                            Log("开始数据绑定");
                            
                            // 清空ListView
                            lstClothing.Items.Clear();
                            
                            // 绑定服装数据到ListView
                            lstClothing.ItemsSource = null;
                            lstClothing.ItemsSource = list;
                            lstClothing.DisplayMemberPath = "ItemName";
                            
                            Log("数据绑定完成，ListView项目数量: " + lstClothing.Items.Count);
                            Log("ListView显示路径: " + lstClothing.DisplayMemberPath);
                            
                            // 测试：手动添加一个项目验证ListView是否正常
                            if (list.Count == 0)
                            {
                                Log("服装列表为空，添加测试项目");
                                list.Add(new ItemshopM { ItemName = "测试服装" });
                                lstClothing.ItemsSource = list;
                                Log("测试项目添加完成，ListView项目数量: " + lstClothing.Items.Count);
                            }
                            
                            // 显示成功消息
                            labErrorMsg.Text = "服装数据加载成功，共 " + list.Count + " 件服装";
                            labErrorMsg.Visibility = Visibility.Visible;
                            
                            CheckAndLoadImages();
                        }
                        catch (Exception ex)
                        {
                            Log("UI更新失败: " + ex.Message);
                            Log("堆栈跟踪: " + ex.StackTrace);
                            labErrorMsg.Text = "UI更新失败: " + ex.Message;
                            labErrorMsg.Visibility = Visibility.Visible;
                        }
                    });
                }
                else
                {
                    Log("解析后的服装数据文件不存在: " + itemshopPath);
                    // 使用Dispatcher.Invoke确保UI操作在主线程执行
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
                Console.WriteLine("堆栈跟踪: " + ex.StackTrace);
                
                // 写入日志
                try
                {
                    string errorLogPath = Path.Combine(Environment.CurrentDirectory, "debug.log");
                    string logMessage = $"[{DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss")}] {errorMessage}";
                    string stackTraceMessage = $"[{DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss")}] 堆栈跟踪: {ex.StackTrace}";
                    File.AppendAllText(errorLogPath, logMessage + "\n" + stackTraceMessage + "\n");
                }
                catch (Exception logEx)
                {
                    Console.WriteLine("写入错误日志失败: " + logEx.Message);
                }
                
                // 使用Dispatcher.Invoke确保UI操作在主线程执行
                this.Dispatcher.Invoke(() =>
                {
                    // 显示错误消息
                    MessageBox.Show(errorMessage, "错误", MessageBoxButton.OK, MessageBoxImage.Error);
                    
                    // 更新错误状态
                    labErrorMsg.Text = "加载失败: " + ex.Message;
                    labErrorMsg.Visibility = Visibility.Visible;
                });
            }
            finally
            {
                // 使用Dispatcher.Invoke确保UI操作在主线程执行
                this.Dispatcher.Invoke(() =>
                {
                    // 隐藏加载状态
                    picLoding.Visibility = Visibility.Collapsed;
                    
                    // 写入日志
                    try
                    {
                        string logPath = Path.Combine(Environment.CurrentDirectory, "debug.log");
                        string logMessage = $"[{DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss")}] 加载流程完成，最终服装数量: {this.list.Count}";
                        File.AppendAllText(logPath, logMessage + "\n");
                    }
                    catch (Exception logEx)
                    {
                        Console.WriteLine("写入完成日志失败: " + logEx.Message);
                    }
                });
            }
        }
        
        // 检查并加载图片
        private void CheckAndLoadImages()
        {
            try
            {
                // 检查是否存在图片目录
                DirectoryInfo directoryInfo = new DirectoryInfo(Environment.CurrentDirectory + "\\" + this.cookiename);
                bool hasIconFiles = false;
                
                foreach (FileInfo fileInfo in directoryInfo.GetFiles())
                {
                    if (fileInfo.Name.IndexOf("icon") != -1)
                    {
                        hasIconFiles = true;
                        break;
                    }
                }
                
                // 如果没有图片文件，自动加载图片
                if (!hasIconFiles && this.list.Count > 0)
                {
                    Console.WriteLine("检测到没有图片文件，自动开始加载");
                    // 使用Dispatcher.Invoke确保UI操作在主线程执行
                    this.Dispatcher.Invoke(() =>
                    {
                        labErrorMsg.Text = "检测到没有图片文件，正在自动加载...";
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
                // 显示加载状态
                this.Dispatcher.Invoke(() =>
                {
                    picLoding.Visibility = Visibility.Visible;
                    labErrorMsg.Text = "正在加载图片...";
                    labErrorMsg.Visibility = Visibility.Visible;
                });
                
                // 检查服装列表是否为空
                if (this.list == null || this.list.Count == 0)
                {
                    throw new InvalidOperationException("服装列表为空，请先加载服装数据");
                }
                
                // 获取唯一的PakNum列表
                List<FS服装搭配专家v1._0.ItemshopM> distinctList = this.list.Distinct(new ItemshopMComparer()).ToList<FS服装搭配专家v1._0.ItemshopM>();
                int totalCount = distinctList.Count;
                int currentCount = 0;
                
                // 确保日志文件路径正确
                string logPath = Path.Combine(Environment.CurrentDirectory, "debug.log");
                Action<string> Log = (message) =>
                {
                    string logMessage = $"[{DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss")}] {message}";
                    Console.WriteLine(logMessage);
                    try
                    {
                        File.AppendAllText(logPath, logMessage + "\n");
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine("写入日志失败: " + ex.Message);
                    }
                };
                
                Log("开始加载图片，共 " + totalCount + " 个不同的icon pak文件");
                
                foreach (FS服装搭配专家v1._0.ItemshopM itemshopM in distinctList)
                {
                    currentCount++;
                    
                    // 更新加载状态
                    this.Dispatcher.Invoke(() =>
                    {
                        labErrorMsg.Text = string.Format("正在加载图片... {0}/{1}", currentCount, totalCount);
                    });
                    
                    string iconDir = Path.Combine(Environment.CurrentDirectory, this.cookiename, "icon" + itemshopM.PakNum.Replace(".", "_").Replace("*", ""));
                    Log("检查icon目录: " + iconDir);
                    
                    if (!Directory.Exists(iconDir))
                    {
                        string iconPakName = "icon" + itemshopM.PakNum.Replace("*", "");
                        Log("处理icon pak文件: " + iconPakName);
                        try
                        {
                            // 构建源文件和目标文件路径
                            string sourcePath = Path.Combine(this.strInstallDirectory, iconPakName);
                            string destPath = Path.Combine(Environment.CurrentDirectory, this.cookiename, iconPakName);
                            
                            Log("源文件路径: " + sourcePath);
                            Log("目标文件路径: " + destPath);
                            
                            // 检查源文件是否存在
                            if (File.Exists(sourcePath))
                            {
                                // 确保目标目录存在
                                string cookiesDir = Path.Combine(Environment.CurrentDirectory, this.cookiename);
                                if (!Directory.Exists(cookiesDir))
                                {
                                    Log("创建cookies目录: " + cookiesDir);
                                    Directory.CreateDirectory(cookiesDir);
                                }
                                
                                // 复制文件
                                Log("复制文件: " + sourcePath + " -> " + destPath);
                                File.Copy(sourcePath, destPath, true);
                                Log("文件复制成功");
                                
                                // 提取图片
                                if (File.Exists(destPath))
                                {
                                    Log("开始解包icon pak文件: " + destPath);
                                    
                                    // 构建resources.exe路径
                                    string resourcesExePath = Path.Combine(Environment.CurrentDirectory, "..", "..", "..", "pack", "resources.exe");
                                    if (!File.Exists(resourcesExePath))
                                    {
                                        resourcesExePath = Path.Combine(Path.GetDirectoryName(System.Reflection.Assembly.GetExecutingAssembly().Location), "..", "..", "..", "pack", "resources.exe");
                                    }
                                    
                                    if (File.Exists(resourcesExePath))
                                    {
                                        // 执行解包命令
                                        ProcessStartInfo processStartInfo = new ProcessStartInfo();
                                        processStartInfo.FileName = resourcesExePath;
                                        processStartInfo.Arguments = $"\"{destPath}\" -byname .+\\.png";
                                        processStartInfo.UseShellExecute = false;
                                        processStartInfo.RedirectStandardInput = true;
                                        processStartInfo.RedirectStandardOutput = true;
                                        processStartInfo.RedirectStandardError = true;
                                        processStartInfo.CreateNoWindow = true;
                                        processStartInfo.WorkingDirectory = Environment.CurrentDirectory;
                                        
                                        Log("执行解包命令: " + processStartInfo.FileName + " " + processStartInfo.Arguments);
                                        
                                        Process process = Process.Start(processStartInfo);
                                        string output = process.StandardOutput.ReadToEnd();
                                        string error = process.StandardError.ReadToEnd();
                                        process.WaitForExit();
                                        int exitCode = process.ExitCode;
                                        process.Close();
                                        
                                        Log("解包命令输出: " + output);
                                        if (!string.IsNullOrEmpty(error))
                                        {
                                            Log("解包命令错误: " + error);
                                        }
                                        Log("解包命令执行完成，退出码: " + exitCode);
                                    }
                                    else
                                    {
                                        Log("resources.exe不存在: " + resourcesExePath);
                                    }
                                }
                                else
                                {
                                    Log("复制后文件不存在: " + destPath);
                                }
                            }
                            else
                            {
                                Log("图片文件不存在: " + sourcePath);
                            }
                        }
                        catch (Exception ex)
                        {
                            Log("加载图片失败: " + ex.Message);
                            Log("堆栈跟踪: " + ex.StackTrace);
                        }
                    }
                    else
                    {
                        Log("icon目录已存在，跳过: " + iconDir);
                    }
                }
                
                Log("图片加载完成，共处理 " + totalCount + " 个icon pak文件");
                
                // 加载完成
                this.Dispatcher.Invoke(() =>
                {
                    labErrorMsg.Text = "图片加载完成！";
                    labErrorMsg.Visibility = Visibility.Visible;
                    
                    // 显示完成消息
                    MessageBox.Show("图片加载完成！", "完成", MessageBoxButton.OK, MessageBoxImage.Information);
                    
                    // 隐藏加载状态
                    picLoding.Visibility = Visibility.Collapsed;
                });
            }
            catch (Exception ex)
            {
                Console.WriteLine("加载图片失败: " + ex.Message);
                Console.WriteLine("堆栈跟踪: " + ex.StackTrace);
                
                // 显示错误消息
                this.Dispatcher.Invoke(() =>
                {
                    MessageBox.Show("加载图片失败: " + ex.Message, "错误", MessageBoxButton.OK, MessageBoxImage.Error);
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