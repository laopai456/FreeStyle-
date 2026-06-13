using System;
using System.Collections.Generic;
using System.Windows;
using FS服装搭配专家.Core.Models;
using FS服装搭配专家.Core.Services;

namespace FS服装搭配专家.UI.Windows
{
    public partial class ItemSearchDialog : Window
    {
        private readonly FridaBridge _bridge;
        private readonly SlotConfigM _slot;
        private System.Threading.Timer? _debounceTimer;

        public string SelectedName { get; private set; } = "";
        public string SelectedPak { get; private set; } = "";
        public int SelectedCode { get; private set; }

        public ItemSearchDialog(FridaBridge bridge, SlotConfigM slot)
        {
            InitializeComponent();
            _bridge = bridge;
            _slot = slot;
            TxtSlotName.Text = $"搜索: {slot.Name}";
        }

        private void TxtSearch_TextChanged(object sender, System.Windows.Controls.TextChangedEventArgs e)
        {
            _debounceTimer?.Dispose();
            _debounceTimer = new System.Threading.Timer(async _ =>
            {
                var keyword = "";
                Dispatcher.Invoke(() => keyword = TxtSearch.Text.Trim());
                if (string.IsNullOrEmpty(keyword)) return;

                try
                {
                    var results = await _bridge.SearchAsync(keyword);
                    Dispatcher.Invoke(() =>
                    {
                        LstResults.ItemsSource = results;
                    });
                }
                catch { }
            }, null, 300, Timeout.Infinite);
        }

        private void BtnOk_Click(object sender, RoutedEventArgs e)
        {
            if (LstResults.SelectedItem is SearchResult item)
            {
                SelectedCode = int.Parse(item.Code);
                SelectedName = item.Name;
                SelectedPak = item.Pak;
                DialogResult = true;
            }
        }

        private void BtnCancel_Click(object sender, RoutedEventArgs e)
        {
            DialogResult = false;
        }

        private void LstResults_MouseDoubleClick(object sender, System.Windows.Input.MouseButtonEventArgs e)
        {
            BtnOk_Click(sender, e);
        }
    }
}
