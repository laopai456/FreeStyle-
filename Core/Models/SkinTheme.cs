using System;
using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace FS服装搭配专家v1._0.Core.Models
{
    public class SkinTheme
    {
        public string Id { get; set; } = "default";
        public string Name { get; set; } = "默认主题";
        public string Author { get; set; } = "";
        public string Version { get; set; } = "1.0";
        public string Description { get; set; } = "";
        public ThemeStyles Styles { get; set; } = new ThemeStyles();
    }

    public class ThemeStyles
    {
        public WindowStyle Window { get; set; } = new WindowStyle();
        public CardStyle Card { get; set; } = new CardStyle();
        public ButtonStyle Button { get; set; } = new ButtonStyle();
        public TextStyle Text { get; set; } = new TextStyle();
        public ListItemStyle ListItem { get; set; } = new ListItemStyle();
        public TabStyle Tab { get; set; } = new TabStyle();
        public TextBoxStyle TextBox { get; set; } = new TextBoxStyle();
        public ScrollBarStyle ScrollBar { get; set; } = new ScrollBarStyle();
    }

    public class WindowStyle
    {
        public BackgroundStyle Background { get; set; } = new BackgroundStyle();
    }

    public class BackgroundStyle
    {
        public string Type { get; set; } = "gradient";
        public List<string> Colors { get; set; } = new List<string> { "#6a85b6", "#bac8e0", "#f0c9e8" };
        public double Angle { get; set; } = 135;
        public string? ImagePath { get; set; }
        public string? VideoPath { get; set; }
        public double Volume { get; set; } = 0;
    }

    public class CardStyle
    {
        public string Background { get; set; } = "#15FFFFFF";
        public string BorderColor { get; set; } = "#20FFFFFF";
        public string ContentPanelBackground { get; set; } = "#0DFFFFFF";
        public double CornerRadius { get; set; } = 16;
        public ShadowStyle? Shadow { get; set; } = new ShadowStyle();
    }

    public class ShadowStyle
    {
        public double BlurRadius { get; set; } = 40;
        public double ShadowDepth { get; set; } = 12;
        public double Opacity { get; set; } = 0.15;
        public string Color { get; set; } = "#000000";
    }

    public class ButtonStyle
    {
        public string Background { get; set; } = "#25FFFFFF";
        public string HoverBackground { get; set; } = "#40FFFFFF";
        public string PressedBackground { get; set; } = "#40FFFFFF";
        public string BorderColor { get; set; } = "#20FFFFFF";
        public double CornerRadius { get; set; } = 16;
        public string Foreground { get; set; } = "#FFFFFFFF";
        public ShadowStyle? Shadow { get; set; } = new ShadowStyle { BlurRadius = 16, ShadowDepth = 4, Opacity = 0.1 };
    }

    public class TextStyle
    {
        public string Primary { get; set; } = "#FFFFFFFF";
        public string Secondary { get; set; } = "#FFCCCCCC";
        public string Title { get; set; } = "#FFFFFFFF";
        public string Body { get; set; } = "#E6FFFFFF";
        public string? FontFamily { get; set; }
        public string? FontWeight { get; set; }
    }

    public class ListItemStyle
    {
        public string Background { get; set; } = "#1AFFFFFF";
        public string HoverBackground { get; set; } = "#33FFFFFF";
        public string SelectedBackground { get; set; } = "#33FFFFFF";
        public string BorderColor { get; set; } = "#33FFFFFF";
        public double CornerRadius { get; set; } = 12;
        public string? Foreground { get; set; }
    }

    public class TabStyle
    {
        public string Background { get; set; } = "transparent";
        public string SelectedBackground { get; set; } = "#40FFFFFF";
        public string HoverBackground { get; set; } = "#25FFFFFF";
        public string BorderColor { get; set; } = "#20FFFFFF";
        public string SelectedForeground { get; set; } = "#FFFFFFFF";
        public double CornerRadius { get; set; } = 8;
    }

    public class TextBoxStyle
    {
        public string Background { get; set; } = "#20FFFFFF";
        public string BorderColor { get; set; } = "#4DFFFFFF";
        public string Foreground { get; set; } = "#FFFFFFFF";
        public double CornerRadius { get; set; } = 8;
    }

    public class ScrollBarStyle
    {
        public string Background { get; set; } = "Transparent";
        public string ThumbColor { get; set; } = "#4DFFFFFF";
        public double Width { get; set; } = 6;
        public double CornerRadius { get; set; } = 3;
    }
}
