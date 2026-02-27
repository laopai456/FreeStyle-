using System.Windows;

namespace FS服装搭配专家v1._0
{
    public partial class ConfirmDialog : Window
    {
        public bool Result { get; private set; }

        public ConfirmDialog(string message)
        {
            InitializeComponent();
            MessageText.Text = message;
            Result = false;
        }

        private void Confirm_Click(object sender, RoutedEventArgs e)
        {
            Result = true;
            this.Close();
        }

        private void Cancel_Click(object sender, RoutedEventArgs e)
        {
            Result = false;
            this.Close();
        }
    }
}
