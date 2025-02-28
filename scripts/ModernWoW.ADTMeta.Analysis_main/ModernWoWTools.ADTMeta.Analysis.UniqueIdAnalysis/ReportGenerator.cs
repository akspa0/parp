using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using OfficeOpenXml;
using OfficeOpenXml.Style;

namespace ModernWoWTools.ADTMeta.Analysis.UniqueIdAnalysis
{
    /// <summary>
    /// Utility class for generating reports from the analysis results
    /// </summary>
    public static class ReportGenerator
    {
        /// <summary>
        /// Generates an Excel report of the analysis.
        /// </summary>
        public static async Task GenerateExcelReportAsync(
            List<AdtInfo> adtFiles,
            Dictionary<string, List<UniqueIdCluster>> mapClusters,
            List<UniqueIdCluster> globalClusters,
            int clusterGapThreshold,
            string outputDirectory)
        {
            Console.WriteLine("Generating Excel report...");
            
            var reportPath = Path.Combine(outputDirectory, "unique_id_analysis.xlsx");
            
            // Set the license context
            ExcelPackage.LicenseContext = LicenseContext.NonCommercial;
            
            using (var package = new ExcelPackage())
            {
                // Create global clusters worksheet
                var globalSheet = CreateGlobalClustersSheet(package, globalClusters, adtFiles);
                
                // Create per-map clusters worksheet
                var mapClustersSheet = CreateMapClustersSheet(package, mapClusters);
                
                // Create ADT data worksheet
                var adtSheet = CreateAdtDataSheet(package, adtFiles, clusterGapThreshold);
                
                // Create ID distribution worksheet (histogram)
                var histogramSheet = CreateHistogramSheet(package, adtFiles);
                
                // Create asset distribution worksheet
                var assetSheet = CreateAssetDistributionSheet(package, globalClusters);
                
                // Create detailed assets worksheet
                var detailedAssetSheet = CreateDetailedAssetsSheet(package, globalClusters);
                
                // Save the Excel file
                await package.SaveAsAsync(new FileInfo(reportPath));
                
                Console.WriteLine($"Excel report written to {reportPath}");
            }
        }

        /// <summary>
        /// Creates the global clusters worksheet.
        /// </summary>
        private static ExcelWorksheet CreateGlobalClustersSheet(
            ExcelPackage package, 
            List<UniqueIdCluster> globalClusters,
            List<AdtInfo> adtFiles)
        {
            var globalSheet = package.Workbook.Worksheets.Add("Global Clusters");
            int row = 1;
            
            // Header
            globalSheet.Cells[row, 1].Value = "Cluster Start";
            globalSheet.Cells[row, 2].Value = "Cluster End";
            globalSheet.Cells[row, 3].Value = "ID Count";
            globalSheet.Cells[row, 4].Value = "ID Span";
            globalSheet.Cells[row, 5].Value = "Density";
            globalSheet.Cells[row, 6].Value = "ADT Count";
            globalSheet.Cells[row, 7].Value = "Asset Count";
            globalSheet.Cells[row, 8].Value = "Maps";
            globalSheet.Cells[row, 1, row, 8].Style.Font.Bold = true;
            globalSheet.Cells[row, 1, row, 8].Style.Fill.PatternType = ExcelFillStyle.Solid;
            globalSheet.Cells[row, 1, row, 8].Style.Fill.BackgroundColor.SetColor(System.Drawing.Color.LightGray);
            
            row++;
            
            // Global clusters data
            foreach (var cluster in globalClusters.OrderBy(c => c.MinId))
            {
                globalSheet.Cells[row, 1].Value = cluster.MinId;
                globalSheet.Cells[row, 2].Value = cluster.MaxId;
                globalSheet.Cells[row, 3].Value = cluster.Count;
                globalSheet.Cells[row, 4].Value = cluster.MaxId - cluster.MinId + 1;
                globalSheet.Cells[row, 5].Value = cluster.Density;
                globalSheet.Cells[row, 5].Style.Numberformat.Format = "0.00";
                globalSheet.Cells[row, 6].Value = cluster.AdtFiles.Count;
                globalSheet.Cells[row, 7].Value = cluster.Assets.Count;
                
                // Maps present in this cluster
                var maps = adtFiles
                    .Where(a => cluster.AdtFiles.Contains(a.FileName))
                    .Select(a => a.MapName)
                    .Distinct()
                    .OrderBy(m => m);
                
                globalSheet.Cells[row, 8].Value = string.Join(", ", maps);
                
                row++;
            }
            
            globalSheet.Cells.AutoFitColumns();
            return globalSheet;
        }

