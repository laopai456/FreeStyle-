using System;
using System.IO;
using System.Windows;
using System.Windows.Media.Imaging;
using System.Windows.Controls;

namespace FS服装搭配专家v1._0
{
    /// <summary>
    /// App.xaml 的交互逻辑
    /// </summary>
    public partial class App : Application
    {
        public static string UserSelectedTeam { get; set; }
        public static string UserSelectedTeamLogoPath { get; set; }
        
        protected override void OnStartup(StartupEventArgs e)
        {
            base.OnStartup(e);
            
            try
            {
                Console.WriteLine("=== 应用程序启动开始 ===");
                Console.WriteLine($"启动时间: {DateTime.Now}");
                
                // 创建日志文件
                string logFilePath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "startup.log");
                using (StreamWriter writer = new StreamWriter(logFilePath))
                {
                    writer.WriteLine($"=== 应用程序启动日志 ===");
                    writer.WriteLine($"启动时间: {DateTime.Now}");
                    writer.WriteLine("开始创建主窗口...");
                }
                
                Console.WriteLine("开始创建主窗口...");
                MainWindow mainWindow = new MainWindow();
                Console.WriteLine("主窗口创建完成");
                
                // 设置应用程序的主窗口
                this.MainWindow = mainWindow;
                Console.WriteLine("已设置为主窗口");
                
                // 确保窗口属性正确设置
                Console.WriteLine($"窗口可见性初始值: {mainWindow.Visibility}");
                Console.WriteLine($"窗口状态初始值: {mainWindow.WindowState}");
                Console.WriteLine($"窗口位置初始值: {mainWindow.Left}, {mainWindow.Top}");
                Console.WriteLine($"窗口大小初始值: {mainWindow.Width}, {mainWindow.Height}");
                
                // 强制设置窗口位置和大小，确保在屏幕可见区域
                mainWindow.Left = 100;
                mainWindow.Top = 100;
                mainWindow.Width = 800;
                mainWindow.Height = 600;
                mainWindow.WindowStartupLocation = WindowStartupLocation.Manual;
                mainWindow.Visibility = Visibility.Visible;
                
                Console.WriteLine($"窗口位置设置后: {mainWindow.Left}, {mainWindow.Top}");
                Console.WriteLine($"窗口大小设置后: {mainWindow.Width}, {mainWindow.Height}");
                Console.WriteLine($"窗口可见性设置后: {mainWindow.Visibility}");
                
                Console.WriteLine("显示主窗口...");
                mainWindow.Show();
                Console.WriteLine("主窗口显示完成");
                
                // 确保窗口被激活并获得焦点
                mainWindow.Activate();
                mainWindow.Focus();
                Console.WriteLine("窗口已激活并获得焦点");
                
                // 更新日志文件
                using (StreamWriter writer = new StreamWriter(logFilePath, true))
                {
                    writer.WriteLine("主窗口显示成功");
                    writer.WriteLine($"窗口最终状态: {mainWindow.WindowState}");
                    writer.WriteLine($"窗口最终可见性: {mainWindow.Visibility}");
                    writer.WriteLine($"窗口最终位置: {mainWindow.Left}, {mainWindow.Top}");
                    writer.WriteLine($"窗口最终大小: {mainWindow.Width}, {mainWindow.Height}");
                    writer.WriteLine("=== 启动完成 ===");
                }
                
                Console.WriteLine("=== 应用程序启动完成 ===");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"启动过程中出错: {ex.Message}");
                Console.WriteLine($"堆栈跟踪: {ex.StackTrace}");
                
                // 将异常写入日志文件
                string logFilePath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "startup.log");
                using (StreamWriter writer = new StreamWriter(logFilePath, true))
                {
                    writer.WriteLine($"启动过程中出错: {ex.Message}");
                    writer.WriteLine($"堆栈跟踪: {ex.StackTrace}");
                    writer.WriteLine("=== 启动失败 ===");
                }
                
                // 显示错误消息框
                MessageBox.Show($"应用程序启动失败: {ex.Message}\n\n请查看startup.log文件获取详细信息", "启动错误", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }
    }
}