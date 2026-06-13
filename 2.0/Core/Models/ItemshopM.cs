using System;
using System.Text.RegularExpressions;

namespace FS服装搭配专家.Core.Models
{
    public class ItemshopM
    {
        public string ItemCode { get; set; } = "";
        public string PakNum { get; set; } = "";
        public string ImgPath { get; set; } = "";
        public string EffectCode { get; set; } = "";
        public string ItemName { get; set; } = "";
        public string Comment { get; set; } = "";

        public string ImgView => ImgPath;
        public string NumSort => ItemCode;
        public string EffAndItemName => $"{EffectCode}-{ItemName}";

        /// <summary>
        /// 特效是否为纯数字编号（如 "1479"），而非能力描述文本（如 "选择1个能力值+1"）
        /// </summary>
        public bool IsEffectId => !string.IsNullOrEmpty(EffectCode) && EffectCode != "无"
            && Regex.IsMatch(EffectCode, @"^\d+$");

        /// <summary>
        /// 特效显示文本：纯数字→"特效 #1479"，能力描述→截断显示，无→空
        /// </summary>
        public string EffectDisplay
        {
            get
            {
                if (string.IsNullOrEmpty(EffectCode) || EffectCode == "无") return "";
                if (IsEffectId) return $"特效 #{EffectCode}";
                // 能力描述：取第一行（\n前）
                var firstLine = EffectCode.Split('\\')[0];
                return firstLine.Length > 12 ? firstLine.Substring(0, 12) + "…" : firstLine;
            }
        }

        /// <summary>
        /// 列表显示：名称 + 特效标记
        /// </summary>
        public string ListDisplay => IsEffectId
            ? $"{ItemName} [特效#{EffectCode}]"
            : ItemName;

        /// <summary>
        /// 列表中的特效徽章文本（纯数字特效显示，其他为空）
        /// </summary>
        public string EffectBadge => IsEffectId ? $"[特效#{EffectCode}]" : "";
    }
}