        /// <summary>
        /// Creates the map clusters worksheet.
        /// </summary>
        private static ExcelWorksheet CreateMapClustersSheet(
            ExcelPackage package,
            Dictionary<string, List<UniqueIdCluster>> mapClusters)
        {
            var mapClustersSheet = package.Workbook.Worksheets.Add("Map Clusters");
            int row = 1;
            
            // Header
            mapClustersSheet.Cells[row, 1].Value = "Map";
            mapClustersSheet.Cells[row, 2].Value = "Cluster Start";
            mapClustersSheet.Cells[row, 3].Value = "Cluster End";
            mapClustersSheet.Cells[row, 4].Value = "ID Count";
            mapClustersSheet.Cells[row, 5].Value = "ID Span";
            mapClustersSheet.Cells[row, 6].Value = "Density";
            mapClustersSheet.Cells[row, 7].Value = "ADT Count";
            mapClustersSheet.Cells[row, 8].Value = "Asset Count";
            mapClustersSheet.Cells[row, 1, row, 8].Style.Font.Bold = true;
            mapClustersSheet.Cells[row, 1, row, 8].Style.Fill.PatternType = ExcelFillStyle.Solid;
            mapClustersSheet.Cells[row, 1, row, 8].Style.Fill.BackgroundColor.SetColor(System.Drawing.Color.LightGray);
            
            row++;
            
            // Map clusters data
            foreach (var mapEntry in mapClusters.OrderBy(m => m.Key))
            {
                var mapName = mapEntry.Key;
                var clusters = mapEntry.Value;
                
                foreach (var cluster in clusters.OrderBy(c => c.MinId))
                {
                    mapClustersSheet.Cells[row, 1].Value = mapName;
                    mapClustersSheet.Cells[row, 2].Value = cluster.MinId;
                    mapClustersSheet.Cells[row, 3].Value = cluster.MaxId;
                    mapClustersSheet.Cells[row, 4].Value = cluster.Count;
                    mapClustersSheet.Cells[row, 5].Value = cluster.MaxId - cluster.MinId + 1;
                    mapClustersSheet.Cells[row, 6].Value = cluster.Density;
                    mapClustersSheet.Cells[row, 6].Style.Numberformat.Format = "0.00";
                    mapClustersSheet.Cells[row, 7].Value = cluster.AdtFiles.Count;
                    mapClustersSheet.Cells[row, 8].Value = cluster.Assets.Count;
                    
                    row++;
                }
            }
            
            mapClustersSheet.Cells.AutoFitColumns();
            return mapClustersSheet;
        }

        /// <summary>
        /// Creates the ADT data worksheet.
        /// </summary>
        private static ExcelWorksheet CreateAdtDataSheet(
            ExcelPackage package,
            List<AdtInfo> adtFiles,
            int gapThreshold)
        {
            var adtSheet = package.Workbook.Worksheets.Add("ADT Data");
            int row = 1;
            
            // Header
            adtSheet.Cells[row, 1].Value = "Map";
            adtSheet.Cells[row, 2].Value = "ADT File";
            adtSheet.Cells[row, 3].Value = "ID Count";
            adtSheet.Cells[row, 4].Value = "Asset Count";
            adtSheet.Cells[row, 5].Value = "Min ID";
            adtSheet.Cells[row, 6].Value = "Max ID";
            adtSheet.Cells[row, 7].Value = "ID Span";
            adtSheet.Cells[row, 8].Value = "Model Count";
            adtSheet.Cells[row, 9].Value = "WMO Count";
            adtSheet.Cells[row, 10].Value = "Major Ranges";
            adtSheet.Cells[row, 1, row, 10].Style.Font.Bold = true;
            adtSheet.Cells[row, 1, row, 10].Style.Fill.PatternType = ExcelFillStyle.Solid;
            adtSheet.Cells[row, 1, row, 10].Style.Fill.BackgroundColor.SetColor(System.Drawing.Color.LightGray);
            
            row++;
            
            // ADT data
            foreach (var mapGroup in adtFiles.GroupBy(a => a.MapName).OrderBy(g => g.Key))
            {
                foreach (var adt in mapGroup.OrderBy(a => a.FileName))
                {
                    adtSheet.Cells[row, 1].Value = adt.MapName;
                    adtSheet.Cells[row, 2].Value = adt.FileName;
                    adtSheet.Cells[row, 3].Value = adt.UniqueIds.Count;
                    
                    // Count all assets
                    var allAssets = adt.AssetsByUniqueId.Values.SelectMany(a => a).ToList();
                    var modelCount = allAssets.Count(a => a.Type == "Model");
                    var wmoCount = allAssets.Count(a => a.Type == "WMO");
                    
                    adtSheet.Cells[row, 4].Value = allAssets.Count;
                    
                    if (adt.UniqueIds.Count > 0)
                    {
                        var minId = adt.UniqueIds.Min();
                        var maxId = adt.UniqueIds.Max();
                        var ranges = ClusterAnalyzer.GetIdRanges(adt.UniqueIds, gapThreshold);
                        
                        adtSheet.Cells[row, 5].Value = minId;
                        adtSheet.Cells[row, 6].Value = maxId;
                        adtSheet.Cells[row, 7].Value = maxId - minId + 1;
                        adtSheet.Cells[row, 8].Value = modelCount;
                        adtSheet.Cells[row, 9].Value = wmoCount;
                        
                        var rangeDescriptions = ranges
                            .OrderBy(r => r.Item1)
                            .Select(r => $"{r.Item1}-{r.Item2} ({r.Item3} IDs)")
                            .ToList();
                        
                        adtSheet.Cells[row, 10].Value = string.Join(", ", rangeDescriptions);
                    }
                    
                    row++;
                }
            }
            
            adtSheet.Cells.AutoFitColumns();
            return adtSheet;
        }

