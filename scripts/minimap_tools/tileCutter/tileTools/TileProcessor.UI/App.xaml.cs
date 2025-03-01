using System.Windows;

namespace TileProcessor.UI
{
    // Fully qualify the Application class to avoid ambiguity
    public partial class App : System.Windows.Application
    {
        protected override void OnStartup(StartupEventArgs e)
        {
            base.OnStartup(e);
            
            var mainWindow = new MainWindow();
            mainWindow.Show();
        }
    }
}