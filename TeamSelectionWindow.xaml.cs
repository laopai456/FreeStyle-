using System;
using System.Collections.Generic;
using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media.Imaging;
using System.Windows.Media;

namespace FS服装搭配专家v1._0
{
    public partial class TeamSelectionWindow : Window
    {
        public string SelectedTeam { get; private set; }
        public string SelectedTeamLogoPath { get; private set; }
        
        private string selectedTeamName;
        private Border selectedTeamBorder;
        private readonly Dictionary<string, string> teamLogos;
        
        public TeamSelectionWindow()
        {
            Console.WriteLine("TeamSelectionWindow构造函数开始");
            InitializeComponent();
            Console.WriteLine("InitializeComponent完成");
            teamLogos = new Dictionary<string, string>();
            Console.WriteLine("开始加载球队logo");
            LoadTeamLogos();
            Console.WriteLine("加载球队logo完成");
        }
        
        private void LoadTeamLogos()
        {
            try
            {
                // 直接使用绝对路径
                string nbaDirectory = "C:\\Users\\27507\\Desktop\\py\\UI\\FS服装搭配专家v1.0\\nba";
                Console.WriteLine($"使用NBA目录路径: {nbaDirectory}");
                
                if (Directory.Exists(nbaDirectory))
                {
                    Console.WriteLine("NBA目录存在");
                    
                    string[] imageFiles = Directory.GetFiles(nbaDirectory, "*.png");
                    Console.WriteLine($"找到 {imageFiles.Length} 个PNG文件");
                    
                    if (imageFiles.Length > 0)
                    {
                        Console.WriteLine("开始创建球队卡片");
                        
                        foreach (string imageFile in imageFiles)
                        {
                            try
                            {
                                string teamName = Path.GetFileNameWithoutExtension(imageFile);
                                teamLogos[teamName] = imageFile;
                                Console.WriteLine($"处理球队: {teamName}");
                                
                                // 创建球队卡片
                                Border teamCard = new Border
                                {
                                    CornerRadius = new CornerRadius(12),
                                    Background = new System.Windows.Media.SolidColorBrush(System.Windows.Media.Color.FromArgb(32, 255, 255, 255)),
                                    BorderBrush = new System.Windows.Media.SolidColorBrush(System.Windows.Media.Color.FromArgb(77, 255, 255, 255)),
                                    BorderThickness = new System.Windows.Thickness(1),
                                    Margin = new System.Windows.Thickness(8),
                                    Padding = new System.Windows.Thickness(12),
                                    Cursor = System.Windows.Input.Cursors.Hand,
                                    Tag = teamName
                                };
                                
                                StackPanel teamContent = new StackPanel
                                {
                                    Orientation = System.Windows.Controls.Orientation.Vertical,
                                    HorizontalAlignment = System.Windows.HorizontalAlignment.Center
                                };
                                
                                // 加载球队logo
                                try
                                {
                                    Console.WriteLine($"加载logo: {imageFile}");
                                    System.Windows.Media.Imaging.BitmapImage logoImage = new System.Windows.Media.Imaging.BitmapImage();
                                    logoImage.BeginInit();
                                    logoImage.UriSource = new Uri(imageFile);
                                    logoImage.EndInit();
                                    
                                    System.Windows.Controls.Image imageControl = new System.Windows.Controls.Image
                                    {
                                        Source = logoImage,
                                        Width = 80,
                                        Height = 80,
                                        Margin = new System.Windows.Thickness(0, 0, 0, 8)
                                    };
                                    
                                    teamContent.Children.Add(imageControl);
                                    Console.WriteLine("Logo加载成功");
                                }
                                catch (Exception ex)
                                {
                                    Console.WriteLine($"加载球队logo失败: {ex.Message}");
                                    
                                    // 添加错误提示
                                    System.Windows.Controls.TextBlock errorText = new System.Windows.Controls.TextBlock
                                    {
                                        Text = "Logo加载失败",
                                        FontSize = 12,
                                        Foreground = System.Windows.Media.Brushes.Red,
                                        Margin = new System.Windows.Thickness(0, 20, 0, 8)
                                    };
                                    teamContent.Children.Add(errorText);
                                }
                                
                                // 添加球队名称
                                System.Windows.Controls.TextBlock teamNameText = new System.Windows.Controls.TextBlock
                                {
                                    Text = teamName,
                                    FontSize = 14,
                                    FontWeight = System.Windows.FontWeights.Medium,
                                    Foreground = new System.Windows.Media.SolidColorBrush(System.Windows.Media.Colors.White),
                                    HorizontalAlignment = System.Windows.HorizontalAlignment.Center
                                };
                                
                                teamContent.Children.Add(teamNameText);
                                teamCard.Child = teamContent;
                                
                                // 添加点击事件
                                teamCard.MouseLeftButtonDown += TeamCard_MouseLeftButtonDown;
                                
                                Console.WriteLine($"添加球队卡片: {teamName}");
                            Console.WriteLine($"当前WrapPanel子元素数量: {TeamsWrapPanel.Children.Count}");
                            TeamsWrapPanel.Children.Add(teamCard);
                            Console.WriteLine($"添加后WrapPanel子元素数量: {TeamsWrapPanel.Children.Count}");
                            }
                            catch (Exception ex)
                            {
                                Console.WriteLine($"处理球队 {imageFile} 时出错: {ex.Message}");
                            }
                        }
                        
                        Console.WriteLine("球队卡片创建完成");
                    }
                    else
                    {
                        Console.WriteLine("NBA目录中没有PNG文件");
                        
                        // 添加错误提示
                        System.Windows.Controls.TextBlock errorText = new System.Windows.Controls.TextBlock
                        {
                            Text = "NBA目录中没有PNG文件",
                            FontSize = 14,
                            Foreground = System.Windows.Media.Brushes.Red,
                            HorizontalAlignment = System.Windows.HorizontalAlignment.Center,
                            TextWrapping = System.Windows.TextWrapping.Wrap,
                            Margin = new System.Windows.Thickness(20)
                        };
                        TeamsWrapPanel.Children.Add(errorText);
                    }
                }
                else
                {
                    Console.WriteLine("NBA目录不存在");
                    
                    // 添加错误提示
                    System.Windows.Controls.TextBlock errorText = new System.Windows.Controls.TextBlock
                    {
                        Text = "NBA目录不存在",
                        FontSize = 14,
                        Foreground = System.Windows.Media.Brushes.Red,
                        HorizontalAlignment = System.Windows.HorizontalAlignment.Center,
                        TextWrapping = System.Windows.TextWrapping.Wrap,
                        Margin = new System.Windows.Thickness(20)
                    };
                    TeamsWrapPanel.Children.Add(errorText);
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"加载球队logo时出错: {ex.Message}");
                
                // 添加错误提示
                System.Windows.Controls.TextBlock errorText = new System.Windows.Controls.TextBlock
                {
                    Text = $"加载球队时出错: {ex.Message}",
                    FontSize = 14,
                    Foreground = System.Windows.Media.Brushes.Red,
                    HorizontalAlignment = System.Windows.HorizontalAlignment.Center,
                    TextWrapping = System.Windows.TextWrapping.Wrap,
                    Margin = new System.Windows.Thickness(20)
                };
                TeamsWrapPanel.Children.Add(errorText);
            }
        }
        
