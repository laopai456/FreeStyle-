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
            bwMain.RunWorkerAsync();
        }

        // 核心业务逻辑方法

        // 加载服装数据
        public void GetNewItem()
        {
            try
            {
                // 清空旧日志
                string logPath = "debug.log";
                if (File.Exists(logPath))
                {
                    File.Delete(logPath);
                }
                
                // 日志记录函数
                Action<string> Log = (message) =>
                {
                    string logMessage = $"[{DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss")}] {message}";
                    Console.WriteLine(logMessage);
                    File.AppendAllText(logPath, logMessage + "\n");
                };
                
                Log("开始加载服装数据");
                
                // 使用Dispatcher.Invoke确保UI操作在主线程执行
                this.Dispatcher.Invoke(() =>
                {
                    // 显示加载状态
                    picLoding.Visibility = Visibility.Visible;
                    labErrorMsg.Visibility = Visibility.Collapsed;
                    labErrorMsg.Text = "";
                });
                
                this.list = new List<ItemshopM>();
                
                // 简化版本：只使用本地安装目录
                Log("当前strInstallDirectory: " + this.strInstallDirectory);
                string sourceFileName = Path.Combine(this.strInstallDirectory, "item_text.pak");
                Log("源文件路径: " + sourceFileName);
                string destFileName = this.cookiename + "\\item_text.pak";
                Log("目标文件路径: " + destFileName);
                
                // 确保目标目录存在
                if (!Directory.Exists(this.cookiename))
                {
                    Log("创建目标目录: " + this.cookiename);
                    Directory.CreateDirectory(this.cookiename);
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
                
                // 复制文件
                try
                {
                    Log("尝试复制文件: " + sourceFileName + " -> " + destFileName);
                    File.Copy(sourceFileName, destFileName, true);
                    Log("文件复制成功");
                }
                catch (Exception ex)
                {
                    Log("文件复制失败: " + ex.Message);
                    // 使用Dispatcher.Invoke确保UI操作在主线程执行
                    this.Dispatcher.Invoke(() =>
                    {
                        labErrorMsg.Text = "文件复制失败: " + ex.Message;
                        labErrorMsg.Visibility = Visibility.Visible;
                        picLoding.Visibility = Visibility.Collapsed;
                    });
                    return;
                }
                
                // 提取数据
                // 使用应用程序根目录作为基准路径，确保便携性
                string appBasePath = Path.GetDirectoryName(System.Reflection.Assembly.GetExecutingAssembly().Location);
                string projectRootPath = Path.GetFullPath(Path.Combine(appBasePath, "..", "..", ".."));
                
                // 简化路径结构，将cookies目录放在项目根目录
                string projectCookiesPath = Path.Combine(projectRootPath, this.cookiename);
                string projectPakPath = Path.Combine(projectCookiesPath, "item_text.pak");
                string resourcesExePath = Path.Combine(projectRootPath, "pack", "resources.exe");
                
                // 确保项目根目录的cookies目录存在
                if (!Directory.Exists(projectCookiesPath))
                {
                    Log("创建项目根目录cookies: " + projectCookiesPath);
                    Directory.CreateDirectory(projectCookiesPath);
                }
                
                // 复制文件到项目根目录的cookies
                try
                {
                    Log("尝试复制文件到项目根目录: " + sourceFileName + " -> " + projectPakPath);
                    File.Copy(sourceFileName, projectPakPath, true);
                    Log("文件复制到项目根目录成功");
                }
                catch (Exception ex)
                {
                    Log("文件复制到项目根目录失败: " + ex.Message);
                }
                
                Log("resources.exe路径: " + resourcesExePath);
                Log("pak文件路径: " + projectPakPath);
                
                // 执行解包命令并获取输出
                try
                {
                    ProcessStartInfo processStartInfo = new ProcessStartInfo();
                    processStartInfo.FileName = resourcesExePath;
                    processStartInfo.Arguments = $"\"{projectPakPath}\" -all";
                    processStartInfo.UseShellExecute = false;
                    processStartInfo.RedirectStandardInput = true;
                    processStartInfo.RedirectStandardOutput = true;
                    processStartInfo.RedirectStandardError = true;
                    processStartInfo.CreateNoWindow = true;
                    processStartInfo.WorkingDirectory = projectRootPath; // 设置工作目录为项目根目录
                    
                    Log("执行解包命令: " + processStartInfo.FileName + " " + processStartInfo.Arguments);
                    Log("工作目录: " + processStartInfo.WorkingDirectory);
                    
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
                catch (Exception ex)
                {
                    Log("执行解包命令失败: " + ex.Message);
                }
                
                // 检查解包结果
                string itemshopPath = Path.Combine(projectCookiesPath, "item_text_pak", "itemshop.txt");
                Log("检查解析后的文件: " + itemshopPath);
                if (File.Exists(itemshopPath))
                {
                    StreamReader streamReader = new StreamReader(itemshopPath, Encoding.Default);
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
                                            projectRootPath,
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
                                            projectRootPath,
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
                                }
                            }
                        }
                    }
                    streamReader.Close();
                    
                    // 加载常用物品颜色配置
                    List<string> colorList = new List<string>();
                    try
                    {
                        if (File.Exists(this.oftenitemcode))
                        {
                            StreamReader streamReader2 = new StreamReader(this.oftenitemcode, Encoding.Default);
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
                        if (File.Exists("dopaklog.ini"))
                        {
                            StreamReader streamReader2 = new StreamReader("dopaklog.ini", Encoding.Default);
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
                    this.Dispatcher.Invoke(() =>
                    {
                        CheckAndLoadImages();
                    });
                }
                else
                {
                    throw new FileNotFoundException("解析后的服装数据文件不存在", itemshopPath);
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine("加载服装数据失败: " + ex.Message);
                Console.WriteLine("堆栈跟踪: " + ex.StackTrace);
                
                // 使用Dispatcher.Invoke确保UI操作在主线程执行
                this.Dispatcher.Invoke(() =>
                {
                    // 显示错误消息
                    MessageBox.Show("加载服装数据失败: " + ex.Message, "错误", MessageBoxButton.OK, MessageBoxImage.Error);
                    
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
                
                // 如果没有图片文件，提示用户
                if (!hasIconFiles && this.list.Count > 0)
                {
                    Console.WriteLine("检测到没有图片文件");
                    // 使用Dispatcher.Invoke确保UI操作在主线程执行
                    this.Dispatcher.Invoke(() =>
                    {
                        labErrorMsg.Text = "提示: 请点击'加载图片'按钮获取服装图标";
                        labErrorMsg.Visibility = Visibility.Visible;
                    });
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
                
                foreach (FS服装搭配专家v1._0.ItemshopM itemshopM in distinctList)
                {
                    currentCount++;
                    
                    // 更新加载状态
                    this.Dispatcher.Invoke(() =>
                    {
                        labErrorMsg.Text = string.Format("正在加载图片... {0}/{1}", currentCount, totalCount);
                    });
                    
                    string iconDir = this.cookiename + "\\icon" + itemshopM.PakNum.Replace(".", "_").Replace("*", "");
                    if (!Directory.Exists(iconDir))
                    {
                        string iconPakName = "icon" + itemshopM.PakNum.Replace("*", "");
                        try
                        {
                            // 简化版本：只使用本地安装目录
                            string sourcePath = this.strInstallDirectory + "\\" + iconPakName;
                            string destPath = this.cookiename + "\\" + iconPakName;
                            
                            // 检查源文件是否存在
                            if (File.Exists(sourcePath))
                            {
                                // 确保目标目录存在
                                if (!Directory.Exists(this.cookiename))
                                {
                                    Directory.CreateDirectory(this.cookiename);
                                }
                                
                                // 复制文件
                                File.Copy(sourcePath, destPath, true);
                                
                                // 提取图片
                                string extractPath = string.Concat(new string[]
                                {
                                    Environment.CurrentDirectory,
                                    "\\",
                                    this.cookiename,
                                    "\\",
                                    iconPakName
                                });
                                
                                if (File.Exists(extractPath))
                                {
                                    string extractCmd = "pack\\resources \"" + extractPath + "\" -byname .+\\.png";
                                    conmon.RunCmd(extractCmd);
                                }
                            }
                            else
                            {
                                Console.WriteLine("图片文件不存在: " + sourcePath);
                            }
                        }
                        catch (Exception ex)
                        {
                            Console.WriteLine("加载图片失败: " + ex.Message);
                            Console.WriteLine("堆栈跟踪: " + ex.StackTrace);
                        }
                    }
                }
                
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
                // 尝试从多个位置读取配置文件
                string[] configPaths = new string[]
                {
                    Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "config.ini"),
                    Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "..", "..", "..", "config.ini"), // 项目根目录
                    Path.Combine(Environment.CurrentDirectory, "config.ini")
                };
                
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
                    MessageBox.Show("请先设置游戏安装目录。\n在config.ini文件中添加游戏目录路径。", "提示", MessageBoxButton.OK, MessageBoxImage.Information);
                }
                else
                {
                    Console.WriteLine("游戏目录: " + this.strInstallDirectory);
                }
                // 不检查路径有效性，因为用户确认路径正确
                
                // 创建必要的目录
                if (!Directory.Exists(this.cookiename))
                {
                    Directory.CreateDirectory(this.cookiename);
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine("初始化配置失败: " + ex.Message);
                MessageBox.Show("初始化配置失败: " + ex.Message, "错误", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        // 后台工作线程方法
        private void bwMain_DoLoadList(object sender, DoWorkEventArgs e)
        {
            InitializeConfig();
            GetNewItem();
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