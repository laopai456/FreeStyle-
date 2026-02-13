using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace FS服装搭配专家v1._0
{
    // Token: 0x0200000F RID: 15
    public class VoiceM
    {
        // Token: 0x17000022 RID: 34
        // (get)
        // (set)
        public string VoiceCode { get; set; }

        // Token: 0x17000023 RID: 35
        // (get)
        // (set)
        public string VoicePath { get; set; }

        // Token: 0x17000022 RID: 34
        // (get)
        // (set)
        public string SoundName { get; set; }

        // Token: 0x17000023 RID: 35
        // (get)
        public string VoiceType
        {
            get
            {
                string result = "";
                if (this.SoundName != null && this.SoundName.ToLower().Contains("backcourt"))
                {
                    result = "注意防守！(#6)";
                }
                else if (this.SoundName != null && this.SoundName.ToLower().Contains("boxout"))
                {
                    result = "卡位,篮板！(#5)";
                }
                else if (this.SoundName != null && this.SoundName.ToLower().Contains("goodjob"))
                {
                    result = "好球！(#1)";
                }
                else if (this.SoundName != null && this.SoundName.ToLower().Contains("niceassist"))
                {
                    result = "妙传！(#2)";
                }
                else if (this.SoundName != null && this.SoundName.ToLower().Contains("passme"))
                {
                    result = "传球给我!(#S)";
                }
                else if (this.SoundName != null && this.SoundName.ToLower().Contains("screen"))
                {
                    result = "挡拆！(#4)";
                }
                else if (this.SoundName != null && this.SoundName.ToLower().Contains("sorry"))
                {
                    result = "我的！(#3)";
                }
                else if (this.SoundName != null && this.SoundName.ToLower().Contains("groaning"))
                {
                    result = "对抗呻吟声(自动)";
                }
                else if (this.SoundName != null && this.SoundName.ToLower().Contains("yell"))
                {
                    result = "Year(自动)";
                }
                return result;
            }
        }

        // Token: 0x17000024 RID: 36
        // (get)
        // (set)
        public string view
        {
            get
            {
                return "查看";
            }
            set
            {
            }
        }
    }
}