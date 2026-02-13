using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Windows.Media;

namespace FS服装搭配专家v1._0
{
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

                    // 只保存自定义皮肤（非默认皮肤）
                    foreach (SkinData skin in skins.Where(s => !IsDefaultSkin(s)))
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
            // 不允许删除默认皮肤
            if (!IsDefaultSkin(new SkinData { Name = skinName }))
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
            int index = skins.FindIndex(s => s.Name == skin.Name);
            if (index >= 0)
            {
                skins[index] = skin;
                SaveSkins();
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