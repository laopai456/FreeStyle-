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

        [JsonPropertyName("mainWindowWidth")]
        public double MainWindowWidth { get; set; } = 1440;

        [JsonPropertyName("mainWindowHeight")]
        public double MainWindowHeight { get; set; } = 768;

        [JsonPropertyName("bgCropWindowWidth")]
        public double BgCropWindowWidth { get; set; } = 800;

        [JsonPropertyName("bgCropWindowHeight")]
        public double BgCropWindowHeight { get; set; } = 600;

        [JsonPropertyName("fillBytesWindowWidth")]
        public double FillBytesWindowWidth { get; set; } = 800;

        [JsonPropertyName("fillBytesWindowHeight")]
        public double FillBytesWindowHeight { get; set; } = 600;

        [JsonPropertyName("skinWindowWidth")]
        public double SkinWindowWidth { get; set; } = 600;

        [JsonPropertyName("skinWindowHeight")]
        public double SkinWindowHeight { get; set; } = 400;

        [JsonPropertyName("teamSelectionWindowWidth")]
        public double TeamSelectionWindowWidth { get; set; } = 800;

        [JsonPropertyName("teamSelectionWindowHeight")]
        public double TeamSelectionWindowHeight { get; set; } = 600;
    }

    public class DataConfig
    {
        [JsonPropertyName("pakSizes")]
        public Dictionary<string, long> PakSizes { get; set; } = new Dictionary<string, long>();

        [JsonPropertyName("referenceBytes")]
        public Dictionary<string, string> ReferenceBytes { get; set; } = new Dictionary<string, string>();
    }
}
