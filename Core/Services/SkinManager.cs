using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows;

namespace FS服装搭配专家v1._0
{
    /// <summary>
    /// 应用程序入口点
    /// </summary>
    public class Program
    {
        [STAThread]
        public static void Main(string[] args)
        {
            App app = new App();
            app.Run();
        }
    }

    /// <summary>
    /// 皮肤数据结构
    /// </summary>
    public class SkinData
    {
        public string Name { get; set; }
        public Color BackColor { get; set; }
        public Color ButtonColor { get; set; }
        public Color BorderColor { get; set; }
        public Color TextColor { get; set; }
        public Color GroupBoxBorderColor { get; set; }
        public Color ComboBoxBaseColor { get; set; }
        public Color ComboBoxBorderColor { get; set; }

        public SkinData()
        {
            // 默认皮肤颜色
            Name = "默认";
            BackColor = Colors.LightPink;
            ButtonColor = Colors.LightPink;
            BorderColor = Colors.LightPink;
            TextColor = Colors.Black;
            GroupBoxBorderColor = Colors.LightPink;
            ComboBoxBaseColor = Colors.LightPink;
            ComboBoxBorderColor = Colors.LightPink;
        }

        public SkinData(string name, Color backColor, Color buttonColor, Color borderColor, 
                       Color textColor, Color groupBoxBorderColor, Color comboBoxBaseColor, Color comboBoxBorderColor)
        {
            Name = name;
            BackColor = backColor;
            ButtonColor = buttonColor;
            BorderColor = borderColor;
            TextColor = textColor;
            GroupBoxBorderColor = groupBoxBorderColor;
            ComboBoxBaseColor = comboBoxBaseColor;
            ComboBoxBorderColor = comboBoxBorderColor;
        }

        /// <summary>
        /// 从字符串解析皮肤数据
        /// </summary>
        /// <param name="skinString">皮肤字符串</param>
        /// <returns>皮肤数据</returns>
        public static SkinData FromString(string skinString)
        {
            try
            {
                string[] parts = skinString.Split('|');
                if (parts.Length != 8)
                    return new SkinData();

                return new SkinData(
                    parts[0],
                    (Color)ColorConverter.ConvertFromString(parts[1]),
                    (Color)ColorConverter.ConvertFromString(parts[2]),
                    (Color)ColorConverter.ConvertFromString(parts[3]),
                    (Color)ColorConverter.ConvertFromString(parts[4]),
                    (Color)ColorConverter.ConvertFromString(parts[5]),
                    (Color)ColorConverter.ConvertFromString(parts[6]),
                    (Color)ColorConverter.ConvertFromString(parts[7])
                );
            }
            catch
            {
                return new SkinData();
            }
        }

        /// <summary>
        /// 转换为字符串
        /// </summary>
        /// <returns>皮肤字符串</returns>
        public override string ToString()
        {
            ColorConverter converter = new ColorConverter();
            return $"{Name}|{converter.ConvertToString(BackColor)}|{converter.ConvertToString(ButtonColor)}|{converter.ConvertToString(BorderColor)}|{converter.ConvertToString(TextColor)}|{converter.ConvertToString(GroupBoxBorderColor)}|{converter.ConvertToString(ComboBoxBaseColor)}|{converter.ConvertToString(ComboBoxBorderColor)}";
        }
    }

    /// <summary>
    /// 皮肤管理器
    /// </summary>
    public class SkinManager
    {
        private const string SkinConfigFile = "skins.ini";
        private const string TemplateFolder = "template";
        private List<SkinData> skins;
        private SkinData currentSkin;

        public List<SkinData> Skins { get { return skins; } }
        public SkinData CurrentSkin { get { return currentSkin; } }

        public SkinManager()
        {
            skins = new List<SkinData>();
            LoadSkins();
        }

