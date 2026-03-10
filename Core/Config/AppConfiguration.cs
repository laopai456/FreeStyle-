using System;
using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace FS服装搭配专家v1._0.Core.Config
{
    public class AppConfiguration
    {
        public GameConfig Game { get; set; } = new GameConfig();
        public UIConfig UI { get; set; } = new UIConfig();
        public DataConfig Data { get; set; } = new DataConfig();

        public static AppConfiguration CreateDefault()
        {
            return new AppConfiguration();
        }
    }

    public class GameConfig
    {
        [JsonPropertyName("installDirectory")]
        public string InstallDirectory { get; set; } = "";

        [JsonPropertyName("mapLibraryPath")]
        public string MapLibraryPath { get; set; } = "";
    }

    public class UIConfig
    {
        [JsonPropertyName("currentTheme")]
        public string CurrentTheme { get; set; } = "default";

        [JsonPropertyName("consoleVisible")]
        public bool ConsoleVisible { get; set; } = false;

        [JsonPropertyName("windowWidth")]
        public double WindowWidth { get; set; } = 1440;

        [JsonPropertyName("windowHeight")]
        public double WindowHeight { get; set; } = 768;
    }

    public class DataConfig
    {
        [JsonPropertyName("pakSizes")]
        public Dictionary<string, long> PakSizes { get; set; } = new Dictionary<string, long>();

        [JsonPropertyName("referenceBytes")]
        public Dictionary<string, string> ReferenceBytes { get; set; } = new Dictionary<string, string>();
    }
}
