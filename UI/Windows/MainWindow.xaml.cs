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
        
        private void btnSkin_Click(object sender, RoutedEventArgs e)
        {
            // 切换到下一个皮肤颜色
            currentSkinIndex = (currentSkinIndex + 1) % skinColors.Length;
            
            // 应用皮肤颜色到窗口
            ApplySkin(skinColors[currentSkinIndex]);
            
            Console.WriteLine($"切换到皮肤 {currentSkinIndex + 1}");
        }
        
        private void ApplySkin(SolidColorBrush skinColor)
        {
            // 应用皮肤颜色到窗口元素
            // 这里可以根据需要修改窗口的各种元素颜色
            // 例如：修改按钮背景、文本颜色、边框颜色等
            
            // 示例：修改换肤按钮的背景颜色
            btnSkin.Background = skinColor;
            
            // 示例：修改其他窗口按钮的背景颜色
            // 注意：这里需要根据实际的按钮名称进行修改
            // 由于我们没有直接引用其他按钮，可以通过遍历视觉树来找到它们
            ApplySkinToVisualTree(this, skinColor);
        }
        
        private void ApplySkinToVisualTree(DependencyObject parent, SolidColorBrush skinColor)
        {
            // 遍历视觉树，应用皮肤颜色到所有元素
            int childrenCount = VisualTreeHelper.GetChildrenCount(parent);
            for (int i = 0; i < childrenCount; i++)
            {
                DependencyObject child = VisualTreeHelper.GetChild(parent, i);
                
                // 应用皮肤颜色到按钮
                if (child is System.Windows.Controls.Button button)
                {
                    // 修改窗口管理按钮和换肤按钮
                    if (button.Name == "btnSkin" || button.Content.ToString() == "最小化" || button.Content.ToString() == "最大化" || button.Content.ToString() == "关闭")
                    {
                        button.Background = skinColor;
                    }
                }
                
                // 应用皮肤颜色到边框
                if (child is System.Windows.Controls.Border border)
                {
                    // 修改主要容器边框
                    if (border.CornerRadius.TopLeft == 16 && border.Margin.Top == 10)
                    {
                        border.Background = new SolidColorBrush(Color.FromArgb(21, skinColor.Color.R, skinColor.Color.G, skinColor.Color.B));
                        border.BorderBrush = new SolidColorBrush(Color.FromArgb(77, skinColor.Color.R, skinColor.Color.G, skinColor.Color.B));
                    }
                    // 修改预览区域边框
                    else if (border.CornerRadius.TopLeft == 16 && border.Height == 400)
                    {
                        border.Background = new SolidColorBrush(Color.FromArgb(21, skinColor.Color.R, skinColor.Color.G, skinColor.Color.B));
                        border.BorderBrush = new SolidColorBrush(Color.FromArgb(77, skinColor.Color.R, skinColor.Color.G, skinColor.Color.B));
                    }
                    // 修改列表项边框
                    else if (border.CornerRadius.TopLeft == 12 && border.Margin.Top == 4)
                    {
                        border.Background = new SolidColorBrush(Color.FromArgb(26, skinColor.Color.R, skinColor.Color.G, skinColor.Color.B));
                        border.BorderBrush = new SolidColorBrush(Color.FromArgb(51, skinColor.Color.R, skinColor.Color.G, skinColor.Color.B));
                    }
                }
                
                // 应用皮肤颜色到文本块
                if (child is System.Windows.Controls.TextBlock textBlock)
                {
                    // 修改标题文本颜色
                    if (textBlock.FontWeight == FontWeights.Bold && textBlock.FontSize >= 18)
                    {
                        textBlock.Foreground = new SolidColorBrush(GetContrastColor(skinColor.Color));
                    }
                    // 修改正文文本颜色
                    else if (textBlock.FontSize >= 14)
                    {
                        textBlock.Foreground = new SolidColorBrush(GetContrastColor(skinColor.Color));
                    }
                }
                
                // 应用皮肤颜色到标签控件
                if (child is System.Windows.Controls.TabControl tabControl)
                {
                    // 修改标签控件的背景颜色
                    tabControl.Background = new SolidColorBrush(Color.FromArgb(13, skinColor.Color.R, skinColor.Color.G, skinColor.Color.B));
                }
                
                // 应用皮肤颜色到列表框
                if (child is System.Windows.Controls.ListBox listBox)
                {
                    // 修改列表框的背景颜色
                    listBox.Background = new SolidColorBrush(Color.FromArgb(13, skinColor.Color.R, skinColor.Color.G, skinColor.Color.B));
                }
                
                // 递归处理子元素
                ApplySkinToVisualTree(child, skinColor);
            }
        }
        
        private Color GetContrastColor(Color color)
        {
            // 计算颜色的亮度
            double brightness = (0.299 * color.R + 0.587 * color.G + 0.114 * color.B) / 255;
            
            // 如果亮度大于0.5，返回黑色；否则返回白色
            return brightness > 0.5 ? Colors.Black : Colors.White;
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
