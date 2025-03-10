using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;

namespace WarcraftAnalyzer.Analysis
{
    /// <summary>
    /// Provides functionality to correlate different file types based on naming patterns.
    /// </summary>
    public static class FileCorrelator
    {
        /// <summary>
        /// Finds correlations between PM4 files and ADT files.
        /// </summary>
        /// <param name="directory">The directory to search for files.</param>
        /// <param name="recursive">Whether to search recursively.</param>
        /// <returns>A dictionary mapping PM4 files to their corresponding ADT files.</returns>
        public static Dictionary<string, List<string>> CorrelatePM4AndADT(string directory, bool recursive = false)
        {
            var result = new Dictionary<string, List<string>>();
            var searchOption = recursive ? SearchOption.AllDirectories : SearchOption.TopDirectoryOnly;
            
            // Get all PM4 and ADT files
            var pm4Files = Directory.GetFiles(directory, "*.pm4", searchOption);
            var adtFiles = Directory.GetFiles(directory, "*.adt", searchOption);
            
            // Regular expressions for extracting coordinates
            var pm4Regex = new Regex(@"(\w+)_(\d+)_(\d+)\.pm4$", RegexOptions.IgnoreCase);
            var adtRegex = new Regex(@"(\w+)_(\d+)_(\d+)(|_obj\d*|_tex\d*)\.adt$", RegexOptions.IgnoreCase);
            
            // Process each PM4 file
            foreach (var pm4File in pm4Files)
            {
                var pm4Match = pm4Regex.Match(pm4File);
                if (pm4Match.Success)
                {
                    var baseName = pm4Match.Groups[1].Value;
                    var pm4X = pm4Match.Groups[2].Value;
                    var pm4Y = pm4Match.Groups[3].Value;
                    
                    // Convert PM4 coordinates to ADT coordinates (PM4 uses 00_00 format, ADT uses 0_0 format)
                    int pm4XValue = int.Parse(pm4X);
                    int pm4YValue = int.Parse(pm4Y);
                    
                    // Find matching ADT files
                    var matchingAdtFiles = new List<string>();
                    foreach (var adtFile in adtFiles)
                    {
                        var adtMatch = adtRegex.Match(adtFile);
                        if (adtMatch.Success)
                        {
                            var adtBaseName = adtMatch.Groups[1].Value;
                            var adtX = adtMatch.Groups[2].Value;
                            var adtY = adtMatch.Groups[3].Value;
                            
                            // Check if base name and coordinates match
                            if (string.Equals(baseName, adtBaseName, StringComparison.OrdinalIgnoreCase) &&
                                pm4XValue.ToString() == adtX && pm4YValue.ToString() == adtY)
                            {
                                matchingAdtFiles.Add(adtFile);
                            }
                        }
                    }
                    
                    if (matchingAdtFiles.Count > 0)
                    {
                        result[pm4File] = matchingAdtFiles;
                    }
                }
            }
            
            return result;
        }
        
        /// <summary>
        /// Generates a report of correlations between PM4 and ADT files.
        /// </summary>
        /// <param name="correlations">The correlations to report.</param>
        /// <returns>A string containing the report.</returns>
        public static string GenerateCorrelationReport(Dictionary<string, List<string>> correlations)
        {
            var report = new System.Text.StringBuilder();
            report.AppendLine("# PM4 and ADT File Correlation Report");
            report.AppendLine();
            
            if (correlations.Count == 0)
            {
                report.AppendLine("No correlations found.");
                return report.ToString();
            }
            
            report.AppendLine($"Found {correlations.Count} PM4 files with matching ADT files.");
            report.AppendLine();
            
            foreach (var correlation in correlations)
            {
                var pm4File = Path.GetFileName(correlation.Key);
                var adtFiles = correlation.Value.Select(Path.GetFileName).ToList();
                
                report.AppendLine($"## {pm4File}");
                report.AppendLine();
                report.AppendLine("Matching ADT files:");
                
                foreach (var adtFile in adtFiles)
                {
                    report.AppendLine($"- {adtFile}");
                }
                
                report.AppendLine();
            }
            
            return report.ToString();
        }
    }
}