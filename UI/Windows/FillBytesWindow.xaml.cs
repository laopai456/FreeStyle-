using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Windows;
using System.Windows.Controls;

namespace FS服装搭配专家v1._0.UI.Windows
{
    public partial class FillBytesWindow : Window
    {
        private string gameDirectory = string.Empty;
        private List<PakFileInfo> allFiles = new List<PakFileInfo>();
        private string referenceBytesPath = string.Empty;
        private string pakSizesPath = string.Empty;
        private Dictionary<string, long> originalPakSizes = new Dictionary<string, long>();

        public FillBytesWindow()
        {
            InitializeComponent();
            InitializeConfig();
        }

        public FillBytesWindow(string gameDir) : this()
        {
            gameDirectory = gameDir;
        }

        private void InitializeConfig()
        {
            referenceBytesPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "reference_bytes.txt");
            pakSizesPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "pak_sizes.txt");
            
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

            LoadReferenceBytes();
            LoadOriginalPakSizes();
            
            if (originalPakSizes.Count == 0)
            {
                ScanAndSaveOriginalPakSizes();
            }
            
            LoadFiles();
        }

        private void LoadReferenceBytes()
        {
            if (File.Exists(referenceBytesPath))
            {
                try
                {
                    string bytesStr = File.ReadAllText(referenceBytesPath).Trim();
                    if (!string.IsNullOrEmpty(bytesStr))
                    {
                        txtTargetBytes.Text = bytesStr;
                    }
                }
                catch
                {
                }
            }
        }

        private void SaveReferenceBytes()
        {
            try
            {
                File.WriteAllText(referenceBytesPath, txtTargetBytes.Text);
            }
            catch
            {
            }
        }

        private void LoadOriginalPakSizes()
        {
            originalPakSizes.Clear();
            
            if (File.Exists(pakSizesPath))
            {
                try
                {
                    string[] lines = File.ReadAllLines(pakSizesPath);
                    foreach (string line in lines)
                    {
                        string trimmedLine = line.Trim();
                        if (string.IsNullOrEmpty(trimmedLine) || !trimmedLine.Contains("="))
                            continue;
                        
                        int eqIndex = trimmedLine.IndexOf('=');
                        string fileName = trimmedLine.Substring(0, eqIndex).Trim();
                        string sizeStr = trimmedLine.Substring(eqIndex + 1).Trim();
                        
                        if (long.TryParse(sizeStr, out long size))
                        {
                            originalPakSizes[fileName] = size;
                        }
                    }
                }
                catch
                {
                }
            }
        }

        private void ScanAndSaveOriginalPakSizes()
        {
            if (string.IsNullOrEmpty(gameDirectory) || !Directory.Exists(gameDirectory))
                return;

            originalPakSizes.Clear();

            try
            {
                string[] pakFiles = Directory.GetFiles(gameDirectory, "*.pak", SearchOption.TopDirectoryOnly);
                List<string> lines = new List<string>();

                foreach (string file in pakFiles)
                {
                    string fileName = Path.GetFileName(file);
                    FileInfo fi = new FileInfo(file);
                    originalPakSizes[fileName] = fi.Length;
                    lines.Add($"{fileName}={fi.Length}");
                }

                File.WriteAllLines(pakSizesPath, lines);
            }
            catch
            {
            }
        }

        private void LoadFiles()
        {
            allFiles.Clear();

            if (string.IsNullOrEmpty(gameDirectory) || !Directory.Exists(gameDirectory))
            {
                MessageBox.Show("游戏目录不存在，请检查配置！", "错误");
                return;
            }

            string cookiesDir = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "cookies");
            if (!Directory.Exists(cookiesDir))
            {
                Directory.CreateDirectory(cookiesDir);
            }

            try
            {
                Dictionary<string, long> gamePakSizes = new Dictionary<string, long>();
                string[] gamePakFiles = Directory.GetFiles(gameDirectory, "*.pak", SearchOption.TopDirectoryOnly);
                foreach (string file in gamePakFiles)
                {
                    string fileName = Path.GetFileName(file);
                    FileInfo fi = new FileInfo(file);
                    gamePakSizes[fileName] = fi.Length;
                }

                string[] cookiesPakFiles = Directory.GetFiles(cookiesDir, "*.pak", SearchOption.TopDirectoryOnly);
                foreach (string file in cookiesPakFiles)
                {
                    string fileName = Path.GetFileName(file);
                    FileInfo fi = new FileInfo(file);
                    long currentSize = fi.Length;
                    
                    long originalSize = originalPakSizes.ContainsKey(fileName) ? originalPakSizes[fileName] : 0;
                    long targetSize = gamePakSizes.ContainsKey(fileName) ? gamePakSizes[fileName] : 0;

                    allFiles.Add(new PakFileInfo
                    {
                        FileName = fileName,
                        FilePath = file,
                        CurrentSize = FormatSize(currentSize),
                        CurrentBytes = currentSize,
                        OriginalSize = originalSize > 0 ? FormatSize(originalSize) : "未知",
                        OriginalBytes = originalSize,
                        TargetSize = targetSize > 0 ? FormatSize(targetSize) : "未知",
                        TargetBytes = targetSize,
                        GameFilePath = Path.Combine(gameDirectory, fileName)
                    });
                }

                dgFiles.ItemsSource = null;
                dgFiles.ItemsSource = allFiles;

                txtStatus.Text = $"状态: 已加载 {allFiles.Count} 个cookies中的pak文件";
            }
            catch (Exception ex)
            {
                MessageBox.Show($"加载文件列表失败：{ex.Message}", "错误");
            }
        }

        private string FormatSize(long bytes)
        {
            if (bytes < 1024)
                return $"{bytes} B";
            else if (bytes < 1024 * 1024)
                return $"{bytes / 1024.0:F2} KB";
            else if (bytes < 1024 * 1024 * 1024)
                return $"{bytes / (1024.0 * 1024):F2} MB";
            else
                return $"{bytes / (1024.0 * 1024 * 1024):F2} GB";
        }

        private void dgFiles_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (dgFiles.SelectedItem == null)
                return;

            var selectedFile = dgFiles.SelectedItem as PakFileInfo;
            if (selectedFile == null)
                return;

            if (selectedFile.OriginalBytes > 0)
            {
                txtOriginalBytes.Text = $"原始: {selectedFile.OriginalBytes:N0}";
            }
            else
            {
                txtOriginalBytes.Text = "原始: 未知";
            }

            if (chkAutoFill.IsChecked == true)
            {
                if (selectedFile.OriginalBytes > 0)
                {
                    txtTargetBytes.Text = selectedFile.OriginalBytes.ToString("N0");
                }
                else if (selectedFile.TargetBytes > 0)
                {
                    txtTargetBytes.Text = selectedFile.TargetBytes.ToString("N0");
                }
            }
        }

        private void txtSearch_TextChanged(object sender, TextChangedEventArgs e)
        {
            FilterFiles();
        }

        private void btnSearch_Click(object sender, RoutedEventArgs e)
        {
            FilterFiles();
        }

        private void FilterFiles()
        {
            string keyword = txtSearch.Text.ToLower().Trim();

            if (string.IsNullOrEmpty(keyword))
            {
                dgFiles.ItemsSource = allFiles;
                return;
            }

            var filteredFiles = allFiles.Where(f =>
                f.FileName.ToLower().Contains(keyword)
            ).ToList();

            dgFiles.ItemsSource = filteredFiles;
        }

        private void btnRefresh_Click(object sender, RoutedEventArgs e)
        {
            LoadFiles();
        }

        private void btnRescan_Click(object sender, RoutedEventArgs e)
        {
            var result = MessageBox.Show(
                "重新扫描将更新所有pak文件的原始大小记录。\n\n这会覆盖之前的记录，确定要继续吗？",
                "确认",
                MessageBoxButton.YesNo,
                MessageBoxImage.Question);

            if (result == MessageBoxResult.Yes)
            {
                ScanAndSaveOriginalPakSizes();
                LoadFiles();
                txtStatus.Text = "状态: 已重新扫描并更新原始大小记录";
            }
        }

        private void btnFill_Click(object sender, RoutedEventArgs e)
        {
            if (dgFiles.SelectedItem == null)
            {
                MessageBox.Show("请先选择要补充字节的文件！", "提示");
                return;
            }

            var selectedFile = dgFiles.SelectedItem as PakFileInfo;
            if (selectedFile == null)
                return;

            string targetBytesStr = txtTargetBytes.Text.Replace(",", "").Replace("，", "").Trim();
            if (!long.TryParse(targetBytesStr, out long targetBytes) || targetBytes <= 0)
            {
                MessageBox.Show("请输入有效的目标字节数！", "提示");
                return;
            }

            long currentSize = selectedFile.CurrentBytes;

            if (currentSize > targetBytes)
            {
                MessageBox.Show($"文件大小超出目标值\n\n文件: {selectedFile.FileName}\n当前大小: {currentSize:N0} 字节\n目标大小: {targetBytes:N0} 字节\n\n无法补充字节（只能增加，不能减少）", "警告");
                return;
            }

            if (currentSize == targetBytes)
            {
                MessageBox.Show($"文件大小已符合要求\n\n文件: {selectedFile.FileName}\n当前大小: {currentSize:N0} 字节\n目标大小: {targetBytes:N0} 字节\n\n无需补充字节", "提示");
                return;
            }

            try
            {
                long bytesToAdd = targetBytes - currentSize;

                using (FileStream fs = new FileStream(selectedFile.FilePath, FileMode.Append, FileAccess.Write))
                {
                    byte[] buffer = new byte[4096];
                    long remaining = bytesToAdd;

                    while (remaining > 0)
                    {
                        int toWrite = (int)Math.Min(buffer.Length, remaining);
                        fs.Write(buffer, 0, toWrite);
                        remaining -= toWrite;
                    }
                }

                if (File.Exists(selectedFile.GameFilePath))
                {
                    File.Copy(selectedFile.FilePath, selectedFile.GameFilePath, true);
                }

                SaveReferenceBytes();

                MessageBox.Show($"补充字节完成\n\n文件: {selectedFile.FileName}\n\n补充前: {currentSize:N0} 字节\n补充后: {targetBytes:N0} 字节\n\n已补充: {bytesToAdd:N0} 字节\n\n已复制到游戏目录", "成功");

                LoadFiles();
            }
            catch (Exception ex)
            {
                MessageBox.Show($"补充字节失败：{ex.Message}", "错误");
            }
        }

        private void btnClose_Click(object sender, RoutedEventArgs e)
        {
            SaveReferenceBytes();
            this.Close();
        }

        private void btnCancel_Click(object sender, RoutedEventArgs e)
        {
            SaveReferenceBytes();
            this.Close();
        }
    }

    public class PakFileInfo
    {
        public string FileName { get; set; }
        public string FilePath { get; set; }
        public string CurrentSize { get; set; }
        public long CurrentBytes { get; set; }
        public string OriginalSize { get; set; }
        public long OriginalBytes { get; set; }
        public string TargetSize { get; set; }
        public long TargetBytes { get; set; }
        public string GameFilePath { get; set; }
    }
}
