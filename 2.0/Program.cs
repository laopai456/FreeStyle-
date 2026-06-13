using System;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Security.Principal;
using System.Threading;
using FS服装搭配专家.Core.Config;

namespace FS服装搭配专家
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

        private static Mutex? _mutex;

        private static bool IsRunningAsAdmin()
        {
            using var identity = WindowsIdentity.GetCurrent();
            var principal = new WindowsPrincipal(identity);
            return principal.IsInRole(WindowsBuiltInRole.Administrator);
        }

        private static void Elevate()
        {
            var exePath = Process.GetCurrentProcess().MainModule?.FileName;
            if (exePath == null) return;
            try
            {
                Process.Start(new ProcessStartInfo(exePath) { Verb = "runas", UseShellExecute = true });
            }
            catch { /* 用户取消UAC */ }
        }

        [STAThread]
        public static void Main(string[] args)
        {
            if (!IsRunningAsAdmin())
            {
                Elevate();
                return;
            }

            bool createdNew;
            _mutex = new Mutex(true, "FS服装搭配专家v2.0_SingleInstance", out createdNew);

            if (!createdNew)
            {
                System.Windows.MessageBox.Show(
                    "程序已经在运行中！\n\n请检查任务栏或系统托盘。",
                    "程序已运行",
                    System.Windows.MessageBoxButton.OK,
                    System.Windows.MessageBoxImage.Warning);
                return;
            }

            bool consoleVisible = ConfigService.Instance.ConsoleVisible;

            if (consoleVisible)
            {
                AllocConsole();
            }

            App.ConsoleVisible = consoleVisible;

            var app = new App();
            app.InitializeComponent();
            app.Run();
        }
        
        public static void ToggleConsole()
        {
            IntPtr consoleWindow = GetConsoleWindow();
            if (consoleWindow == IntPtr.Zero)
            {
                AllocConsole();
                App.ConsoleVisible = true;
            }
            else
            {
                FreeConsole();
                App.ConsoleVisible = false;
            }
            
            ConfigService.Instance.ConsoleVisible = App.ConsoleVisible;
        }
    }
}
