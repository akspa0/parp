using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using System.Windows;
// Use fully qualified names for WPF versions
using WPFMessageBox = System.Windows.MessageBox;
using WPFOpenFileDialog = Microsoft.Win32.OpenFileDialog;
using WPFSaveFileDialog = Microsoft.Win32.SaveFileDialog;
// System.Windows.Forms is still imported for FolderBrowserDialog

namespace TileProcessor.UI
{
    public partial class MainWindow : Window
    {
        private bool _isCutMode = true;
        
        public MainWindow()
        {
            InitializeComponent();
            
            // Initialize with Cut mode selected
            SetCutMode();
        }

        private void SetCutMode()
        {
            _isCutMode = true;

            if (lblMode != null) lblMode.Content = "Cut Image Mode";
            if (lblPrimaryInput != null) lblPrimaryInput.Content = "Input Image:";
            if (btnBrowseInput != null) btnBrowseInput.Content = "Browse Image...";
            if (lblPrefix != null) lblPrefix.Visibility = Visibility.Visible;
            if (txtPrefix != null) txtPrefix.Visibility = Visibility.Visible;

            // Show/hide appropriate options
            if (chkCombineOutput != null) chkCombineOutput.Visibility = Visibility.Visible;
            if (chkVCol != null) chkVCol.Visibility = Visibility.Visible;
            if (chkIncludeAlpha != null) chkIncludeAlpha.Visibility = Visibility.Collapsed;
        }

        private void SetJoinMode()
        {
            _isCutMode = false;

            if (lblMode != null) lblMode.Content = "Join Tiles Mode";
            if (lblPrimaryInput != null) lblPrimaryInput.Content = "Input Folder:";
            if (btnBrowseInput != null) btnBrowseInput.Content = "Browse Folder...";
            if (lblPrefix != null) lblPrefix.Visibility = Visibility.Collapsed;
            if (txtPrefix != null) txtPrefix.Visibility = Visibility.Collapsed;

            // Show/hide appropriate options
            if (chkCombineOutput != null) chkCombineOutput.Visibility = Visibility.Collapsed;
            if (chkVCol != null) chkVCol.Visibility = Visibility.Collapsed;
            if (chkIncludeAlpha != null) chkIncludeAlpha.Visibility = Visibility.Visible;
        }

        private void RadioCut_Checked(object sender, RoutedEventArgs e)
        {
            SetCutMode();
        }

        private void RadioJoin_Checked(object sender, RoutedEventArgs e)
        {
            SetJoinMode();
        }

        private void BtnBrowseInput_Click(object sender, RoutedEventArgs e)
        {
            if (_isCutMode)
            {
                // Browse for image file
                var openFileDialog = new WPFOpenFileDialog
                {
                    Filter = "Image files (*.png;*.jpg;*.jpeg;*.bmp;*.tif)|*.png;*.jpg;*.jpeg;*.bmp;*.tif|All files (*.*)|*.*",
                    Title = "Select an image file"
                };

                if (openFileDialog.ShowDialog() == true)
                {
                    txtInputPath.Text = openFileDialog.FileName;
                }
            }
            else
            {
                // Browse for folder
                var dialog = new System.Windows.Forms.FolderBrowserDialog
                {
                    Description = "Select folder containing image tiles",
                    UseDescriptionForTitle = true,
                    ShowNewFolderButton = true
                };

                if (dialog.ShowDialog() == System.Windows.Forms.DialogResult.OK)
                {
                    txtInputPath.Text = dialog.SelectedPath;
                }
            }
        }

        private void BtnBrowseOutput_Click(object sender, RoutedEventArgs e)
        {
            if (_isCutMode)
            {
                // Browse for output folder
                var dialog = new System.Windows.Forms.FolderBrowserDialog
                {
                    Description = "Select output folder for tiles",
                    UseDescriptionForTitle = true,
                    ShowNewFolderButton = true
                };

                if (dialog.ShowDialog() == System.Windows.Forms.DialogResult.OK)
                {
                    txtOutputPath.Text = dialog.SelectedPath;
                }
            }
            else
            {
                // Browse for output image file
                var saveFileDialog = new WPFSaveFileDialog
                {
                    Filter = "PNG Image (*.png)|*.png|All files (*.*)|*.*",
                    Title = "Save joined image as",
                    DefaultExt = ".png"
                };

                if (saveFileDialog.ShowDialog() == true)
                {
                    txtOutputPath.Text = saveFileDialog.FileName;
                }
            }
        }

