using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Threading;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Data;
using System.Windows.Media;
using System.Windows.Media.Animation;
using System.Windows.Media.Effects;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using EllipseShape = System.Windows.Shapes.Ellipse;
using FS服装搭配专家.Core.Config;
using FS服装搭配专家.Core.Models;
using FS服装搭配专家.Core.Services;
using LibVLCSharp.Shared;

namespace FS服装搭配专家.UI.Windows
{
    public partial class MainWindow : Window
    {
        private FridaBridge _bridge = new();
        private SkinManager skinManager;
        private bool _connected;
        private bool _titleGradientActive;
        private bool _isBorderless;
        private DateTime _lastTitleClick = DateTime.MinValue;
        private Storyboard _titleStoryboard;
        private string _gameDir = "";

        // 服装数据
        private List<ItemshopM> list = new();
        private List<ItemshopM> effectList = new();
        private Dictionary<string, ItemshopM> _itemDict = new(); // ItemCode → ItemshopM 快速查找
        private ICollectionView? _clothingView;
        private ICollectionView? _effectView;

        // ItemCode 前缀 → 类别名称映射
        private static readonly Dictionary<string, string> PrefixCategoryMap = new()
        {
            ["501"] = "发型",
            ["502"] = "套装上衣",
            ["503"] = "套装下衣",
            ["504"] = "上衣",
            ["505"] = "下衣",
            ["506"] = "鞋子",
            ["509"] = "饰品",
            ["510"] = "饰品",
            ["512"] = "手套",
            ["513"] = "手套",
            ["515"] = "装饰",
            ["516"] = "特殊装饰",
            ["814"] = "特效",
        };

        // 前缀类别 → 固定格子索引映射（非饰品类直接映射）
        private static readonly Dictionary<string, int> FixedSlotMap = new()
        {
            ["发型"] = 0,
            ["上衣"] = 1,
            ["套装上衣"] = 1,
            ["下衣"] = 2,
            ["套装下衣"] = 2,
            ["鞋子"] = 3,
        };

        // 饰品类前缀集合（分配到格子 4-9）
        private static readonly HashSet<string> AccessoryPrefixes = new() { "509", "510", "512", "513", "515", "516", "814" };

        /// <summary>
        /// 从 ItemCode 前缀推导类别名称
        /// </summary>
        private static string GetCategoryFromCode(string itemCode)
        {
            if (string.IsNullOrEmpty(itemCode) || itemCode.Length < 3) return "未知";
            var prefix = itemCode.Substring(0, 3);
            return PrefixCategoryMap.TryGetValue(prefix, out var cat) ? cat : "未知";
        }

        // 装备位配置（排除 hidden）
        private List<SlotConfigM> _slotConfig = new();

        // 每个装备位的状态：slotIdx -> (before, after)
        private Dictionary<int, SlotState> _slotStates = new();

        // 当前选中的装备位（用于从列表填入）
        private int _selectedSlotIdx = -1;

        // ========== 按钮状态机 ==========
        private enum FlowState { Refresh, SaveOrLoad, Confirm, Restore }
        private FlowState _flowState = FlowState.Refresh;

        // 按钮流光
        private Button? _breathingBtn;
        private DispatcherTimer? _btnBreathTimer;
        private int _btnBreathTick;
        private LinearGradientBrush? _btnBreathBrush;

        // 保存按钮常驻流光
        private DispatcherTimer? _saveGlowTimer;
        private int _saveGlowTick;

        private HashSet<Border> _breathingCards = new();
        private Dictionary<Border, SolidColorBrush> _breathingBrushes = new();
        private Dictionary<Border, DropShadowEffect> _breathingGlows = new();
        private DispatcherTimer? _breathingTimer;
        private int _breathingTick;
        private static readonly Color[] RainbowColors = new Color[]
        {
            Color.FromRgb(0xFF, 0x45, 0x45), // 红
            Color.FromRgb(0xFF, 0xA5, 0x00), // 橙
            Color.FromRgb(0xFF, 0xD7, 0x00), // 黄
            Color.FromRgb(0x00, 0xE6, 0x76), // 绿
            Color.FromRgb(0x00, 0xD4, 0xFF), // 青
            Color.FromRgb(0x66, 0x7E, 0xFF), // 蓝
            Color.FromRgb(0xC5, 0x8A, 0xF9), // 紫
        };

        // 当前角色标识（用于预设方案隔离）
        private string _currentCharName = "";  // 方案 key（人物名_角色名）
        private string _currentPlayerName = "";  // 人物名
        private string _currentCharType = "";    // 角色类型名（如 RUMI、RUKA）

        // 预设文件路径（AppData 持久化，不受构建输出目录清理影响）
        private static readonly string PresetFilePath = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
            "FS服装搭配专家", "presets.json");

        // 装备位 UI 元素引用（slotIdx → (iconBorder, dummy, infoPanel)）
        private Dictionary<int, (Border card, Border iconArea, StackPanel infoPanel)> _slotUI = new();

        // 搜索防抖
        private DispatcherTimer _searchDebounceTimer;

        // Hook 日志轮询
        private DispatcherTimer _hookLogTimer;
        private int _hookLogOffset;

        // 动态背景
        private double _bgAngle;
        private DispatcherTimer _bgTimer;
        private static Color BgColor1 = Color.FromRgb(0x1E, 0x1E, 0x1E);
        private static Color BgColor2 = Color.FromRgb(0x25, 0x25, 0x35);
        private static Color BgColor3 = Color.FromRgb(0x1A, 0x1A, 0x2E);

        // 视频背景
        private LibVLC? _libVLC;
        private LibVLCSharp.Shared.MediaPlayer? _mediaPlayer;
        private Media? _currentMedia;
        private WriteableBitmap? _videoBitmap;
        private IntPtr _videoBuffer;
        private int _videoBufferSize;
        private int _videoWidth, _videoHeight;
        private volatile bool _videoActive; // 安全标志：防止停止后回调竞态
        private byte _videoOverlayAlpha = 0xAA; // 视频模式 UI 覆盖层不透明度（从配置加载）

        // VLC 视频回调委托（必须保持引用，防止 GC 回收）
        private LibVLCSharp.Shared.MediaPlayer.LibVLCVideoFormatCb? _videoFormatCb;
        private LibVLCSharp.Shared.MediaPlayer.LibVLCVideoCleanupCb? _videoCleanupCb;
        private LibVLCSharp.Shared.MediaPlayer.LibVLCVideoLockCb? _lockVideoCb;
        private LibVLCSharp.Shared.MediaPlayer.LibVLCVideoUnlockCb? _unlockVideoCb;

        public MainWindow()
        {
            InitializeComponent();

            // 窗口状态变化时更新最大化按钮显示
            this.StateChanged += (s, e) =>
            {
                if (btnWinMax != null)
                    btnWinMax.Content = this.WindowState == WindowState.Maximized ? "❐" : "□";
            };

            // 窗口尺寸
            this.Width = 1440;
            this.Height = 768;
            this.WindowStartupLocation = WindowStartupLocation.CenterScreen;

            // 皮肤管理器
            skinManager = new SkinManager();

            // 从配置加载视频透明度
            _videoOverlayAlpha = (byte)(ConfigService.Instance.VideoOverlayOpacity / 100.0 * 255);

            // 立即应用主题资源（颜色/字体），确保 BuildSlotUI 的 FindResource 取到正确颜色
            ApplyThemeResources();

            // 延迟处理背景（bgBrush/bgStop 需要 XAML 可视树已构建）
            this.Loaded += (s, e) =>
            {
                ApplyThemeBackground();
                // 标题渐变默认启动
                StartTitleGradient();

                // 恢复无边框状态（必须在 Loaded 后，窗口 Handle 已创建）
                if (ConfigService.Instance.Borderless)
                {
                    chkBorderless.IsChecked = true;
                }
            };

            // 游戏目录
            InitGameDir();

            // 加载装备位配置
            _slotConfig = LoadSlotConfig().Where(s => !s.Hidden).ToList();

            // 初始化装备位状态
            foreach (var slot in _slotConfig)
                _slotStates[slot.Id] = new SlotState { SlotIdx = slot.Id };

            // 生成装备位 UI
            BuildSlotUI();

            // 保存按钮常驻流光
            StartSaveGlow();

            // 加载服装数据
            LoadItemshopData();

            // 搜索防抖
            _searchDebounceTimer = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(200) };
            _searchDebounceTimer.Tick += (s, e) =>
            {
                _searchDebounceTimer.Stop();
                DoSearch();
            };

