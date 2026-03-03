using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Text.Json;
using FS服装搭配专家v1._0.Core.Models;
using FS服装搭配专家v1._0.Core.Services;

namespace FS服装搭配专家v1._0
{
    public class SkinManager
    {
        private const string CurrentSkinConfigFile = "current_skin.ini";
        private readonly ThemeLoader _themeLoader;
        private List<SkinTheme> _themes;
        private SkinTheme _currentTheme;

        public List<SkinTheme> Themes => _themes;
        public SkinTheme CurrentTheme => _currentTheme;

        public SkinManager()
        {
            _themeLoader = new ThemeLoader();
            _themes = new List<SkinTheme>();
            LoadThemes();
        }

        public void LoadThemes()
        {
            _themes.Clear();

            _themeLoader.EnsureDefaultThemesExist();

            _themes = _themeLoader.LoadAllThemes();

            string savedThemeId = LoadCurrentThemeId();
            if (!string.IsNullOrEmpty(savedThemeId))
            {
                _currentTheme = _themes.Find(t => t.Id == savedThemeId) ?? _themes[0];
            }
            else
            {
                _currentTheme = _themes.Count > 0 ? _themes[0] : _themeLoader.GetDefaultTheme();
            }
        }

        public void ApplyTheme(string themeId)
        {
            var theme = _themes.Find(t => t.Id == themeId);
            if (theme != null)
            {
                _currentTheme = theme;
                SaveCurrentThemeId(themeId);
                ThemeChanged?.Invoke(this, EventArgs.Empty);
            }
        }

        public void ApplyTheme(SkinTheme theme)
        {
            if (theme != null)
            {
                _currentTheme = theme;
                SaveCurrentThemeId(theme.Id);
                ThemeChanged?.Invoke(this, EventArgs.Empty);
            }
        }

        public event EventHandler? ThemeChanged;

        private string LoadCurrentThemeId()
        {
            try
            {
                if (File.Exists(CurrentSkinConfigFile))
                {
                    return File.ReadAllText(CurrentSkinConfigFile).Trim();
                }
            }
            catch
            {
            }
            return string.Empty;
        }

        private void SaveCurrentThemeId(string themeId)
        {
            try
            {
                File.WriteAllText(CurrentSkinConfigFile, themeId);
            }
            catch
            {
            }
        }

        public SkinTheme GetThemeById(string themeId)
        {
            return _themes.Find(t => t.Id == themeId) ?? _themeLoader.GetDefaultTheme();
        }

        public void AddCustomTheme(SkinTheme theme)
        {
            if (!_themes.Exists(t => t.Id == theme.Id))
            {
                _themeLoader.SaveTheme(theme);
                _themes.Add(theme);
            }
        }

        public void DeleteCustomTheme(string themeId)
        {
            if (themeId == "default" || themeId == "dark")
            {
                return;
            }

            var theme = _themes.Find(t => t.Id == themeId);
            if (theme != null)
            {
                _themes.Remove(theme);
                _themeLoader.DeleteTheme(themeId);
            }
        }

        public string GetSkinsPath()
        {
            return _themeLoader.GetSkinsPath();
        }
    }
}
