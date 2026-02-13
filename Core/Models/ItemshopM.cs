using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace FS服装搭配专家v1._0
{
    // Token: 0x0200000C RID: 12
    public class ItemshopM
    {
        // Token: 0x17000010 RID: 16
        // (get)
        // (set)
        public string ItemCode { get; set; }

        // Token: 0x17000011 RID: 17
        // (get)
        // (set)
        public string PakNum { get; set; }

        // Token: 0x17000012 RID: 18
        // (get)
        // (set)
        public string ImgPath { get; set; }

        // Token: 0x17000013 RID: 19
        // (get)
        // (set)
        public string EffectCode { get; set; }

        // Token: 0x17000014 RID: 20
        // (get)
        // (set)
        public string ItemName { get; set; }

        // Token: 0x17000015 RID: 21
        // (get)
        // (set)
        public string Comment { get; set; }

        // Token: 0x17000016 RID: 22
        // (get)
        // (set)
        public string RowBackColor { get; set; }

        // Token: 0x17000017 RID: 23
        // (get)
        // (set)
        public string EditNewCode { get; set; }

        // Token: 0x17000018 RID: 24
        // (get)
        // (set)
        public string ItemType { get; set; }

        // Token: 0x17000019 RID: 25
        // (get)
        // (set)
        public string ImgView
        {
            get
            {
                return this.ImgPath;
            }
            set
            {
                this.ImgPath = value;
            }
        }

        // Token: 0x1700001A RID: 26
        // (get)
        // (set)
        public string NumSort
        {
            get
            {
                return this.ItemCode;
            }
            set
            {
                this.ItemCode = value;
            }
        }

        // Token: 0x1700001B RID: 27
        // (get)
        // (set)
        public string view
        {
            get
            {
                return "查看"; ;
            }
            set
            {
            }
        }

        // Token: 0x1700001C RID: 28
        // (get)
        // (set)
        public string ReSetPak
        {
            get
            {
                return "还原";
            }
            set
            {
            }
        }

        // Token: 0x1700001D RID: 29
        // (get)
        // (set)
        public string viewOhter
        {
            get
            {
                return this.PakNum;
            }
            set
            {
                this.PakNum = value;
            }
        }

        // Token: 0x1700001E RID: 30
        // (get)
        // (set)
        public string EffAndItemName
        {
            get
            {
                return this.EffectCode + "-" + this.ItemName;
            }
            set
            {
            }
        }
    }
}