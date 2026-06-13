using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Text.Json;
using FS服装搭配专家.Core.Models;
using FS服装搭配专家.Core.Services;
using FS服装搭配专家.Core.Config;

namespace FS服装搭配专家
{
    public class SkinManager
    {
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

            string savedThemeId = ConfigService.Instance.CurrentTheme;
            if (!string.IsNullOrEmpty(savedThemeId))
            {
                _currentTheme = _themes.Find(t => t.Id == savedThemeId);
                if (_currentTheme == null)
                {
                    // 保存的主题找不到（可能被删除），回退到 default 并更新配置
                    _currentTheme = _themes.Find(t => t.Id == "default") ?? _themes[0];
                    ConfigService.Instance.CurrentTheme = _currentTheme.Id;
                }
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
                ConfigService.Instance.CurrentTheme = themeId;
                ThemeChanged?.Invoke(this, EventArgs.Empty);
            }
        }

        public void ApplyTheme(SkinTheme theme)
        {
            if (theme != null)
            {
                _currentTheme = theme;
                ConfigService.Instance.CurrentTheme = theme.Id;
                ThemeChanged?.Invoke(this, EventArgs.Empty);
            }
        }

        public event EventHandler? ThemeChanged;

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

        public void AddTheme(SkinTheme theme)
        {
            if (!_themes.Exists(t => t.Id == theme.Id))
            {
                _themes.Add(theme);
            }
        }

        public void DeleteCustomTheme(string themeId)
        {
            if (themeId == "default" || themeId == "dark" || themeId == "galaxy")
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
