using System;
using System.IO;
using System.Runtime.InteropServices;
using FS服装搭配专家v1._0.Core.Config;

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
        
        [STAThread]
        public static void Main(string[] args)
        {
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