        /// <summary>
        /// 加载皮肤配置
        /// </summary>
        public void LoadSkins()
        {
            skins.Clear();

            // 添加默认皮肤
            AddDefaultSkins();

            // 从模板图片生成皮肤
            AddSkinsFromTemplates();

            // 从配置文件加载自定义皮肤
            if (File.Exists(SkinConfigFile))
            {
                try
                {
                    using (StreamReader reader = new StreamReader(SkinConfigFile, Encoding.Default))
                    {
                        string line;
                        while ((line = reader.ReadLine()) != null)
                        {
                            if (!string.IsNullOrEmpty(line) && !line.StartsWith("#"))
                            {
                                SkinData skin = SkinData.FromString(line);
                                if (!skins.Any(s => s.Name == skin.Name))
                                {
                                    skins.Add(skin);
                                }
                            }
                        }
                    }
                }
                catch
                {
                    // 配置文件读取失败，使用默认皮肤
                }
            }

            // 设置当前皮肤为第一个
            if (skins.Count > 0)
            {
                currentSkin = skins[0];
            }
        }

        /// <summary>
        /// 添加默认皮肤
        /// </summary>
        private void AddDefaultSkins()
        {
            // 粉色主题
            skins.Add(new SkinData("粉色主题", Colors.LightPink, Colors.LightPink, Colors.LightPink, Colors.Black, Colors.LightPink, Colors.LightPink, Colors.LightPink));
            
            // 珊瑚主题
            skins.Add(new SkinData("珊瑚主题", Colors.LightCoral, Colors.LightCoral, Colors.LightCoral, Colors.Black, Colors.LightCoral, Colors.LightCoral, Colors.LightCoral));
            
            // 蓝色主题
            skins.Add(new SkinData("蓝色主题", Colors.LightSkyBlue, Colors.LightSkyBlue, Colors.LightSkyBlue, Colors.Black, Colors.LightSkyBlue, Colors.LightSkyBlue, Colors.LightSkyBlue));
            
            // 紫色主题
            skins.Add(new SkinData("紫色主题", Colors.Plum, Colors.Plum, Colors.Plum, Colors.Black, Colors.Plum, Colors.Plum, Colors.Plum));
            
            // 绿色主题
            skins.Add(new SkinData("绿色主题", Colors.LightGreen, Colors.LightGreen, Colors.LightGreen, Colors.Black, Colors.LightGreen, Colors.LightGreen, Colors.LightGreen));
            
            // 金色主题
            skins.Add(new SkinData("金色主题", Colors.LightGoldenrodYellow, Colors.LightGoldenrodYellow, Colors.LightGoldenrodYellow, Colors.Black, Colors.LightGoldenrodYellow, Colors.LightGoldenrodYellow, Colors.LightGoldenrodYellow));
        }

        /// <summary>
        /// 从模板图片生成皮肤
        /// </summary>
        private void AddSkinsFromTemplates()
        {
            try
            {
                // 检查template文件夹是否存在
                // 尝试多个可能的路径
                string[] possiblePaths = {
                    Path.Combine(AppDomain.CurrentDomain.BaseDirectory, TemplateFolder),
                    Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "..", "..", "..", TemplateFolder),
                    Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "..", "..", TemplateFolder)
                };
                
                string templatePath = null;
                foreach (var path in possiblePaths)
                {
                    if (Directory.Exists(path))
                    {
                        templatePath = path;
                        break;
                    }
                }
                
