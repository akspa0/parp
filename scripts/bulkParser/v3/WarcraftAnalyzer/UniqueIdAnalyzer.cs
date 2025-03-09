using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using WarcraftAnalyzer.Files.ADT;

namespace WarcraftAnalyzer.Examples
{
    /// <summary>
    /// Example class demonstrating how to port the UniqueIdAnalysis functionality from ADTAnalysis_old
    /// to use the WarcraftAnalyzer library.
    /// </summary>
    public class UniqueIdAnalyzer
    {
        /// <summary>
        /// Dictionary mapping ADT file paths to the unique IDs found in them.
        /// </summary>
        private Dictionary<string, HashSet<int>> _fileToUniqueIds = new Dictionary<string, HashSet<int>>();
        
        /// <summary>
        /// Dictionary mapping unique IDs to the ADT files they appear in.
        /// </summary>
        private Dictionary<int, List<string>> _uniqueIdToFiles = new Dictionary<int, List<string>>();
        
        /// <summary>
        /// Analyzes a directory of ADT files to extract and analyze unique IDs.
        /// </summary>
        /// <param name="directoryPath">The directory containing ADT files to analyze.</param>
        /// <param name="recursive">Whether to search subdirectories recursively.</param>
        public void AnalyzeDirectory(string directoryPath, bool recursive = false)
        {
            // Find all ADT files in the directory
            var searchOption = recursive ? SearchOption.AllDirectories : SearchOption.TopDirectoryOnly;
            var adtFiles = Directory.GetFiles(directoryPath, "*.adt", searchOption);
            
            Console.WriteLine($"Found {adtFiles.Length} ADT files in {directoryPath}");
            
            // Process each ADT file
            foreach (var adtFile in adtFiles)
            {
                try
                {
                    AnalyzeFile(adtFile);
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Error analyzing {adtFile}: {ex.Message}");
                }
            }
            
            // Print summary
            Console.WriteLine($"\nAnalysis complete. Found {_uniqueIdToFiles.Count} unique IDs across {_fileToUniqueIds.Count} files.");
        }
        
        /// <summary>
        /// Analyzes a single ADT file to extract unique IDs.
        /// </summary>
        /// <param name="filePath">The path to the ADT file to analyze.</param>
        public void AnalyzeFile(string filePath)
        {
            Console.WriteLine($"Analyzing {Path.GetFileName(filePath)}...");
            
            try
            {
                // Load the ADT file using WarcraftAnalyzer
                byte[] fileData = File.ReadAllBytes(filePath);
                var adtFile = new ADTFile(fileData, Path.GetFileName(filePath));
                
                // Extract unique IDs
                var uniqueIds = adtFile.UniqueIds;
                
                // Skip if no unique IDs found
                if (uniqueIds.Count == 0)
                {
                    Console.WriteLine($"  No unique IDs found in {Path.GetFileName(filePath)}");
                    return;
                }
                
                // Store the unique IDs for this file
                _fileToUniqueIds[filePath] = new HashSet<int>(uniqueIds);
                
                // Update the mapping of unique IDs to files
                foreach (var uniqueId in uniqueIds)
                {
                    if (!_uniqueIdToFiles.TryGetValue(uniqueId, out var files))
                    {
                        files = new List<string>();
                        _uniqueIdToFiles[uniqueId] = files;
                    }
                    
                    files.Add(filePath);
                }
                
                Console.WriteLine($"  Found {uniqueIds.Count} unique IDs in {Path.GetFileName(filePath)}");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"  Error: {ex.Message}");
                throw;
            }
        }
        
        /// <summary>
        /// Finds duplicate unique IDs (IDs that appear in multiple files).
        /// </summary>
        /// <returns>A dictionary mapping unique IDs to the files they appear in, for IDs that appear in multiple files.</returns>
        public Dictionary<int, List<string>> FindDuplicateUniqueIds()
        {
            var duplicates = _uniqueIdToFiles
                .Where(kvp => kvp.Value.Count > 1)
                .ToDictionary(kvp => kvp.Key, kvp => kvp.Value);
            
            return duplicates;
        }
        
        /// <summary>
        /// Exports the analysis results to a CSV file.
        /// </summary>
        /// <param name="outputPath">The path to write the CSV file to.</param>
        public void ExportToCsv(string outputPath)
        {
            using (var writer = new StreamWriter(outputPath))
            {
                // Write header
                writer.WriteLine("UniqueID,FileCount,Files");
                
                // Write data
                foreach (var kvp in _uniqueIdToFiles.OrderBy(kvp => kvp.Key))
                {
                    var uniqueId = kvp.Key;
                    var files = kvp.Value;
                    var fileNames = string.Join(";", files.Select(Path.GetFileName));
                    
                    writer.WriteLine($"{uniqueId},{files.Count},\"{fileNames}\"");
                }
            }
            
            Console.WriteLine($"Exported analysis results to {outputPath}");
        }
        
        /// <summary>
        /// Main entry point for the UniqueIdAnalyzer example.
        /// </summary>
        /// <param name="args">Command-line arguments.</param>
        public static void Main(string[] args)
        {
            if (args.Length < 1)
            {
                Console.WriteLine("Usage: UniqueIdAnalyzer <directory_path> [output_csv_path]");
                return;
            }
            
            string directoryPath = args[0];
            string outputPath = args.Length > 1 ? args[1] : Path.Combine(directoryPath, "unique_ids.csv");
            
            var analyzer = new UniqueIdAnalyzer();
            
            // Analyze the directory
            analyzer.AnalyzeDirectory(directoryPath, true);
            
            // Find and print duplicate unique IDs
            var duplicates = analyzer.FindDuplicateUniqueIds();
            Console.WriteLine($"\nFound {duplicates.Count} duplicate unique IDs:");
            foreach (var kvp in duplicates.OrderByDescending(kvp => kvp.Value.Count).Take(10))
            {
                var uniqueId = kvp.Key;
                var files = kvp.Value;
                Console.WriteLine($"  UniqueID {uniqueId} appears in {files.Count} files");
            }
            
            // Export results to CSV
            analyzer.ExportToCsv(outputPath);
        }
    }
}