        private void BtnProcess_Click(object sender, RoutedEventArgs e)
        {
            // Validate inputs
            if (string.IsNullOrWhiteSpace(txtInputPath.Text))
            {
                ShowError("Please select an input " + (_isCutMode ? "image" : "folder"));
                return;
            }

            if (string.IsNullOrWhiteSpace(txtOutputPath.Text))
            {
                ShowError("Please select an output " + (_isCutMode ? "folder" : "file"));
                return;
            }

            if (_isCutMode && string.IsNullOrWhiteSpace(txtPrefix.Text))
            {
                ShowError("Please enter a prefix for the output filenames");
                return;
            }

            if (!int.TryParse(txtTileSize.Text, out int tileSize) || tileSize <= 0)
            {
                ShowError("Please enter a valid tile size (positive integer)");
                return;
            }

            // Prepare command
            var arguments = new List<string>();

            if (_isCutMode)
            {
                arguments.Add("cut");
                arguments.Add($"--input-image \"{txtInputPath.Text}\"");
                arguments.Add($"--output-folder \"{txtOutputPath.Text}\"");
                arguments.Add($"--tile-size {tileSize}");
                arguments.Add($"--prefix \"{txtPrefix.Text}\"");

                if (!chkCombineOutput.IsChecked.GetValueOrDefault())
                {
                    arguments.Add("--no-combine");
                }

                if (chkVCol.IsChecked.GetValueOrDefault())
                {
                    arguments.Add("--vcol");
                }
            }
            else
            {
                arguments.Add("join");
                arguments.Add($"--input-folder \"{txtInputPath.Text}\"");
                arguments.Add($"--output-image \"{txtOutputPath.Text}\"");
                arguments.Add($"--tile-size {tileSize}");
                
                if (!chkIncludeAlpha.IsChecked.GetValueOrDefault())
                {
                    arguments.Add("--include-alpha false");
                }
            }

            if (!chkCreateKrita.IsChecked.GetValueOrDefault())
            {
                arguments.Add("--create-krita false");
            }

            // Show progress and disable UI
            txtOutput.Text = "Processing... Please wait.\n";
            SetUIEnabled(false);

            // Run in background
            Task.Run(() =>
            {
                try
                {
                    // Start the process
                    var command = string.Join(" ", arguments);
                    RunProcess(command);
                }
                catch (Exception ex)
                {
                    Dispatcher.Invoke(() =>
                    {
                        txtOutput.Text += $"Error: {ex.Message}\n";
                        SetUIEnabled(true);
                    });
                }
            });
        }

