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
    /// Base class for report generators
    /// </summary>
    public abstract class BaseReportGenerator
    {
        protected readonly List<AdtInfo> _adtFiles;
        protected readonly string _outputDirectory;
        protected readonly bool _comprehensive;

        public BaseReportGenerator(
            List<AdtInfo> adtFiles,
            string outputDirectory,
            bool comprehensive = true)
        {
            _adtFiles = adtFiles;
            _outputDirectory = outputDirectory;
            _comprehensive = comprehensive;
        }

        /// <summary>
        /// Helper method to find global clusters across all maps.
        /// </summary>
        protected List<UniqueIdCluster> FindGlobalClusters(int threshold = 30, int gapThreshold = 2000)
        {
            // Collect all unique IDs
            var allIds = _adtFiles
                .SelectMany(adt => adt.UniqueIds)
                .Distinct()
                .OrderBy(id => id)
                .ToList();
            
            // Find clusters with a higher threshold for global analysis
            return ClusterAnalyzer.FindClusters(allIds, threshold, gapThreshold);
        }
    }

    /// <summary>
    /// Generates the main Excel report with cluster information
    /// </summary>
    public class ExcelReportGenerator : BaseReportGenerator
    {
        private readonly Dictionary<string, List<UniqueIdCluster>> _mapClusters;
        private readonly List<UniqueIdCluster> _globalClusters;
        private readonly int _clusterGapThreshold;

        public ExcelReportGenerator(
            List<AdtInfo> adtFiles,
            Dictionary<string, List<UniqueIdCluster>> mapClusters,
            List<UniqueIdCluster> globalClusters,
            int clusterGapThreshold,
            string outputDirectory,
            bool comprehensive = true)
            : base(adtFiles, outputDirectory, comprehensive)
        {
            _mapClusters = mapClusters;
            _globalClusters = globalClusters;
            _clusterGapThreshold = clusterGapThreshold;
        }

        /// <summary>
        /// Generates the Excel report.
        /// </summary>
        public async Task GenerateAsync()
        {
            Console.WriteLine("Generating Excel report...");
            
            var reportPath = Path.Combine(_outputDirectory, "unique_id_analysis.xlsx");
            
            // Set the license context
            ExcelPackage.LicenseContext = LicenseContext.NonCommercial;
            
            using (var package = new ExcelPackage())
            {
                // Create global clusters worksheet
                var globalSheet = CreateGlobalClustersSheet(package);
                
                // Create per-map clusters worksheet
                var mapClustersSheet = CreateMapClustersSheet(package);
                
                // Create ADT data worksheet
                var adtSheet = CreateAdtDataSheet(package);
                
                // Create ID distribution worksheet (histogram)
                var histogramSheet = CreateHistogramSheet(package);
                
                // Create asset distribution worksheet
                var assetSheet = CreateAssetDistributionSheet(package);
                
                // Create detailed assets worksheet
                var detailedAssetSheet = CreateDetailedAssetsSheet(package);
                
                // Create complete uniqueID to asset mapping worksheet (always included)
                var completeIdMappingSheet = CreateCompleteIdMappingSheet(package);
                
                // Add comprehensive analysis sheets if requested
                if (_comprehensive)
                {
                    // Create lowest ID worksheet
                    var lowestIdSheet = CreateLowestIdSheet(package);
                    
                    // Create non-clustered IDs worksheet
                    var nonClusteredSheet = CreateNonClusteredIdsSheet(package);
                }
                
                // Save the Excel file
                await package.SaveAsAsync(new FileInfo(reportPath));
                
                Console.WriteLine($"Excel report written to {reportPath}");
            }
        }

        /// <summary>
        /// Creates the global clusters worksheet.
        /// </summary>
        private ExcelWorksheet CreateGlobalClustersSheet(ExcelPackage package)
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
            foreach (var cluster in _globalClusters.OrderBy(c => c.MinId))
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
                var maps = _adtFiles
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
        private ExcelWorksheet CreateMapClustersSheet(ExcelPackage package)
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
            foreach (var mapEntry in _mapClusters.OrderBy(m => m.Key))
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
        private ExcelWorksheet CreateAdtDataSheet(ExcelPackage package)
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
            foreach (var mapGroup in _adtFiles.GroupBy(a => a.MapName).OrderBy(g => g.Key))
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
                        var ranges = ClusterAnalyzer.GetIdRanges(adt.UniqueIds, _clusterGapThreshold);
                        
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
        private ExcelWorksheet CreateHistogramSheet(ExcelPackage package)
        {
            var histogramSheet = package.Workbook.Worksheets.Add("ID Distribution");
            int row = 1;
            
            // Get all unique IDs
            var allIds = _adtFiles
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
        private ExcelWorksheet CreateAssetDistributionSheet(ExcelPackage package)
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
            foreach (var cluster in _globalClusters.OrderBy(c => c.MinId))
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
        private ExcelWorksheet CreateDetailedAssetsSheet(ExcelPackage package)
        {
            var detailSheet = package.Workbook.Worksheets.Add("Detailed Assets");
            int row = 1;
            
            // Header
            detailSheet.Cells[row, 1].Value = "Asset Path";
            detailSheet.Cells[row, 2].Value = "Asset Type";
            detailSheet.Cells[row, 3].Value = "Usage Count";
            detailSheet.Cells[row, 4].Value = "First Seen ID";
            detailSheet.Cells[row, 5].Value = "Earliest Cluster";
            detailSheet.Cells[row, 6].Value = "Position X";
            detailSheet.Cells[row, 7].Value = "Position Y";
            detailSheet.Cells[row, 8].Value = "Position Z";
            detailSheet.Cells[row, 9].Value = "Maps";
            detailSheet.Cells[row, 1, row, 9].Style.Font.Bold = true;
            detailSheet.Cells[row, 1, row, 6].Style.Fill.PatternType = ExcelFillStyle.Solid;
            detailSheet.Cells[row, 1, row, 6].Style.Fill.BackgroundColor.SetColor(System.Drawing.Color.LightGray);
            
            row++;
            
            // Collect all unique assets across all clusters
            var allAssets = _globalClusters
                .SelectMany(c => c.Assets)
                .GroupBy(a => a.AssetPath)
                .Select(g => new {
                    Path = g.Key,
                    Type = g.First().Type,
                    Count = g.Count(),
                    FirstSeenId = g.Min(a => a.UniqueId),
                    PosX = g.First().PositionX,
                    PosY = g.First().PositionY,
                    PosZ = g.First().PositionZ,
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
                var earliestCluster = _globalClusters
                    .Where(c => c.MinId <= asset.FirstSeenId && c.MaxId >= asset.FirstSeenId)
                    .OrderBy(c => c.MinId)
                    .FirstOrDefault();
                
                if (earliestCluster != null)
                {
                    detailSheet.Cells[row, 5].Value = $"{earliestCluster.MinId} - {earliestCluster.MaxId}";
                }

                
detailSheet.Cells[row, 6].Value = asset.PosX;
                detailSheet.Cells[row, 7].Value = asset.PosY;
                detailSheet.Cells[row, 8].Value = asset.PosZ;
                
                detailSheet.Cells[row, 9].Value = string.Join(", ", asset.Maps);
                
                row++;
            }
            
            detailSheet.Cells.AutoFitColumns();
            return detailSheet;
        }
        
        /// <summary>
        /// Creates a worksheet with a complete mapping of all uniqueIDs to their associated assets.
        /// This provides an exhaustive view of what each uniqueID maps to.
        /// </summary>
        private ExcelWorksheet CreateCompleteIdMappingSheet(ExcelPackage package)
        {
            var mappingSheet = package.Workbook.Worksheets.Add("Complete ID Mapping");
            int row = 1;
            
            // Title
            mappingSheet.Cells[row, 1].Value = "Complete UniqueID to Asset Mapping";
            mappingSheet.Cells[row, 1].Style.Font.Size = 14;
            mappingSheet.Cells[row, 1].Style.Font.Bold = true;
            mappingSheet.Cells[row, 1, row, 10].Merge = true;
            row += 2;
            
            // Explanation
            mappingSheet.Cells[row, 1].Value = "This sheet provides a complete mapping of every uniqueID to its associated assets.";
            mappingSheet.Cells[row, 1, row, 10].Merge = true;
            row += 2;
            
            // Header
            mappingSheet.Cells[row, 1].Value = "UniqueID";
            mappingSheet.Cells[row, 2].Value = "Asset Path";
            mappingSheet.Cells[row, 3].Value = "Asset Type";
            mappingSheet.Cells[row, 4].Value = "Map";
            mappingSheet.Cells[row, 5].Value = "ADT X";
            mappingSheet.Cells[row, 6].Value = "ADT Y";
            mappingSheet.Cells[row, 7].Value = "Position X";
            mappingSheet.Cells[row, 8].Value = "Position Y";
            mappingSheet.Cells[row, 9].Value = "Position Z";
            mappingSheet.Cells[row, 10].Value = "In Cluster";
            mappingSheet.Cells[row, 1, row, 10].Style.Font.Bold = true;
            mappingSheet.Cells[row, 1, row, 10].Style.Fill.PatternType = ExcelFillStyle.Solid;
            mappingSheet.Cells[row, 1, row, 10].Style.Fill.BackgroundColor.SetColor(System.Drawing.Color.LightGray);
            row++;
            
            // Collect all uniqueIDs and their associated assets
            var allIds = new Dictionary<int, List<AssetReference>>();
            
            foreach (var adt in _adtFiles)
            {
                foreach (var entry in adt.AssetsByUniqueId)
                {
                    int id = entry.Key;
                    var assets = entry.Value;
                    
                    if (!allIds.TryGetValue(id, out var idAssets))
                    {
                        idAssets = new List<AssetReference>();
                        allIds[id] = idAssets;
                    }
                    
                    idAssets.AddRange(assets);
                }
            }
            
            // Find global clusters to determine if IDs are in clusters
            var globalClusters = FindGlobalClusters();
            var clusteredIds = new HashSet<int>();
            foreach (var cluster in globalClusters)
            {
                for (int id = cluster.MinId; id <= cluster.MaxId; id++)
                {
                    clusteredIds.Add(id);
                }
            }
            
            // Write all uniqueIDs and their assets
            foreach (var entry in allIds.OrderBy(e => e.Key))
            {
                int id = entry.Key;
                var assets = entry.Value;
                bool isInCluster = clusteredIds.Contains(id);
                
                foreach (var asset in assets)
                {
                    // Extract ADT coordinates from filename (format: map_xx_yy.adt)
                    int adtX = 0;
                    int adtY = 0;
                    string adtFile = asset.AdtFile;
                    
                    var parts = adtFile.Split('_');
                    if (parts.Length >= 3)
                    {
                        if (int.TryParse(parts[parts.Length - 2], out int x))
                        {
                            adtX = x;
                        }
                        if (int.TryParse(parts[parts.Length - 1].Replace(".adt", ""), out int y))
                        {
                            adtY = y;
                        }
                    }
                    
                    mappingSheet.Cells[row, 1].Value = id;
                    mappingSheet.Cells[row, 2].Value = asset.AssetPath;
                    mappingSheet.Cells[row, 3].Value = asset.Type;
                    mappingSheet.Cells[row, 4].Value = asset.MapName;
                    mappingSheet.Cells[row, 5].Value = adtX;
                    mappingSheet.Cells[row, 6].Value = adtY;
                    mappingSheet.Cells[row, 7].Value = asset.PositionX;
                    mappingSheet.Cells[row, 8].Value = asset.PositionY;
                    mappingSheet.Cells[row, 9].Value = asset.PositionZ;
                    mappingSheet.Cells[row, 10].Value = isInCluster ? "Yes" : "No";
                    
                    // Color rows based on whether the ID is in a cluster
                    if (!isInCluster)
                    {
                        mappingSheet.Cells[row, 1, row, 10].Style.Fill.PatternType = ExcelFillStyle.Solid;
                        mappingSheet.Cells[row, 1, row, 10].Style.Fill.BackgroundColor.SetColor(System.Drawing.Color.LightYellow);
                    }
                    
                    row++;
                }
            }
            
            // Add a filter to the header row
            mappingSheet.Cells[4, 1, 4, 10].AutoFilter = true;
            
            mappingSheet.Cells.AutoFitColumns();
            return mappingSheet;
        }
        
        /// <summary>
        /// Creates a worksheet with information about the lowest uniqueID.
        /// </summary>
        private ExcelWorksheet CreateLowestIdSheet(ExcelPackage package)
        {
            var lowestIdSheet = package.Workbook.Worksheets.Add("Lowest UniqueID");
            int row = 1;
            
            // Title
            lowestIdSheet.Cells[row, 1].Value = "Lowest UniqueID Analysis";
            lowestIdSheet.Cells[row, 1].Style.Font.Size = 14;
            lowestIdSheet.Cells[row, 1].Style.Font.Bold = true;
            lowestIdSheet.Cells[row, 1, row, 8].Merge = true;
            row += 2;
            
            if (!_adtFiles.SelectMany(a => a.UniqueIds).Any())
            {
                lowestIdSheet.Cells[row, 1].Value = "No uniqueIDs found in the dataset.";
                lowestIdSheet.Cells[row, 1, row, 5].Merge = true;
                return lowestIdSheet;
            }
            
            // Find the lowest ID
            int lowestId = _adtFiles.SelectMany(a => a.UniqueIds).Min();
            
            // Basic information
            lowestIdSheet.Cells[row, 1].Value = "Lowest UniqueID:";
            lowestIdSheet.Cells[row, 2].Value = lowestId;
            lowestIdSheet.Cells[row, 1].Style.Font.Bold = true;
            row++;
            
            // Find assets associated with the lowest ID
            var assetsForLowestId = new List<AssetReference>();
            var adtsWithLowestId = new List<string>();
            var mapsWithLowestId = new HashSet<string>();
            
            foreach (var adt in _adtFiles)
            {
                if (adt.UniqueIds.Contains(lowestId))
                {
                    adtsWithLowestId.Add(adt.FileName);
                    mapsWithLowestId.Add(adt.MapName);
                    
                    if (adt.AssetsByUniqueId.TryGetValue(lowestId, out var assets))
                    {
                        assetsForLowestId.AddRange(assets);
                    }
                }
            }
            
            // Maps containing this ID
            lowestIdSheet.Cells[row, 1].Value = "Found in Maps:";
            lowestIdSheet.Cells[row, 2].Value = string.Join(", ", mapsWithLowestId);
            lowestIdSheet.Cells[row, 1].Style.Font.Bold = true;
            row++;
            
            // ADT files containing this ID
            lowestIdSheet.Cells[row, 1].Value = "Found in ADT Files:";
            lowestIdSheet.Cells[row, 2].Value = adtsWithLowestId.Count;
            lowestIdSheet.Cells[row, 1].Style.Font.Bold = true;
            row++;
            
            // Asset count
            lowestIdSheet.Cells[row, 1].Value = "Associated Assets:";
            lowestIdSheet.Cells[row, 2].Value = assetsForLowestId.Count;
            lowestIdSheet.Cells[row, 1].Style.Font.Bold = true;
            row += 2;
            
            // Asset details header
            lowestIdSheet.Cells[row, 1].Value = "Asset Details";
            lowestIdSheet.Cells[row, 1].Style.Font.Bold = true;
            row++;
            
            lowestIdSheet.Cells[row, 1].Value = "Asset Path";
            lowestIdSheet.Cells[row, 2].Value = "Asset Type";
            lowestIdSheet.Cells[row, 3].Value = "Map";
            lowestIdSheet.Cells[row, 4].Value = "Position X";
            lowestIdSheet.Cells[row, 5].Value = "Position Y";
            lowestIdSheet.Cells[row, 6].Value = "Position Z";
            lowestIdSheet.Cells[row, 7].Value = "ADT File";
            lowestIdSheet.Cells[row, 1, row, 7].Style.Font.Bold = true;
            lowestIdSheet.Cells[row, 1, row, 4].Style.Fill.PatternType = ExcelFillStyle.Solid;
            lowestIdSheet.Cells[row, 1, row, 4].Style.Fill.BackgroundColor.SetColor(System.Drawing.Color.LightGray);
            row++;
            
            // List all assets
            foreach (var asset in assetsForLowestId)
            {
                lowestIdSheet.Cells[row, 1].Value = asset.AssetPath;
                lowestIdSheet.Cells[row, 2].Value = asset.Type;
                lowestIdSheet.Cells[row, 3].Value = asset.MapName;
                lowestIdSheet.Cells[row, 4].Value = asset.PositionX;
                lowestIdSheet.Cells[row, 5].Value = asset.PositionY;
                lowestIdSheet.Cells[row, 6].Value = asset.PositionZ;
                lowestIdSheet.Cells[row, 7].Value = asset.AdtFile;
                row++;
            }
            
            lowestIdSheet.Cells.AutoFitColumns();
            return lowestIdSheet;
        }
        
        /// <summary>
        /// Creates a worksheet with information about non-clustered uniqueIDs.
        /// </summary>
        private ExcelWorksheet CreateNonClusteredIdsSheet(ExcelPackage package)
        {
            var nonClusteredSheet = package.Workbook.Worksheets.Add("Non-Clustered IDs");
            int row = 1;
            
            // Title
            nonClusteredSheet.Cells[row, 1].Value = "Non-Clustered UniqueIDs Analysis";
            nonClusteredSheet.Cells[row, 1].Style.Font.Size = 14;
            nonClusteredSheet.Cells[row, 1].Style.Font.Bold = true;
            nonClusteredSheet.Cells[row, 1, row, 5].Merge = true;
            row += 2;
            
            // Find all global clusters
            var allIds = _adtFiles.SelectMany(a => a.UniqueIds).Distinct().OrderBy(id => id).ToList();
            
            // Get all IDs that are part of global clusters
            var clusteredIds = new HashSet<int>();
            var globalClusters = FindGlobalClusters();
            foreach (var cluster in globalClusters)
            {
                for (int id = cluster.MinId; id <= cluster.MaxId; id++)
                {
                    if (allIds.Contains(id))
                    {
                        clusteredIds.Add(id);
                    }
                }
            }
            
            // Find IDs that aren't in any cluster
            var nonClusteredIds = allIds.Where(id => !clusteredIds.Contains(id)).OrderBy(id => id).ToList();
            
            if (nonClusteredIds.Count == 0)
            {
                nonClusteredSheet.Cells[row, 1].Value = "No non-clustered uniqueIDs found.";
                nonClusteredSheet.Cells[row, 1, row, 5].Merge = true;
                return nonClusteredSheet;
            }
            
            // Basic information
            nonClusteredSheet.Cells[row, 1].Value = "Non-Clustered UniqueIDs:";
            nonClusteredSheet.Cells[row, 2].Value = nonClusteredIds.Count;
            nonClusteredSheet.Cells[row, 1].Style.Font.Bold = true;
            row++;
            
            nonClusteredSheet.Cells[row, 1].Value = "ID Range:";
            nonClusteredSheet.Cells[row, 2].Value = $"{nonClusteredIds.Min()} - {nonClusteredIds.Max()}";
            nonClusteredSheet.Cells[row, 1].Style.Font.Bold = true;
            row += 2;
            
            // Distribution by map
            nonClusteredSheet.Cells[row, 1].Value = "Distribution by Map";
            nonClusteredSheet.Cells[row, 1].Style.Font.Bold = true;
            row++;
            
            nonClusteredSheet.Cells[row, 1].Value = "Map";
            nonClusteredSheet.Cells[row, 2].Value = "Non-Clustered ID Count";
            nonClusteredSheet.Cells[row, 3].Value = "Min ID";
            nonClusteredSheet.Cells[row, 4].Value = "Max ID";
            nonClusteredSheet.Cells[row, 1, row, 4].Style.Font.Bold = true;
            nonClusteredSheet.Cells[row, 1, row, 4].Style.Fill.PatternType = ExcelFillStyle.Solid;
            nonClusteredSheet.Cells[row, 1, row, 4].Style.Fill.BackgroundColor.SetColor(System.Drawing.Color.LightGray);
            row++;
            
            // Group by map
            var idsByMap = new Dictionary<string, List<int>>();
            foreach (var id in nonClusteredIds)
            {
                foreach (var adt in _adtFiles.Where(a => a.UniqueIds.Contains(id)))
                {
                    if (!idsByMap.TryGetValue(adt.MapName, out var mapIds))
                    {
                        mapIds = new List<int>();
                        idsByMap[adt.MapName] = mapIds;
                    }
                    
                    if (!mapIds.Contains(id))
                    {
                        mapIds.Add(id);
                    }
                }
            }
            
            foreach (var mapEntry in idsByMap.OrderBy(m => m.Key))
            {
                nonClusteredSheet.Cells[row, 1].Value = mapEntry.Key;
                nonClusteredSheet.Cells[row, 2].Value = mapEntry.Value.Count;
                nonClusteredSheet.Cells[row, 3].Value = mapEntry.Value.Min();
                nonClusteredSheet.Cells[row, 4].Value = mapEntry.Value.Max();
                row++;
            }
            
            nonClusteredSheet.Cells.AutoFitColumns();
            return nonClusteredSheet;
        }
    }

    /// <summary>
    /// Generates the text report with cluster information
    /// </summary>
    public class TextReportGenerator : BaseReportGenerator
    {
        private readonly Dictionary<string, List<UniqueIdCluster>> _mapClusters;
        private readonly List<UniqueIdCluster> _globalClusters;
        private readonly List<int> _nonClusteredIds;
        private readonly Dictionary<int, List<AssetReference>> _nonClusteredAssets;

        public TextReportGenerator(
            List<AdtInfo> adtFiles,
            Dictionary<string, List<UniqueIdCluster>> mapClusters,
            List<UniqueIdCluster> globalClusters,
            List<int> nonClusteredIds,
            Dictionary<int, List<AssetReference>> nonClusteredAssets,
            string outputDirectory,
            bool comprehensive = true)
            : base(adtFiles, outputDirectory, comprehensive)
        {
            _mapClusters = mapClusters;
            _globalClusters = globalClusters;
            _nonClusteredIds = nonClusteredIds;
            _nonClusteredAssets = nonClusteredAssets;
        }

        /// <summary>
        /// Generates a text report of the analysis.
        /// </summary>
        public async Task GenerateAsync()
        {
            Console.WriteLine("Generating text report...");
            
            var reportPath = Path.Combine(_outputDirectory, "unique_id_analysis.txt");
            
            using (var writer = new StreamWriter(reportPath))
            {
                await writer.WriteLineAsync($"ADT UniqueID Analysis Report - {DateTime.Now}");
                await writer.WriteLineAsync("=========================================");
                await writer.WriteLineAsync();
                
                // Write lowest ID information
                if (_comprehensive && _adtFiles.SelectMany(a => a.UniqueIds).Any())
                {
                    int lowestId = _adtFiles.SelectMany(a => a.UniqueIds).Min();
                    await writer.WriteLineAsync("LOWEST UNIQUE ID INFORMATION");
                    await writer.WriteLineAsync("==========================");
                    await writer.WriteLineAsync($"Lowest UniqueID: {lowestId}");
                    
                    // Find assets associated with the lowest ID
                    var assetsForLowestId = new List<AssetReference>();
                    foreach (var adt in _adtFiles)
                    {
                        if (adt.UniqueIds.Contains(lowestId) && adt.AssetsByUniqueId.TryGetValue(lowestId, out var assets))
                        {
                            assetsForLowestId.AddRange(assets);
                        }
                    }
                    
                    await writer.WriteLineAsync($"Associated with {assetsForLowestId.Count} assets");
                    
                    // Group assets by type
                    var assetsByType = assetsForLowestId.GroupBy(a => a.Type);
                    foreach (var typeGroup in assetsByType.OrderBy(g => g.Key))
                    {
                        await writer.WriteLineAsync($"  {typeGroup.Key}s ({typeGroup.Count()}):");
                        foreach (var asset in typeGroup)
                        {
                            await writer.WriteLineAsync($"    {asset.AssetPath} in {asset.MapName}/{asset.AdtFile}");
                        }
                    }
                    await writer.WriteLineAsync();
                }
                
                // Write global clusters
                await writer.WriteLineAsync("GLOBAL CLUSTERS");
                await writer.WriteLineAsync("==============");
                
                foreach (var cluster in _globalClusters.OrderBy(c => c.MinId))
                {
                    await writer.WriteLineAsync($"Cluster: {cluster.MinId} - {cluster.MaxId}");
                    await writer.WriteLineAsync($"Count: {cluster.Count} unique IDs");
                    await writer.WriteLineAsync($"Span: {cluster.MaxId - cluster.MinId + 1} potential IDs");
                    await writer.WriteLineAsync($"Density: {cluster.Density:F2}");
                    await writer.WriteLineAsync($"Present in {cluster.AdtFiles.Count} ADT files");
                    await writer.WriteLineAsync($"Contains {cluster.Assets.Count} unique assets");
                    
                    // Group ADTs by map
                    var adtsByMap = cluster.AdtFiles
                        .Select(file => _adtFiles.FirstOrDefault(a => a.FileName == file))
                        .Where(a => a != null)
                        .GroupBy(a => a.MapName)
                        .OrderBy(g => g.Key);
                    
                    await writer.WriteLineAsync("Maps and ADTs:");
                    foreach (var mapGroup in adtsByMap)
                    {
                        await writer.WriteLineAsync($"  {mapGroup.Key}: {mapGroup.Count()} ADTs");
                        
                        foreach (var adt in mapGroup.OrderBy(a => a.FileName))
                        {
                            if (cluster.IdCountsByAdt.TryGetValue(adt.FileName, out var count))
                            {
                                await writer.WriteLineAsync($"    {adt.FileName}: {count} IDs");
                            }
                        }
                    }
                    
                    // Write asset information
                    await writer.WriteLineAsync("Assets:");
                    
                    // Group assets by type
                    var assetsByType = cluster.Assets.GroupBy(a => a.Type);
                    foreach (var typeGroup in assetsByType.OrderBy(g => g.Key))
                    {
                        await writer.WriteLineAsync($"  {typeGroup.Key}s ({typeGroup.Count()}):");
                        
                        if (_comprehensive)
                        {
                            // List ALL assets when comprehensive is true
                            foreach (var asset in typeGroup.GroupBy(a => a.AssetPath).OrderByDescending(g => g.Count()))
                            {
                                await writer.WriteLineAsync($"    {asset.Key} (used {asset.Count()} times)");
                            }
                        }
                        else
                        {
                            // List only top 20 assets when not comprehensive
                            var topAssets = typeGroup.GroupBy(a => a.AssetPath)
                                .Select(g => new { Path = g.Key, Count = g.Count() })
                                .OrderByDescending(a => a.Count)
                                .Take(20);
                            
                            foreach (var asset in topAssets)
                            {
                                await writer.WriteLineAsync($"    {asset.Path} (used {asset.Count} times)");
                            }
                            
                            if (typeGroup.Count() > 20)
                            {
                                await writer.WriteLineAsync($"    ... and {typeGroup.Count() - 20} more {typeGroup.Key}s");
                            }
                        }
                    }
                    
                    await writer.WriteLineAsync();
                }
                
                // Write per-map clusters
                await writer.WriteLineAsync();
                await writer.WriteLineAsync("PER-MAP CLUSTERS");
                await writer.WriteLineAsync("===============");
                
                foreach (var mapEntry in _mapClusters.OrderBy(m => m.Key))
                {
                    var mapName = mapEntry.Key;
                    var clusters = mapEntry.Value;
                    
                    await writer.WriteLineAsync();
                    await writer.WriteLineAsync($"MAP: {mapName}");
                    await writer.WriteLineAsync($"{new string('=', mapName.Length + 5)}");
                    
                    foreach (var cluster in clusters.OrderBy(c => c.MinId))
                    {
                        await writer.WriteLineAsync($"Cluster: {cluster.MinId} - {cluster.MaxId}");
                        await writer.WriteLineAsync($"Count: {cluster.Count} unique IDs");
                        await writer.WriteLineAsync($"Span: {cluster.MaxId - cluster.MinId + 1} potential IDs");
                        await writer.WriteLineAsync($"Density: {cluster.Density:F2}");
                        await writer.WriteLineAsync($"Present in {cluster.AdtFiles.Count} ADT files");
                        await writer.WriteLineAsync($"Contains {cluster.Assets.Count} unique assets");
                        
                        // ADT files in this cluster
                        await writer.WriteLineAsync("ADT Files:");
                        foreach (var adtFile in cluster.AdtFiles.OrderBy(f => f))
                        {
                            if (cluster.IdCountsByAdt.TryGetValue(adtFile, out var count))
                            {
                                await writer.WriteLineAsync($"  {adtFile}: {count} IDs");
                            }
                        }
                        
                        // Write asset information
                        await writer.WriteLineAsync("Assets:");
                        
                        // Group assets by type
                        var assetsByType = cluster.Assets.GroupBy(a => a.Type);
                        foreach (var typeGroup in assetsByType.OrderBy(g => g.Key))
                        {
                            await writer.WriteLineAsync($"  {typeGroup.Key}s ({typeGroup.Count()}):");
                            
                            if (_comprehensive)
                            {
                                // List ALL assets when comprehensive is true
                                foreach (var asset in typeGroup.GroupBy(a => a.AssetPath).OrderByDescending(g => g.Count()))
                                {
                                    await writer.WriteLineAsync($"    {asset.Key} (used {asset.Count()} times)");
                                }
                            }
                            else
                            {
                                // List only top 10 assets when not comprehensive
                                var topAssets = typeGroup.GroupBy(a => a.AssetPath)
                                    .Select(g => new { Path = g.Key, Count = g.Count() })
                                    .OrderByDescending(a => a.Count)
                                    .Take(10);
                                
                                foreach (var asset in topAssets)
                                {
                                    await writer.WriteLineAsync($"    {asset.Path} (used {asset.Count} times)");
                                }
                                
                                if (typeGroup.Count() > 10)
                                {
                                    await writer.WriteLineAsync($"    ... and {typeGroup.Count() - 10} more {typeGroup.Key}s");
                                }
                            }
                        }
                        
                        await writer.WriteLineAsync();
                    }
                }
                
                // Write individual ADT data
                await writer.WriteLineAsync();
                await writer.WriteLineAsync("INDIVIDUAL ADT DATA");
                await writer.WriteLineAsync("==================");
                
                foreach (var mapGroup in _adtFiles.GroupBy(a => a.MapName).OrderBy(g => g.Key))
                {
                    await writer.WriteLineAsync();
                    await writer.WriteLineAsync($"MAP: {mapGroup.Key}");
                    await writer.WriteLineAsync($"{new string('=', mapGroup.Key.Length + 5)}");
                    
                    foreach (var adt in mapGroup.OrderBy(a => a.FileName))
                    {
                        await writer.WriteLineAsync($"{adt.FileName}: {adt.UniqueIds.Count} IDs, {adt.AssetsByUniqueId.Values.SelectMany(a => a).Count()} assets");
                        
                        // Calculate some basic statistics
                        var minId = adt.UniqueIds.Min();
                        var maxId = adt.UniqueIds.Max();
                        var ranges = ClusterAnalyzer.GetIdRanges(adt.UniqueIds, 1000); // Using default gap threshold
                        
                        await writer.WriteLineAsync($"  Range: {minId} - {maxId} (span: {maxId - minId + 1})");
                        
                        // Group assets by type
                        var assetsByType = adt.AssetsByUniqueId.Values
                            .SelectMany(a => a)
                            .GroupBy(a => a.Type);
                            
                        await writer.WriteLineAsync($"  Assets: {string.Join(", ", assetsByType.Select(g => $"{g.Count()} {g.Key}s"))}");
                        
                        if (ranges.Count > 1)
                        {
                            await writer.WriteLineAsync($"  Major ranges ({ranges.Count}):");
                            foreach (var range in ranges.OrderBy(r => r.Item1))
                            {
                                await writer.WriteLineAsync($"    {range.Item1} - {range.Item2} ({range.Item2 - range.Item1 + 1} span, {range.Item3} IDs)");
                            }
                        }
                        
                        await writer.WriteLineAsync();
                    }
                }

                // Write non-clustered ID data if comprehensive report is requested
                if (_comprehensive)
                {
                    await writer.WriteLineAsync();
                    await writer.WriteLineAsync("NON-CLUSTERED UNIQUE IDS");
                    await writer.WriteLineAsync("======================");
                    
                    if (_nonClusteredIds.Count == 0)
                    {
                        await writer.WriteLineAsync("No non-clustered uniqueIDs found.");
                    }
                    else
                    {
                        await writer.WriteLineAsync($"Found {_nonClusteredIds.Count} uniqueIDs that don't belong to any cluster.");
                        await writer.WriteLineAsync($"ID Range: {_nonClusteredIds.Min()} - {_nonClusteredIds.Max()}");
                        
                        // Group by map
                        var idsByMap = new Dictionary<string, List<int>>();
                        foreach (var id in _nonClusteredIds)
                        {
                            foreach (var adt in _adtFiles.Where(a => a.UniqueIds.Contains(id)))
                            {
                                if (!idsByMap.TryGetValue(adt.MapName, out var mapIds))
                                {
                                    mapIds = new List<int>();
                                    idsByMap[adt.MapName] = mapIds;
                                }
                                
                                if (!mapIds.Contains(id))
                                {
                                    mapIds.Add(id);
                                }
                            }
                        }
                        
                        await writer.WriteLineAsync("Distribution by map:");
                        foreach (var mapEntry in idsByMap.OrderBy(m => m.Key))
                        {
                            await writer.WriteLineAsync($"  {mapEntry.Key}: {mapEntry.Value.Count} non-clustered IDs");
                            await writer.WriteLineAsync($"    Range: {mapEntry.Value.Min()} - {mapEntry.Value.Max()}");
                        }
                        
                        await writer.WriteLineAsync();
                    }
                }
                
                Console.WriteLine($"Text report written to {reportPath}");
            }
        }
    }
}