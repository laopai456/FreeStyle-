using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using System.Windows;
using System.Windows.Media.Imaging;
using Microsoft.Win32;
using FS服装搭配专家v1._0;

namespace FS服装搭配专家v1._0.UI.Windows
{
    public partial class BgCropWindow : Window
    {
        private string gameDirectory = string.Empty;
        private string selectedImagePath = null;
        private Bitmap previewImage = null;

        private Dictionary<int, BackgroundTypeInfo> bgTypeMap = new Dictionary<int, BackgroundTypeInfo>
        {
            { 0, new BackgroundTypeInfo { Name = "登录界面", Prefix = "bg1027" } },
            { 1, new BackgroundTypeInfo { Name = "角色选择", Prefix = "bg1013" } },
            { 2, new BackgroundTypeInfo { Name = "大厅背景", Prefix = "bg1012" } },
            { 3, new BackgroundTypeInfo { Name = "等待房间", Prefix = "bg1014" } },
            { 4, new BackgroundTypeInfo { Name = "读取加载1", Prefix = "bg1004" } },
            { 5, new BackgroundTypeInfo { Name = "读取加载2", Prefix = "bg1005" } },
            { 6, new BackgroundTypeInfo { Name = "读取加载3", Prefix = "bg1006" } },
        };

        public BgCropWindow()
        {
            InitializeComponent();
            LoadWindowSize();
            LoadConfig();
            InitBgTypeComboBox();
            this.SizeChanged += BgCropWindow_SizeChanged;
        }

        public BgCropWindow(string gameDir) : this()
        {
            gameDirectory = gameDir;
        }

        private void InitBgTypeComboBox()
        {
            foreach (var kvp in bgTypeMap)
            {
                cmbBgType.Items.Add($"【{kvp.Key}】{kvp.Value.Name}");
            }
            cmbBgType.SelectedIndex = 0;
        }

        private void LoadConfig()
        {
            string configPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "config.ini");
            if (File.Exists(configPath))
            {
                try
                {
                    string[] lines = File.ReadAllLines(configPath);
                    foreach (string line in lines)
                    {
                        string trimmedLine = line.Trim();
                        if (trimmedLine.StartsWith("InstallDirectory="))
                        {
                            gameDirectory = trimmedLine.Substring("InstallDirectory=".Length);
                            break;
                        }
                    }
                }
                catch
                {
                }
            }
        }

        private void btnBrowse_Click(object sender, RoutedEventArgs e)
        {
            OpenFileDialog dialog = new OpenFileDialog();
            dialog.Filter = "图片文件|*.jpg;*.jpeg;*.png|所有文件|*.*";
            dialog.Title = "选择背景图片";

            if (dialog.ShowDialog() == true)
            {
                try
                {
                    selectedImagePath = dialog.FileName;

                    if (previewImage != null)
                    {
                        previewImage.Dispose();
                    }
                    previewImage = new Bitmap(selectedImagePath);

                    BitmapImage bitmap = new BitmapImage();
                    bitmap.BeginInit();
                    bitmap.CacheOption = BitmapCacheOption.OnLoad;
                    bitmap.UriSource = new Uri(selectedImagePath);
                    bitmap.EndInit();
                    imgPreview.Source = bitmap;

                    txtPreviewPlaceholder.Visibility = Visibility.Collapsed;
                    txtImageInfo.Text = $"图片大小: {previewImage.Width} x {previewImage.Height}";
                    txtStatus.Text = "状态: 已加载图片";
                }
                catch (Exception ex)
                {
                    MessageBox.Show($"加载图片失败：{ex.Message}", "错误");
                    txtStatus.Text = "状态: 加载失败";
                }
            }
        }

        private void btnStart_Click(object sender, RoutedEventArgs e)
        {
            if (string.IsNullOrEmpty(selectedImagePath) || !File.Exists(selectedImagePath))
            {
                MessageBox.Show("请先选择图片！", "提示");
                return;
            }

            if (cmbBgType.SelectedIndex < 0)
            {
                MessageBox.Show("请选择背景类型！", "提示");
                return;
            }

            if (string.IsNullOrEmpty(gameDirectory) || !Directory.Exists(gameDirectory))
            {
                MessageBox.Show("游戏目录不存在，请检查配置！", "错误");
                return;
            }

            int selectedIndex = cmbBgType.SelectedIndex;
            var bgTypeInfo = bgTypeMap[selectedIndex];

            try
            {
                txtStatus.Text = "状态: 正在处理...";

                string sourcePak = Path.Combine(gameDirectory, "u_background.pak");
                string unpackedDir = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "cookies\\u_background_pak");

                if (!File.Exists(sourcePak))
                {
                    MessageBox.Show($"背景文件不存在：{sourcePak}", "错误");
                    txtStatus.Text = "状态: 背景文件不存在";
                    return;
                }

                if (!Directory.Exists(unpackedDir))
                {
                    txtStatus.Text = "状态: 正在解压背景包...";
                    string pakPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "cookies\\u_background.pak");
                    Directory.CreateDirectory(Path.GetDirectoryName(pakPath));
                    File.Copy(sourcePak, pakPath, true);

                    string unpackCmd = $"pack\\resources \"{pakPath}\" -all";
                    conmon.RunCmd(unpackCmd);
                }

