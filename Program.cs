using System;
using System.IO;
using System.Runtime.InteropServices;

namespace FS服装搭配专家v1._0
{
    public static class Program
    {
        [DllImport("kernel32.dll")]
        private static extern bool AllocConsole();
        [DllImport("kernel32.dll")]
        private static extern bool FreeConsole();
        [DllImport("kernel32.dll")]
        private static extern IntPtr GetConsoleWindow();
        [DllImport("user32.dll")]
        private static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
        private const int SW_HIDE = 0;
        private const int SW_SHOW = 5;
        
        private static string consoleConfigPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "console.ini");
        
        [STAThread]
        public static void Main(string[] args)
        {
            // 读取控制台配置
            bool consoleVisible = false;
            if (File.Exists(consoleConfigPath))
            {
                string config = File.ReadAllText(consoleConfigPath).Trim();
                consoleVisible = (config == "1" || config.ToLower() == "true");
            }
            
            // 如果配置要求显示控制台，则创建
            if (consoleVisible)
            {
                AllocConsole();
            }
            
            // 保存配置到 App 类
            App.ConsoleVisible = consoleVisible;
            
            // 启动 WPF 应用
            var app = new App();
            app.InitializeComponent();
            app.Run();
        }
        
        public static void ToggleConsole()
        {
            IntPtr consoleWindow = GetConsoleWindow();
            if (consoleWindow == IntPtr.Zero)
            {
                // 没有控制台，创建一个
                AllocConsole();
                App.ConsoleVisible = true;
            }
            else
            {
                // 有控制台，释放它
                FreeConsole();
                App.ConsoleVisible = false;
            }
            
            // 保存配置
            File.WriteAllText(consoleConfigPath, App.ConsoleVisible ? "1" : "0");
        }
    }
}
