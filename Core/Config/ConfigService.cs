using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Text.Json;

namespace FS服装搭配专家v1._0.Core.Config
{
    public class ConfigService
    {
        private static ConfigService? _instance;
        private static readonly object _lock = new object();

        private readonly string _configPath;
        private AppConfiguration _config;

        public static ConfigService Instance
        {
            get
            {
                if (_instance == null)
                {
                    lock (_lock)
                    {
                        if (_instance == null)
                        {
                            _instance = new ConfigService();
                        }
                    }
                }
                return _instance;
            }
        }

        public AppConfiguration Config => _config;

        private ConfigService()
        {
            string appPath = AppDomain.CurrentDomain.BaseDirectory;
            _configPath = Path.Combine(appPath, "app.config.json");
            _config = LoadOrCreateConfig();
        }

        private AppConfiguration LoadOrCreateConfig()
        {
            bool needMigration = !File.Exists(_configPath);
            
            if (File.Exists(_configPath))
            {
                try
                {
                    string json = File.ReadAllText(_configPath, Encoding.UTF8);
                    if (!string.IsNullOrWhiteSpace(json) && json.Trim() != "null")
                    {
                        var config = JsonSerializer.Deserialize<AppConfiguration>(json, new JsonSerializerOptions
                        {
                            PropertyNameCaseInsensitive = true
                        });
                        if (config != null)
                        {
                            return config;
                        }
                    }
                    needMigration = true;
                    Console.WriteLine("[ConfigService] 配置文件为空或无效，将重新创建");
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"[ConfigService] 加载配置文件失败: {ex.Message}");
                    needMigration = true;
                }
            }

            var newConfig = AppConfiguration.CreateDefault();
            if (needMigration)
            {
                MigrateFromOldConfig(newConfig);
            }
            SaveConfig();
            return newConfig;
        }

        private void MigrateFromOldConfig(AppConfiguration config)
        {
            string appPath = AppDomain.CurrentDomain.BaseDirectory;

            string[] configPaths = new[]
            {
                _configPath,
                Path.Combine(appPath, "config.ini"),
                Path.Combine(appPath, "..", "..", "..", "config.ini"),
                Path.Combine(Environment.CurrentDirectory, "config.ini")
            };

            foreach (var configPath in configPaths)
            {
                if (File.Exists(configPath) && configPath.EndsWith(".ini"))
                {
                    try
                    {
                        var lines = File.ReadAllLines(configPath, Encoding.Default);
                        foreach (var line in lines)
                        {
                            if (line.StartsWith("InstallDirectory="))
                            {
                                config.Game.InstallDirectory = line.Substring("InstallDirectory=".Length).Trim();
                            }
                            else if (line.StartsWith("MapLibraryPath="))
                            {
                                config.Game.MapLibraryPath = line.Substring("MapLibraryPath=".Length).Trim();
                            }
                        }
                        Console.WriteLine($"[ConfigService] 已从 {configPath} 迁移配置");
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine($"[ConfigService] 迁移 config.ini 失败: {ex.Message}");
                    }
                    break;
                }
            }

            string consoleIniPath = Path.Combine(appPath, "console.ini");
            if (File.Exists(consoleIniPath))
            {
                try
                {
                    var content = File.ReadAllText(consoleIniPath, Encoding.Default).Trim();
                    config.UI.ConsoleVisible = content.Equals("true", StringComparison.OrdinalIgnoreCase);
                    Console.WriteLine("[ConfigService] 已迁移 console.ini");
                }
                catch { }
            }

            string skinIniPath = Path.Combine(appPath, "current_skin.ini");
            if (File.Exists(skinIniPath))
            {
                try
                {
                    var content = File.ReadAllText(skinIniPath, Encoding.Default).Trim();
                    if (!string.IsNullOrEmpty(content))
                    {
                        config.UI.CurrentTheme = content;
                    }
                    Console.WriteLine("[ConfigService] 已迁移 current_skin.ini");
                }
                catch { }
            }

            string pakSizesPath = Path.Combine(appPath, "pak_sizes.txt");
            if (File.Exists(pakSizesPath))
            {
                try
                {
                    var lines = File.ReadAllLines(pakSizesPath, Encoding.Default);
                    foreach (var line in lines)
                    {
                        var parts = line.Split('=');
                        if (parts.Length == 2)
                        {
                            if (long.TryParse(parts[1].Trim(), out long size))
                            {
                                config.Data.PakSizes[parts[0].Trim()] = size;
                            }
                        }
                    }
                    Console.WriteLine("[ConfigService] 已迁移 pak_sizes.txt");
                }
                catch { }
            }
        }

        public void SaveConfig()
        {
            try
            {
                var options = new JsonSerializerOptions
                {
                    WriteIndented = true,
                    Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping
                };
                string json = JsonSerializer.Serialize(_config, options);
                File.WriteAllText(_configPath, json, Encoding.UTF8);
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[ConfigService] 保存配置文件失败: {ex.Message}");
            }
        }

        public string GameInstallDirectory
        {
            get => _config.Game.InstallDirectory;
            set
            {
                _config.Game.InstallDirectory = value;
                SaveConfig();
            }
        }

        public string MapLibraryPath
        {
            get => _config.Game.MapLibraryPath;
            set
            {
                _config.Game.MapLibraryPath = value;
                SaveConfig();
            }
        }

        public string CurrentTheme
        {
            get => _config.UI.CurrentTheme;
            set
            {
                _config.UI.CurrentTheme = value;
                SaveConfig();
            }
        }

        public bool ConsoleVisible
        {
            get => _config.UI.ConsoleVisible;
            set
            {
                _config.UI.ConsoleVisible = value;
                SaveConfig();
            }
        }

        public double WindowWidth
        {
            get => _config.UI.WindowWidth;
            set
            {
                _config.UI.WindowWidth = value;
                SaveConfig();
            }
        }

        public double WindowHeight
        {
            get => _config.UI.WindowHeight;
            set
            {
                _config.UI.WindowHeight = value;
                SaveConfig();
            }
        }

        public Dictionary<string, long> PakSizes => _config.Data.PakSizes;

        public void SetPakSize(string pakName, long size)
        {
            _config.Data.PakSizes[pakName] = size;
            SaveConfig();
        }

        public long? GetPakSize(string pakName)
        {
            if (_config.Data.PakSizes.TryGetValue(pakName, out long size))
            {
                return size;
            }
            return null;
        }
    }
}