                if (templatePath != null)
                {
                    // 获取template文件夹中的图片文件
                    string[] imageExtensions = { ".jpg", ".jpeg", ".png", ".bmp" };
                    var imageFiles = Directory.GetFiles(templatePath)
                        .Where(file => imageExtensions.Contains(Path.GetExtension(file).ToLower()))
                        .ToList();

                    // 为每个图片文件生成皮肤
                    foreach (var imageFile in imageFiles)
                    {
                        try
                        {
                            string skinName = Path.GetFileNameWithoutExtension(imageFile);
                            if (!skins.Any(s => s.Name == skinName))
                            {
                                // 从图片中提取颜色
                                Color dominantColor = GetDominantColorFromImage(imageFile);
                                
                                // 创建基于图片颜色的皮肤
                                SkinData skin = new SkinData(
                                    skinName,
                                    dominantColor,
                                    AdjustColorBrightness(dominantColor, 0.9f),
                                    AdjustColorBrightness(dominantColor, 0.8f),
                                    GetContrastColor(dominantColor),
                                    AdjustColorBrightness(dominantColor, 0.7f),
                                    AdjustColorBrightness(dominantColor, 0.95f),
                                    AdjustColorBrightness(dominantColor, 0.85f)
                                );
                                
                                skins.Add(skin);
                            }
                        }
                        catch
                        {
                            // 处理单个图片失败，继续处理其他图片
                        }
                    }
                }
            }
            catch
            {
                // 处理文件夹访问失败
            }
        }

        /// <summary>
        /// 从图片中提取主色调
        /// </summary>
        /// <param name="imagePath">图片路径</param>
        /// <returns>主色调</returns>
        private Color GetDominantColorFromImage(string imagePath)
        {
            try
            {
                // 加载图片
                BitmapImage bitmap = new BitmapImage(new Uri(imagePath));
                FormatConvertedBitmap formattedBitmap = new FormatConvertedBitmap(bitmap, PixelFormats.Bgr32, null, 0);
                int width = formattedBitmap.PixelWidth;
                int height = formattedBitmap.PixelHeight;
                int stride = width * 4; // 4 bytes per pixel (B, G, R, A)
                byte[] pixels = new byte[height * stride];
                formattedBitmap.CopyPixels(pixels, stride, 0);

                // 计算颜色频率
                Dictionary<Color, int> colorFrequency = new Dictionary<Color, int>();
                for (int i = 0; i < pixels.Length; i += 4)
                {
                    byte b = pixels[i];
                    byte g = pixels[i + 1];
                    byte r = pixels[i + 2];
                    Color color = Color.FromRgb(r, g, b);

                    if (colorFrequency.ContainsKey(color))
                    {
                        colorFrequency[color]++;
                    }
                    else
                    {
                        colorFrequency[color] = 1;
                    }
                }

                // 找出出现频率最高的颜色
                Color dominantColor = Colors.LightPink; // 默认颜色
                int maxFrequency = 0;
                foreach (var kvp in colorFrequency)
                {
                    if (kvp.Value > maxFrequency)
                    {
                        maxFrequency = kvp.Value;
                        dominantColor = kvp.Key;
                    }
                }

                return dominantColor;
            }
            catch
            {
                // 处理图片加载失败，返回默认颜色
                return Colors.LightPink;
            }
        }

        /// <summary>
        /// 调整颜色亮度
        /// </summary>
        /// <param name="color">原始颜色</param>
        /// <param name="factor">亮度调整因子（小于1变暗，大于1变亮）</param>
        /// <returns>调整后的颜色</returns>
        private Color AdjustColorBrightness(Color color, float factor)
        {
            float r = color.R * factor;
            float g = color.G * factor;
            float b = color.B * factor;

            return Color.FromRgb(
                (byte)Math.Max(0, Math.Min(255, r)),
                (byte)Math.Max(0, Math.Min(255, g)),
                (byte)Math.Max(0, Math.Min(255, b))
            );
        }

        /// <summary>
        /// 获取与给定颜色对比度高的颜色
        /// </summary>
        /// <param name="color">原始颜色</param>
        /// <returns>对比色</returns>
        private Color GetContrastColor(Color color)
        {
            // 计算颜色的亮度
            double brightness = (0.299 * color.R + 0.587 * color.G + 0.114 * color.B) / 255;
            
            // 如果亮度大于0.5，返回黑色；否则返回白色
            return brightness > 0.5 ? Colors.Black : Colors.White;
        }

        /// <summary>
        /// 保存皮肤配置
        /// </summary>
        public void SaveSkins()
        {
            try
            {
                using (StreamWriter writer = new StreamWriter(SkinConfigFile, false, Encoding.Default))
                {
                    writer.WriteLine("# 皮肤配置文件");
                    writer.WriteLine("# 格式: 名称|背景色|按钮色|边框色|文本色|分组框边框色|组合框基色|组合框边框色");
                    writer.WriteLine();

                    // 只保存自定义皮肤（非默认皮肤和非模板皮肤）
                    foreach (SkinData skin in skins.Where(s => !IsDefaultSkin(s) && !IsTemplateSkin(s)))
                    {
                        writer.WriteLine(skin.ToString());
                    }
                }
            }
            catch
            {
                // 保存失败
            }
        }

        /// <summary>
        /// 判断是否为默认皮肤
        /// </summary>
        /// <param name="skin">皮肤数据</param>
        /// <returns>是否为默认皮肤</returns>
        private bool IsDefaultSkin(SkinData skin)
        {
            string[] defaultSkinNames = { "粉色主题", "珊瑚主题", "蓝色主题", "紫色主题", "绿色主题", "金色主题" };
            return defaultSkinNames.Contains(skin.Name);
        }

        /// <summary>
        /// 判断是否为模板皮肤
        /// </summary>
        /// <param name="skin">皮肤数据</param>
        /// <returns>是否为模板皮肤</returns>
        private bool IsTemplateSkin(SkinData skin)
        {
            try
            {
                // 检查skin.Name是否对应template文件夹中的图片文件
                // 尝试多个可能的路径
                string[] possiblePaths = {
                    Path.Combine(AppDomain.CurrentDomain.BaseDirectory, TemplateFolder),
                    Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "..", "..", "..", TemplateFolder),
                    Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "..", "..", TemplateFolder)
                };
                
                foreach (var templatePath in possiblePaths)
                {
                    if (Directory.Exists(templatePath))
                    {
                        string[] imageExtensions = { ".jpg", ".jpeg", ".png", ".bmp" };
                        foreach (var extension in imageExtensions)
                        {
                            string expectedFilePath = Path.Combine(templatePath, skin.Name + extension);
                            if (File.Exists(expectedFilePath))
                            {
                                return true;
                            }
                        }
                    }
                }
            }
            catch
            {
                // 处理文件夹访问失败
            }
            return false;
        }

        /// <summary>
        /// 添加新皮肤
        /// </summary>
        /// <param name="skin">皮肤数据</param>
        public void AddSkin(SkinData skin)
        {
            if (!skins.Any(s => s.Name == skin.Name))
            {
                skins.Add(skin);
                SaveSkins();
            }
        }

        /// <summary>
        /// 删除皮肤
        /// </summary>
        /// <param name="skinName">皮肤名称</param>
        public void RemoveSkin(string skinName)
        {
            // 不允许删除默认皮肤和模板皮肤
            SkinData tempSkin = new SkinData { Name = skinName };
            if (!IsDefaultSkin(tempSkin) && !IsTemplateSkin(tempSkin))
            {
                skins.RemoveAll(s => s.Name == skinName);
                SaveSkins();
            }
        }

        /// <summary>
        /// 更新皮肤
        /// </summary>
        /// <param name="skin">皮肤数据</param>
        public void UpdateSkin(SkinData skin)
        {
            // 不允许更新默认皮肤和模板皮肤
            if (!IsDefaultSkin(skin) && !IsTemplateSkin(skin))
            {
                int index = skins.FindIndex(s => s.Name == skin.Name);
                if (index >= 0)
                {
                    skins[index] = skin;
                    SaveSkins();
                }
            }
        }

        /// <summary>
        /// 获取皮肤名称列表
        /// </summary>
        /// <returns>皮肤名称列表</returns>
        public List<string> GetSkinNames()
        {
            return skins.Select(s => s.Name).ToList();
        }

        /// <summary>
        /// 根据名称获取皮肤
        /// </summary>
        /// <param name="skinName">皮肤名称</param>
        /// <returns>皮肤数据</returns>
        public SkinData GetSkinByName(string skinName)
        {
            return skins.FirstOrDefault(s => s.Name == skinName) ?? skins[0];
        }
    }
}