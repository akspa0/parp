using System;
using System.IO;
using WarcraftAnalyzer.Files.WDT;
using WarcraftAnalyzer.Files.Serialization;

namespace WarcraftAnalyzer.Examples
{
    /// <summary>
    /// Example program demonstrating how to use the WarcraftAnalyzer library to analyze WDT files.
    /// </summary>
    public class WDTAnalysisExample
    {
        public static void Main(string[] args)
        {
            if (args.Length < 1)
            {
                Console.WriteLine("Usage: WDTAnalysisExample <path_to_wdt_file> [output_directory]");
                return;
            }

            string wdtFilePath = args[0];
            string outputDirectory = args.Length > 1 ? args[1] : Path.GetDirectoryName(wdtFilePath);
            
            // Ensure output directory exists
            if (!Directory.Exists(outputDirectory))
            {
                Directory.CreateDirectory(outputDirectory);
            }

            try
            {
                // Step 1: Load the WDT file
                Console.WriteLine($"Loading WDT file: {wdtFilePath}");
                byte[] fileData = File.ReadAllBytes(wdtFilePath);
                
                // Create WDTFile object which parses the file
                var wdtFile = new WDTFile(fileData, Path.GetFileName(wdtFilePath));
                Console.WriteLine($"WDT file loaded successfully. Version: {wdtFile.Version}");
                
                // Step 2: Extract and display information from the WDT file
                DisplayWDTInfo(wdtFile);
                
                // Step 3: Serialize to JSON
                string jsonOutputPath = Path.Combine(outputDirectory, Path.GetFileNameWithoutExtension(wdtFilePath) + ".json");
                Console.WriteLine($"Serializing WDT to JSON: {jsonOutputPath}");
                string json = JsonSerializer.SerializeWDT(wdtFile);
                File.WriteAllText(jsonOutputPath, json);
                Console.WriteLine("JSON serialization completed successfully");

                // Step 4: If this is an Alpha WDT, display additional information
                if (wdtFile.Version == WDTVersion.Alpha)
                {
                    // Output model and object names
                    string mdnmOutputPath = Path.Combine(outputDirectory, Path.GetFileNameWithoutExtension(wdtFilePath) + "_models.txt");
                    string monmOutputPath = Path.Combine(outputDirectory, Path.GetFileNameWithoutExtension(wdtFilePath) + "_objects.txt");
                    
                    File.WriteAllLines(mdnmOutputPath, wdtFile.ModelNames);
                    File.WriteAllLines(monmOutputPath, wdtFile.WorldObjectNames);
                    
                    Console.WriteLine($"Model names written to: {mdnmOutputPath}");
                    Console.WriteLine($"Object names written to: {monmOutputPath}");
                }
                
                Console.WriteLine("Analysis completed successfully");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error analyzing WDT file: {ex.Message}");
                Console.WriteLine($"Stack trace: {ex.StackTrace}");
            }
        }
        
        /// <summary>
        /// Displays information about the WDT file.
        /// </summary>
        /// <param name="wdtFile">The WDT file to display information about.</param>
        private static void DisplayWDTInfo(WDTFile wdtFile)
        {
            Console.WriteLine("\n=== WDT File Information ===");
            Console.WriteLine($"File Name: {wdtFile.FileName}");
            Console.WriteLine($"Version: {wdtFile.Version}");
            
            // Count total tiles
            int totalTiles = 0;
            for (int y = 0; y < 64; y++)
            {
                for (int x = 0; x < 64; x++)
                {
                    if (wdtFile.MapTiles[x, y])
                        totalTiles++;
                }
            }
            Console.WriteLine($"Total Map Tiles: {totalTiles}");
            
            if (wdtFile.Version == WDTVersion.Alpha)
            {
                Console.WriteLine($"\nModel Names (MDNM): {wdtFile.ModelNames.Count}");
                Console.WriteLine($"World Object Names (MONM): {wdtFile.WorldObjectNames.Count}");
                Console.WriteLine($"ADT Offsets: {wdtFile.AdtOffsets.Count}");
                
                // Display first few entries of each type
                if (wdtFile.ModelNames.Count > 0)
                {
                    Console.WriteLine("\nFirst 5 Model Names:");
                    for (int i = 0; i < Math.Min(5, wdtFile.ModelNames.Count); i++)
                    {
                        Console.WriteLine($"  - {wdtFile.ModelNames[i]}");
                    }
                }
                
                if (wdtFile.WorldObjectNames.Count > 0)
                {
                    Console.WriteLine("\nFirst 5 World Object Names:");
                    for (int i = 0; i < Math.Min(5, wdtFile.WorldObjectNames.Count); i++)
                    {
                        Console.WriteLine($"  - {wdtFile.WorldObjectNames[i]}");
                    }
                }
                
                if (wdtFile.AdtOffsets.Count > 0)
                {
                    Console.WriteLine("\nFirst 5 ADT Offsets:");
                    int count = 0;
                    foreach (var offset in wdtFile.AdtOffsets)
                    {
                        if (count >= 5) break;
                        Console.WriteLine($"  - Tile ({offset.Key.x}, {offset.Key.y}): Offset {offset.Value}");
                        count++;
                    }
                }
            }
            
            Console.WriteLine("===========================\n");
        }
    }
}