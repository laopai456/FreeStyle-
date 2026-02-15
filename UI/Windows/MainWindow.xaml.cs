using System;
using System.Collections.Generic;
using System.Windows;
using System.Windows.Media;
using System.IO;
using System.Linq;
using System.Diagnostics;
using System.ComponentModel;
using System.Text;

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
                // 调用InitializeComponent
                InitializeComponent();
                
                // 设置窗口属性
                this.Width = 1440;
                this.Height = 1080;
                this.WindowStartupLocation = WindowStartupLocation.CenterScreen;
                this.WindowState = WindowState.Normal;
                this.Visibility = Visibility.Visible;
                
                // 初始化皮肤管理器
                skinManager = new SkinManager();
                
                // 显示初始化提示
                labErrorMsg.Text = "正在初始化配置...";
                labErrorMsg.Visibility = Visibility.Visible;
                
                // 直接调用InitializeConfig，不使用后台线程
                InitializeConfig();
            }
            catch (Exception ex)
            {
                // 显示错误消息
                MessageBox.Show($"主窗口初始化失败: {ex.Message}", "初始化错误", MessageBoxButton.OK, MessageBoxImage.Error);
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

        private void MainWindow_Loaded(object sender, RoutedEventArgs e)
        {
            try
            {
                // 在后台线程中加载服装数据
                System.Threading.ThreadPool.QueueUserWorkItem((state) =>
                {
                    try
                    {
                        // 加载服装数据
                        GetNewItem();
                    }
                    catch (Exception ex)
                    {
                        // 显示错误消息
                        this.Dispatcher.Invoke(() =>
                        {
                            MessageBox.Show($"加载服装数据出错: {ex.Message}", "错误", MessageBoxButton.OK, MessageBoxImage.Error);
                        });
                    }
                });
            }
            catch (Exception ex)
            {
                // 显示错误消息
                MessageBox.Show($"Loaded事件处理出错: {ex.Message}", "错误", MessageBoxButton.OK, MessageBoxImage.Error);
            }
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
        
        // 手动加载服装数据按钮点击事件
        private void btnLoadData_Click(object sender, RoutedEventArgs e)
        {
            try
            {
                // 显示加载提示
                this.Dispatcher.Invoke(() =>
                {
                    labErrorMsg.Text = "正在加载服装数据...请稍候";
                    labErrorMsg.Visibility = Visibility.Visible;
                    picLoding.Visibility = Visibility.Visible;
                });
                
                // 初始化配置
                InitializeConfig();
                
                // 加载服装数据
                GetNewItem();
            }
            catch (Exception ex)
            {
                Console.WriteLine("加载服装数据按钮点击事件出错: " + ex.Message);
                this.Dispatcher.Invoke(() =>
                {
                    labErrorMsg.Text = "加载服装数据失败: " + ex.Message;
                    labErrorMsg.Visibility = Visibility.Visible;
                    picLoding.Visibility = Visibility.Collapsed;
                });
            }
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
                
                // 检查搭配信息
                if (tsbBeforeInfo.Text.Trim() == "beforeInfo")
                {
                    MessageBox.Show("请先选择搭配的‘当前装备’，然后使用搭配功能！");
                    return;
                }
                
                if (tsbAfterInfo.Text.Trim() == "afterinfo")
                {
                    MessageBox.Show("请先选择搭配的‘目标装备’，然后使用搭配功能！");
                    return;
                }
                
                if (tsbAfterInfo.Text.Trim() == tsbBeforeInfo.Text.Trim())
                {
                    MessageBox.Show("搭配的‘当前装备’和‘目标装备’不能相同！");
                    return;
                }
                
                // 确认操作
                string beforeName = tsbBeforeInfo.Text.Split(new char[] { '-' })[0];
                string afterName = tsbAfterInfo.Text.Split(new char[] { '-' })[0];
                
                string confirmMsg = string.Concat(new string[]
                {
                    "确认要将‘",
                    beforeName,
                    "’替换为‘",
                    afterName,
                    "’吗？\n注意：一定要先关闭游戏再操作！"
                });
                
                if (MessageBox.Show(confirmMsg, "确认", MessageBoxButton.OKCancel, MessageBoxImage.Question) == MessageBoxResult.Cancel)
                {
                    return;
                }
                
                // 显示加载状态
                picLoding.Visibility = Visibility.Visible;
                labErrorMsg.Text = "正在更新搭配...";
                labErrorMsg.Visibility = Visibility.Visible;
                
                // 启动后台线程执行搭配更新
                bwLast = new BackgroundWorker();
                bwLast.WorkerSupportsCancellation = true;
                bwLast.DoWork += bw_DoWorkLast;
                bwLast.RunWorkerCompleted += bw_CompletedWorkLast;
                bwLast.RunWorkerAsync();
            }
            catch (Exception ex)
            {
                Console.WriteLine("更新搭配失败: " + ex.Message);
                Console.WriteLine("堆栈跟踪: " + ex.StackTrace);
                MessageBox.Show("更新搭配失败: " + ex.Message);
                picLoding.Visibility = Visibility.Collapsed;
            }
        }
        
        // 执行搭配更新
        private void bw_DoWorkLast(object sender, DoWorkEventArgs e)
        {
            try
            {
                string strAfterPak = "";
                string strAfterMod = "";
                string strBeforePak = "";
                string strBeforeMod = "";
                
                // 解析搭配信息
                strAfterPak = tsbAfterInfo.Text.Split(new char[] { ',' })[0].Split(new char[] { ':' })[1].Replace(".", "_");
                strAfterMod = tsbAfterInfo.Text.Split(new char[] { ',' })[1].Split(new char[] { ':' })[1];
                strAfterEffCode = tsbAfterInfo.Text.Split(new char[] { ',' })[2].Split(new char[] { ':' })[1].Replace("无", "");
                
                strBeforePak = tsbBeforeInfo.Text.Split(new char[] { ',' })[0].Split(new char[] { ':' })[1].Replace(".", "_");
                strBeforeMod = tsbBeforeInfo.Text.Split(new char[] { ',' })[1].Split(new char[] { ':' })[1];
                strBeforeEffCode = tsbBeforeInfo.Text.Split(new char[] { ',' })[2].Split(new char[] { ':' })[1].Replace("无", "");
                
                // 复制模板文件
                string sourceFileName = string.Concat(new string[]
                {
                    Environment.CurrentDirectory,
                    "\\",
                    "cookies",
                    "\\",
                    strAfterPak,
                    "\\",
                    strAfterMod
                });
                
                string destFileName = string.Concat(new string[]
                {
                    Environment.CurrentDirectory,
                    "\\cookies\\",
                    strBeforePak,
                    "\\",
                    strBeforeMod
                });
                
                // 确保目标目录存在
                string destDir = Path.GetDirectoryName(destFileName);
                if (!Directory.Exists(destDir))
                {
                    Directory.CreateDirectory(destDir);
                }
                
                // 复制文件
                File.Copy(sourceFileName, destFileName, true);
                
                // 重新打包
                string packCmd = string.Concat(new string[]
                {
                    "pack\\resources -file2pak \"",
                    Environment.CurrentDirectory,
                    "\\cookies\\",
                    strBeforePak,
                    "\" \"",
                    this.strInstallDirectory,
                    "\\",
                    strBeforePak.Replace("_", "."),
                    "\""
                });
                conmon.RunCmd(packCmd);
                
                // 处理特效代码
                ProcessEffectCode();
            }
            catch (Exception ex)
            {
                Console.WriteLine("执行搭配更新失败: " + ex.Message);
                Console.WriteLine("堆栈跟踪: " + ex.StackTrace);
                throw;
            }
        }
        
        // 搭配更新完成
        private void bw_CompletedWorkLast(object sender, RunWorkerCompletedEventArgs e)
        {
            try
            {
                picLoding.Visibility = Visibility.Collapsed;
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
                
                // 记录操作日志
                RecordModifyLog();
                
                // 刷新服装数据
                GetNewItem();
            }
            catch (Exception ex)
            {
                Console.WriteLine("搭配更新完成处理失败: " + ex.Message);
            }
        }
        
        // 处理特效代码
        private void ProcessEffectCode()
        {
            try
            {
                if (string.IsNullOrEmpty(strBeforeEffCode) && string.IsNullOrEmpty(strAfterEffCode))
                {
                    iseffok = false;
                    return;
                }
                
                // 获取特效代码
                string beforeEff = string.IsNullOrEmpty(strBeforeEffCode) ? "无" : strBeforeEffCode;
                string afterEff = string.IsNullOrEmpty(strAfterEffCode) ? "无" : strAfterEffCode;
                
                // 确认是否更新特效
                bool updateEffect = false;
                labErrorMsg.Dispatcher.Invoke(() =>
                {
                    updateEffect = (MessageBox.Show(string.Concat(new string[]
                    {
                        "注意:此处仅为替换装备特效\n是否要将特效",
                        beforeEff,
                        "替换为特效",
                        afterEff,
                        "？\n点击确定将替换，取消将不替换特效"
                    }), "确认", MessageBoxButton.OKCancel) == MessageBoxResult.OK);
                });
                
                if (!updateEffect)
                {
                    iseffok = false;
                    return;
                }
                
                // 解析搭配信息获取必要的变量
                string strBeforeMod = "";
                string strBeforePak = "";
                
                if (!string.IsNullOrEmpty(tsbBeforeInfo.Text))
                {
                    string[] beforeParts = tsbBeforeInfo.Text.Split(new char[] { ',' });
                    if (beforeParts.Length > 1)
                    {
                        strBeforeMod = beforeParts[1].Split(new char[] { ':' })[1];
                    }
                    if (beforeParts.Length > 0)
                    {
                        strBeforePak = beforeParts[0].Split(new char[] { ':' })[1];
                    }
                }
                
                // 解析物品代码
                string beforeCode = strBeforeMod.Replace(".bml", "").Replace("i", "");
                string pakNum = strBeforePak.Replace("_pak", "").Replace("item", "");
                if (string.IsNullOrEmpty(pakNum))
                {
                    pakNum = "1";
                }
                
                // 构建替换文本
                string oldValue = beforeCode + "\t" + pakNum + "\t" + strBeforeEffCode + "\t";
                string newValue = beforeCode + "\t" + pakNum + "\t" + strAfterEffCode + "\t";
                
                // 读取itemshop.txt
                string itemshopPath = Environment.CurrentDirectory + "\\cookies\\item_text_pak\\itemshop.txt";
                if (File.Exists(itemshopPath))
                {
                    string content = File.ReadAllText(itemshopPath, Encoding.Default);
                    
                    // 检查物品是否存在
                    if (!content.Contains(beforeCode))
                    {
                        // 物品不存在，添加新记录
                        using (StreamWriter writer = new StreamWriter(itemshopPath, true, Encoding.Default))
                        {
                            writer.WriteLine(newValue + tsbBeforeInfo.Text.Split(new char[] { '-' })[0] + "\t装备相同但不同颜色装备，模板替换特效代码\t");
                        }
                    }
                    else
                    {
                        // 物品存在，替换特效代码
                        content = content.Replace(oldValue, newValue);
                        File.WriteAllText(itemshopPath, content, Encoding.Default);
                    }
                    
                    // 重新打包item_text.pak
                    string packCmd = string.Concat(new string[]
                    {
                        "pack\\resources -file2pak \"",
                        Environment.CurrentDirectory,
                        "\\cookies\\item_text_pak",
                        "\" \"",
                        this.strInstallDirectory,
                        "\\item_text.pak",
                        "\""
                    });
                    conmon.RunCmd(packCmd);
                    
                    iseffok = true;
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine("处理特效代码失败: " + ex.Message);
                iseffok = false;
            }
        }
        
        // 记录修改日志
        private void RecordModifyLog()
        {
            try
            {
                List<string> existingLogs = new List<string>();
                
                // 读取现有日志
                if (File.Exists("dopaklog.ini"))
                {
                    using (StreamReader reader = new StreamReader("dopaklog.ini", Encoding.Default))
                    {
                        string line;
                        while ((line = reader.ReadLine()) != null)
                        {
                            if (line.IndexOf("#") != -1)
                            {
                                existingLogs.Add(line.Split(new char[] { '#' })[0]);
                            }
                        }
                    }
                }
                
                // 解析搭配信息
                string beforeCode = tsbBeforeInfo.Text.Split(new char[] { ',' })[1].Split(new char[] { ':' })[1].Replace("i", "").Replace(".bml", "");
                string afterCode = tsbAfterInfo.Text.Split(new char[] { ',' })[1].Split(new char[] { ':' })[1].Replace("i", "").Replace(".bml", "");
                
                // 检查是否已存在
                if (!existingLogs.Contains(beforeCode))
                {
                    // 添加新日志
                    using (StreamWriter writer = new StreamWriter("dopaklog.ini", true, Encoding.Default))
                    {
                        writer.WriteLine(beforeCode + "#" + afterCode);
                    }
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine("记录修改日志失败: " + ex.Message);
            }
        }
        
        private void InitializeItemList()
        {
            try
            {
                // 写入日志文件
                string logFilePath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "init.log");
                using (StreamWriter writer = new StreamWriter(logFilePath, true))
                {
                    writer.WriteLine($"[{DateTime.Now}] 开始InitializeItemList方法");
                }
                
                // 初始化后台工作线程
                bwMain = new BackgroundWorker();
                bwMain.WorkerSupportsCancellation = true;
                bwMain.DoWork += bwMain_DoLoadList;
                bwMain.RunWorkerCompleted += bwMain_CompletedLoadList;
                
                // 写入日志文件
                using (StreamWriter writer = new StreamWriter(logFilePath, true))
                {
                    writer.WriteLine($"[{DateTime.Now}] 启动bwMain后台线程");
                }
                
                bwMain.RunWorkerAsync();
            }
            catch (Exception ex)
            {
                // 写入日志文件
                string logFilePath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "init.log");
                using (StreamWriter writer = new StreamWriter(logFilePath, true))
                {
                    writer.WriteLine($"[{DateTime.Now}] InitializeItemList方法出错: {ex.Message}");
                    writer.WriteLine($"[{DateTime.Now}] 堆栈跟踪: {ex.StackTrace}");
                }
            }
        }

        // 核心业务逻辑方法

        // 加载服装数据
        public void GetNewItem()
        {
            try
            {
                // 移除加载提示，实现静默加载
                this.Dispatcher.Invoke(() =>
                {
                    // 隐藏加载状态
                    picLoding.Visibility = Visibility.Collapsed;
                    labErrorMsg.Visibility = Visibility.Collapsed;
                });
                
                this.list = new List<ItemshopM>();
                
                // 简化版本：只使用本地安装目录
                string appBaseDir = AppDomain.CurrentDomain.BaseDirectory;
                string sourceFileName = Path.Combine(this.strInstallDirectory, "item_text.pak");
                string destFileName = Path.Combine(appBaseDir, this.cookiename, "item_text.pak");
                
                // 确保目标目录存在
                string cookiesDir = Path.Combine(appBaseDir, this.cookiename);
                if (!Directory.Exists(cookiesDir))
                {
                    Directory.CreateDirectory(cookiesDir);
                }
                
                // 检查源文件是否存在
                if (!File.Exists(sourceFileName))
                {
                    // 显示友好的错误提示
                    this.Dispatcher.Invoke(() =>
                    {
                        labErrorMsg.Text = "服装数据文件不存在，请先设置游戏安装目录";
                        labErrorMsg.Visibility = Visibility.Visible;
                        picLoding.Visibility = Visibility.Collapsed;
                    });
                    return;
                }
                
                // 尝试复制文件，处理文件锁定情况
                bool copied = false;
                int retryCount = 0;
                while (!copied && retryCount < 3)
                {
                    try
                    {
                        // 检查目标文件是否存在，如果存在则尝试删除
                        if (File.Exists(destFileName))
                        {
                            try
                            {
                                File.Delete(destFileName);
                            }
                            catch { }
                        }
                        
                        // 复制文件
                        File.Copy(sourceFileName, destFileName, true);
                        copied = true;
                    }
                    catch
                    {
                        retryCount++;
                        System.Threading.Thread.Sleep(500); // 减少等待时间
                    }
                }
                
                if (!copied)
                {
                    // 显示友好的错误提示
                    this.Dispatcher.Invoke(() =>
                    {
                        labErrorMsg.Text = "无法复制文件，请确保文件未被其他进程使用，然后重试";
                        labErrorMsg.Visibility = Visibility.Visible;
                        picLoding.Visibility = Visibility.Collapsed;
                    });
                    return;
                }
                
                // 提取数据
                string extractCmd = string.Concat(new string[]
                {
                    "pack\\resources ",
                    "\"",
                    Path.Combine(appBaseDir, this.cookiename, "item_text.pak"),
                    "\"",
                    " -all"
                });
                
                // 检查pack目录是否存在
                string packDir = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "pack");
                if (!Directory.Exists(packDir))
                {
                    // 显示友好的错误提示
                    this.Dispatcher.Invoke(() =>
                    {
                        labErrorMsg.Text = "pack目录不存在，请确保pack\\resources.exe工具存在且可执行";
                        labErrorMsg.Visibility = Visibility.Visible;
                        picLoding.Visibility = Visibility.Collapsed;
                    });
                    return;
                }
                
                // 执行提取命令
                try
                {
                    conmon.RunCmd(extractCmd);

                }
                catch (Exception ex)
                {

                    // 显示友好的错误提示
                    this.Dispatcher.Invoke(() =>
                    {
                        labErrorMsg.Text = "提取数据失败，请确保pack\resources.exe工具存在且可执行";
                        labErrorMsg.Visibility = Visibility.Visible;
                        picLoding.Visibility = Visibility.Collapsed;
                    });
                    return;
                }
                
                // 读取并解析服装数据
                string itemshopPath = Path.Combine(appBaseDir, this.cookiename, "item_text_pak", "itemshop.txt");
                
                // 尝试打开文件并解析
                using (StreamReader streamReader = new StreamReader(itemshopPath, Encoding.Default))
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
                                        PakNum = array[1],
                                        ImgPath = string.Concat(new string[]
                                        {
                                            appBaseDir,
                                            this.cookiename,
                                            "\\icon",
                                            array[1],
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
                                            appBaseDir,
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
                    
                    // 加载常用物品颜色配置
                    List<string> colorList = new List<string>();
                    try
                    {
                        if (File.Exists(this.oftenitemcode))
                        {
                            using (StreamReader streamReader2 = new StreamReader(this.oftenitemcode, Encoding.Default))
                            {
                                string text3;
                                while ((text3 = streamReader2.ReadLine()) != null)
                                {
                                    colorList.Add(text3.ToString());
                                }
                            }
                        }
                    }
                    catch (Exception ex)
                    {
                    }
                    
                    // 加载修改记录
                    List<string> modifyList = new List<string>();
                    try
                    {
                        if (File.Exists("dopaklog.ini"))
                        {
                            using (StreamReader streamReader2 = new StreamReader("dopaklog.ini", Encoding.Default))
                            {
                                string text4;
                                while ((text4 = streamReader2.ReadLine()) != null)
                                {
                                    modifyList.Add(text4.ToString());
                                }
                            }
                        }
                    }
                    catch (Exception ex)
                    {
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
            }
            catch (Exception ex)
            {
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
                    // 隐藏提示文字
                    labErrorMsg.Visibility = Visibility.Collapsed;
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

                    
                    // 初始化配置
                    InitializeConfig();
                    
                    // 加载服装数据
                    GetNewItem();
                    
                    // 再次检查服装列表是否为空
                    if (this.list == null || this.list.Count == 0)
                    {
                        throw new InvalidOperationException("服装列表为空，请先加载服装数据");
                    }
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
                    
                    string appBaseDir = AppDomain.CurrentDomain.BaseDirectory;
                    string iconDir = appBaseDir + this.cookiename + "\\icon" + itemshopM.PakNum.Replace(".", "_").Replace("*", "");
                    if (!Directory.Exists(iconDir))
                    {
                        string iconPakName = "icon" + itemshopM.PakNum.Replace("*", "") + ".pak";
                        try
                        {
                            // 简化版本：只使用本地安装目录
                            string sourcePath = this.strInstallDirectory + "\\" + iconPakName;
                            string destPath = appBaseDir + this.cookiename + "\\" + iconPakName;
                            
                            // 检查源文件是否存在
                            if (File.Exists(sourcePath))
                            {
                                // 确保目标目录存在
                                string cookiesDir = appBaseDir + this.cookiename;
                                if (!Directory.Exists(cookiesDir))
                                {
                                    Directory.CreateDirectory(cookiesDir);
                                }
                                
                                // 复制文件
                                File.Copy(sourcePath, destPath, true);
                                
                                // 提取图片
                                string extractPath = string.Concat(new string[]
                                {
                                    appBaseDir,
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
    
                            }
                        }
                        catch (Exception ex)
                        {
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
                        picPreview.Source = null;
                        txtPreview.Text = "请选择一件服装进行预览";
                        return;
                    }
                    
                    // 显示预览加载状态
                    txtPreview.Text = "正在加载预览图片...";
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
                            picPreview.Source = bitmap;
                            txtPreview.Text = item.ItemName;
                        });
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine("加载图片失败: " + ex.Message);
                        this.Dispatcher.Invoke(() =>
                        {
                            picPreview.Source = null;
                            txtPreview.Text = "加载图片失败: " + ex.Message;
                        });
                    }
                }
                else
                {
                    // 图片不存在
                    this.Dispatcher.Invoke(() =>
                    {
                        picPreview.Source = null;
                        txtPreview.Text = "图片不存在，请先加载图片";
                        
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
                    picPreview.Source = null;
                    txtPreview.Text = "预览失败: " + ex.Message;
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
                // 读取安装目录配置
                if (File.Exists("config.ini"))
                {
                    StreamReader streamReader = new StreamReader("config.ini", Encoding.Default);
                    string text;
                    while ((text = streamReader.ReadLine()) != null)
                    {
                        this.strInstallDirectory = text.ToString();
                    }
                    streamReader.Close();
                }
                
                // 如果没有配置路径，使用默认路径
                if (string.IsNullOrEmpty(this.strInstallDirectory) || !Directory.Exists(this.strInstallDirectory))
                {
                    // 使用Console.WriteLine来调试
                    Console.WriteLine("没有配置路径或路径不存在，使用默认路径");
                    
                    // 使用默认路径
                    string defaultPath = "C:\\Program Files (x86)\\T2CN\\街头篮球";
                    this.strInstallDirectory = defaultPath;
                    
                    // 保存路径到配置文件
                    using (StreamWriter writer = new StreamWriter("config.ini", false, Encoding.Default))
                    {
                        writer.WriteLine(this.strInstallDirectory);
                    }
                    
                    Console.WriteLine($"使用默认游戏安装目录: {this.strInstallDirectory}");
                    Console.WriteLine("如果路径不正确，请手动编辑config.ini文件修改路径");
                }
                else
                {
                    Console.WriteLine($"使用已保存的游戏安装目录: {this.strInstallDirectory}");
                }
                
                // 创建必要的目录
                if (!Directory.Exists(this.cookiename))
                {
                    Directory.CreateDirectory(this.cookiename);
                }
                if (!Directory.Exists("othercookies"))
                {
                    Directory.CreateDirectory("othercookies");
                }
                if (!Directory.Exists("myplans"))
                {
                    Directory.CreateDirectory("myplans");
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine("初始化配置失败: " + ex.Message);
                Console.WriteLine("堆栈跟踪: " + ex.StackTrace);
                
                // 显示错误消息
                MessageBox.Show("初始化配置失败: " + ex.Message, "错误", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        // 后台工作线程方法
        private void bwMain_DoLoadList(object sender, DoWorkEventArgs e)
        {
            try
            {
                // 写入日志文件
                string logFilePath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "init.log");
                using (StreamWriter writer = new StreamWriter(logFilePath, true))
                {
                    writer.WriteLine($"[{DateTime.Now}] 开始bwMain_DoLoadList方法");
                }
                
                InitializeConfig();
                
                // 写入日志文件
                using (StreamWriter writer = new StreamWriter(logFilePath, true))
                {
                    writer.WriteLine($"[{DateTime.Now}] InitializeConfig方法执行完成");
                    writer.WriteLine($"[{DateTime.Now}] 开始调用GetNewItem方法");
                }
                
                GetNewItem();
                
                // 写入日志文件
                using (StreamWriter writer = new StreamWriter(logFilePath, true))
                {
                    writer.WriteLine($"[{DateTime.Now}] GetNewItem方法执行完成");
                }
            }
            catch (Exception ex)
            {
                // 写入日志文件
                string logFilePath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "init.log");
                using (StreamWriter writer = new StreamWriter(logFilePath, true))
                {
                    writer.WriteLine($"[{DateTime.Now}] bwMain_DoLoadList方法出错: {ex.Message}");
                    writer.WriteLine($"[{DateTime.Now}] 堆栈跟踪: {ex.StackTrace}");
                }
            }
        }

        private void bwMain_CompletedLoadList(object sender, RunWorkerCompletedEventArgs e)
        {
            try
            {
                // 写入日志文件
                string logFilePath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "init.log");
                using (StreamWriter writer = new StreamWriter(logFilePath, true))
                {
                    writer.WriteLine($"[{DateTime.Now}] 开始bwMain_CompletedLoadList方法");
                    if (e.Error != null)
                    {
                        writer.WriteLine($"[{DateTime.Now}] 加载数据失败: {e.Error.Message}");
                    }
                    else
                    {
                        writer.WriteLine($"[{DateTime.Now}] 加载数据成功");
                    }
                }
                
                if (e.Error != null)
                {
                    MessageBox.Show("加载数据失败: " + e.Error.Message);
                }
                else
                {
                    bwMain.Dispose();
                }
            }
            catch (Exception ex)
            {
                // 写入日志文件
                string logFilePath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "init.log");
                using (StreamWriter writer = new StreamWriter(logFilePath, true))
                {
                    writer.WriteLine($"[{DateTime.Now}] bwMain_CompletedLoadList方法出错: {ex.Message}");
                }
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