        private void RunProcess(string arguments)
        {
            try
            {
                var currentAssembly = System.Reflection.Assembly.GetExecutingAssembly();
                var executablePath = currentAssembly.Location;
                var executableDir = Path.GetDirectoryName(executablePath);

                // First, try to find the executable in the most likely locations
                var possibleLocations = new[]
                {
            Path.Combine(executableDir, "TileProcessor.exe"),
            Path.Combine(executableDir, "..", "TileProcessor", "bin", "Debug", "net8.0", "TileProcessor.exe"),
            Path.Combine(executableDir, "..", "..", "TileProcessor", "bin", "Debug", "net8.0", "TileProcessor.exe"),
            Path.Combine(executableDir, "..", "..", "..", "TileProcessor", "bin", "Debug", "net8.0", "TileProcessor.exe")
        };

                string cliPath = null;

                foreach (var location in possibleLocations)
                {
                    var fullPath = Path.GetFullPath(location);
                    Dispatcher.Invoke(() => {
                        txtOutput.Text += $"Checking location: {fullPath}\n";
                    });

                    if (File.Exists(fullPath))
                    {
                        cliPath = fullPath;
                        Dispatcher.Invoke(() => {
                            txtOutput.Text += $"Found executable at: {cliPath}\n";
                        });
                        break;
                    }
                }

                if (cliPath == null)
                {
                    Dispatcher.Invoke(() => {
                        txtOutput.Text += "ERROR: Could not find TileProcessor.exe in any expected location.\n";
                        txtOutput.Text += "Please build the TileProcessor project and try again.\n";
                        SetUIEnabled(true);
                    });
                    return;
                }

                // For diagnostic purposes, try running a simple command
                Dispatcher.Invoke(() => {
                    txtOutput.Text += $"Attempting to run: {cliPath} --help\n";
                });

                var startInfo = new ProcessStartInfo
                {
                    FileName = cliPath,
                    Arguments = arguments,
                    UseShellExecute = false,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    CreateNoWindow = true,
                    WorkingDirectory = executableDir // Set the working directory explicitly
                };

                Dispatcher.Invoke(() => {
                    txtOutput.Text += $"Full command: {cliPath} {arguments}\n";
                    txtOutput.Text += $"Working directory: {executableDir}\n";
                });

                using var process = new Process { StartInfo = startInfo };

                process.OutputDataReceived += (sender, e) =>
                {
                    if (!string.IsNullOrEmpty(e.Data))
                    {
                        Dispatcher.Invoke(() =>
                        {
                            txtOutput.Text += "OUT: " + e.Data + "\n";
                            txtOutput.ScrollToEnd();
                        });
                    }
                };

                process.ErrorDataReceived += (sender, e) =>
                {
                    if (!string.IsNullOrEmpty(e.Data))
                    {
                        Dispatcher.Invoke(() =>
                        {
                            txtOutput.Text += "ERR: " + e.Data + "\n";
                            txtOutput.ScrollToEnd();
                        });
                    }
                };

                Dispatcher.Invoke(() => {
                    txtOutput.Text += "Starting process...\n";
                });

                bool started = process.Start();

                if (!started)
                {
                    Dispatcher.Invoke(() => {
                        txtOutput.Text += "ERROR: Failed to start the process.\n";
                        SetUIEnabled(true);
                    });
                    return;
                }

                Dispatcher.Invoke(() => {
                    txtOutput.Text += $"Process started with ID: {process.Id}\n";
                });

                process.BeginOutputReadLine();
                process.BeginErrorReadLine();

                // Add a timeout
                bool exited = process.WaitForExit(60000); // 60 second timeout

                if (!exited)
                {
                    Dispatcher.Invoke(() => {
                        txtOutput.Text += "ERROR: Process timed out after 60 seconds.\n";
                        SetUIEnabled(true);
                    });

                    try { process.Kill(); } catch { }
                    return;
                }

                Dispatcher.Invoke(() =>
                {
                    txtOutput.Text += $"Process exited with code: {process.ExitCode}\n";

                    if (process.ExitCode == 0)
                    {
                        txtOutput.Text += "Process completed successfully.\n";
                    }
                    else
                    {
                        txtOutput.Text += $"Process completed with errors. Exit code: {process.ExitCode}\n";
                    }
                    SetUIEnabled(true);
                });
            }
            catch (Exception ex)
            {
                Dispatcher.Invoke(() =>
                {
                    txtOutput.Text += $"Exception: {ex.Message}\n";
                    txtOutput.Text += $"Stack trace: {ex.StackTrace}\n";
                    SetUIEnabled(true);
                });
            }
        }

        private void SetUIEnabled(bool enabled)
        {
            // Enable/disable all input controls
            radioCut.IsEnabled = enabled;
            radioJoin.IsEnabled = enabled;
            txtInputPath.IsEnabled = enabled;
            txtOutputPath.IsEnabled = enabled;
            txtPrefix.IsEnabled = enabled;
            txtTileSize.IsEnabled = enabled;
            btnBrowseInput.IsEnabled = enabled;
            btnBrowseOutput.IsEnabled = enabled;
            btnProcess.IsEnabled = enabled;
            chkCreateKrita.IsEnabled = enabled;
            chkCombineOutput.IsEnabled = enabled;
            chkVCol.IsEnabled = enabled;
            chkIncludeAlpha.IsEnabled = enabled;
        }

        private void ShowError(string message)
        {
            WPFMessageBox.Show(message, "Error", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }
}
