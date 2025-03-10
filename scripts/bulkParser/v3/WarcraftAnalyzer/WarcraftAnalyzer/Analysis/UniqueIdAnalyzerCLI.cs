using System;
using System.Collections.Generic;
using System.IO;
using System.Threading.Tasks;
using WarcraftAnalyzer.Files.ADT;

namespace WarcraftAnalyzer.Analysis
{
    /// <summary>
    /// Command-line interface for the UniqueIdAnalyzer.
    /// </summary>
    public static class UniqueIdAnalyzerCLI
    {
        /// <summary>
        /// Runs the unique ID analyzer on a directory of ADT files.
        /// </summary>
        /// <param name="inputDirectory">The directory containing ADT files to analyze.</param>
        /// <param name="outputDirectory">The directory to write analysis results to.</param>
        /// <param name="clusterThreshold">The minimum number of IDs to form a cluster.</param>
        /// <param name="gapThreshold">The maximum gap between IDs to be considered part of the same cluster.</param>
        /// <param name="recursive">Whether to search subdirectories.</param>
        /// <param name="generateComprehensiveReport">Whether to generate a comprehensive report with all assets.</param>
        /// <returns>A task representing the asynchronous operation.</returns>
        public static async Task RunAsync(
            string inputDirectory,
            string outputDirectory,
            int clusterThreshold = 10,
            int gapThreshold = 1000,
            bool recursive = false,
            bool generateComprehensiveReport = true)
        {
            Console.WriteLine($"Starting unique ID analysis on {inputDirectory}");
            Console.WriteLine($"Output will be written to {outputDirectory}");
            Console.WriteLine($"Cluster threshold: {clusterThreshold}");
            Console.WriteLine($"Gap threshold: {gapThreshold}");
            Console.WriteLine($"Recursive: {recursive}");
            Console.WriteLine($"Comprehensive report: {generateComprehensiveReport}");
            Console.WriteLine();

            // Create the analyzer
            var analyzer = new UniqueIdAnalyzer(outputDirectory, clusterThreshold, gapThreshold);

            // Find ADT files in the directory
            var searchOption = recursive ? SearchOption.AllDirectories : SearchOption.TopDirectoryOnly;
            var adtFiles = Directory.GetFiles(inputDirectory, "*.adt", searchOption);

            Console.WriteLine($"Found {adtFiles.Length} ADT files");
            Console.WriteLine();

            // Group ADT files by map
            var adtFilesByMap = new Dictionary<string, List<string>>();
            foreach (var file in adtFiles)
            {
                var fileName = Path.GetFileNameWithoutExtension(file);
                var parts = fileName.Split('_');
                if (parts.Length >= 3)
                {
                    var mapName = parts[0];
                    if (!adtFilesByMap.TryGetValue(mapName, out var files))
                    {
                        files = new List<string>();
                        adtFilesByMap[mapName] = files;
                    }
                    files.Add(file);
                }
                else
                {
                    // If the file name doesn't follow the expected pattern, use "Unknown" as the map name
                    if (!adtFilesByMap.TryGetValue("Unknown", out var files))
                    {
                        files = new List<string>();
                        adtFilesByMap["Unknown"] = files;
                    }
                    files.Add(file);
                }
            }

            Console.WriteLine($"Found {adtFilesByMap.Count} maps");
            foreach (var map in adtFilesByMap)
            {
                Console.WriteLine($"  {map.Key}: {map.Value.Count} files");
            }
            Console.WriteLine();

            // Process each ADT file
            int successCount = 0;
            int errorCount = 0;
            foreach (var map in adtFilesByMap)
            {
                Console.WriteLine($"Processing map: {map.Key}");
                foreach (var file in map.Value)
                {
                    try
                    {
                        Console.WriteLine($"  Processing {Path.GetFileName(file)}");
                        var fileData = File.ReadAllBytes(file);
                        var adt = new ADTFile(fileData, Path.GetFileName(file));
                        analyzer.AddAdtFile(adt, map.Key);
                        successCount++;
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine($"  Error processing {file}: {ex.Message}");
                        errorCount++;
                    }
                }
            }

            Console.WriteLine();
            Console.WriteLine($"Successfully processed {successCount} files");
            Console.WriteLine($"Failed to process {errorCount} files");
            Console.WriteLine();

            // Run the analysis
            Console.WriteLine("Running analysis...");
            await analyzer.AnalyzeAsync(generateComprehensiveReport);

            Console.WriteLine();
            Console.WriteLine($"Analysis complete. Results written to {outputDirectory}");
        }
    }
}