        /// <summary>
        /// Creates the histogram worksheet.
        /// </summary>
        private static ExcelWorksheet CreateHistogramSheet(
            ExcelPackage package,
            List<AdtInfo> adtFiles)
        {
            var histogramSheet = package.Workbook.Worksheets.Add("ID Distribution");
            int row = 1;
            
            // Get all unique IDs
            var allIds = adtFiles
                .SelectMany(adt => adt.UniqueIds)
                .Distinct()
                .OrderBy(id => id)
                .ToList();
            
            if (allIds.Count > 0)
            {
                // Determine bin size and number of bins
                var minId = allIds.Min();
                var maxId = allIds.Max();
                var range = maxId - minId;
                
                // Aim for around 100-200 bins, but adjust based on the range
                var binSize = Math.Max(1, range / 150);
                var numBins = (int)Math.Ceiling((double)range / binSize) + 1;
                
                // Create histogram
                var histogram = new int[numBins];
                foreach (var id in allIds)
                {
                    var bin = (id - minId) / binSize;
                    histogram[bin]++;
                }
                
                // Header
                histogramSheet.Cells[row, 1].Value = "ID Range Start";
                histogramSheet.Cells[row, 2].Value = "ID Range End";
                histogramSheet.Cells[row, 3].Value = "Count";
                histogramSheet.Cells[row, 1, row, 3].Style.Font.Bold = true;
                histogramSheet.Cells[row, 1, row, 3].Style.Fill.PatternType = ExcelFillStyle.Solid;
                histogramSheet.Cells[row, 1, row, 3].Style.Fill.BackgroundColor.SetColor(System.Drawing.Color.LightGray);
                
                row++;
                
                // Histogram data
                for (int i = 0; i < numBins; i++)
                {
                    var startId = minId + (i * binSize);
                    var endId = Math.Min(maxId, startId + binSize - 1);
                    
                    histogramSheet.Cells[row, 1].Value = startId;
                    histogramSheet.Cells[row, 2].Value = endId;
                    histogramSheet.Cells[row, 3].Value = histogram[i];
                    
                    row++;
                }
                
                histogramSheet.Cells.AutoFitColumns();
            }
            
            return histogramSheet;
        }
        
