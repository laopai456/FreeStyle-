using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media.Imaging;
using FS服装搭配专家v1._0.Core.Models;
using Microsoft.Win32;

namespace FS服装搭配专家v1._0.UI.Windows
{
    public partial class MapControl : UserControl
    {
        private List<MapM> allMaps = new List<MapM>();
        private MapM selectedMap = null;
        private string gameDirectory = string.Empty;
        private string configFilePath = string.Empty;
        private string mapLibraryPath = string.Empty;

        public MapControl()
        {
            InitializeComponent();
            InitializeConfig();
        }

        public MapControl(string gameDir) : this()
        {
            gameDirectory = gameDir;
        }

        private void InitializeConfig()
        {
            configFilePath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "config.ini");
            LoadConfig();
        }

        private void LoadConfig()
        {
            if (File.Exists(configFilePath))
            {
                try
                {
                    string[] lines = File.ReadAllLines(configFilePath);
                    foreach (string line in lines)
                    {
                        string trimmedLine = line.Trim();
                        if (trimmedLine.StartsWith("InstallDirectory="))
                        {
                            gameDirectory = trimmedLine.Substring("InstallDirectory=".Length);
                        }
                        else if (trimmedLine.StartsWith("MapLibraryPath="))
                        {
                            mapLibraryPath = trimmedLine.Substring("MapLibraryPath=".Length);
                            if (!string.IsNullOrEmpty(mapLibraryPath))
                            {
                                LoadMapsFromLibrary(mapLibraryPath);
                            }
                        }
                    }
                }
                catch
                {
                }
            }
        }

        private void SaveMapLibraryPath(string path)
        {
            try
            {
                List<string> lines = new List<string>();
                bool found = false;

                if (File.Exists(configFilePath))
                {
                    lines = File.ReadAllLines(configFilePath).ToList();
                    for (int i = 0; i < lines.Count; i++)
                    {
                        if (lines[i].Trim().StartsWith("MapLibraryPath="))
                        {
                            lines[i] = "MapLibraryPath=" + path;
                            found = true;
                            break;
                        }
                    }
                }

                if (!found)
                {
                    lines.Add("MapLibraryPath=" + path);
                }

                File.WriteAllLines(configFilePath, lines);
            }
            catch
            {
            }
        }

        private void LoadMapsFromLibrary(string mapLibraryPath)
        {
            if (string.IsNullOrEmpty(mapLibraryPath) || !Directory.Exists(mapLibraryPath))
            {
                txtStatus.Text = "地图库路径不存在";
                return;
            }

            allMaps.Clear();

            try
            {
                foreach (string folder in Directory.GetDirectories(mapLibraryPath))
                {
                    string mapName = Path.GetFileName(folder);
                    string pakPath = Path.Combine(folder, "stage02.pak");

                    if (!File.Exists(pakPath))
                        continue;

                    string previewPath = Directory.GetFiles(folder, "*.png")
                        .Concat(Directory.GetFiles(folder, "*.jpg"))
                        .FirstOrDefault();

                    if (previewPath == null)
                        continue;

                    allMaps.Add(new MapM
                    {
                        MapName = mapName,
                        PreviewPath = previewPath,
                        PakPath = pakPath,
                        FolderPath = folder
                    });
                }

                lstMaps.ItemsSource = null;
                lstMaps.ItemsSource = allMaps;
                txtStatus.Text = $"已加载 {allMaps.Count} 个地图";
            }
            catch (Exception ex)
            {
                txtStatus.Text = $"加载地图失败：{ex.Message}";
            }
        }

        private void lstMaps_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (lstMaps.SelectedItem == null)
                return;

            selectedMap = lstMaps.SelectedItem as MapM;
            if (selectedMap == null)
                return;

            txtMapName.Text = selectedMap.MapName;

            try
            {
                if (!string.IsNullOrEmpty(selectedMap.PreviewPath) && File.Exists(selectedMap.PreviewPath))
                {
                    BitmapImage bitmap = new BitmapImage();
                    bitmap.BeginInit();
                    bitmap.CacheOption = BitmapCacheOption.OnLoad;
                    bitmap.UriSource = new Uri(selectedMap.PreviewPath);
                    bitmap.EndInit();
                    imgPreview.Source = bitmap;
                }
            }
            catch
            {
                imgPreview.Source = null;
            }
        }

        private void btnBrowseLibrary_Click(object sender, RoutedEventArgs e)
        {
            OpenFolderDialog dialog = new OpenFolderDialog();
            dialog.Title = "选择地图库路径";

            if (!string.IsNullOrEmpty(mapLibraryPath) && Directory.Exists(mapLibraryPath))
            {
                dialog.InitialDirectory = mapLibraryPath;
            }

            if (dialog.ShowDialog() == true)
            {
                mapLibraryPath = dialog.FolderName;
                SaveMapLibraryPath(mapLibraryPath);
                LoadMapsFromLibrary(mapLibraryPath);
            }
        }

        private void btnRefreshLibrary_Click(object sender, RoutedEventArgs e)
        {
            if (!string.IsNullOrEmpty(mapLibraryPath))
            {
                LoadMapsFromLibrary(mapLibraryPath);
            }
        }

        private void btnSearch_Click(object sender, RoutedEventArgs e)
        {
            FilterMaps();
        }

        private void txtSearch_TextChanged(object sender, TextChangedEventArgs e)
        {
            FilterMaps();
        }

        private void FilterMaps()
        {
            string keyword = txtSearch.Text.ToLower().Trim();

            if (string.IsNullOrEmpty(keyword))
            {
                lstMaps.ItemsSource = allMaps;
                txtStatus.Text = $"共 {allMaps.Count} 个地图";
                return;
            }

            var filteredMaps = allMaps.Where(m =>
                m.MapName.ToLower().Contains(keyword)
            ).ToList();

            lstMaps.ItemsSource = filteredMaps;
            txtStatus.Text = $"找到 {filteredMaps.Count} 个地图";
        }

        private void btnApply_Click(object sender, RoutedEventArgs e)
        {
            if (selectedMap == null)
            {
                ShowMessage("请先选择要应用的地图！");
                return;
            }

            if (string.IsNullOrEmpty(gameDirectory) || !Directory.Exists(gameDirectory))
            {
                ShowMessage("无法获取游戏路径，请检查配置！");
                return;
            }

            string targetPak = Path.Combine(gameDirectory, "stage02.pak");

            try
            {
                File.Copy(selectedMap.PakPath, targetPak, true);
                txtStatus.Text = $"应用成功：{selectedMap.MapName}";
                ShowMessage($"地图「{selectedMap.MapName}」应用成功！");
            }
            catch (Exception ex)
            {
                txtStatus.Text = "应用失败";
                ShowMessage($"地图应用失败：{ex.Message}");
            }
        }

        private void ShowMessage(string message)
        {
            var dialog = new ConfirmDialog(message);
            dialog.ShowDialog();
        }
    }
}
