namespace FS服装搭配专家.Core.Models
{
    public class SlotConfigM
    {
        public int Id { get; set; }
        public string Key { get; set; } = "";
        public string Name { get; set; } = "";
        public string Prefix { get; set; } = "";
        public string Sample { get; set; } = "";
        public string Lifecycle { get; set; } = "unknown";
        public bool Hidden { get; set; }

        // 运行时填充
        public int CurrentCode { get; set; }
        public string CurrentName { get; set; } = "";
        public string CurrentPak { get; set; } = "";
        public string? CurrentImg { get; set; }

        public int? TargetCode { get; set; }
        public string TargetName { get; set; } = "";
        public string TargetPak { get; set; } = "";
        public string? TargetImg { get; set; }

        public bool HasTarget => TargetCode.HasValue && TargetCode.Value > 0;
        public bool NeedsPersistentHook => Lifecycle == "reload";
    }
}
