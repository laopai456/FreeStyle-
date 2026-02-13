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
                Console.WriteLine("直接启动主窗口");
                MainWindow mainWindow = new MainWindow();
                Console.WriteLine("主窗口创建完成");
                
                Console.WriteLine("显示主窗口");
                mainWindow.Show();
                Console.WriteLine("主窗口显示完成");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"启动过程中出错: {ex.Message}");
                Console.WriteLine($"堆栈跟踪: {ex.StackTrace}");
            }
        }
    }
}