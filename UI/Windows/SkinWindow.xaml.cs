using System;
using System.Windows;
using System.Windows.Input;
using System.Windows.Media;

namespace FS服装搭配专家v1._0
{
    public partial class SkinWindow : Window
    {
        private SkinManager skinManager;
        private SkinData selectedSkin;

        public SkinWindow()
        {
            InitializeComponent();
            skinManager = new SkinManager();
            InitializeSkinList();
        }

        private void InitializeSkinList()
        {
            // 绑定皮肤列表到ListBox
            lstSkins.ItemsSource = skinManager.Skins;
            
            // 默认选择第一个皮肤
            if (lstSkins.Items.Count > 0)
            {
                lstSkins.SelectedIndex = 0;
            }
        }

        private void TitleBar_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
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

        private void Close_Click(object sender, RoutedEventArgs e)
        {
            this.Close();
        }

        private void Cancel_Click(object sender, RoutedEventArgs e)
        {
            this.Close();
        }

        private void Apply_Click(object sender, RoutedEventArgs e)
        {
            if (selectedSkin != null)
            {
                // 应用选中的皮肤
                ApplySkin(selectedSkin);
                this.Close();
            }
        }

        private void lstSkins_SelectionChanged(object sender, System.Windows.Controls.SelectionChangedEventArgs e)
        {
            if (lstSkins.SelectedItem != null)
            {
                selectedSkin = lstSkins.SelectedItem as SkinData;
                if (selectedSkin != null)
                {
                    // 更新预览区域
                    UpdatePreview(selectedSkin);
                    
                    // 更新皮肤信息
                    txtSkinInfo.Text = $"皮肤名称: {selectedSkin.Name}\n" +
                                      $"背景颜色: {selectedSkin.BackColor.ToString()}\n" +
                                      $"按钮颜色: {selectedSkin.ButtonColor.ToString()}\n" +
                                      $"边框颜色: {selectedSkin.BorderColor.ToString()}\n" +
                                      $"文本颜色: {selectedSkin.TextColor.ToString()}";
                }
            }
        }

        private void UpdatePreview(SkinData skin)
        {
            // 更新预览区域的背景颜色
            previewGrid.Background = new SolidColorBrush(skin.BackColor);
            
            // 更新预览区域的边框颜色
            previewBorder.BorderBrush = new SolidColorBrush(skin.BorderColor);
            
            // 更新预览文本颜色
            foreach (var child in previewGrid.Children)
            {
                if (child is System.Windows.Controls.TextBlock textBlock)
                {
                    textBlock.Foreground = new SolidColorBrush(skin.TextColor);
                }
            }
        }

        private void ApplySkin(SkinData skin)
        {
            // 这里可以实现应用皮肤到整个应用程序的逻辑
            // 例如，更新主窗口的颜色、控件的颜色等
            
            // 示例：更新主窗口的背景颜色
            if (this.Owner is MainWindow mainWindow)
            {
                // 这里可以添加具体的皮肤应用逻辑
                Console.WriteLine($"应用皮肤: {skin.Name}");
            }
        }
    }
}