using System;
using System.Collections.Generic;
using System.Windows;
using System.Windows.Media;

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

        public MainWindow()
        {
            InitializeComponent();
            Console.WriteLine("窗口已初始化");
            
            // 确保窗口可见
            this.Visibility = Visibility.Visible;
            this.Activate();
            this.Focus();
            
            // 初始化服装列表数据
            InitializeItemList();
            
            Console.WriteLine($"窗口状态: {this.WindowState}");
            Console.WriteLine($"窗口可见性: {this.Visibility}");
            Console.WriteLine($"窗口位置: {this.Left}, {this.Top}");
            Console.WriteLine($"窗口大小: {this.Width}, {this.Height}");
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
        
        private void InitializeItemList()
        {
            // 添加示例服装数据
            var items = new List<string>
            {
                "红色上衣",
                "蓝色裤子",
                "绿色鞋子",
                "黄色外套",
                "紫色裙子",
                "黑色帽子",
                "白色衬衫",
                "灰色毛衣"
            };
            
            // 绑定数据到列表框
            lstItemShop.ItemsSource = items;
        }
        
        private void lstItemShop_SelectionChanged(object sender, System.Windows.Controls.SelectionChangedEventArgs e)
        {
            // 更新预览文本
            if (lstItemShop.SelectedItem != null)
            {
                txtPreview.Text = $"您选择了: {lstItemShop.SelectedItem.ToString()}";
            }
            else
            {
                txtPreview.Text = "请选择一件服装进行预览";
            }
            
            // 更新选中项样式
            foreach (var item in lstItemShop.Items)
            {
                var listBoxItem = lstItemShop.ItemContainerGenerator.ContainerFromItem(item) as System.Windows.Controls.ListBoxItem;
                if (listBoxItem != null)
                {
                    var border = FindVisualChild<System.Windows.Controls.Border>(listBoxItem);
                    if (border != null)
                    {
                        if (lstItemShop.SelectedItem == item)
                        {
                            border.Style = this.FindResource("ListItemSelectedStyle") as System.Windows.Style;
                        }
                        else
                        {
                            border.Style = this.FindResource("ListItemStyle") as System.Windows.Style;
                        }
                    }
                }
            }
        }
        
        private T FindVisualChild<T>(System.Windows.DependencyObject parent) where T : System.Windows.DependencyObject
        {
            for (int i = 0; i < System.Windows.Media.VisualTreeHelper.GetChildrenCount(parent); i++)
            {
                var child = System.Windows.Media.VisualTreeHelper.GetChild(parent, i);
                if (child is T typedChild)
                {
                    return typedChild;
                }
                else
                {
                    var result = FindVisualChild<T>(child);
                    if (result != null)
                    {
                        return result;
                    }
                }
            }
            return null;
        }
    }
}
