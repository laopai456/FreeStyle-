namespace FS服装搭配专家v1._0.Core.Config
{
    public static class AppConfig
    {
        public static class Directories
        {
            public const string Cookies = "cookies";
            public const string Pack = "pack";
            public const string Skins = "skins";
            public const string Videos = "videos";
            public const string Logs = "logs";
        }

        public static class Files
        {
            public const string Config = "app.config.json";
            public const string DopakLog = "dopaklog.ini";
            public const string OftenItemCode = "oftenitemcode.ini";
            public const string ItemTextPak = "item_text.pak";
            public const string ResourcesExe = "resources.exe";
        }

        public static class WindowSize
        {
            public const double MainWindowWidth = 1440;
            public const double MainWindowHeight = 768;
            public const double BgCropWindowWidth = 800;
            public const double BgCropWindowHeight = 600;
            public const double FillBytesWindowWidth = 700;
            public const double FillBytesWindowHeight = 550;
            public const double ConfirmDialogWidth = 550;
            public const double ConfirmDialogHeight = 140;
        }

        public static class IconSize
        {
            public const double ContainerSize = 70;
            public const double IconDisplaySize = 60;
        }

        public static class Theme
        {
            public const string DefaultThemeId = "default";
            public const string DarkThemeId = "dark";
            public const string GalaxyThemeId = "galaxy";
            public const string ThemeFileName = "theme.json";
            public const string SkinsConfigFileName = "skins.json";
        }
    }
}