        /// <summary>
        /// Creates a worksheet showing asset distribution across clusters.
        /// </summary>
        private static ExcelWorksheet CreateAssetDistributionSheet(
            ExcelPackage package,
            List<UniqueIdCluster> globalClusters)
        {
            var assetSheet = package.Workbook.Worksheets.Add("Asset Distribution");
            int row = 1;
            
            // Header
            assetSheet.Cells[row, 1].Value = "Cluster Range";
            assetSheet.Cells[row, 2].Value = "Asset Type";
            assetSheet.Cells[row, 3].Value = "Asset Count";
            assetSheet.Cells[row, 4].Value = "Top Assets";
            assetSheet.Cells[row, 1, row, 4].Style.Font.Bold = true;
            assetSheet.Cells[row, 1, row, 4].Style.Fill.PatternType = ExcelFillStyle.Solid;
            assetSheet.Cells[row, 1, row, 4].Style.Fill.BackgroundColor.SetColor(System.Drawing.Color.LightGray);
            
            row++;
            
            // Asset distribution data
            foreach (var cluster in globalClusters.OrderBy(c => c.MinId))
            {
                var clusterRange = $"{cluster.MinId} - {cluster.MaxId}";
                var assetsByType = cluster.Assets.GroupBy(a => a.Type);
                
                foreach (var typeGroup in assetsByType.OrderBy(g => g.Key))
                {
                    assetSheet.Cells[row, 1].Value = clusterRange;
                    assetSheet.Cells[row, 2].Value = typeGroup.Key;
                    assetSheet.Cells[row, 3].Value = typeGroup.Count();
                    
                    // Get the top 5 most used assets
                    var topAssets = typeGroup
                        .GroupBy(a => a.AssetPath)
                        .Select(g => new { Path = g.Key, Count = g.Count() })
                        .OrderByDescending(a => a.Count)
                        .Take(5)
                        .Select(a => $"{Path.GetFileName(a.Path)} ({a.Count})")
                        .ToList();
                    
                    assetSheet.Cells[row, 4].Value = string.Join(", ", topAssets);
                    
                    row++;
                }
                
                // Add a blank row between clusters
                row++;
            }
            
            assetSheet.Cells.AutoFitColumns();
            return assetSheet;
        }
        
        /// <summary>
        /// Creates a worksheet with detailed asset information.
        /// </summary>
        private static ExcelWorksheet CreateDetailedAssetsSheet(
            ExcelPackage package,
            List<UniqueIdCluster> globalClusters)
        {
            var detailSheet = package.Workbook.Worksheets.Add("Detailed Assets");
            int row = 1;
            
            // Header
            detailSheet.Cells[row, 1].Value = "Asset Path";
            detailSheet.Cells[row, 2].Value = "Asset Type";
            detailSheet.Cells[row, 3].Value = "Usage Count";
            detailSheet.Cells[row, 4].Value = "First Seen ID";
            detailSheet.Cells[row, 5].Value = "Earliest Cluster";
            detailSheet.Cells[row, 6].Value = "Maps";
            detailSheet.Cells[row, 1, row, 6].Style.Font.Bold = true;
            detailSheet.Cells[row, 1, row, 6].Style.Fill.PatternType = ExcelFillStyle.Solid;
            detailSheet.Cells[row, 1, row, 6].Style.Fill.BackgroundColor.SetColor(System.Drawing.Color.LightGray);
            
            row++;
            
            // Collect all unique assets across all clusters
            var allAssets = globalClusters
                .SelectMany(c => c.Assets)
                .GroupBy(a => a.AssetPath)
                .Select(g => new {
                    Path = g.Key,
                    Type = g.First().Type,
                    Count = g.Count(),
                    FirstSeenId = g.Min(a => a.UniqueId),
                    Maps = g.Select(a => a.MapName).Distinct().OrderBy(m => m).ToList()
                })
                .OrderBy(a => a.Type)
                .ThenBy(a => a.Path);
                
            // Find cluster for each first seen ID
            foreach (var asset in allAssets)
            {
                detailSheet.Cells[row, 1].Value = asset.Path;
                detailSheet.Cells[row, 2].Value = asset.Type;
                detailSheet.Cells[row, 3].Value = asset.Count;
                detailSheet.Cells[row, 4].Value = asset.FirstSeenId;
                
                // Find earliest cluster containing this ID
                var earliestCluster = globalClusters
                    .Where(c => c.MinId <= asset.FirstSeenId && c.MaxId >= asset.FirstSeenId)
                    .OrderBy(c => c.MinId)
                    .FirstOrDefault();
                
                if (earliestCluster != null)
                {
                    detailSheet.Cells[row, 5].Value = $"{earliestCluster.MinId} - {earliestCluster.MaxId}";
                }
                
                detailSheet.Cells[row, 6].Value = string.Join(", ", asset.Maps);
                
                row++;
            }
            
            detailSheet.Cells.AutoFitColumns();
            return detailSheet;
        }
    }
}