        private void TeamCard_MouseLeftButtonDown(object sender, System.Windows.Input.MouseButtonEventArgs e)
        {
            if (sender is Border teamCard)
            {
                // 取消之前的选择
                if (selectedTeamBorder != null)
                {
                    selectedTeamBorder.Background = (SolidColorBrush)FindResource("GlassCardColor");
                    selectedTeamBorder.BorderBrush = (SolidColorBrush)FindResource("GlassBorderColor");
                }
                
                // 设置新的选择
                selectedTeamBorder = teamCard;
                selectedTeamName = teamCard.Tag as string;
                
                // 高亮显示选中的球队
                selectedTeamBorder.Background = (SolidColorBrush)FindResource("ButtonGlassHoverColor");
                selectedTeamBorder.BorderBrush = (SolidColorBrush)FindResource("TextColor");
            }
        }
        
        private void Cancel_Click(object sender, RoutedEventArgs e)
        {
            SelectedTeam = null;
            SelectedTeamLogoPath = null;
            this.DialogResult = false;
            this.Close();
        }
        
        private void Confirm_Click(object sender, RoutedEventArgs e)
        {
            if (!string.IsNullOrEmpty(selectedTeamName) && teamLogos.ContainsKey(selectedTeamName))
            {
                SelectedTeam = selectedTeamName;
                SelectedTeamLogoPath = teamLogos[selectedTeamName];
                this.DialogResult = true;
                this.Close();
            }
            else
            {
                MessageBox.Show("请选择一个球队", "提示", MessageBoxButton.OK, MessageBoxImage.Information);
            }
        }
    }
}