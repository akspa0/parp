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
    /// Extension methods for advanced analysis features
    /// </summary>
    public static class AnalysisExtensions
    {
        /// <summary>
        /// Generates reports for cross-map collision detection, unique assets, and development timeline
        /// </summary>
        public static async Task GenerateAdvancedReportsAsync(
            List<AdtInfo> adtFiles,
            string outputDirectory)
        {
            Console.WriteLine("Generating advanced analysis reports...");
            
            var idCollisionsPath = Path.Combine(outputDirectory, "id_collisions.xlsx");
            var uniqueAssetsPath = Path.Combine(outputDirectory, "unique_assets.xlsx");
            var timelinePath = Path.Combine(outputDirectory, "development_timeline.xlsx");
            
            // Set license context for EPPlus
            ExcelPackage.LicenseContext = LicenseContext.NonCommercial;
            
            // Generate ID collisions report
            await GenerateIdCollisionsReportAsync(adtFiles, idCollisionsPath);
            
            // Generate unique assets report
            await GenerateUniqueAssetsReportAsync(adtFiles, uniqueAssetsPath);
            
            // Generate development timeline report
            await GenerateDevelopmentTimelineAsync(adtFiles, timelinePath);
            
            Console.WriteLine("Advanced analysis reports complete!");
        }
        
        /// <summary>
        /// Identifies uniqueID collisions across different maps and generates a report
        /// </summary>
        private static async Task GenerateIdCollisionsReportAsync(List<AdtInfo> adtFiles, string outputPath)
        {
            Console.WriteLine("Analyzing uniqueID collisions across maps...");
            
            using (var package = new ExcelPackage())
            {
                var collisionsSheet = package.Workbook.Worksheets.Add("ID Collisions");
                int row = 1;
                
                // Header
                collisionsSheet.Cells[row, 1].Value = "UniqueID";
                collisionsSheet.Cells[row, 2].Value = "Maps";
                collisionsSheet.Cells[row, 3].Value = "ADT Files";
                collisionsSheet.Cells[row, 4].Value = "Assets in First Map";
                collisionsSheet.Cells[row, 5].Value = "Assets in Second Map";
                collisionsSheet.Cells[row, 1, row, 5].Style.Font.Bold = true;
                collisionsSheet.Cells[row, 1, row, 5].Style.Fill.PatternType = ExcelFillStyle.Solid;
                collisionsSheet.Cells[row, 1, row, 5].Style.Fill.BackgroundColor.SetColor(System.Drawing.Color.LightGray);
                
                row++;
                
                // Find all uniqueIDs and the maps they appear in
                var idToMaps = new Dictionary<int, HashSet<string>>();
                var idToAdts = new Dictionary<int, HashSet<string>>();
                var idToAssets = new Dictionary<int, Dictionary<string, List<AssetReference>>>();
                
                foreach (var adt in adtFiles)
                {
                    foreach (var id in adt.UniqueIds)
                    {
                        // Track maps for this ID
                        if (!idToMaps.TryGetValue(id, out var maps))
                        {
                            maps = new HashSet<string>();
                            idToMaps[id] = maps;
                        }
                        maps.Add(adt.MapName);
                        
                        // Track ADTs for this ID
                        if (!idToAdts.TryGetValue(id, out var adts))
                        {
                            adts = new HashSet<string>();
                            idToAdts[id] = adts;
                        }
                        adts.Add(adt.FileName);
                        
                        // Track assets for this ID by map
                        if (!idToAssets.TryGetValue(id, out var assetsByMap))
                        {
                            assetsByMap = new Dictionary<string, List<AssetReference>>();
                            idToAssets[id] = assetsByMap;
                        }
                        
                        if (adt.AssetsByUniqueId.TryGetValue(id, out var assets))
                        {
                            if (!assetsByMap.TryGetValue(adt.MapName, out var mapAssets))
                            {
                                mapAssets = new List<AssetReference>();
                                assetsByMap[adt.MapName] = mapAssets;
                            }
                            mapAssets.AddRange(assets);
                        }
                    }
                }
                
                // Find collisions (IDs that appear in more than one map)
                var collisions = idToMaps
                    .Where(kvp => kvp.Value.Count > 1)
                    .OrderBy(kvp => kvp.Key)
                    .ToList();
                    
                if (collisions.Count == 0)
                {
                    collisionsSheet.Cells[row, 1].Value = "No uniqueID collisions found across maps";
                    collisionsSheet.Cells[row, 1, row, 5].Merge = true;
                    collisionsSheet.Cells[row, 1, row, 5].Style.HorizontalAlignment = ExcelHorizontalAlignment.Center;
                    row++;
                }
                else
                {
                    // Write collision data
                    foreach (var collision in collisions)
                    {
                        int id = collision.Key;
                        var maps = collision.Value.ToList();
                        
                        collisionsSheet.Cells[row, 1].Value = id;
                        collisionsSheet.Cells[row, 2].Value = string.Join(", ", maps);
                        collisionsSheet.Cells[row, 3].Value = string.Join(", ", idToAdts[id]);
                        
                        // Get assets for the first map
                        if (idToAssets.TryGetValue(id, out var assetsByMap) && 
                            assetsByMap.TryGetValue(maps[0], out var firstMapAssets))
                        {
                            var firstMapAssetPaths = firstMapAssets
                                .Select(a => $"{a.Type}: {a.AssetPath}")
                                .Distinct()
                                .ToList();
                                
                            collisionsSheet.Cells[row, 4].Value = string.Join(", ", firstMapAssetPaths);
                        }
                        
                        // Get assets for the second map
                        if (maps.Count > 1 && 
                            idToAssets.TryGetValue(id, out var assetsByMap2) && 
                            assetsByMap2.TryGetValue(maps[1], out var secondMapAssets))
                        {
                            var secondMapAssetPaths = secondMapAssets
                                .Select(a => $"{a.Type}: {a.AssetPath}")
                                .Distinct()
                                .ToList();
                                
                            collisionsSheet.Cells[row, 5].Value = string.Join(", ", secondMapAssetPaths);
                        }
                        
                        row++;
                    }
                    
                    // Add summary row
                    row++;
                    collisionsSheet.Cells[row, 1].Value = "Total Collisions:";
                    collisionsSheet.Cells[row, 2].Value = collisions.Count;
                    collisionsSheet.Cells[row, 1, row, 2].Style.Font.Bold = true;
                }
                
                // Additional summary sheet
                var summarySheet = package.Workbook.Worksheets.Add("Collision Summary");
                row = 1;
                
                // Header
                summarySheet.Cells[row, 1].Value = "Map Pair";
                summarySheet.Cells[row, 2].Value = "Collision Count";
                summarySheet.Cells[row, 3].Value = "Sample IDs";
                summarySheet.Cells[row, 1, row, 3].Style.Font.Bold = true;
                summarySheet.Cells[row, 1, row, 3].Style.Fill.PatternType = ExcelFillStyle.Solid;
                summarySheet.Cells[row, 1, row, 3].Style.Fill.BackgroundColor.SetColor(System.Drawing.Color.LightGray);
                
                row++;
                
                // Count collisions between each pair of maps
                var mapPairCounts = new Dictionary<string, List<int>>();
                
                foreach (var collision in collisions)
                {
                    var maps = collision.Value.ToList();
                    for (int i = 0; i < maps.Count; i++)
                    {
                        for (int j = i + 1; j < maps.Count; j++)
                        {
                            var pair = $"{maps[i]} - {maps[j]}";
                            if (!mapPairCounts.TryGetValue(pair, out var ids))
                            {
                                ids = new List<int>();
                                mapPairCounts[pair] = ids;
                            }
                            ids.Add(collision.Key);
                        }
                    }
                }
                
                // Write map pair data
                foreach (var pair in mapPairCounts.OrderByDescending(p => p.Value.Count))
                {
                    summarySheet.Cells[row, 1].Value = pair.Key;
                    summarySheet.Cells[row, 2].Value = pair.Value.Count;
                    
                    // Sample up to 20 IDs
                    var sampleIds = pair.Value.Take(20).Select(id => id.ToString());
                    summarySheet.Cells[row, 3].Value = string.Join(", ", sampleIds);
                    
                    if (pair.Value.Count > 20)
                    {
                        summarySheet.Cells[row, 3].Value += $" (and {pair.Value.Count - 20} more)";
                    }
                    
                    row++;
                }
                
                collisionsSheet.Cells.AutoFitColumns();
                summarySheet.Cells.AutoFitColumns();
                
                // Save the Excel file
                await package.SaveAsAsync(new FileInfo(outputPath));
                
                Console.WriteLine($"Collision report written to {outputPath}");
            }
        }
        
        /// <summary>
        /// Creates a report of assets that appear exactly once across all maps
        /// </summary>
        private static async Task GenerateUniqueAssetsReportAsync(List<AdtInfo> adtFiles, string outputPath)
        {
            Console.WriteLine("Analyzing unique assets (assets that appear only once)...");
            
            using (var package = new ExcelPackage())
            {
                var uniqueSheet = package.Workbook.Worksheets.Add("Unique Assets");
                int row = 1;
                
                // Header
                uniqueSheet.Cells[row, 1].Value = "Asset Path";
                uniqueSheet.Cells[row, 2].Value = "Asset Type";
                uniqueSheet.Cells[row, 3].Value = "Map";
                uniqueSheet.Cells[row, 4].Value = "ADT File";
                uniqueSheet.Cells[row, 5].Value = "UniqueID";
                uniqueSheet.Cells[row, 1, row, 5].Style.Font.Bold = true;
                uniqueSheet.Cells[row, 1, row, 5].Style.Fill.PatternType = ExcelFillStyle.Solid;
                uniqueSheet.Cells[row, 1, row, 5].Style.Fill.BackgroundColor.SetColor(System.Drawing.Color.LightGray);
                
                row++;
                
                // Collect all assets across all ADTs
                var assetCounts = new Dictionary<string, int>();
                var assetDetails = new Dictionary<string, List<AssetReference>>();
                
                foreach (var adt in adtFiles)
                {
                    foreach (var entry in adt.AssetsByUniqueId)
                    {
                        foreach (var asset in entry.Value)
                        {
                            string key = $"{asset.Type}:{asset.AssetPath}";
                            
                            // Count occurrences
                            if (!assetCounts.TryGetValue(key, out int count))
                            {
                                count = 0;
                                assetCounts[key] = 0;
                            }
                            assetCounts[key] = count + 1;
                            
                            // Store details
                            if (!assetDetails.TryGetValue(key, out var details))
                            {
                                details = new List<AssetReference>();
                                assetDetails[key] = details;
                            }
                            details.Add(asset);
                        }
                    }
                }
                
                // Find assets that appear only once
                var uniqueAssets = assetCounts
                    .Where(kvp => kvp.Value == 1)
                    .Select(kvp => kvp.Key)
                    .OrderBy(k => k)
                    .ToList();
                    
                if (uniqueAssets.Count == 0)
                {
                    uniqueSheet.Cells[row, 1].Value = "No assets that appear exactly once were found";
                    uniqueSheet.Cells[row, 1, row, 5].Merge = true;
                    uniqueSheet.Cells[row, 1, row, 5].Style.HorizontalAlignment = ExcelHorizontalAlignment.Center;
                    row++;
                }
                else
                {
                    // Write unique asset data
                    foreach (var assetKey in uniqueAssets)
                    {
                        var asset = assetDetails[assetKey].First();
                        
                        uniqueSheet.Cells[row, 1].Value = asset.AssetPath;
                        uniqueSheet.Cells[row, 2].Value = asset.Type;
                        uniqueSheet.Cells[row, 3].Value = asset.MapName;
                        uniqueSheet.Cells[row, 4].Value = asset.AdtFile;
                        uniqueSheet.Cells[row, 5].Value = asset.UniqueId;
                        
                        row++;
                    }
                    
                    // Add summary row
                    row++;
                    uniqueSheet.Cells[row, 1].Value = "Total Unique Assets:";
                    uniqueSheet.Cells[row, 2].Value = uniqueAssets.Count;
                    uniqueSheet.Cells[row, 1, row, 2].Style.Font.Bold = true;
                }
                
                // Add summary sheet by map and asset type
                var summarySheet = package.Workbook.Worksheets.Add("Unique Assets Summary");
                row = 1;
                
                // Header
                summarySheet.Cells[row, 1].Value = "Map";
                summarySheet.Cells[row, 2].Value = "Asset Type";
                summarySheet.Cells[row, 3].Value = "Count";
                summarySheet.Cells[row, 1, row, 3].Style.Font.Bold = true;
                summarySheet.Cells[row, 1, row, 3].Style.Fill.PatternType = ExcelFillStyle.Solid;
                summarySheet.Cells[row, 1, row, 3].Style.Fill.BackgroundColor.SetColor(System.Drawing.Color.LightGray);
                
                row++;
                
                // Group unique assets by map and type
                var uniqueByMapAndType = uniqueAssets
                    .Select(key => assetDetails[key].First())
                    .GroupBy(a => new { a.MapName, a.Type })
                    .Select(g => new {
                        Map = g.Key.MapName,
                        Type = g.Key.Type,
                        Count = g.Count()
                    })
                    .OrderBy(g => g.Map)
                    .ThenBy(g => g.Type);
                    
                foreach (var group in uniqueByMapAndType)
                {
                    summarySheet.Cells[row, 1].Value = group.Map;
                    summarySheet.Cells[row, 2].Value = group.Type;
                    summarySheet.Cells[row, 3].Value = group.Count;
                    row++;
                }
                
                uniqueSheet.Cells.AutoFitColumns();
                summarySheet.Cells.AutoFitColumns();
                
                // Save the Excel file
                await package.SaveAsAsync(new FileInfo(outputPath));
                
                Console.WriteLine($"Unique assets report written to {outputPath}");
            }
        }
        
        /// <summary>
        /// Creates a development timeline analysis showing how uniqueIDs evolved across maps
        /// </summary>
        private static async Task GenerateDevelopmentTimelineAsync(List<AdtInfo> adtFiles, string outputPath)
        {
            Console.WriteLine("Generating development timeline analysis...");
            
            using (var package = new ExcelPackage())
            {
                // Create timeline overview sheet
                var overviewSheet = package.Workbook.Worksheets.Add("Development Timeline");
                int row = 1;
                
                // Title and introduction
                overviewSheet.Cells[row, 1].Value = "World of Warcraft Development Timeline Analysis";
                overviewSheet.Cells[row, 1].Style.Font.Size = 16;
                overviewSheet.Cells[row, 1].Style.Font.Bold = true;
                overviewSheet.Cells[row, 1, row, 8].Merge = true;
                row += 2;
                
                overviewSheet.Cells[row, 1].Value = "This analysis examines how uniqueIDs flow across different maps, revealing the development timeline of World of Warcraft.";
                overviewSheet.Cells[row, 1, row, 8].Merge = true;
                row += 2;
                
                // Get all maps
                var allMaps = adtFiles.Select(a => a.MapName).Distinct().OrderBy(m => m).ToList();
                
                // Get global ID range
                var allIds = adtFiles.SelectMany(a => a.UniqueIds).Distinct().OrderBy(id => id).ToList();
                var minId = allIds.FirstOrDefault();
                var maxId = allIds.LastOrDefault();
                
                // Divide the entire ID range into segments
                const int segmentCount = 20; // Number of timeline segments
                var segmentSize = (maxId - minId) / segmentCount;
                
                // Prepare data for timeline
                var timelineData = new List<TimelineSegment>();
                
                for (int i = 0; i < segmentCount; i++)
                {
                    var segmentStart = minId + (i * segmentSize);
                    var segmentEnd = (i < segmentCount - 1) 
                        ? segmentStart + segmentSize - 1 
                        : maxId; // Last segment includes the remainder
                    
                    var segment = new TimelineSegment
                    {
                        SegmentIndex = i,
                        StartId = segmentStart,
                        EndId = segmentEnd,
                        MapActivity = new Dictionary<string, int>()
                    };
                    
                    // Count IDs in this segment for each map
                    foreach (var map in allMaps)
                    {
                        var mapAdts = adtFiles.Where(a => a.MapName == map).ToList();
                        var idsInSegment = mapAdts
                            .SelectMany(a => a.UniqueIds)
                            .Count(id => id >= segmentStart && id <= segmentEnd);
                        
                        segment.MapActivity[map] = idsInSegment;
                    }
                    
                    timelineData.Add(segment);
                }
                
                // Calculate total activity in each segment for sorting
                foreach (var segment in timelineData)
                {
                    segment.TotalActivity = segment.MapActivity.Values.Sum();
                }
                
                // Create timeline header
                overviewSheet.Cells[row, 1].Value = "Timeline Segment";
                overviewSheet.Cells[row, 2].Value = "ID Range";
                overviewSheet.Cells[row, 3].Value = "Total Activity";
                
                int col = 4;
                foreach (var map in allMaps)
                {
                    overviewSheet.Cells[row, col].Value = map;
                    overviewSheet.Cells[row, col].Style.TextRotation = 90;
                    col++;
                }
                
                overviewSheet.Cells[row, 1, row, col - 1].Style.Font.Bold = true;
                overviewSheet.Cells[row, 1, row, col - 1].Style.Fill.PatternType = ExcelFillStyle.Solid;
                overviewSheet.Cells[row, 1, row, col - 1].Style.Fill.BackgroundColor.SetColor(System.Drawing.Color.LightGray);
                row++;
                
                // Fill timeline data
                for (int i = 0; i < timelineData.Count; i++)
                {
                    var segment = timelineData[i];
                    
                    overviewSheet.Cells[row, 1].Value = i + 1;
                    overviewSheet.Cells[row, 2].Value = $"{segment.StartId} - {segment.EndId}";
                    overviewSheet.Cells[row, 3].Value = segment.TotalActivity;
                    
                    col = 4;
                    foreach (var map in allMaps)
                    {
                        int activity = segment.MapActivity[map];
                        overviewSheet.Cells[row, col].Value = activity;
                        
                        // Color cells based on activity level
                        if (activity > 0)
                        {
                            // Calculate color intensity (blue) based on activity level
                            var maxActivity = segment.MapActivity.Values.Max();
                            var intensity = (byte)(255 - Math.Min(255, (activity * 255 / Math.Max(1, maxActivity))));
                            
                            overviewSheet.Cells[row, col].Style.Fill.PatternType = ExcelFillStyle.Solid;
                            overviewSheet.Cells[row, col].Style.Fill.BackgroundColor.SetColor(Color.FromArgb(intensity, intensity, 255));
                        }
                        
                        col++;
                    }
                    
                    row++;
                }
                
                // Format the table
                overviewSheet.Cells.AutoFitColumns();
                
                // Create major development phases sheet
                var phasesSheet = CreateDevelopmentPhasesSheet(package, timelineData, allMaps);
                
                // Create cross-map development sheet
                var crossMapSheet = CreateCrossMapDevelopmentSheet(package, adtFiles, allMaps);
                
                // Create ID flow chart
                CreateIdFlowChart(package, timelineData, allMaps);
                
                // Save the Excel file
                await package.SaveAsAsync(new FileInfo(outputPath));
                
                Console.WriteLine($"Development timeline analysis written to {outputPath}");
            }
        }
        
        /// <summary>
        /// Creates a sheet analyzing the major development phases
        /// </summary>
        private static ExcelWorksheet CreateDevelopmentPhasesSheet(
            ExcelPackage package, 
            List<TimelineSegment> timelineData,
            List<string> allMaps)
        {
            // Create phases worksheet
            var phasesSheet = package.Workbook.Worksheets.Add("Development Phases");
            int row = 1;
            
            // Title
            phasesSheet.Cells[row, 1].Value = "Major Development Phases";
            phasesSheet.Cells[row, 1].Style.Font.Size = 14;
            phasesSheet.Cells[row, 1].Style.Font.Bold = true;
            phasesSheet.Cells[row, 1, row, 5].Merge = true;
            row += 2;
            
            // Identify significant activity changes as phase boundaries
            var phases = IdentifyDevelopmentPhases(timelineData, allMaps);
            
            // Header
            phasesSheet.Cells[row, 1].Value = "Phase";
            phasesSheet.Cells[row, 2].Value = "ID Range";
            phasesSheet.Cells[row, 3].Value = "Primary Maps";
            phasesSheet.Cells[row, 4].Value = "Secondary Maps";
            phasesSheet.Cells[row, 5].Value = "Activity Description";
            phasesSheet.Cells[row, 1, row, 5].Style.Font.Bold = true;
            phasesSheet.Cells[row, 1, row, 5].Style.Fill.PatternType = ExcelFillStyle.Solid;
            phasesSheet.Cells[row, 1, row, 5].Style.Fill.BackgroundColor.SetColor(System.Drawing.Color.LightGray);
            row++;
            
            // Fill phase data
            int phaseNum = 1;
            foreach (var phase in phases)
            {
                phasesSheet.Cells[row, 1].Value = $"Phase {phaseNum}";
                phasesSheet.Cells[row, 2].Value = $"{phase.StartId} - {phase.EndId}";
                
                // Determine primary maps (highest activity)
                var sortedMaps = phase.MapActivity
                    .OrderByDescending(m => m.Value)
                    .ToList();
                
                var primaryMaps = sortedMaps
                    .Take(Math.Min(3, sortedMaps.Count))
                    .Where(m => m.Value > 0)
                    .Select(m => m.Key)
                    .ToList();
                
                var secondaryMaps = sortedMaps
                    .Skip(primaryMaps.Count)
                    .Take(Math.Min(5, sortedMaps.Count - primaryMaps.Count))
                    .Where(m => m.Value > 0)
                    .Select(m => m.Key)
                    .ToList();
                
                phasesSheet.Cells[row, 3].Value = string.Join(", ", primaryMaps);
                phasesSheet.Cells[row, 4].Value = string.Join(", ", secondaryMaps);
                
                // Create activity description
                string description = DeterminePhaseDescription(phase, allMaps);
                phasesSheet.Cells[row, 5].Value = description;
                
                // Format cells
                phasesSheet.Cells[row, 1, row, 5].Style.HorizontalAlignment = ExcelHorizontalAlignment.Left;
                phasesSheet.Cells[row, 1, row, 5].Style.VerticalAlignment = ExcelVerticalAlignment.Top;
                phasesSheet.Cells[row, 5].Style.WrapText = true;
                
                row++;
                phaseNum++;
            }
            
            // Format the table
            phasesSheet.Cells.AutoFitColumns();
            phasesSheet.Row(row - 1).Height = 60; // Give more space for the description
            
            return phasesSheet;
        }
        
        /// <summary>
        /// Creates a sheet analyzing cross-map development patterns
        /// </summary>
        private static ExcelWorksheet CreateCrossMapDevelopmentSheet(
            ExcelPackage package,
            List<AdtInfo> adtFiles,
            List<string> allMaps)
        {
            // Create cross-map development worksheet
            var crossMapSheet = package.Workbook.Worksheets.Add("Cross-Map Patterns");
            int row = 1;
            
            // Title
            crossMapSheet.Cells[row, 1].Value = "Cross-Map Development Patterns";
            crossMapSheet.Cells[row, 1].Style.Font.Size = 14;
            crossMapSheet.Cells[row, 1].Style.Font.Bold = true;
            crossMapSheet.Cells[row, 1, row, 5].Merge = true;
            row += 2;
            
            // Calculate sequential vs. parallel development
            // Find maps with overlapping ID ranges
            crossMapSheet.Cells[row, 1].Value = "Map Development Overlaps";
            crossMapSheet.Cells[row, 1].Style.Font.Bold = true;
            row++;
            
            crossMapSheet.Cells[row, 1].Value = "Map A";
            crossMapSheet.Cells[row, 2].Value = "Map B";
            crossMapSheet.Cells[row, 3].Value = "Overlap %";
            crossMapSheet.Cells[row, 4].Value = "Shared ID Range";
            crossMapSheet.Cells[row, 5].Value = "Development Pattern";
            crossMapSheet.Cells[row, 1, row, 5].Style.Font.Bold = true;
            crossMapSheet.Cells[row, 1, row, 5].Style.Fill.PatternType = ExcelFillStyle.Solid;
            crossMapSheet.Cells[row, 1, row, 5].Style.Fill.BackgroundColor.SetColor(System.Drawing.Color.LightGray);
            row++;
            
            // Calculate overlaps between all map pairs
            var overlapData = new List<MapOverlap>();
            
            for (int i = 0; i < allMaps.Count; i++)
            {
                for (int j = i + 1; j < allMaps.Count; j++)
                {
                    var mapA = allMaps[i];
                    var mapB = allMaps[j];
                    
                    // Get ID ranges for each map
                    var mapAIds = adtFiles
                        .Where(a => a.MapName == mapA)
                        .SelectMany(a => a.UniqueIds)
                        .Distinct()
                        .OrderBy(id => id)
                        .ToList();
                        
                    var mapBIds = adtFiles
                        .Where(a => a.MapName == mapB)
                        .SelectMany(a => a.UniqueIds)
                        .Distinct()
                        .OrderBy(id => id)
                        .ToList();
                    
                    if (mapAIds.Count == 0 || mapBIds.Count == 0)
                        continue;
                        
                    // Calculate overlap
                    int overlapCount = 0;
                    int minAId = mapAIds.First();
                    int maxAId = mapAIds.Last();
                    int minBId = mapBIds.First();
                    int maxBId = mapBIds.Last();
                    
                    // Check if ranges overlap
                    if (minAId <= maxBId && minBId <= maxAId)
                    {
                        int overlapStart = Math.Max(minAId, minBId);
                        int overlapEnd = Math.Min(maxAId, maxBId);
                        
                        // Count IDs in both maps that fall in the overlap range
                        var overlapAIds = mapAIds.Count(id => id >= overlapStart && id <= overlapEnd);
                        var overlapBIds = mapBIds.Count(id => id >= overlapStart && id <= overlapEnd);
                        
                        // Calculate overlap percentage (average of both maps)
                        double overlapPercentA = (double)overlapAIds / mapAIds.Count * 100;
                        double overlapPercentB = (double)overlapBIds / mapBIds.Count * 100;
                        double overlapPercent = (overlapPercentA + overlapPercentB) / 2;
                        
                        // Determine development pattern
                        string pattern;
                        if (overlapPercent < 10)
                            pattern = "Sequential";
                        else if (overlapPercent < 40)
                            pattern = "Slight Overlap";
                        else if (overlapPercent < 70)
                            pattern = "Moderate Parallel Development";
                        else
                            pattern = "Strong Parallel Development";
                        
                        // Add to overlap data
                        overlapData.Add(new MapOverlap
                        {
                            MapA = mapA,
                            MapB = mapB,
                            OverlapPercent = overlapPercent,
                            OverlapStart = overlapStart,
                            OverlapEnd = overlapEnd,
                            Pattern = pattern
                        });
                    }
                }
            }
            
            // Write overlap data
            foreach (var overlap in overlapData.OrderByDescending(o => o.OverlapPercent))
            {
                crossMapSheet.Cells[row, 1].Value = overlap.MapA;
                crossMapSheet.Cells[row, 2].Value = overlap.MapB;
                crossMapSheet.Cells[row, 3].Value = overlap.OverlapPercent;
                crossMapSheet.Cells[row, 4].Value = $"{overlap.OverlapStart} - {overlap.OverlapEnd}";
                crossMapSheet.Cells[row, 5].Value = overlap.Pattern;
                
                // Format percentage
                crossMapSheet.Cells[row, 3].Style.Numberformat.Format = "0.0";
                
                // Color based on overlap level
                if (overlap.OverlapPercent > 50)
                {
                    crossMapSheet.Cells[row, 3].Style.Fill.PatternType = ExcelFillStyle.Solid;
                    crossMapSheet.Cells[row, 3].Style.Fill.BackgroundColor.SetColor(Color.LightGreen);
                }
                else if (overlap.OverlapPercent > 20)
                {
                    crossMapSheet.Cells[row, 3].Style.Fill.PatternType = ExcelFillStyle.Solid;
                    crossMapSheet.Cells[row, 3].Style.Fill.BackgroundColor.SetColor(Color.LightYellow);
                }
                
                row++;
            }
            
            // Add section for development sequence
            row += 2;
            crossMapSheet.Cells[row, 1].Value = "Proposed Development Sequence";
            crossMapSheet.Cells[row, 1].Style.Font.Bold = true;
            row++;
            
            crossMapSheet.Cells[row, 1].Value = "Order";
            crossMapSheet.Cells[row, 2].Value = "Map";
            crossMapSheet.Cells[row, 3].Value = "First ID";
            crossMapSheet.Cells[row, 4].Value = "Last ID";
            crossMapSheet.Cells[row, 5].Value = "Notes";
            crossMapSheet.Cells[row, 1, row, 5].Style.Font.Bold = true;
            crossMapSheet.Cells[row, 1, row, 5].Style.Fill.PatternType = ExcelFillStyle.Solid;
            crossMapSheet.Cells[row, 1, row, 5].Style.Fill.BackgroundColor.SetColor(System.Drawing.Color.LightGray);
            row++;
            
            // Create a proposed development sequence based on average uniqueID values
            var sequenceData = allMaps
                .Select(map => {
                    var mapIds = adtFiles
                        .Where(a => a.MapName == map)
                        .SelectMany(a => a.UniqueIds)
                        .Distinct()
                        .ToList();
                        
                    return new {
                        Map = map,
                        FirstId = mapIds.Any() ? mapIds.Min() : 0,
                        LastId = mapIds.Any() ? mapIds.Max() : 0,
                        MedianId = mapIds.Any() ? mapIds.OrderBy(id => id).Skip(mapIds.Count / 2).FirstOrDefault() : 0,
                        IdCount = mapIds.Count
                    };
                })
                .Where(m => m.IdCount > 0)
                .OrderBy(m => m.FirstId)
                .ToList();
                
            int order = 1;
            foreach (var mapData in sequenceData)
            {
                crossMapSheet.Cells[row, 1].Value = order;
                crossMapSheet.Cells[row, 2].Value = mapData.Map;
                crossMapSheet.Cells[row, 3].Value = mapData.FirstId;
                crossMapSheet.Cells[row, 4].Value = mapData.LastId;
                
                // Add notes about parallel development
                var parallelMaps = overlapData
                    .Where(o => (o.MapA == mapData.Map || o.MapB == mapData.Map) && o.OverlapPercent > 30)
                    .Select(o => o.MapA == mapData.Map ? o.MapB : o.MapA)
                    .Take(3)
                    .ToList();
                    
                if (parallelMaps.Any())
                {
                    crossMapSheet.Cells[row, 5].Value = $"Parallel development with: {string.Join(", ", parallelMaps)}";
                }
                
                row++;
                order++;
            }
            
            // Format the table
            crossMapSheet.Cells.AutoFitColumns();
            
            return crossMapSheet;
        }
        
        /// <summary>
        /// Creates a chart showing the flow of uniqueIDs across maps over time
        /// </summary>
        private static void CreateIdFlowChart(
            ExcelPackage package,
            List<TimelineSegment> timelineData,
            List<string> allMaps)
        {
            var chartSheet = package.Workbook.Worksheets.Add("Activity Chart");
            
            // Create a data table for the chart
            int row = 1;
            
            // Header
            chartSheet.Cells[row, 1].Value = "Segment";
            
            int col = 2;
            foreach (var map in allMaps)
            {
                chartSheet.Cells[row, col].Value = map;
                col++;
            }
            
            row++;
            
            // Data
            foreach (var segment in timelineData)
            {
                chartSheet.Cells[row, 1].Value = $"{segment.StartId} - {segment.EndId}";
                
                col = 2;
                foreach (var map in allMaps)
                {
                    chartSheet.Cells[row, col].Value = segment.MapActivity[map];
                    col++;
                }
                
                row++;
            }
            
            // Create a line chart
            var chart = chartSheet.Drawings.AddChart("ID Activity Chart", eChartType.Line);
            chart.SetPosition(row + 2, 0, 0, 0);
            chart.SetSize(800, 400);
            
            // Add a series for each map
            for (int i = 0; i < allMaps.Count; i++)
            {
                var series = chart.Series.Add(chartSheet.Cells[2, i + 2, timelineData.Count + 1, i + 2], 
                                             chartSheet.Cells[2, 1, timelineData.Count + 1, 1]);
                series.Header = allMaps[i];
            }
            
            chart.Title.Text = "Development Activity Across Maps";
            chart.XAxis.Title.Text = "UniqueID Segments";
            chart.YAxis.Title.Text = "Activity Level";
            chart.Legend.Position = eLegendPosition.Bottom;
            
            // Format the table
            chartSheet.Cells.AutoFitColumns();
        }
        
        /// <summary>
        /// Identifies major development phases based on timeline data
        /// </summary>
        private static List<DevelopmentPhase> IdentifyDevelopmentPhases(
            List<TimelineSegment> timelineData,
            List<string> allMaps)
        {
            var phases = new List<DevelopmentPhase>();
            
            // Look for significant changes in activity patterns
            DevelopmentPhase currentPhase = null;
            Dictionary<string, int> previousMapActivity = null;
            
            foreach (var segment in timelineData)
            {
                // Skip segments with very low total activity
                if (segment.TotalActivity < 10)
                    continue;
                    
                // For the first active segment, create initial phase
                if (currentPhase == null)
                {
                    currentPhase = new DevelopmentPhase
                    {
                        StartId = segment.StartId,
                        EndId = segment.EndId,
                        Segments = new List<TimelineSegment> { segment },
                        MapActivity = new Dictionary<string, int>(segment.MapActivity)
                    };
                    
                    previousMapActivity = new Dictionary<string, int>(segment.MapActivity);
                    continue;
                }
                
                // Check if this segment represents a significant change in activity pattern
                bool significantChange = IsSignificantActivityChange(previousMapActivity, segment.MapActivity);
                
                if (significantChange && currentPhase.Segments.Count >= 2)
                {
                    // Finalize current phase
                    currentPhase.EndId = segment.StartId - 1;
                    
                    // Calculate activity totals for the phase
                    foreach (var map in allMaps)
                    {
                        currentPhase.MapActivity[map] = currentPhase.Segments.Sum(s => s.MapActivity[map]);
                    }
                    
                    phases.Add(currentPhase);
                    
                    // Start a new phase
                    currentPhase = new DevelopmentPhase
                    {
                        StartId = segment.StartId,
                        EndId = segment.EndId,
                        Segments = new List<TimelineSegment> { segment },
                        MapActivity = new Dictionary<string, int>(segment.MapActivity)
                    };
                }
                else
                {
                    // Continue current phase
                    currentPhase.EndId = segment.EndId;
                    currentPhase.Segments.Add(segment);
                    
                    // Update map activity
                    foreach (var map in allMaps)
                    {
                        if (!currentPhase.MapActivity.ContainsKey(map))
                        {
                            currentPhase.MapActivity[map] = 0;
                        }
                        
                        currentPhase.MapActivity[map] += segment.MapActivity[map];
                    }
                }
                
                previousMapActivity = new Dictionary<string, int>(segment.MapActivity);
            }
            
            // Add the final phase if it exists and wasn't added yet
            if (currentPhase != null && !phases.Contains(currentPhase))
            {
                // Calculate activity totals for the phase
                foreach (var map in allMaps)
                {
                    currentPhase.MapActivity[map] = currentPhase.Segments.Sum(s => s.MapActivity[map]);
                }
                
                phases.Add(currentPhase);
            }
            
            return phases;
        }
        
        /// <summary>
        /// Determines if there is a significant change in activity patterns between segments
        /// </summary>
        private static bool IsSignificantActivityChange(
            Dictionary<string, int> previous,
            Dictionary<string, int> current)
        {
            if (previous == null || current == null)
                return true;
            
            int changeThreshold = 3; // Number of maps that need to change significantly
            int significantChanges = 0;
            
            foreach (var map in previous.Keys)
            {
                int prevActivity = previous[map];
                int currActivity = current[map];
                
                // Check for significant increase or decrease
                if ((prevActivity > 50 && currActivity < 10) ||     // Major decrease
                    (prevActivity < 10 && currActivity > 50) ||     // Major increase
                    (prevActivity > 0 && currActivity == 0) ||      // Activity stopped
                    (prevActivity == 0 && currActivity > 0))        // Activity started
                {
                    significantChanges++;
                }
            }
            
            return significantChanges >= changeThreshold;
        }
        
        /// <summary>
        /// Creates a descriptive text for a development phase
        /// </summary>
        private static string DeterminePhaseDescription(DevelopmentPhase phase, List<string> allMaps)
        {
            // Get top maps by activity
            var topMaps = phase.MapActivity
                .OrderByDescending(m => m.Value)
                .Where(m => m.Value > 0)
                .Take(3)
                .ToList();
            
            if (topMaps.Count == 0)
                return "No significant development activity.";
            
            // Calculate the focus of this phase
            var totalActivity = phase.MapActivity.Values.Sum();
            
            // Determine if development was focused or distributed
            bool focusedDevelopment = topMaps.First().Value > (totalActivity * 0.6);
            bool highlyDistributed = !topMaps.Any(m => m.Value > (totalActivity * 0.3));
            
            string description;
            
            if (focusedDevelopment)
            {
                description = $"Focused development on {topMaps.First().Key} ({topMaps.First().Value} objects). ";
                
                if (topMaps.Count > 1 && topMaps[1].Value > 0)
                {
                    description += $"Secondary work on {topMaps[1].Key} ({topMaps[1].Value} objects).";
                }
            }
            else if (highlyDistributed)
            {
                description = "Distributed development across multiple maps: " +
                    string.Join(", ", topMaps.Select(m => $"{m.Key} ({m.Value} objects)"));
            }
            else
            {
                description = "Mixed development focus on " +
                    string.Join(" and ", topMaps.Select(m => $"{m.Key} ({m.Value} objects)"));
            }
            
            return description;
        }
    }
    
    /// <summary>
    /// Represents a segment of the development timeline
    /// </summary>
    class TimelineSegment
    {
        public int SegmentIndex { get; set; }
        public int StartId { get; set; }
        public int EndId { get; set; }
        public Dictionary<string, int> MapActivity { get; set; }
        public int TotalActivity { get; set; }
    }
    
    /// <summary>
    /// Represents a major phase in development
    /// </summary>
    class DevelopmentPhase
    {
        public int StartId { get; set; }
        public int EndId { get; set; }
        public List<TimelineSegment> Segments { get; set; }
        public Dictionary<string, int> MapActivity { get; set; } = new Dictionary<string, int>();
    }
    
    /// <summary>
    /// Represents the development overlap between two maps
    /// </summary>
    class MapOverlap
    {
        public string MapA { get; set; }
        public string MapB { get; set; }
        public double OverlapPercent { get; set; }
        public int OverlapStart { get; set; }
        public int OverlapEnd { get; set; }
        public string Pattern { get; set; }
    }
}