                txtStatus.Text = "状态: 正在缩放图片...";
                Bitmap resizedImage = new Bitmap(1366, 768);
                using (Graphics g = Graphics.FromImage(resizedImage))
                {
                    g.InterpolationMode = System.Drawing.Drawing2D.InterpolationMode.HighQualityBicubic;
                    g.DrawImage(previewImage, 0, 0, 1366, 768);
                }

                txtStatus.Text = "状态: 正在切割图片...";
                List<Bitmap> splitImages = SplitImage(resizedImage);

                Bitmap mergedImage = null;
                if (splitImages.Count >= 5)
                {
                    mergedImage = new Bitmap(512, 512, PixelFormat.Format32bppArgb);
                    using (Graphics g = Graphics.FromImage(mergedImage))
                    {
                        g.Clear(Color.Transparent);
                        g.InterpolationMode = System.Drawing.Drawing2D.InterpolationMode.NearestNeighbor;
                        g.DrawImage(splitImages[3], 0, 0);
                        g.DrawImage(splitImages[4], 0, 256);
                    }
                }

                txtStatus.Text = "状态: 正在保存图片...";
                int savedCount = 0;
                for (int i = 0; i < splitImages.Count; i++)
                {
                    if (i == 3 || i == 4)
                        continue;

                    string filename;
                    if (i < 3)
                    {
                        filename = $"{bgTypeInfo.Prefix}_{i}";
                    }
                    else
                    {
                        filename = $"{bgTypeInfo.Prefix}_{i - 1}";
                    }

                    string outputPath = Path.Combine(unpackedDir, $"{filename}.png");
                    splitImages[i].Save(outputPath, ImageFormat.Png);
                    savedCount++;
                }

                if (mergedImage != null)
                {
                    string mergedPath = Path.Combine(unpackedDir, $"{bgTypeInfo.Prefix}_3.png");
                    mergedImage.Save(mergedPath, ImageFormat.Png);
                    savedCount++;
                }

                foreach (Bitmap bmp in splitImages)
                {
                    bmp.Dispose();
                }
                resizedImage.Dispose();

                txtStatus.Text = "状态: 正在压包...";
                string packCmd = $"pack\\resources -file2pak \"{unpackedDir}\" \"{Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "cookies\\u_background.pak")}\"";
                conmon.RunCmd(packCmd);

                string targetPak = Path.Combine(gameDirectory, "u_background.pak");
                File.Copy(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "cookies\\u_background.pak"), targetPak, true);

                txtStatus.Text = "状态: 完成";
                MessageBox.Show($"背景修改完成！\n背景类型：{bgTypeInfo.Name}\n已生成 {savedCount} 张图片\n已应用到游戏目录", "成功");
            }
            catch (Exception ex)
            {
                MessageBox.Show($"背景修改失败：{ex.Message}", "错误");
                txtStatus.Text = "状态: 处理失败";
            }
        }

        private List<Bitmap> SplitImage(Bitmap source)
        {
            List<Bitmap> result = new List<Bitmap>();
            int width = source.Width;
            int height = source.Height;
            int splitWidth = 512;
            int splitHeight = 512;

            for (int j = 0; j < height; j += splitHeight)
            {
                for (int i = 0; i < width; i += splitWidth)
                {
                    int srcX = i;
                    int srcY = j;
                    int srcWidth = Math.Min(splitWidth, width - i);
                    int srcHeight = Math.Min(splitHeight, height - j);

                    Rectangle srcRect = new Rectangle(srcX, srcY, srcWidth, srcHeight);
                    Rectangle destRect = new Rectangle(0, 0, srcWidth, srcHeight);

                    Bitmap splitImg = source.Clone(srcRect, source.PixelFormat);

                    Bitmap newImg = new Bitmap(splitWidth, splitHeight, PixelFormat.Format32bppArgb);
                    using (Graphics g = Graphics.FromImage(newImg))
                    {
                        g.Clear(Color.Transparent);
                        g.InterpolationMode = System.Drawing.Drawing2D.InterpolationMode.NearestNeighbor;
                        g.DrawImage(splitImg, destRect);
                    }

                    splitImg.Dispose();
                    result.Add(newImg);
                }
            }

            return result;
        }

        private void btnClose_Click(object sender, RoutedEventArgs e)
        {
            this.Close();
        }

        private void btnCancel_Click(object sender, RoutedEventArgs e)
        {
            this.Close();
        }

        /// <summary>
        /// 从配置文件加载窗口尺寸
        /// </summary>
        private void LoadWindowSize()
        {
            try
            {
                var configService = Core.Config.ConfigService.Instance;
                this.Width = configService.BgCropWindowWidth;
                this.Height = configService.BgCropWindowHeight;
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[BgCropWindow] 加载窗口尺寸失败: {ex.Message}");
            }
        }

        /// <summary>
        /// 窗口尺寸变化事件处理
        /// </summary>
        private void BgCropWindow_SizeChanged(object sender, SizeChangedEventArgs e)
        {
            try
            {
                if (this.WindowState == WindowState.Normal)
                {
                    var configService = Core.Config.ConfigService.Instance;
                    configService.BgCropWindowWidth = this.ActualWidth;
                    configService.BgCropWindowHeight = this.ActualHeight;
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[BgCropWindow] 保存窗口尺寸失败: {ex.Message}");
            }
        }
    }

    public class BackgroundTypeInfo
    {
        public string Name { get; set; }
        public string Prefix { get; set; }
    }
}
