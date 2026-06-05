using System;
using System.IO;
using System.Windows;
using System.Windows.Media.Imaging;
using System.Windows.Controls;
using System.Text;
using System.Runtime.InteropServices;

namespace FS服装搭配专家v1._0
{
    /// <summary>
    /// App.xaml 的交互逻辑
    /// </summary>
    public partial class App : Application
    {
        [DllImport("kernel32.dll")]
        private static extern IntPtr GetConsoleWindow();
        [DllImport("user32.dll")]
        private static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
        private const int SW_HIDE = 0;
        private const int SW_SHOW = 5;
        
        public static string UserSelectedTeam { get; set; }
        public static string UserSelectedTeamLogoPath { get; set; }
        
        public static bool ConsoleVisible { get; set; } = false;
        
        protected override void OnStartup(StartupEventArgs e)
        {
            try
            {
                // 简化启动过程，先输出到控制台
                Console.WriteLine("=== 应用程序启动开始 ===");
                Console.WriteLine($"启动时间: {DateTime.Now}");
                
                // 注册编码提供程序以支持Big5编码
                Console.WriteLine("注册编码提供程序...");
                Encoding.RegisterProvider(CodePagesEncodingProvider.Instance);
                Console.WriteLine("编码提供程序注册完成");
                
                // 调用基类方法
                Console.WriteLine("调用base.OnStartup...");
                base.OnStartup(e);
                Console.WriteLine("base.OnStartup完成");
                
                // 创建主窗口
                Console.WriteLine("创建主窗口...");
                MainWindow mainWindow = new MainWindow();
                Console.WriteLine("主窗口创建完成");
                
                // 设置主窗口
                this.MainWindow = mainWindow;
                Console.WriteLine("已设置为主窗口");
                
                // 显示主窗口
                Console.WriteLine("显示主窗口...");
                mainWindow.Show();
                Console.WriteLine("主窗口显示完成");
                
                Console.WriteLine("=== 应用程序启动完成 ===");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"启动过程中出错: {ex.Message}");
                Console.WriteLine($"堆栈跟踪: {ex.StackTrace}");
                
                // 尝试显示错误消息
                try
                {
                    MessageBox.Show($"应用程序启动失败: {ex.Message}\n\n{ex.StackTrace}", "启动错误", MessageBoxButton.OK, MessageBoxImage.Error);
                }
                catch (Exception msgEx)
                {
                    Console.WriteLine($"显示错误消息框失败: {msgEx.Message}");
                }
            }
        }
    }
}