            // 动态背景
            _bgAngle = 0;
            _bgTimer = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(50) };
            _bgTimer.Tick += AnimateBackground;
            _bgTimer.Start();

            // Hook 日志轮询（每2秒获取一次 JS hook 活动）
            _hookLogTimer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(2) };
            _hookLogTimer.Tick += async (s, e) =>
            {
                if (!_connected) return;
                try
                {
                    var lines = await _bridge.PollHookLogAsync(_hookLogOffset);
                    if (lines.Count > 0)
                    {
                        foreach (var line in lines)
                            AppendLog($"[Hook] {line}");
                        _hookLogOffset += lines.Count;
                    }
                }
                catch (Exception ex)
                {
                    AppendLog($"[Hook轮询异常] {ex.Message}");
                }
            };

            // 启动后自动检测游戏进程并连接
            this.Loaded += async (s, e) =>
            {
                await AutoConnectAsync();
            };

            // 日志回调
            _bridge.OnLog += msg => Dispatcher.Invoke(() =>
            {
                labStatus.Text = $"状态: {msg}";
                AppendLog(msg);
            });
        }

        // ========== 游戏目录 & 图片加载 ==========

        private void InitGameDir()
        {
            try
            {
                _gameDir = ConfigService.Instance.GameInstallDirectory;
                if (string.IsNullOrEmpty(_gameDir) || !Directory.Exists(_gameDir))
                {
                    var detected = ConfigService.Instance.AutoDetectGamePath();
                    if (!string.IsNullOrEmpty(detected))
                    {
                        _gameDir = detected;
                        ConfigService.Instance.SetGameInstallDirectory(detected);
                    }
                }
                Console.WriteLine($"游戏目录: {_gameDir}");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"InitGameDir失败: {ex.Message}");
            }
        }

        private string BuildImgPath(string itemCode, string pakNum)
        {
            var p = pakNum.Replace("*", "").Replace(".pak", "").Replace(".", "_").Trim();
            if (p == "1") p = "";
            return Path.Combine(AppDomain.CurrentDomain.BaseDirectory,
                AppConfig.Directories.Cookies, $"icon{p}_pak", $"u{itemCode}.png");
        }

        private void btnLoadImages_Click(object sender, RoutedEventArgs e)
        {
            if (string.IsNullOrEmpty(_gameDir) || !Directory.Exists(_gameDir))
            {
                ShowError("游戏目录未设置，无法加载图片");
                return;
            }
            if (list.Count == 0)
            {
                ShowError("服装列表为空，请先等待数据加载");
                return;
            }

            btnLoadImages.IsEnabled = false;
            btnLoadImages.Content = "加载中...";

            Task.Run(() => LoadImages()).ContinueWith(t =>
            {
                Dispatcher.Invoke(() =>
                {
                    btnLoadImages.IsEnabled = true;
                    btnLoadImages.Content = "📷 加载图片";
                    if (t.Exception != null)
                        ShowError($"加载图片失败: {t.Exception.InnerException?.Message}");
                });
            });
        }

        private void LoadImages()
        {
            try
            {
                string cookiesDir = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, AppConfig.Directories.Cookies);
                Directory.CreateDirectory(cookiesDir);

                string resourcesExePath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory,
                    AppConfig.Directories.Pack, AppConfig.Files.ResourcesExe);

                if (!File.Exists(resourcesExePath))
                {
                    Dispatcher.Invoke(() => ShowError("找不到 resources.exe"));
                    return;
                }

                var pakNums = new HashSet<string>();
                foreach (var item in list)
                {
                    string pakNum = item.PakNum.Replace("*", "").Replace(".pak", "");
                    if (!string.IsNullOrEmpty(pakNum))
                        pakNums.Add(pakNum);
                }

                var paksToProcess = new List<string>();
                foreach (var pakNum in pakNums)
                {
                    string dirName = pakNum == "1" ? "icon_pak" : $"icon{pakNum}_pak";
                    string iconDir = Path.Combine(cookiesDir, dirName);
                    if (Directory.Exists(iconDir) && Directory.GetFiles(iconDir).Length > 0)
                        continue;

                    // pak=1 时游戏目录下文件名是 icon/icon.pak（没有数字1），其他 pak 是 icon{N}/icon{N}.pak
                    string filePart = pakNum == "1" ? "icon" : $"icon{pakNum}";
                    string sourcePath = Path.Combine(_gameDir, filePart);
                    if (!File.Exists(sourcePath))
                        sourcePath = Path.Combine(_gameDir, $"{filePart}.pak");
                    if (File.Exists(sourcePath))
                        paksToProcess.Add(pakNum);
                }

                int total = paksToProcess.Count;
                int done = 0;
                int success = 0;
                int skip = pakNums.Count - total;

                object lockObj = new object();

                Parallel.ForEach(paksToProcess, new ParallelOptions { MaxDegreeOfParallelism = 4 }, pakNum =>
                {
                    try
                    {
                        // pak=1 时游戏目录下文件名是 icon/icon.pak（没有数字1），destPath 也是 icon（不带1）
                        // 这样 resources.exe 解包输出目录为 icon_pak，与 BuildImgPath 一致
                        string filePart = pakNum == "1" ? "icon" : $"icon{pakNum}";
                        string sourcePath = Path.Combine(_gameDir, filePart);
                        if (!File.Exists(sourcePath))
                            sourcePath = Path.Combine(_gameDir, $"{filePart}.pak");
                        string destPath = Path.Combine(cookiesDir, filePart);

                        if (File.Exists(sourcePath))
                        {
                            File.Copy(sourcePath, destPath, true);

                            var psi = new ProcessStartInfo
                            {
                                FileName = resourcesExePath,
                                Arguments = $"\"{destPath}\" -byname .+\\.png",
                                UseShellExecute = false,
                                CreateNoWindow = true,
                                WindowStyle = ProcessWindowStyle.Hidden,
                                RedirectStandardOutput = true,
                                RedirectStandardError = true,
                                WorkingDirectory = AppDomain.CurrentDomain.BaseDirectory
                            };

                            using (var proc = Process.Start(psi))
                            {
                                proc.WaitForExit(30000);
                                if (!proc.HasExited) proc.Kill();
                            }

                            lock (lockObj)
                            {
                                success++;
                                done++;
                                if (done % 5 == 0)
                                {
                                    int c = done;
                                    Dispatcher.BeginInvoke(new Action(() =>
                                    {
                                        labLoadingStatus.Text = $"正在解包图片... {c}/{total}";
                                        labLoadingStatus.Visibility = Visibility.Visible;
                                    }));
                                }
                            }
                        }
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine($"解包 icon{pakNum} 失败: {ex.Message}");
                    }
                });

                // 更新所有 item 的 ImgPath
                foreach (var item in list)
                    item.ImgPath = BuildImgPath(item.ItemCode, item.PakNum);
                foreach (var item in effectList)
                    item.ImgPath = BuildImgPath(item.ItemCode, item.PakNum);

                int iconCount = list.Count(i => File.Exists(i.ImgPath));

                Dispatcher.Invoke(() =>
                {
                    labLoadingStatus.Visibility = Visibility.Collapsed;
                    ShowInfo($"图片加载完成！新解包: {success}, 跳过: {skip}, 有图标: {iconCount}/{list.Count}");
                    // 刷新装备位 UI
                    foreach (var slot in _slotConfig)
                        RefreshSlotRow(slot.Id);
                });
            }
            catch (Exception ex)
            {
                Console.WriteLine($"LoadImages失败: {ex.Message}");
                Dispatcher.Invoke(() => ShowError($"加载图片失败: {ex.Message}"));
            }
        }

        // ========== 服装数据加载 ==========

        private void LoadItemshopData()
        {
            var paths = new[]
            {
                Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "data", "itemshop.json"),
            };

            string jsonPath = paths.FirstOrDefault(File.Exists);
            if (jsonPath == null)
            {
                ShowError("未找到 itemshop.json，请先运行 update_itemshop.py");
                return;
            }

            try
            {
                var json = File.ReadAllText(jsonPath, Encoding.UTF8);
                var dict = JsonSerializer.Deserialize<Dictionary<string, JsonElement>>(json);
                if (dict == null) return;

                list.Clear();
                foreach (var kv in dict)
                {
                    var v = kv.Value;
                    var name = v.TryGetProperty("name", out var nameEl) ? nameEl.GetString() ?? "" : "";

                    // 跳过空名称的道具
                    if (string.IsNullOrWhiteSpace(name)) continue;

                    var item = new ItemshopM
                    {
                        ItemCode = kv.Key,
                        PakNum = v.TryGetProperty("pak", out var pakEl) ? pakEl.GetString() ?? "" : "",
                        ItemName = name,
                        EffectCode = v.TryGetProperty("effect", out var effEl) ? (effEl.ValueKind == JsonValueKind.Null ? "无" : effEl.GetString() ?? "无") : "无",
                    };
                    item.ImgPath = BuildImgPath(item.ItemCode, item.PakNum);
                    list.Add(item);
                }

                list.Reverse();
                effectList = list.Where(i => i.EffectCode != "无" && !string.IsNullOrEmpty(i.EffectCode)).ToList();

                // 构建快速查找字典
                _itemDict = list.ToDictionary(i => i.ItemCode, i => i);

                // 用 CollectionView 绑定，搜索时只改 Filter 不重建列表
                _clothingView = CollectionViewSource.GetDefaultView(list);
                _effectView = CollectionViewSource.GetDefaultView(effectList);
                lstClothing.ItemsSource = _clothingView;
                lstEffect.ItemsSource = _effectView;

                ShowInfo($"服装数据加载成功，共 {list.Count} 件服装，其中 {effectList.Count} 件有特效");
            }
            catch (Exception ex)
            {
                ShowError($"加载服装数据失败: {ex.Message}");
            }
        }

        // ========== 搜索 ==========

        private void txtSearch_TextChanged(object sender, TextChangedEventArgs e)
        {
            _searchDebounceTimer.Stop();
            _searchDebounceTimer.Start();
        }

        private void DoSearch()
        {
            var keyword = txtSearch.Text.Trim();

            if (string.IsNullOrEmpty(keyword))
            {
                if (_clothingView != null) _clothingView.Filter = null;
                if (_effectView != null) _effectView.Filter = null;
                return;
            }

            // 用 CollectionView.Filter 过滤，不替换 ItemsSource，不重建 UI
            Predicate<object> filter = obj =>
            {
                if (obj is ItemshopM item)
                {
                    return (item.ItemCode?.IndexOf(keyword, StringComparison.OrdinalIgnoreCase) >= 0) ||
                           (item.ItemName?.IndexOf(keyword, StringComparison.OrdinalIgnoreCase) >= 0);
                }
                return false;
            };

            if (_clothingView != null) _clothingView.Filter = filter;
            if (_effectView != null) _effectView.Filter = filter;
        }

        // ========== 装备位槽位 UI ==========

        /// <summary>
        /// 生成 4×2 装备位网格
        /// </summary>
        private void BuildSlotUI()
        {
            var grid = this.FindName("slotGrid") as Grid ?? slotGrid;
            grid.Children.Clear();
            grid.ColumnDefinitions.Clear();
            grid.RowDefinitions.Clear();

            for (int c = 0; c < 5; c++)
                grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            for (int r = 0; r < 2; r++)
                grid.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });

            for (int i = 0; i < _slotConfig.Count; i++)
            {
                var slotCfg = _slotConfig[i];
                int col = i % 5;
                int row = i / 5;

                var (slotBorder, iconBorder, infoPanel) = CreateSlotCard(slotCfg);
                Grid.SetRow(slotBorder, row);
                Grid.SetColumn(slotBorder, col);
                grid.Children.Add(slotBorder);

                _slotUI[slotCfg.Id] = (slotBorder, iconBorder, infoPanel);
            }
        }

        private (Border card, Border iconArea, StackPanel infoPanel) CreateSlotCard(SlotConfigM slotCfg)
        {
            var card = new Border
            {
                Margin = new Thickness(4),
                BorderThickness = new Thickness(1),
                CornerRadius = new CornerRadius(6),
                Cursor = Cursors.Hand,
                Tag = slotCfg.Id,
            };
            card.SetResourceReference(Border.BackgroundProperty, "SlotCardBackgroundColor");
            card.SetResourceReference(Border.BorderBrushProperty, "CardBorderColor");
            // 强制卡片宽高比接近1:1（方形）
            card.SizeChanged += (s, e) =>
            {
                if (s is FrameworkElement fe && fe.ActualWidth > 0)
                    fe.MaxHeight = fe.ActualWidth * 1.15;
            };

            var inner = new Grid();
            inner.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });   // 三行文字
            inner.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) }); // 图标

            // === 三行文字区 ===
            var infoPanel = new StackPanel
            {
                Margin = new Thickness(8, 6, 8, 4),
                Orientation = Orientation.Vertical,
            };

            // 第1行：固定分类名
            var categoryLabel = new TextBlock
            {
                Text = slotCfg.Name,
                FontSize = 11,
                FontWeight = FontWeights.Bold,
            };
            categoryLabel.SetResourceReference(TextBlock.ForegroundProperty, "SlotCategoryTextColor");
            infoPanel.Children.Add(categoryLabel);

            // 第2行：道具名称（初始空）
            var itemNameLabel = new TextBlock
            {
                Text = "",
                FontSize = 10,
                TextTrimming = TextTrimming.CharacterEllipsis,
                Margin = new Thickness(0, 2, 0, 0),
            };
            itemNameLabel.SetResourceReference(TextBlock.ForegroundProperty, "SlotItemNameTextColor");
            itemNameLabel.SetValue(FrameworkElement.NameProperty, $"itemName_{slotCfg.Id}");
            infoPanel.Children.Add(itemNameLabel);

            // 第3行：特效（初始空）
            var effectLabel = new TextBlock
            {
                Text = "",
                FontSize = 9,
                TextTrimming = TextTrimming.CharacterEllipsis,
                Margin = new Thickness(0, 1, 0, 0),
            };
            effectLabel.SetResourceReference(TextBlock.ForegroundProperty, "SlotEffectTextColor");
            effectLabel.SetValue(FrameworkElement.NameProperty, $"effect_{slotCfg.Id}");
            infoPanel.Children.Add(effectLabel);

            Grid.SetRow(infoPanel, 0);
            inner.Children.Add(infoPanel);

            // === 图标区（居中等比） ===
            var iconBorder = new Border
            {
                Margin = new Thickness(4, 0, 4, 4),
                CornerRadius = new CornerRadius(4),
                BorderThickness = new Thickness(1),
                HorizontalAlignment = HorizontalAlignment.Stretch,
                VerticalAlignment = VerticalAlignment.Stretch,
                Child = new TextBlock
                {
                    Text = "空",
                    FontSize = 14,
                    HorizontalAlignment = HorizontalAlignment.Center,
                    VerticalAlignment = VerticalAlignment.Center,
                },
            };
            iconBorder.SetResourceReference(Border.BackgroundProperty, "SlotIconBackgroundColor");
            iconBorder.SetResourceReference(Border.BorderBrushProperty, "CardBorderColor");
            // 空字颜色
            ((TextBlock)iconBorder.Child).SetResourceReference(TextBlock.ForegroundProperty, "SlotEmptyTextColor");
            Grid.SetRow(iconBorder, 1);
            inner.Children.Add(iconBorder);

            card.Child = inner;

            card.MouseLeftButtonDown += (s, e) => SelectSlot(slotCfg.Id);
            iconBorder.MouseLeftButtonDown += (s, e) => SelectSlot(slotCfg.Id);

            return (card, iconBorder, infoPanel);
        }

        private void SelectSlot(int slotIdx)
        {
            _selectedSlotIdx = slotIdx;

            foreach (var slot in _slotConfig)
            {
                if (!_slotUI.ContainsKey(slot.Id)) continue;
                var (_, slotIconArea, _) = _slotUI[slot.Id];

                // 选中：主题选中色；未选中：主题边框色
                if (slot.Id == slotIdx)
                {
                    slotIconArea.BorderBrush = (Brush)FindResource("SlotSelectedBorderColor");
                    slotIconArea.BorderThickness = new Thickness(2);
                    var cfg = _slotConfig.FirstOrDefault(s => s.Id == slotIdx);
                    ShowInfo($"已选中 [{cfg?.Name}]，点击左侧服装设置替换目标");
                }
                else
                {
                    slotIconArea.BorderBrush = (Brush)FindResource("CardBorderColor");
                    slotIconArea.BorderThickness = new Thickness(1);
                }
            }
        }

        private void StartBreathing(Border card)
        {
            if (_breathingCards.Contains(card)) return;

            card.BorderThickness = new Thickness(2);

            var brush = new SolidColorBrush(RainbowColors[0]);
            card.BorderBrush = brush;

            var glow = new DropShadowEffect
            {
                BlurRadius = 25,
                ShadowDepth = 0,
                Opacity = 0.7,
                Color = RainbowColors[0]
            };
            card.Effect = glow;

            _breathingCards.Add(card);
            _breathingBrushes[card] = brush;
            _breathingGlows[card] = glow;

            // 首次启动时开启全局定时器
            if (_breathingTimer == null)
            {
                _breathingTick = 0;
                _breathingTimer = new DispatcherTimer
                {
                    Interval = TimeSpan.FromMilliseconds(80)
                };
                _breathingTimer.Tick += BreathingTimer_Tick;
                _breathingTimer.Start();
            }
        }

        private void BreathingTimer_Tick(object? sender, EventArgs e)
        {
            _breathingTick++;
            // 80ms × 6 ≈ 480ms 每色段，7 色 ≈ 3.36 秒一轮
            int idx = (_breathingTick / 6) % RainbowColors.Length;
            // 在两个颜色之间插值实现平滑过渡
            int nextIdx = (idx + 1) % RainbowColors.Length;
            double t = (_breathingTick % 6) / 6.0;

            Color c = InterpolateColor(RainbowColors[idx], RainbowColors[nextIdx], t);

            // 发光脉冲：正弦波 0.3 ~ 1.0
            double pulse = 0.3 + 0.7 * (Math.Sin(_breathingTick * 0.12) * 0.5 + 0.5);

            foreach (var card in _breathingCards)
            {
                if (_breathingBrushes.TryGetValue(card, out var brush))
                    brush.Color = c;
                if (_breathingGlows.TryGetValue(card, out var glow))
                {
                    glow.Color = c;
                    glow.Opacity = pulse;
                }
            }
        }

        private void StopBreathingFor(Border card)
        {
            if (!_breathingCards.Contains(card)) return;
            _breathingCards.Remove(card);
            _breathingBrushes.Remove(card);
            _breathingGlows.Remove(card);

            card.Effect = null;
            card.BorderBrush = (Brush)FindResource("CardBorderColor");
            card.BorderThickness = new Thickness(1);

            // 所有卡片都停了就关定时器
            if (_breathingCards.Count == 0 && _breathingTimer != null)
            {
                _breathingTimer.Stop();
                _breathingTimer = null;
            }
        }

        // ========== 按钮状态机：锁定/解锁 + 呼吸灯 ==========

        private void TransitionTo(FlowState state)
        {
            _flowState = state;
            StopBtnBreathing();

            // 全部锁定（保存按钮除外，始终可点）
            btnRefresh.IsEnabled = false;
            btnLoadPreset.IsEnabled = false;
            btnConfirm.IsEnabled = false;
            btnRestore.IsEnabled = false;

            // 根据状态解锁目标按钮 + 开呼吸灯
            switch (state)
            {
                case FlowState.Refresh:
                    btnRefresh.IsEnabled = true;
                    StartBtnBreathing(btnRefresh);
                    break;
                case FlowState.SaveOrLoad:
                    // 判断有没有已保存方案
                    bool hasPreset = HasPresetForCurrentChar();
                    if (hasPreset)
                    {
                        btnLoadPreset.IsEnabled = true;
                        StartBtnBreathing(btnLoadPreset);
                    }
                    else
                    {
                        StartBtnBreathing(btnSavePreset);
                    }
                    break;
                case FlowState.Confirm:
                    btnConfirm.IsEnabled = true;
                    StartBtnBreathing(btnConfirm);
                    break;
                case FlowState.Restore:
                    btnRestore.IsEnabled = true;
                    StartBtnBreathing(btnRestore);
                    break;
            }
        }

        private bool HasPresetForCurrentChar()
        {
            if (string.IsNullOrEmpty(_currentCharName)) return false;
            var data = LoadPresetFile();
            return data.ContainsKey(_currentCharName);
        }

        private void StartBtnBreathing(Button btn)
        {
            // 清除 VSM 对模板 ButtonBorder.Background 的动画持有（MouseOver/Pressed 的 HoldEnd 会压制 local value，
            // 导致按钮被点过一次后流光失效）。同时清除按钮自身 Background 的动画持有。
            btn.ApplyTemplate();
            if (btn.Template?.FindName("ButtonBorder", btn) is Border tplBorder)
                tplBorder.BeginAnimation(Border.BackgroundProperty, null);
            btn.BeginAnimation(Button.BackgroundProperty, null);

            _breathingBtn = btn;
            _btnBreathTick = 0;

            // 复用 LinearGradientBrush，每帧只改 GradientStops（避免每帧 new 对象导致渲染挂起/泄漏）
            _btnBreathBrush = new LinearGradientBrush
            {
                StartPoint = new Point(0, 0.5),
                EndPoint = new Point(1, 0.5)
            };
            for (int i = 0; i < 5; i++)
                _btnBreathBrush.GradientStops.Add(new GradientStop(Colors.Transparent, 0));
            btn.Background = _btnBreathBrush;

            // 单例 timer：Tick 只挂一次（命名方法，避免每次 Start 重复订阅 + lambda 闭包泄漏）
            if (_btnBreathTimer == null)
            {
                _btnBreathTimer = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(40) };
                _btnBreathTimer.Tick += BtnBreathTimer_Tick;
            }
            _btnBreathTimer.Start();
        }

        private void BtnBreathTimer_Tick(object? sender, EventArgs e)
        {
            if (_breathingBtn == null || _btnBreathBrush == null) return;
            _btnBreathTick++;
            // 流光高亮带从左到右滑动（不做缩放）
            double pos = (_btnBreathTick * 0.04) % 1.0;
            double band = 0.5;
            double lo = pos - band / 2;
            double hi = pos + band / 2;
            var stops = _btnBreathBrush.GradientStops;
            stops[0].Color = Color.FromArgb(0x20, 0x66, 0x7E, 0xEA); stops[0].Offset = 0;
            stops[1].Color = Color.FromArgb(0x90, 0x66, 0x7E, 0xEA); stops[1].Offset = Math.Max(0, lo);
            stops[2].Color = Color.FromArgb(0xD0, 0xC5, 0x8A, 0xF9); stops[2].Offset = Math.Max(0, pos);
            stops[3].Color = Color.FromArgb(0x90, 0x6D, 0xD5, 0xFA); stops[3].Offset = Math.Min(1, hi);
            stops[4].Color = Color.FromArgb(0x20, 0x6D, 0xD5, 0xFA); stops[4].Offset = 1;
        }

        private void StopBtnBreathing()
        {
            if (_btnBreathTimer != null)
                _btnBreathTimer.Stop();  // 单例复用，不置 null
            if (_breathingBtn != null)
            {
                _breathingBtn.BeginAnimation(Button.BackgroundProperty, null);
                _breathingBtn.Background = (Brush)FindResource("ButtonGlassColor");
                _breathingBtn = null;
            }
            _btnBreathBrush = null;
        }

        private void StartSaveGlow()
        {
            if (_saveGlowTimer != null) return;
            _saveGlowTick = 0;
            btnSavePreset.RenderTransformOrigin = new Point(0.5, 0.5);

            _saveGlowTimer = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(40) };
            _saveGlowTimer.Tick += (s, e) =>
            {
                _saveGlowTick++;
                double pos = (_saveGlowTick * 0.04) % 1.0;
                var brush = new LinearGradientBrush
                {
                    StartPoint = new Point(0, 0.5),
                    EndPoint = new Point(1, 0.5)
                };
                double band = 0.5;
                double lo = pos - band / 2;
                double hi = pos + band / 2;
                brush.GradientStops.Add(new GradientStop(Color.FromArgb(0x20, 0x66, 0x7E, 0xEA), 0));
                brush.GradientStops.Add(new GradientStop(Color.FromArgb(0x90, 0x66, 0x7E, 0xEA), Math.Max(0, lo)));
                brush.GradientStops.Add(new GradientStop(Color.FromArgb(0xD0, 0xC5, 0x8A, 0xF9), Math.Max(0, pos)));
                brush.GradientStops.Add(new GradientStop(Color.FromArgb(0x90, 0x6D, 0xD5, 0xFA), Math.Min(1, hi)));
                brush.GradientStops.Add(new GradientStop(Color.FromArgb(0x20, 0x6D, 0xD5, 0xFA), 1));
                btnSavePreset.Background = brush;
            };
            _saveGlowTimer.Start();
        }

        private void RefreshSlotRow(int slotIdx)
        {
            if (!_slotUI.ContainsKey(slotIdx)) return;
            var (slotCard, iconArea, infoPanel) = _slotUI[slotIdx];

            var state = _slotStates.ContainsKey(slotIdx) ? _slotStates[slotIdx] : null;
            if (state == null) return;

            // 确定显示内容：After 优先，否则 Before
            var displayItem = state.After ?? state.Before;

            if (displayItem != null)
            {
                iconArea.Child = CreateIconElement(displayItem);
                iconArea.ToolTip = displayItem.ItemName;
                iconArea.BorderBrush = (Brush)FindResource("SlotSelectedBorderColor");
                iconArea.BorderThickness = new Thickness(2);

                // 更新三行文字
                // 第1行：固定分类名（从 slot_config）
                if (infoPanel.Children.Count > 0 && infoPanel.Children[0] is TextBlock catBlock)
                {
                    var cfg = _slotConfig.FirstOrDefault(s => s.Id == slotIdx);
                    catBlock.Text = cfg?.Name ?? "未知";
                }
                // 第2行：道具名称（children[1]）
                if (infoPanel.Children.Count > 1 && infoPanel.Children[1] is TextBlock nameBlock)
                {
                    nameBlock.Text = displayItem.ItemName ?? "";
                }
                // 第3行：特效（children[2]）——统一三级辅助色
                if (infoPanel.Children.Count > 2 && infoPanel.Children[2] is TextBlock effectBlock)
                {
                    effectBlock.Text = displayItem.EffectDisplay;
                    effectBlock.Foreground = (Brush)FindResource("SlotEffectTextColor");
                }
            }
            else
            {
                iconArea.Child = new TextBlock
                {
                    Text = "空",
                    FontSize = 16,
                    Foreground = (Brush)FindResource("SlotEmptyTextColor"),
                    HorizontalAlignment = HorizontalAlignment.Center,
                    VerticalAlignment = VerticalAlignment.Center,
                };
                iconArea.ToolTip = null;
                iconArea.BorderBrush = (Brush)FindResource("CardBorderColor");
                iconArea.BorderThickness = new Thickness(1);

                // 清空道具名和特效行，分类名恢复为 slot_config 默认
                var cfg = _slotConfig.FirstOrDefault(s => s.Id == slotIdx);
                if (infoPanel.Children.Count > 0 && infoPanel.Children[0] is TextBlock catBlock)
                    catBlock.Text = cfg?.Name ?? "未知";
                if (infoPanel.Children.Count > 1 && infoPanel.Children[1] is TextBlock nameBlock)
                    nameBlock.Text = "";
                if (infoPanel.Children.Count > 2 && infoPanel.Children[2] is TextBlock effectBlock)
                    effectBlock.Text = "";
            }

            // ===== 呼吸灯：有变更（After != null）的槽位亮起 =====
            if (state.After != null)
            {
                StartBreathing(slotCard);
            }
            else
            {
                StopBreathingFor(slotCard);
            }
        }

        private UIElement CreateIconElement(ItemshopM item)
        {
            bool hasIcon = !string.IsNullOrEmpty(item.ImgPath) && File.Exists(item.ImgPath);
            if (hasIcon)
            {
                try
                {
                    var bitmap = new BitmapImage();
                    bitmap.BeginInit();
                    bitmap.UriSource = new Uri(item.ImgPath);
                    bitmap.CacheOption = BitmapCacheOption.OnLoad;
                    // 不设 DecodePixelWidth/Height，加载原图保持清晰
                    bitmap.EndInit();

                    var img = new Image
                    {
                        Source = bitmap,
                        Stretch = Stretch.Uniform,  // 等比缩放，不变形
                        HorizontalAlignment = HorizontalAlignment.Center,
                        VerticalAlignment = VerticalAlignment.Center,
                        MaxWidth = 72,
                        MaxHeight = 72,
                        Margin = new Thickness(2),
                    };
                    RenderOptions.SetBitmapScalingMode(img, BitmapScalingMode.HighQuality);
                    return img;
                }
                catch { }
            }

            // 无图标：显示名称
            return new TextBlock
            {
                Text = (item.ItemName?.Length > 6 ? item.ItemName.Substring(0, 6) + "…" : item.ItemName) ?? item.ItemCode,
                FontSize = 10,
                Foreground = new SolidColorBrush(Color.FromRgb(0xDC, 0xDC, 0xDC)),
                TextWrapping = TextWrapping.Wrap,
                HorizontalAlignment = HorizontalAlignment.Center,
                VerticalAlignment = VerticalAlignment.Center,
                TextAlignment = TextAlignment.Center,
            };
        }

        // ========== 服装列表操作 ==========

        private void lstClothing_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (lstClothing.SelectedItem == null) return;
            var item = lstClothing.SelectedItem as ItemshopM;
            if (item == null) return;

            // 如果没有选中槽位，提示用户先选中
            if (_selectedSlotIdx < 0)
            {
                ShowError("请先点击右侧装备位选中要替换的槽位");
                lstClothing.UnselectAll();
                return;
            }

            // 填入选中的槽位
            var state = _slotStates.ContainsKey(_selectedSlotIdx) ? _slotStates[_selectedSlotIdx] : null;
            if (state == null) return;

            state.After = item;
            RefreshSlotRow(_selectedSlotIdx);

            var cfg = _slotConfig.FirstOrDefault(s => s.Id == _selectedSlotIdx);
            ShowInfo($"[{cfg?.Name}] → {item.ItemName}");

            // 不再自动跳到下一个槽位，避免覆盖其他槽位的标签

            lstClothing.UnselectAll();
        }

        private void lstEffect_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (lstEffect.SelectedItem == null) return;
            var item = lstEffect.SelectedItem as ItemshopM;
            if (item == null) return;

            if (_selectedSlotIdx < 0)
            {
                ShowError("请先点击右侧装备位选中要替换的槽位");
                lstEffect.UnselectAll();
                return;
            }

            var state = _slotStates.ContainsKey(_selectedSlotIdx) ? _slotStates[_selectedSlotIdx] : null;
            if (state == null) return;

            // 特效列表选择 = 完整道具替换（特效绑定在道具属性表中，必须替换ItemCode才能生效）
            state.After = item;
            RefreshSlotRow(_selectedSlotIdx);

            var cfg = _slotConfig.FirstOrDefault(s => s.Id == _selectedSlotIdx);
            ShowInfo($"[{cfg?.Name}] → {item.ItemName} (含特效)");

            lstEffect.UnselectAll();
        }

        private void TabClothing_Checked(object sender, RoutedEventArgs e)
        {
            if (lstClothing == null || lstEffect == null) return;
            lstClothing.Visibility = Visibility.Visible;
            lstEffect.Visibility = Visibility.Collapsed;
        }

        private void TabEffect_Checked(object sender, RoutedEventArgs e)
        {
            if (lstClothing == null || lstEffect == null) return;
            lstClothing.Visibility = Visibility.Collapsed;
            lstEffect.Visibility = Visibility.Visible;
        }

        // ========== 标题渐变 ==========

        private void txtTitle_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
        {
            // 标题渐变默认启动，点击不再切换
        }

        private void StartTitleGradient()
        {
            if (_titleGradientActive) return;
            _titleGradientActive = true;

            // 从 XAML 资源加载 Storyboard 并启动
            _titleStoryboard = (Storyboard)FindResource("TitleFlowAnimation");
            txtTitle.Foreground = (LinearGradientBrush)FindResource("TitleGradientBrush");

            // Storyboard 的 TargetName 在模板中已绑定 TitleGradientBg
            // 需要改为操作 txtTitle 内的画刷
            var gradient = new LinearGradientBrush
            {
                StartPoint = new Point(0, 0.5),
                EndPoint = new Point(1, 0.5)
            };
            gradient.GradientStops.Add(new GradientStop(Color.FromRgb(0x66, 0x7E, 0xEA), 0));
            gradient.GradientStops.Add(new GradientStop(Color.FromRgb(0x6D, 0xD5, 0xFA), 0.5));
            gradient.GradientStops.Add(new GradientStop(Color.FromRgb(0xC5, 0x8A, 0xF9), 1));
            txtTitle.Resources["TitleGradientBg"] = gradient;
            txtTitle.RegisterName("TitleGradientBg", gradient);
            txtTitle.Foreground = gradient;

            var sb = new Storyboard { RepeatBehavior = RepeatBehavior.Forever };
            var anim1 = new PointAnimation(new Point(-1, 0.5), new Point(2, 0.5),
                TimeSpan.FromSeconds(5)) { AutoReverse = true };
            Storyboard.SetTargetName(anim1, "TitleGradientBg");
            Storyboard.SetTargetProperty(anim1, new PropertyPath(LinearGradientBrush.StartPointProperty));
            sb.Children.Add(anim1);

            var anim2 = new PointAnimation(new Point(0, 0.5), new Point(3, 0.5),
                TimeSpan.FromSeconds(5)) { AutoReverse = true };
            Storyboard.SetTargetName(anim2, "TitleGradientBg");
            Storyboard.SetTargetProperty(anim2, new PropertyPath(LinearGradientBrush.EndPointProperty));
            sb.Children.Add(anim2);

            sb.Begin(txtTitle, true);
            _titleStoryboard = sb;
        }

        private void StopTitleGradient()
        {
            if (!_titleGradientActive) return;
            _titleGradientActive = false;

            if (_titleStoryboard != null)
            {
                _titleStoryboard.Stop(txtTitle);
                _titleStoryboard = null;
            }
            txtTitle.Foreground = (Brush)FindResource("TitleTextColor");
        }


        // ========== 按钮事件 ==========

        private async Task AutoConnectAsync()
        {
            try
            {
                await _bridge.EnsureEngineAsync();
                var pid = await _bridge.ConnectGameAsync();
                _connected = true;
                btnLaunch.Content = $"🚀 PID {pid}";
                ShowInfo($"已自动连接 (PID {pid})");
                AppendLog($"[自动连接] PID {pid}");
                _hookLogOffset = 0;
                _hookLogTimer.Start();
                TransitionTo(FlowState.Refresh);
            }
            catch
            {
                // 没有检测到运行中的游戏，保持启动按钮可点击
                btnLaunch.Content = "🚀 启动游戏";
                btnLaunch.IsEnabled = true;
            }
        }

        private async void btnLaunch_Click(object sender, RoutedEventArgs e)
        {
            if (string.IsNullOrEmpty(_gameDir) || !Directory.Exists(_gameDir))
            {
                ShowError("游戏目录未设置，无法启动游戏");
                return;
            }
            try
            {
                btnLaunch.IsEnabled = false;
                btnLaunch.Content = "连接中...";
                await _bridge.EnsureEngineAsync();

                // 先尝试直接连接（游戏可能已在运行）
                int pid;
                try
                {
                    pid = await _bridge.ConnectGameAsync();
                    AppendLog($"[连接] PID {pid}（检测到已运行的游戏）");
                }
                catch
                {
                    // 连接失败，启动游戏
                    btnLaunch.Content = "启动中...";
                    var launchPid = await _bridge.LaunchGameAsync(_gameDir);
                    AppendLog($"[启动] PID {launchPid}");

                    btnLaunch.Content = "连接中...";
                    pid = await _bridge.ConnectGameAsync();
                }

                _connected = true;
                btnLaunch.Content = $"🚀 PID {pid}";
                ShowInfo($"已连接 (PID {pid})");
                AppendLog($"[连接] PID {pid}");
                _hookLogOffset = 0;
                _hookLogTimer.Start();
                TransitionTo(FlowState.Refresh);
            }
            catch (Exception ex)
            {
                ShowError($"启动/连接失败: {ex.Message}");
                btnLaunch.Content = "🚀 启动游戏";
                btnLaunch.IsEnabled = true;
            }
        }

        private async void btnRefresh_Click(object sender, RoutedEventArgs e)
        {
            if (!_connected) { ShowError("请先连接游戏"); return; }
            StopBtnBreathing();
            try
            {
                // 先读取当前已收集的穿搭数据
                var (slots, hint) = await _bridge.ReadCurrentSlotsAsync();

                if (slots.Count == 0)
                {
                    ShowError("未收集到穿搭数据。请先进一次房间让游戏加载装备，然后再点刷新");
                    return;
                }

                // 读取成功后重置收集状态，下次进房间会重新收集（解决角色切换后数据不更新的问题）
                await _bridge.RecollectAsync();

                // 清空 before
                foreach (var st in _slotStates.Values)
                    st.Before = null;

                // === 两阶段匹配 ===
                // 阶段1：slot 0-3 精确匹配（发型/上衣/下衣/鞋子）
                // 阶段2：slot 4-9 依次展示（所有饰品/装饰/背部/手套，按优先级排序填入）

                // 固定 slot 的 prefix 映射
                var fixedSlotMap = new Dictionary<int, string[]>
                {
                    [0] = new[] { "501" },
                    [1] = new[] { "502", "504" },
                    [2] = new[] { "503", "505" },
                    [3] = new[] { "506" },
                };

                // 饰品/装饰类前缀及其优先级（数值越小优先级越高，手套最低）
                var accPrefixPriority = new Dictionary<string, int>
                {
                    ["509"] = 0, ["510"] = 0,   // 饰品
                    ["514"] = 1, ["814"] = 1,   // 背部/翅膀
                    ["515"] = 2, ["516"] = 2,   // 装饰
                    ["512"] = 3, ["513"] = 3,   // 手套（最低）
                };
                var accPrefixes = new HashSet<string>(accPrefixPriority.Keys);

                var assignedCodes = new HashSet<string>();
                var accItems = new List<(string code, string name, string pak, int priority)>();
                var skippedCodes = new List<string>(); // 被跳过的道具（c8xx 或未知前缀）

                // 日志：原始数据
                AppendLog($"[刷新] 收到 {slots.Count} 个道具: {string.Join(", ", slots.Select(kv => kv.Value.Code.ToString()))}");

                foreach (var kv in slots)
                {
                    var codeStr = kv.Value.Code.ToString();
                    var prefix = codeStr.Length >= 3 ? codeStr.Substring(0, 3) : "";

                    // 跳过角色基础（c800/c801 等）
                    if (codeStr.StartsWith("c", StringComparison.OrdinalIgnoreCase))
                    {
                        skippedCodes.Add($"{codeStr}(角色基础)");
                        continue;
                    }
                    if (assignedCodes.Contains(codeStr)) continue;

                    // 阶段1：精确匹配固定 slot
                    int? fixedSlot = null;
                    foreach (var (slotId, prefixes) in fixedSlotMap)
                    {
                        if (prefixes.Contains(prefix) && _slotStates[slotId].Before == null)
                        {
                            fixedSlot = slotId;
                            break;
                        }
                    }

                    if (fixedSlot != null)
                    {
                        assignedCodes.Add(codeStr);
                        _itemDict.TryGetValue(codeStr, out var localItem);
                        var displayName = kv.Value.Name;
                        if (displayName.StartsWith("未知") && localItem != null && !string.IsNullOrEmpty(localItem.ItemName))
                            displayName = localItem.ItemName;
                        _slotStates[fixedSlot.Value].Before = new ItemshopM
                        {
                            ItemCode = codeStr,
                            ItemName = displayName,
                            PakNum = kv.Value.Pak,
                            EffectCode = localItem?.EffectCode ?? "无",
                            ImgPath = BuildImgPath(codeStr, kv.Value.Pak),
                        };
                        AppendLog($"[刷新] 固定slot{fixedSlot} ← {codeStr}({displayName})");
                    }
                    else if (accPrefixes.Contains(prefix))
                    {
                        // 阶段2：收集饰品/装饰类道具
                        var priority = accPrefixPriority.TryGetValue(prefix, out var p) ? p : 99;
                        accItems.Add((codeStr, kv.Value.Name, kv.Value.Pak, priority));
                    }
                    else
                    {
                        skippedCodes.Add($"{codeStr}(未知前缀{prefix})");
                    }
                }

                // 日志：被跳过的道具
                if (skippedCodes.Count > 0)
                    AppendLog($"[刷新] 跳过: {string.Join(", ", skippedCodes)}");

                // 阶段2：按优先级排序后依次填入 slot 4-9
                accItems.Sort((a, b) => a.priority.CompareTo(b.priority));
                AppendLog($"[刷新] 饰品排序: {string.Join(", ", accItems.Select(a => $"{a.code}(pri={a.priority})"))}");
                var flexSlots = new[] { 4, 5, 6, 7, 8, 9 };
                for (int i = 0; i < accItems.Count && i < flexSlots.Length; i++)
                {
                    var item = accItems[i];
                    var slotId = flexSlots[i];
                    _itemDict.TryGetValue(item.code, out var localItem);
                    var displayName = item.name;
                    if (displayName.StartsWith("未知") && localItem != null && !string.IsNullOrEmpty(localItem.ItemName))
                        displayName = localItem.ItemName;
                    _slotStates[slotId].Before = new ItemshopM
                    {
                        ItemCode = item.code,
                        ItemName = displayName,
                        PakNum = item.pak,
                        EffectCode = localItem?.EffectCode ?? "无",
                        ImgPath = BuildImgPath(item.code, item.pak),
                    };
                    AppendLog($"[刷新] 灵活slot{slotId} ← {item.code}({displayName})");
                }
                if (accItems.Count > flexSlots.Length)
                    AppendLog($"[刷新] 饰品溢出: {accItems.Count - flexSlots.Length} 个未显示");

                // 日志：最终结果
                var filledSlots = Enumerable.Range(0, _slotConfig.Count)
                    .Select(si => _slotStates.TryGetValue(si, out var ss) && ss.Before != null ? $"{ss.Before.ItemCode}" : "空")
                    .ToList();
                AppendLog($"[刷新] 最终: [{string.Join(", ", filledSlots)}]");

                // 识别当前角色（c-code 映射角色类型 + FSB_CHN 中文名）
                _currentCharName = "";
                _currentPlayerName = "";
                _currentCharType = "";
                try
                {
                    var charInfo = await _bridge.ReadCharInfoAsync();
                    if (charInfo != null)
                    {
                        // key 优先用角色类型名，回退用 FSB_CHN 中文名
                        _currentCharName = !string.IsNullOrEmpty(charInfo.CharName)
                            ? charInfo.CharName
                            : charInfo.PlayerName;
                        _currentPlayerName = charInfo.PlayerName;  // FSB_CHN 中文名
                        _currentCharType = charInfo.CharName;      // 角色类型名
                    }
                }
                catch (Exception ex)
                {
                    AppendLog($"[刷新] 角色信息读取失败: {ex.Message}");
                }
                if (!string.IsNullOrEmpty(_currentCharName))
                    AppendLog($"[刷新] 当前角色: {_currentPlayerName} ({_currentCharType})");

                // 更新方案 UI
                UpdatePresetUI();

                // 刷新所有行
                foreach (var slot in _slotConfig)
                    RefreshSlotRow(slot.Id);

                int filled = _slotStates.Values.Count(s => s.Before != null);
                txtPairStatus.Text = $"已读取 {filled} 个装备位";
                ShowInfo($"已读取 {filled} 个装备位");
                TransitionTo(FlowState.SaveOrLoad);
            }
            catch (Exception ex)
            {
                ShowError($"读取失败: {ex.Message}");
            }
        }

        private List<SlotConfigM> LoadSlotConfig()
        {
            var path = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "data", "slot_config.json");
            if (!File.Exists(path)) return new();
            var json = File.ReadAllText(path);
            var options = new JsonSerializerOptions { PropertyNameCaseInsensitive = true };
            return JsonSerializer.Deserialize<List<SlotConfigM>>(json, options) ?? new();
        }

        private async void btnConfirm_Click(object sender, RoutedEventArgs e)
        {
            if (!_connected) { ShowError("请先连接游戏"); return; }
            StopBtnBreathing();

            // 收集有 before+after 的槽位
            var map = new Dictionary<string, int>();
            var effectMap = new Dictionary<string, int>();

            foreach (var slot in _slotConfig)
            {
                var state = _slotStates.ContainsKey(slot.Id) ? _slotStates[slot.Id] : null;
                if (state?.Before == null || state.After == null) continue;

                if (int.TryParse(state.Before.ItemCode, out int srcCode))
                {
                    map[srcCode.ToString()] = int.Parse(state.After.ItemCode);

                    // 特效自动继承：DST 有特效编号时，写入 effect_map
                    if (state.After.IsEffectId && int.TryParse(state.After.EffectCode, out int effectId))
                    {
                        effectMap[state.After.ItemCode] = effectId;
                    }
                }
            }

            if (map.Count == 0)
            {
                ShowError("没有设置任何替换，请先选中装备位并选择替换道具");
                return;
            }

            try
            {
                var enableEffect = chkEffect.IsChecked == true;
                await _bridge.ReplaceAsync(map, effectMap, enableEffect);
                var effectInfo = effectMap.Count > 0 ? $"，含 {effectMap.Count} 个特效" : "";
                var effectMode = enableEffect ? "（特效模式：进场景卡5秒）" : "（轻量模式：秒进无特效）";
                ShowInfo($"已设置 {map.Count} 个装备位替换{effectInfo}{effectMode}，进房间生效");
                AppendLog($"[替换] {map.Count}个装备位, 特效{effectMap.Count}个, 模式:{(enableEffect ? "特效" : "轻量")}");
                foreach (var kv in map)
                    AppendLog($"[替换] {kv.Key} → {kv.Value}");
                TransitionTo(FlowState.Restore);
            }
            catch (Exception ex)
            {
                ShowError($"变更失败: {ex.Message}");
            }
        }

        private async void btnRestore_Click(object sender, RoutedEventArgs e)
        {
            if (!_connected) { ShowError("请先连接游戏"); return; }
            StopBtnBreathing();
            try
            {
                await _bridge.RestoreAsync();

                // 彻底重置：清空所有装备状态、角色信息
                foreach (var state in _slotStates.Values)
                {
                    state.Before = null;
                    state.After = null;
                }
                foreach (var slot in _slotConfig)
                    RefreshSlotRow(slot.Id);
                _selectedSlotIdx = -1;
                _currentCharName = "";
                _currentPlayerName = "";
                _currentCharType = "";
                txtPairStatus.Text = "";
                txtPresetName.Text = "";
                if (labCharName != null) labCharName.Text = "";

                ShowInfo("已彻底重置，可以刷新其他角色穿搭");
                TransitionTo(FlowState.Refresh);
            }
            catch (Exception ex)
            {
                ShowError($"还原失败: {ex.Message}");
            }
        }

        private void btnSkin_Click(object sender, RoutedEventArgs e)
        {
            var skinWindow = new SkinWindow(skinManager);
            skinWindow.Owner = this;
            SkinTheme? themeToApply = null;
            skinWindow.ThemeApplied += (s, theme) => themeToApply = theme;
            skinWindow.ShowDialog();

            // 在 SkinWindow 关闭后应用主题（避免在对话框消息循环中更新 UI）
            if (themeToApply != null)
            {
                ApplyCurrentTheme();
            }
        }

        // ========== 主题 ==========

        /// <summary>
        /// 只应用主题资源（颜色/字体），不涉及背景。在 BuildSlotUI 之前调用。
        /// </summary>
        private void ApplyThemeResources()
        {
            if (skinManager?.CurrentTheme != null)
            {
                var applier = new ThemeApplier();
                applier.ApplyResourcesOnly(this, skinManager.CurrentTheme);
            }
        }

        /// <summary>
        /// 应用主题背景（渐变/视频），需要 XAML 可视树已构建。
        /// </summary>
        private void ApplyThemeBackground()
        {
            if (skinManager?.CurrentTheme != null)
            {
                var theme = skinManager.CurrentTheme;
                var bgStyle = theme.Styles.Window.Background;
                Console.WriteLine($"[Theme] ApplyThemeBackground: id={theme.Id}, bgType={bgStyle?.Type}");
                Console.WriteLine($"[Theme] VideoBackgroundImage diagnostic: Visibility={VideoBackgroundImage.Visibility}, " +
                    $"Row={Grid.GetRow(VideoBackgroundImage)}, RowSpan={Grid.GetRowSpan(VideoBackgroundImage)}, " +
                    $"ActualWidth={VideoBackgroundImage.ActualWidth:F0}, ActualHeight={VideoBackgroundImage.ActualHeight:F0}");

                // 更新渐变色
                if (bgStyle?.Type?.ToLower() != "video" && bgStyle?.Colors != null && bgStyle.Colors.Count >= 3
                    && bgStop1 != null && bgStop2 != null && bgStop3 != null)
                {
                    BgColor1 = ParseThemeColor(bgStyle.Colors[0]);
                    BgColor2 = ParseThemeColor(bgStyle.Colors[1]);
                    BgColor3 = ParseThemeColor(bgStyle.Colors[2]);
                    bgStop1.Color = BgColor1;
                    bgStop2.Color = BgColor2;
                    bgStop3.Color = BgColor3;
                }

                ApplyVideoBackground(theme);
            }
        }

        private void ApplyCurrentTheme()
        {
            ApplyThemeResources();
            ApplyThemeBackground();
        }

        private static Color ParseThemeColor(string colorString)
        {
            if (string.IsNullOrEmpty(colorString)) return Colors.Transparent;
            colorString = colorString.Trim();
            if (colorString.ToLower() == "transparent") return Colors.Transparent;
            try
            {
                if (colorString.StartsWith("#"))
                {
                    string hex = colorString.Substring(1);
                    if (hex.Length == 6)
                        return Color.FromRgb(Convert.ToByte(hex.Substring(0, 2), 16), Convert.ToByte(hex.Substring(2, 2), 16), Convert.ToByte(hex.Substring(4, 2), 16));
                    if (hex.Length == 8)
                        return Color.FromArgb(Convert.ToByte(hex.Substring(0, 2), 16), Convert.ToByte(hex.Substring(2, 2), 16), Convert.ToByte(hex.Substring(4, 2), 16), Convert.ToByte(hex.Substring(6, 2), 16));
                }
                return (Color)ColorConverter.ConvertFromString(colorString);
            }
            catch { return Colors.Transparent; }
        }

        // ========== 窗口拖动 ==========

        private void TitleBar_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
        {
            if (this.WindowState == WindowState.Maximized)
            {
                this.WindowState = WindowState.Normal;
                var point = e.GetPosition(this);
                this.Left = point.X;
                this.Top = point.Y;
            }
            this.DragMove();
        }

        // ========== 预设方案 ==========

        private const int MAX_PRESETS = 10;

        /// <summary>
        /// 自动识别当前角色（c-code 映射角色类型，不读取装备数据）
        /// </summary>
        private async Task<bool> TryIdentifyCharAsync()
        {
            if (!_connected) { ShowError("请先连接游戏"); return false; }
            try
            {
                var charInfo = await _bridge.ReadCharInfoAsync();
                if (charInfo != null)
                {
                    _currentCharName = !string.IsNullOrEmpty(charInfo.CharName)
                        ? charInfo.CharName
                        : charInfo.PlayerName;
                    _currentPlayerName = charInfo.PlayerName;
                    _currentCharType = charInfo.CharName;
                }
            }
            catch (Exception ex)
            {
                ShowError($"识别角色失败: {ex.Message}");
                return false;
            }
            if (string.IsNullOrEmpty(_currentCharName))
            {
                ShowError("无法识别当前角色，请先进一次房间");
                return false;
            }
            UpdatePresetUI();
            ShowInfo($"已识别: {_currentPlayerName} ({_currentCharType})");
            return true;
        }

        private void UpdatePresetUI()
        {
            if (labCharName == null || txtPresetName == null) return;

            if (string.IsNullOrEmpty(_currentCharName))
            {
                labCharName.Text = "未识别";
                txtPresetName.Text = "";
                return;
            }

            // 显示：中文名
            labCharName.Text = string.IsNullOrEmpty(_currentPlayerName)
                ? _currentCharName
                : _currentPlayerName;

            var data = LoadPresetFile();
            if (data.TryGetValue(_currentCharName, out var preset))
            {
                txtPresetName.Text = preset.Name;
            }
            else
            {
                // 方案名默认用角色类型名，玩家可自行修改
                txtPresetName.Text = _currentCharType;
            }
        }

        private void AutoLoadPreset()
        {
            if (string.IsNullOrEmpty(_currentCharName)) return;

            var data = LoadPresetFile();
            if (!data.TryGetValue(_currentCharName, out var preset) || preset.Items.Count == 0)
                return;

            // 清除当前 After 状态
            foreach (var state in _slotStates.Values)
                state.After = null;

            // 加载预设数据到 After
            foreach (var kv in preset.Items)
            {
                if (!int.TryParse(kv.Key, out int slotId)) continue;
                if (!_slotStates.ContainsKey(slotId)) continue;

                var presetItem = kv.Value;

                // 设置 Before（保持游戏读取的值不变）
                // 设置 After（预设目标）
                _itemDict.TryGetValue(presetItem.Dst, out var dstLocal);
                _slotStates[slotId].After = new ItemshopM
                {
                    ItemCode = presetItem.Dst,
                    ItemName = dstLocal?.ItemName ?? presetItem.Dst,
                    PakNum = dstLocal?.PakNum ?? "",
                    EffectCode = presetItem.Effect.HasValue
                        ? presetItem.Effect.Value.ToString()
                        : (dstLocal?.EffectCode ?? "无"),
                    ImgPath = dstLocal != null ? BuildImgPath(dstLocal.ItemCode, dstLocal.PakNum) : "",
                };
            }

            // 刷新 UI
            foreach (var slotCfg in _slotConfig)
                RefreshSlotRow(slotCfg.Id);

            AppendLog($"[方案] 自动加载: {preset.Name} ({preset.Items.Count}个替换)");
        }

        private Dictionary<string, CharPresets> LoadPresetFile()
        {
            if (!File.Exists(PresetFilePath)) return new Dictionary<string, CharPresets>();
            try
            {
                var json = File.ReadAllText(PresetFilePath, Encoding.UTF8);
                return JsonSerializer.Deserialize<Dictionary<string, CharPresets>>(json)
                    ?? new Dictionary<string, CharPresets>();
            }
            catch { return new Dictionary<string, CharPresets>(); }
        }

        private void SavePresetFile(Dictionary<string, CharPresets> data)
        {
            try
            {
                var dir = Path.GetDirectoryName(PresetFilePath);
                if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir))
                    Directory.CreateDirectory(dir);
                var json = JsonSerializer.Serialize(data, new JsonSerializerOptions { WriteIndented = true });
                File.WriteAllText(PresetFilePath, json, Encoding.UTF8);
            }
            catch (Exception ex)
            {
                ShowError($"保存预设文件失败: {ex.Message}");
            }
        }

        /// <summary>收集当前装备位中有效的 Before→After 替换对</summary>
        private Dictionary<string, PresetItem> CollectCurrentItems()
        {
            var items = new Dictionary<string, PresetItem>();
            foreach (var slotCfg in _slotConfig)
            {
                var state = _slotStates.ContainsKey(slotCfg.Id) ? _slotStates[slotCfg.Id] : null;
                if (state?.Before == null || state.After == null) continue;

                var item = new PresetItem
                {
                    Src = state.Before.ItemCode,
                    Dst = state.After.ItemCode,
                };
                if (state.After.IsEffectId && int.TryParse(state.After.EffectCode, out int effectId))
                    item.Effect = effectId;

                items[slotCfg.Id.ToString()] = item;
            }
            return items;
        }

        private async void btnSavePreset_Click(object sender, RoutedEventArgs e)
        {
            if (string.IsNullOrEmpty(_currentCharName))
            {
                if (!await TryIdentifyCharAsync()) return;
            }

            var items = CollectCurrentItems();
            if (items.Count == 0)
            {
                ShowError("没有设置任何替换，请先选择替换道具");
                return;
            }

            var data = LoadPresetFile();

            // 检查上限（新角色才计数）
            if (!data.ContainsKey(_currentCharName) && data.Count >= MAX_PRESETS)
            {
                ShowError($"已保存 {data.Count} 个人物方案，达到上限 {MAX_PRESETS}，请先删除旧方案");
                return;
            }

            var presetName = txtPresetName.Text.Trim();
            if (string.IsNullOrEmpty(presetName))
                presetName = _currentCharName;

            if (data.TryGetValue(_currentCharName, out var existing))
            {
                // 已有方案：合并（新 items 覆盖已有的，已有的但未在新 items 中的保留）
                foreach (var kv in items)
                    existing.Items[kv.Key] = kv.Value;
                existing.Name = presetName;
                SavePresetFile(data);
                ShowInfo($"已更新「{presetName}」的方案（{existing.Items.Count}个替换）");
            }
            else
            {
                // 新建方案
                data[_currentCharName] = new CharPresets
                {
                    Name = presetName,
                    Items = items
                };
                SavePresetFile(data);
                ShowInfo($"已保存「{presetName}」的方案（{items.Count}个替换）");
            }
        }

        private async void btnLoadPreset_Click(object sender, RoutedEventArgs e)
        {
            StopBtnBreathing();
            if (string.IsNullOrEmpty(_currentCharName))
            {
                if (!await TryIdentifyCharAsync()) return;
            }

            var data = LoadPresetFile();
            if (!data.TryGetValue(_currentCharName, out var preset) || preset.Items.Count == 0)
            {
                ShowError("当前角色没有已保存的方案");
                return;
            }

            // 清除当前 After 状态
            foreach (var state in _slotStates.Values)
                state.After = null;

            // 加载预设数据到 After
            foreach (var kv in preset.Items)
            {
                if (!int.TryParse(kv.Key, out int slotId)) continue;
                if (!_slotStates.ContainsKey(slotId)) continue;

                var presetItem = kv.Value;

                _itemDict.TryGetValue(presetItem.Dst, out var dstLocal);
                _slotStates[slotId].After = new ItemshopM
                {
                    ItemCode = presetItem.Dst,
                    ItemName = dstLocal?.ItemName ?? presetItem.Dst,
                    PakNum = dstLocal?.PakNum ?? "",
                    EffectCode = presetItem.Effect.HasValue
                        ? presetItem.Effect.Value.ToString()
                        : (dstLocal?.EffectCode ?? "无"),
                    ImgPath = dstLocal != null ? BuildImgPath(dstLocal.ItemCode, dstLocal.PakNum) : "",
                };
            }

            txtPresetName.Text = preset.Name;

            // 刷新所有行
            foreach (var slot in _slotConfig)
                RefreshSlotRow(slot.Id);

            ShowInfo($"已加载「{preset.Name}」的方案（{preset.Items.Count}个替换）");
            TransitionTo(FlowState.Confirm);
        }

        private async void btnDeletePreset_Click(object sender, RoutedEventArgs e)
        {
            if (string.IsNullOrEmpty(_currentCharName))
            {
                if (!await TryIdentifyCharAsync()) return;
            }

            var data = LoadPresetFile();
            if (!data.ContainsKey(_currentCharName))
            {
                ShowError("当前角色没有已保存的方案");
                return;
            }

            var name = data[_currentCharName].Name;
            data.Remove(_currentCharName);
            SavePresetFile(data);

            // 清除 After
            foreach (var state in _slotStates.Values)
                state.After = null;
            foreach (var slotCfg in _slotConfig)
                RefreshSlotRow(slotCfg.Id);

            txtPresetName.Text = _currentCharName;
            ShowInfo($"已删除「{name}」的方案");
        }

        // ========== 视频背景 ==========

        [DllImport("kernel32.dll", EntryPoint = "RtlMoveMemory")]
        private static extern void CopyMemory(IntPtr dest, IntPtr src, uint count);

        private void EnsureVLCInitialized()
        {
            if (_libVLC != null) return;

            LibVLCSharp.Shared.Core.Initialize();
            _libVLC = new LibVLC("--no-video-title-show", "--input-repeat=65535");
            _mediaPlayer = new LibVLCSharp.Shared.MediaPlayer(_libVLC);

            _videoFormatCb = new LibVLCSharp.Shared.MediaPlayer.LibVLCVideoFormatCb(OnVideoFormat);
            _videoCleanupCb = new LibVLCSharp.Shared.MediaPlayer.LibVLCVideoCleanupCb(OnVideoCleanup);
            _lockVideoCb = new LibVLCSharp.Shared.MediaPlayer.LibVLCVideoLockCb(OnLockVideo);
            _unlockVideoCb = new LibVLCSharp.Shared.MediaPlayer.LibVLCVideoUnlockCb(OnUnlockVideo);

            _mediaPlayer.SetVideoFormatCallbacks(_videoFormatCb, _videoCleanupCb);
            _mediaPlayer.SetVideoCallbacks(_lockVideoCb, _unlockVideoCb, null);

            _mediaPlayer.EndReached += (s, e) =>
            {
                // 注意：此回调在 VLC 线程，不能直接访问 WPF 对象
                Console.WriteLine($"[Theme][Video] EndReached: media={_currentMedia != null}, videoActive={_videoActive}");
                bool shouldLoop = _videoActive && _currentMedia != null;
                Dispatcher.BeginInvoke(new Action(() =>
                {
                    // 只在视频模式仍激活时循环播放
                    if (shouldLoop && VideoBackgroundImage.Visibility == Visibility.Visible)
                    {
                        try
                        {
                            Console.WriteLine("[Theme][Video] Looping video playback...");
                            _mediaPlayer.Play(_currentMedia);
                        }
                        catch (Exception ex) { Console.WriteLine($"[Theme][Video] Loop play error: {ex.Message}"); }
                    }
                    else
                    {
                        Console.WriteLine($"[Theme][Video] EndReached but not looping: shouldLoop={shouldLoop}, visibility={VideoBackgroundImage.Visibility}");
                    }
                }));
            };
        }

        private uint OnVideoFormat(ref nint opaque, nint chroma, ref uint width, ref uint height, ref uint pitches, ref uint lines)
        {
            _videoWidth = (int)width;
            _videoHeight = (int)height;
            pitches = width * 4;
            lines = height;
            _videoBufferSize = _videoWidth * _videoHeight * 4;

            // 释放旧 buffer（VLC 可能多次回调 OnVideoFormat）
            if (_videoBuffer != IntPtr.Zero)
            {
                Marshal.FreeHGlobal(_videoBuffer);
                _videoBuffer = IntPtr.Zero;
            }
            _videoBuffer = Marshal.AllocHGlobal(_videoBufferSize);

            // 设置 chroma 为 RV32 (Bgr32)
            var chromaBytes = System.Text.Encoding.ASCII.GetBytes("RV32");
            Marshal.Copy(chromaBytes, 0, chroma, 4);

            Console.WriteLine($"[Theme][Video] OnVideoFormat: {width}x{height}, bufferSize={_videoBufferSize}, buffer=0x{_videoBuffer.ToInt64():X}");

            Dispatcher.BeginInvoke(new Action(() =>
            {
                _videoBitmap = new WriteableBitmap(_videoWidth, _videoHeight, 96, 96, PixelFormats.Bgr32, null);
                VideoBackgroundImage.Source = _videoBitmap;
                Console.WriteLine($"[Theme][Video] WriteableBitmap created: {_videoWidth}x{_videoHeight}, Source assigned to VideoBackgroundImage");
            }));

            opaque = _videoBuffer;
            return 1; // 缓冲区数量
        }

        private void OnVideoCleanup(ref nint opaque)
        {
            // 不在这里释放 buffer！VLC 回调和 Dispatcher 存在竞态：
            // OnUnlockVideo 可能已入队 BeginInvoke 但还没执行，此时释放 buffer → AccessViolation
            // buffer 由 ApplyVideoBackground 在 Dispatcher.Invoke 中同步释放
            Console.WriteLine("[Theme][Video] OnVideoCleanup called (buffer NOT freed here, deferred)");
        }

        private IntPtr OnLockVideo(IntPtr opaque, IntPtr planes)
        {
            Marshal.WriteIntPtr(planes, _videoBuffer);
            return opaque;
        }

        private int _videoFrameCount = 0;
        private void OnUnlockVideo(IntPtr opaque, IntPtr picture, IntPtr planes)
        {
            // 停止后不再处理帧，防止访问已释放 buffer
            if (!_videoActive || _videoBitmap == null || _videoBuffer == IntPtr.Zero) return;

            _videoFrameCount++;
            int frameNum = _videoFrameCount;
            int w = _videoWidth, h = _videoHeight;
            IntPtr buffer = _videoBuffer;
            int bufSize = _videoBufferSize;

            // 每100帧输出一次诊断
            if (frameNum % 100 == 1)
            {
                Console.WriteLine($"[Theme][Video] OnUnlockVideo: frame #{frameNum}, videoSize={w}x{h}");
            }

            Dispatcher.BeginInvoke(new Action(() =>
            {
                try
                {
                    if (_videoBitmap == null) return;
                    _videoBitmap.Lock();
                    CopyMemory(_videoBitmap.BackBuffer, buffer, (uint)bufSize);
                    _videoBitmap.AddDirtyRect(new Int32Rect(0, 0, w, h));
                    _videoBitmap.Unlock();
                }
                catch { }
            }));
        }

        private void ApplyVideoBackground(SkinTheme theme)
        {
            // 先停止当前播放（标记 _videoActive=false 防止回调竞态）
            _videoActive = false;
            try
            {
                if (_mediaPlayer != null && _mediaPlayer.IsPlaying)
                {
                    Console.WriteLine("[Theme][Video] Stopping current video playback...");
                    _mediaPlayer.Stop();
                }
            }
            catch (Exception ex) { Console.WriteLine($"[Theme][Video] Error stopping video: {ex.Message}"); }

            var applier = new ThemeApplier();
            var bgStyle = theme.Styles.Window.Background;
            var isVideo = applier.IsVideoBackground(bgStyle);
            Console.WriteLine($"[Theme][Video] ApplyVideoBackground: theme={theme.Id}, isVideo={isVideo}, bgType={bgStyle?.Type}");
            Console.WriteLine($"[Theme][Video] VideoBackgroundImage: Visibility={VideoBackgroundImage.Visibility}, " +
                $"ActualWidth={VideoBackgroundImage.ActualWidth:F0}, ActualHeight={VideoBackgroundImage.ActualHeight:F0}, " +
                $"RowSpan={Grid.GetRowSpan(VideoBackgroundImage)}");

            if (isVideo)
            {
                string? videoPath = applier.GetVideoPath(bgStyle);
                Console.WriteLine($"[Theme][Video] Video path: {videoPath}, exists={videoPath != null && File.Exists(videoPath)}");
                if (!string.IsNullOrEmpty(videoPath) && File.Exists(videoPath))
                {
                    try
                    {
                        EnsureVLCInitialized();

                        _currentMedia?.Dispose();
                        _currentMedia = new Media(_libVLC, new Uri(videoPath));

                        // 视频模式：隐藏渐变背景，显示视频层
                        mainGrid.Background = new SolidColorBrush(Colors.Transparent);
                        VideoBackgroundImage.Visibility = Visibility.Visible;
                        videoOpacityPanel.Visibility = Visibility.Visible;
                        sliderVideoOpacity.Value = ConfigService.Instance.VideoOverlayOpacity;
                        // 强制同步 alpha：slider 值未变时 ValueChanged 不触发，需手动应用
                        _videoOverlayAlpha = (byte)(ConfigService.Instance.VideoOverlayOpacity / 100.0 * 255);
                        new ThemeApplier().ApplyVideoOverlayAlpha(this, _videoOverlayAlpha);
                        _videoActive = true;
                        _mediaPlayer.Play(_currentMedia);
                        Console.WriteLine($"[Theme][Video] ▶ Video playback started, RowSpan={Grid.GetRowSpan(VideoBackgroundImage)}");
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine($"[Theme][Video] ❌ Error playing video: {ex.Message}");
                        VideoBackgroundImage.Visibility = Visibility.Collapsed;
                        videoOpacityPanel.Visibility = Visibility.Collapsed;
                        RestoreGradientBackground();
                    }
                }
                else
                {
                    Console.WriteLine($"[Theme][Video] ❌ Video file not found: {videoPath}, restoring gradient");
                    VideoBackgroundImage.Visibility = Visibility.Collapsed;
                    videoOpacityPanel.Visibility = Visibility.Collapsed;
                    RestoreGradientBackground();
                }
            }
            else
            {
                // 非视频主题：停止视频、恢复渐变背景
                VideoBackgroundImage.Visibility = Visibility.Collapsed;
                videoOpacityPanel.Visibility = Visibility.Collapsed;

                // 同步释放 buffer 和 bitmap（确保所有 pending 的 OnUnlockVideo 回调已执行完）
                Dispatcher.Invoke(new Action(() =>
                {
                    if (_videoBuffer != IntPtr.Zero)
                    {
                        Marshal.FreeHGlobal(_videoBuffer);
                        _videoBuffer = IntPtr.Zero;
                    }
                    _videoBitmap = null;
                    Console.WriteLine("[Theme][Video] Buffer freed and bitmap cleared on UI thread (safe)");
                }));

                try
                {
                    _currentMedia?.Dispose();
                    _currentMedia = null;
                    Console.WriteLine("[Theme][Video] ⏹ Video stopped and media disposed");
                }
                catch (Exception ex) { Console.WriteLine($"[Theme][Video] Error cleaning video: {ex.Message}"); }

                RestoreGradientBackground();
                Console.WriteLine($"[Theme][Video] ✅ Gradient background restored, mainGrid.Background type={mainGrid.Background?.GetType().Name}");
            }
        }

        private void RestoreGradientBackground()
        {
            // 恢复 bgBrush 动画渐变背景
            Console.WriteLine($"[Theme] RestoreGradientBackground: bgBrush={bgBrush != null}, bgStop1={bgStop1 != null}, bgStop2={bgStop2 != null}, bgStop3={bgStop3 != null}");
            if (bgBrush != null && bgStop1 != null && bgStop2 != null && bgStop3 != null)
            {
                bgStop1.Color = BgColor1;
                bgStop2.Color = BgColor2;
                bgStop3.Color = BgColor3;
                mainGrid.Background = bgBrush;
                Console.WriteLine($"[Theme] mainGrid.Background restored to bgBrush, colors: {BgColor1}, {BgColor2}, {BgColor3}");
            }
            else
            {
                Console.WriteLine("[Theme] WARNING: Cannot restore gradient - bgBrush or bgStop is null!");
            }
        }

        // ========== 动态背景 ==========

        private void AnimateBackground(object? sender, EventArgs e)
        {
            _bgAngle += 0.005;
            if (_bgAngle > 1) _bgAngle -= 1;

            var t = _bgAngle;
            bgStop1.Color = InterpolateColor(BgColor1, BgColor3, (Math.Sin(t * Math.PI * 2) + 1) / 2);
            bgStop2.Color = InterpolateColor(BgColor2, BgColor1, (Math.Sin(t * Math.PI * 2 + 2) + 1) / 2);
            bgStop3.Color = InterpolateColor(BgColor3, BgColor2, (Math.Sin(t * Math.PI * 2 + 4) + 1) / 2);
        }

        private static Color InterpolateColor(Color a, Color b, double t)
        {
            return Color.FromRgb(
                (byte)(a.R + (b.R - a.R) * t),
                (byte)(a.G + (b.G - a.G) * t),
                (byte)(a.B + (b.B - a.B) * t));
        }

        // ========== 工具方法 ==========

        /// <summary>
        /// 视频模式透明度滑块：实时调节所有 UI 覆盖层不透明度。
        /// 滑块 0-100 映射到 alpha 0x00-0xFF。
        /// </summary>
        private void sliderVideoOpacity_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
        {
            if (videoOpacityPanel == null || videoOpacityPanel.Visibility != Visibility.Visible) return;

            // 滑块值 0-100 → alpha 0x00-0xFF
            byte alpha = (byte)(e.NewValue / 100.0 * 255);
            _videoOverlayAlpha = alpha;
            Console.WriteLine($"[Theme][Video] Opacity slider: {e.NewValue:F0}% → alpha=0x{alpha:X2}");

            new ThemeApplier().ApplyVideoOverlayAlpha(this, alpha);

            // 持久化到配置文件
            ConfigService.Instance.VideoOverlayOpacity = e.NewValue;
        }

        private void chkLog_Checked(object sender, RoutedEventArgs e)
        {
            logPanel.Visibility = Visibility.Visible;
        }

        private void chkLog_Unchecked(object sender, RoutedEventArgs e)
        {
            logPanel.Visibility = Visibility.Collapsed;
        }

        // ========== 无边框模式 ==========

        [DllImport("dwmapi.dll")]
        private static extern int DwmSetWindowAttribute(IntPtr hwnd, int dwAttribute, ref int pvAttribute, int cbAttribute);

        private const int DWMWA_WINDOW_CORNER_PREFERENCE = 33;
        private const int DWMWCP_DEFAULT = 0;    // 系统默认
        private const int DWMWCP_ROUND = 2;      // 圆角 ~8px

        private Brush _originalWindowBackground;
        private Thickness _originalMainMargin;

        private void TopBar_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
        {
            if (!_isBorderless) return;

            // 双击标题栏 → 最大化/还原
            var now = DateTime.Now;
            if ((now - _lastTitleClick).TotalMilliseconds < 300)
            {
                this.WindowState = this.WindowState == WindowState.Maximized
                    ? WindowState.Normal
                    : WindowState.Maximized;
                _lastTitleClick = DateTime.MinValue;
                return;
            }
            _lastTitleClick = now;

            // 单击拖拽
            if (this.WindowState == WindowState.Maximized)
            {
                this.WindowState = WindowState.Normal;
                var point = e.GetPosition(this);
                this.Left = point.X;
                this.Top = point.Y;
            }
            this.DragMove();
        }

        private void chkBorderless_Checked(object sender, RoutedEventArgs e)
        {
            _isBorderless = true;

            // 保存原始值
            _originalWindowBackground = this.Background;
            _originalMainMargin = mainGrid.Margin;

            // 1) 去掉系统窗口框架（标题栏+黑边全部移除）
            this.WindowStyle = System.Windows.WindowStyle.None;

            // 2) WindowChrome 保持可调整大小，GlassFrameThickness=0 彻底去 DWM 框架
            var chrome = new System.Windows.Shell.WindowChrome
            {
                CaptionHeight = 0,
                GlassFrameThickness = new Thickness(0),
                ResizeBorderThickness = SystemParameters.WindowResizeBorderThickness,
                CornerRadius = new CornerRadius(8),
            };
            System.Windows.Shell.WindowChrome.SetWindowChrome(this, chrome);

            // 3) 白色背景 → mainGrid Margin 露出的就是白边
            this.Background = Brushes.White;
            mainGrid.Margin = new Thickness(3);

            // 4) Win11 圆角
            var hwnd = new System.Windows.Interop.WindowInteropHelper(this).Handle;
            int cornerPref = DWMWCP_ROUND;
            DwmSetWindowAttribute(hwnd, DWMWA_WINDOW_CORNER_PREFERENCE, ref cornerPref, sizeof(int));

            windowControls.Visibility = Visibility.Visible;
            btnWinMax.Content = this.WindowState == WindowState.Maximized ? "❐" : "□";
            ConfigService.Instance.Borderless = true;
        }

        private void chkBorderless_Unchecked(object sender, RoutedEventArgs e)
        {
            _isBorderless = false;

            ConfigService.Instance.Borderless = false;

            // 恢复 Win11 默认直角
            var hwnd = new System.Windows.Interop.WindowInteropHelper(this).Handle;
            int cornerDefault = DWMWCP_DEFAULT;
            DwmSetWindowAttribute(hwnd, DWMWA_WINDOW_CORNER_PREFERENCE, ref cornerDefault, sizeof(int));

            // 恢复原始值
            this.Background = _originalWindowBackground;
            mainGrid.Margin = _originalMainMargin;

            // 移除 WindowChrome，恢复系统窗口框架
            System.Windows.Shell.WindowChrome.SetWindowChrome(this, null);
            this.WindowStyle = System.Windows.WindowStyle.SingleBorderWindow;

            windowControls.Visibility = Visibility.Collapsed;
        }

        private void btnWinMin_Click(object sender, RoutedEventArgs e)
        {
            this.WindowState = WindowState.Minimized;
        }

        private void btnWinMax_Click(object sender, RoutedEventArgs e)
        {
            this.WindowState = this.WindowState == WindowState.Maximized
                ? WindowState.Normal
                : WindowState.Maximized;
        }

        private void btnWinClose_Click(object sender, RoutedEventArgs e)
        {
            this.Close();
        }

        private void btnCopyLog_Click(object sender, RoutedEventArgs e)
        {
            if (lstLog != null && lstLog.Items.Count > 0)
            {
                var sb = new System.Text.StringBuilder();
                foreach (var item in lstLog.Items)
                    sb.AppendLine(item?.ToString());
                try
                {
                    Clipboard.SetText(sb.ToString());
                    ShowInfo("日志已复制到剪贴板");
                }
                catch (System.Exception ex)
                {
                    ShowError($"复制失败: {ex.Message}");
                }
            }
        }

        private void AppendLog(string msg)
        {
            if (lstLog == null) return;
            var time = DateTime.Now.ToString("HH:mm:ss");
            lstLog.Items.Add($"[{time}] {msg}");
            // 限制日志条数
            while (lstLog.Items.Count > 300)
                lstLog.Items.RemoveAt(0);
            lstLog.ScrollIntoView(lstLog.Items[lstLog.Items.Count - 1]);
        }

        private void ShowInfo(string msg)
        {
            Dispatcher.Invoke(() =>
            {
                labErrorMsg.Text = msg;
                labErrorMsg.Foreground = (Brush)FindResource("AccentColor");
                labErrorMsg.Visibility = Visibility.Visible;
                var timer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(3) };
                timer.Tick += (s, e) => { labErrorMsg.Visibility = Visibility.Collapsed; timer.Stop(); };
                timer.Start();
            });
        }

        private void ShowError(string msg)
        {
            Dispatcher.Invoke(() =>
            {
                labErrorMsg.Text = msg;
                labErrorMsg.Foreground = (Brush)FindResource("AccentColor");
                labErrorMsg.Visibility = Visibility.Visible;
            });
        }
    }

    // ========== 装备位状态模型 ==========

    public class SlotState
    {
        public int SlotIdx { get; set; }
        public ItemshopM? Before { get; set; }  // 当前装备（从游戏读取）
        public ItemshopM? After { get; set; }   // 替换目标（用户选择）
    }

    // ========== 预设数据模型 ==========

    public class CharPresets
    {
        [JsonPropertyName("name")]
        public string Name { get; set; } = "";

        [JsonPropertyName("items")]
        public Dictionary<string, PresetItem> Items { get; set; } = new();
    }

    public class PresetItem
    {
        [JsonPropertyName("src")]
        public string Src { get; set; } = "";

        [JsonPropertyName("dst")]
        public string Dst { get; set; } = "";

        [JsonPropertyName("effect")]
        public int? Effect { get; set; }
    }

    /// <summary>
    /// 按钮涟漪效果：点击时按钮背景闪亮白色再消退。
    /// </summary>
    public static class RippleEffect
    {
        public static readonly DependencyProperty EnableProperty =
            DependencyProperty.RegisterAttached("Enable", typeof(bool), typeof(RippleEffect),
                new PropertyMetadata(false, OnEnableChanged));

        public static bool GetEnable(DependencyObject obj) => (bool)obj.GetValue(EnableProperty);
        public static void SetEnable(DependencyObject obj, bool value) => obj.SetValue(EnableProperty, value);

        private static void OnEnableChanged(DependencyObject d, DependencyPropertyChangedEventArgs e)
        {
            if (d is Button btn)
            {
                if ((bool)e.NewValue)
                    btn.PreviewMouseLeftButtonDown += OnMouseDown;
                else
                    btn.PreviewMouseLeftButtonDown -= OnMouseDown;
            }
        }

        private static void OnMouseDown(object sender, MouseButtonEventArgs e)
        {
            if (sender is not Button btn || btn.Template == null) return;

            // 找到模板中的 ButtonBorder，直接闪亮它的背景
            if (btn.Template.FindName("ButtonBorder", btn) is not Border border) return;

            var flash = new SolidColorBrush(Colors.White);
            var originalBg = border.Background;
            border.Background = flash;

            var fade = new ColorAnimation(
                Colors.White,
                Color.FromArgb(0x40, 0xFF, 0xFF, 0xFF), // 渐变回半透明白
                TimeSpan.FromSeconds(0.35))
            {
                EasingFunction = new QuadraticEase { EasingMode = EasingMode.EaseOut }
            };
            fade.Completed += (s, _) =>
            {
                border.Background = originalBg;
            };
            flash.BeginAnimation(SolidColorBrush.ColorProperty, fade);
        }
    }
}
