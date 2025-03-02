using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using OfficeOpenXml;
using OfficeOpenXml.Style;
using OfficeOpenXml.Drawing.Chart;
using System.Drawing;

namespace ModernWoWTools.ADTMeta.Analysis.UniqueIdAnalysis
{
    /// <summary>
    /// Extension methods for enhanced timeline analysis features
    /// </summary>
    public static class TimelineAnalysisExtensions
    {
        /// <summary>
        /// Generates enhanced timeline analysis reports
        /// </summary>
        public static async Task GenerateTimelineAnalysisReportAsync(
            List<AdtInfo> adtFiles,
            string outputDirectory)
        {
            Console.WriteLine("Generating enhanced timeline analysis report...");
            
            var timelinePath = Path.Combine(outputDirectory, "development_timeline_enhanced.xlsx");
            
            // Set license context for EPPlus
            ExcelPackage.LicenseContext = LicenseContext.NonCommercial;
            
            using (var package = new ExcelPackage())
            {
                // Create the cluster timeline visualization
                CreateClusterTimelineSheet(package, adtFiles);
                
                // Save the Excel file
                await package.SaveAsAsync(new FileInfo(timelinePath));
                
                Console.WriteLine($"Enhanced timeline analysis written to {timelinePath}");
            }
        }

        /// <summary>
        /// Creates a visual timeline sheet showing how clusters span across maps
        /// </summary>
        private static ExcelWorksheet CreateClusterTimelineSheet(
            ExcelPackage package,
            List<AdtInfo> adtFiles)
        {
            var timelineSheet = package.Workbook.Worksheets.Add("Cluster Timeline");
            int row = 1;
            
            // Title and explanation
            timelineSheet.Cells[row, 1].Value = "ID Cluster Timeline Visualization";
            timelineSheet.Cells[row, 1].Style.Font.Size = 14;
            timelineSheet.Cells[row, 1].Style.Font.Bold = true;
            timelineSheet.Cells[row, 1, row, 3].Merge = true;
            row += 2;
            
            timelineSheet.Cells[row, 1].Value = "This visualization shows uniqueID clusters across different maps, helping to visualize temporal development patterns.";
            timelineSheet.Cells[row, 1, row, 10].Merge = true;
            row += 2;
            
            // Get all global IDs
            var allIds = adtFiles.SelectMany(a => a.UniqueIds).Distinct().OrderBy(id => id).ToList();
            if (allIds.Count == 0)
                return timelineSheet;
                
            // Get global min/max ID
            int minId = allIds.First();
            int maxId = allIds.Last();
            
            // Create timeline segments (try to keep under 50 segments)
            int segmentCount = Math.Min(50, (maxId - minId) / 1000 + 1);
            int segmentSize = (maxId - minId) / segmentCount + 1;
            
            // Create timeline labels
            List<int> timelineLabels = new List<int>();
            for (int i = 0; i <= segmentCount; i++)
            {
                timelineLabels.Add(minId + (i * segmentSize));
            }
            
            // Get all maps
            var allMaps = adtFiles.Select(a => a.MapName).Distinct().OrderBy(m => m).ToList();
            
            // Table header - timeline labels
            timelineSheet.Cells[row, 1].Value = "Map";
            for (int i = 0; i < timelineLabels.Count; i++)
            {
                timelineSheet.Cells[row, i + 2].Value = timelineLabels[i];
            }
            timelineSheet.Cells[row, 1, row, timelineLabels.Count + 1].Style.Font.Bold = true;
            timelineSheet.Cells[row, 1, row, timelineLabels.Count + 1].Style.Fill.PatternType = ExcelFillStyle.Solid;
            timelineSheet.Cells[row, 1, row, timelineLabels.Count + 1].Style.Fill.BackgroundColor.SetColor(Color.LightGray);
            row++;
            
            // For each map, create a visual timeline
            foreach (var mapName in allMaps)
            {
                var mapAdts = adtFiles.Where(a => a.MapName == mapName).ToList();
                var mapIds = mapAdts.SelectMany(a => a.UniqueIds).Distinct().OrderBy(id => id).ToList();
                
                if (mapIds.Count == 0)
                    continue;
                
                // Create the row for this map
                timelineSheet.Cells[row, 1].Value = mapName;
                timelineSheet.Cells[row, 1].Style.Font.Bold = true;
                
                // Calculate presence in each segment
                for (int i = 0; i < segmentCount; i++)
                {
                    int segmentStart = minId + (i * segmentSize);
                    int segmentEnd = segmentStart + segmentSize - 1;
                    
                    // Count IDs in this segment
                    int idsInSegment = mapIds.Count(id => id >= segmentStart && id <= segmentEnd);
                    double segmentDensity = (double)idsInSegment / segmentSize;
                    
                    // Decide if this segment has activity
                    if (idsInSegment > 0)
                    {
                        timelineSheet.Cells[row, i + 2].Value = idsInSegment;
                        
                        // Color based on density
                        byte colorIntensity = (byte)(255 - Math.Min(255, (segmentDensity * 5000)));
                        timelineSheet.Cells[row, i + 2].Style.Fill.PatternType = ExcelFillStyle.Solid;
                        timelineSheet.Cells[row, i + 2].Style.Fill.BackgroundColor.SetColor(Color.FromArgb(colorIntensity, colorIntensity, 255));
                    }
                }
                
                row++;
            }
            
            // Add legend
            row += 2;
            timelineSheet.Cells[row, 1].Value = "Legend:";
            timelineSheet.Cells[row, 1].Style.Font.Bold = true;
            row++;
            
            timelineSheet.Cells[row, 1].Value = "Numbers:";
            timelineSheet.Cells[row, 2].Value = "Count of unique IDs in that segment";
            row++;
            
            timelineSheet.Cells[row, 1].Value = "Color:";
            timelineSheet.Cells[row, 2].Value = "Darker blue indicates higher ID density in that segment";
            row++;
            
            timelineSheet.Cells.AutoFitColumns();
            return timelineSheet;
        }
    }
}