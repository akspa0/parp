using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;

namespace WarcraftAnalyzer.Analysis
{
    /// <summary>
    /// Provides functionality to correlate PM4 and ADT files.
    /// </summary>
    public static class FileCorrelator
    {
        /// <summary>
        /// Correlates PM4 and ADT files in a directory.
        /// </summary>
        /// <param name="directory">The directory to search for files.</param>
        /// <param name="recursive">Whether to search subdirectories.</param>
        /// <returns>A dictionary mapping PM4 files to their corresponding ADT files.</returns>
        public static Dictionary<string, string> CorrelatePM4AndADT(string directory, bool recursive)
        {
            var correlations = new Dictionary<string, string>();
            var searchOption = recursive ? SearchOption.AllDirectories : SearchOption.TopDirectoryOnly;
            
            // Get all PM4 files
            var pm4Files = Directory.GetFiles(directory, "*.pm4", searchOption);
            
            // Get all ADT files (excluding split parts)
            var adtFiles = Directory.GetFiles(directory, "*.adt", searchOption)
                .Where(f => !Path.GetFileNameWithoutExtension(f).EndsWith("_obj") && 
                            !Path.GetFileNameWithoutExtension(f).EndsWith("_tex"))
                .ToArray();
            
            // Regular expression to extract coordinates from filenames
            var pm4Regex = new Regex(@"(\w+)_(\d+)_(\d+)\.pm4", RegexOptions.IgnoreCase);
            var adtRegex = new Regex(@"(\w+)_(\d+)_(\d+)\.adt", RegexOptions.IgnoreCase);
            
            // Process each PM4 file
            foreach (var pm4File in pm4Files)
            {
                var pm4Match = pm4Regex.Match(Path.GetFileName(pm4File));
                if (pm4Match.Success)
                {
                    var pm4BaseName = pm4Match.Groups[1].Value;
                    var pm4X = int.Parse(pm4Match.Groups[2].Value);
                    var pm4Y = int.Parse(pm4Match.Groups[3].Value);
                    
                    // Look for matching ADT file
                    foreach (var adtFile in adtFiles)
                    {
                        var adtMatch = adtRegex.Match(Path.GetFileName(adtFile));
                        if (adtMatch.Success)
                        {
                            var adtBaseName = adtMatch.Groups[1].Value;
                            var adtX = int.Parse(adtMatch.Groups[2].Value);
                            var adtY = int.Parse(adtMatch.Groups[3].Value);
                            
                            // Check if coordinates match
                            if (pm4BaseName.Equals(adtBaseName, StringComparison.OrdinalIgnoreCase) &&
                                pm4X == adtX && pm4Y == adtY)
                            {
                                correlations[pm4File] = adtFile;
                                break;
                            }
                            
                            // Check for off-by-one matches (some files might have different coordinate formats)
                            if (pm4BaseName.Equals(adtBaseName, StringComparison.OrdinalIgnoreCase) &&
                                (pm4X == adtX / 10 || pm4X * 10 == adtX) &&
                                (pm4Y == adtY / 10 || pm4Y * 10 == adtY))
                            {
                                correlations[pm4File] = adtFile;
                                break;
                            }
                        }
                    }
                }
            }
            
            return correlations;
        }
        
        /// <summary>
        /// Generates a correlation report in Markdown format.
        /// </summary>
        /// <param name="correlations">The dictionary of correlations.</param>
        /// <returns>A Markdown-formatted report.</returns>
        public static string GenerateCorrelationReport(Dictionary<string, string> correlations)
        {
            var sb = new StringBuilder();
            
            sb.AppendLine("# PM4 and ADT File Correlation Report");
            sb.AppendLine();
            sb.AppendLine("This report shows the correlation between PM4 and ADT files based on their filenames and coordinates.");
            sb.AppendLine();
            
            sb.AppendLine("## Matched Files");
            sb.AppendLine();
            sb.AppendLine("| PM4 File | ADT File |");
            sb.AppendLine("|----------|----------|");
            
            foreach (var correlation in correlations)
            {
                sb.AppendLine($"| {Path.GetFileName(correlation.Key)} | {Path.GetFileName(correlation.Value)} |");
            }
            
            sb.AppendLine();
            sb.AppendLine("## Statistics");
            sb.AppendLine();
            sb.AppendLine($"- Total PM4 files: {correlations.Count}");
            sb.AppendLine($"- Total matched ADT files: {correlations.Values.Distinct().Count()}");
            sb.AppendLine($"- Match ratio: {(correlations.Count > 0 ? (double)correlations.Values.Distinct().Count() / correlations.Count * 100 : 0):F2}%");
            
            return sb.ToString();
        }
    }
}