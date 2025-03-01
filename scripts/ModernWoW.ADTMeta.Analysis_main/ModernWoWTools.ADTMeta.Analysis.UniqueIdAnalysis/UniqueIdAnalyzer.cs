using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Threading.Tasks;

namespace ModernWoWTools.ADTMeta.Analysis.UniqueIdAnalysis
{
    /// <summary>
    /// Main class for analyzing unique IDs from ADT analysis results.
    /// </summary>
    public class UniqueIdAnalyzer
    {
        private readonly string _resultsDirectory;
        private readonly string _outputDirectory;
        private readonly int _clusterThreshold;
        private readonly int _clusterGapThreshold;
        
        private List<AdtInfo> _adtFiles = new List<AdtInfo>();
        private Dictionary<string, List<UniqueIdCluster>> _mapClusters = new Dictionary<string, List<UniqueIdCluster>>();
        private List<UniqueIdCluster> _globalClusters = new List<UniqueIdCluster>();
        
        /// <summary>
        /// Creates a new instance of the UniqueIdAnalyzer class.
        /// </summary>
        /// <param name="resultsDirectory">Directory containing JSON results from ADT analysis</param>
        /// <param name="outputDirectory">Directory to write analysis results to</param>
        /// <param name="clusterThreshold">Minimum number of IDs to form a cluster</param>
        /// <param name="clusterGapThreshold">Maximum gap between IDs to be considered part of the same cluster</param>
        public UniqueIdAnalyzer(
            string resultsDirectory,
            string outputDirectory,
            int clusterThreshold = 10,
            int clusterGapThreshold = 1000)
        {
            _resultsDirectory = resultsDirectory;
            _outputDirectory = outputDirectory;
            _clusterThreshold = clusterThreshold;
            _clusterGapThreshold = clusterGapThreshold;
            
            // Create output directory if it doesn't exist
            if (!Directory.Exists(_outputDirectory))
            {
                Directory.CreateDirectory(_outputDirectory);
            }
        }

        /// <summary>
        /// Gets the ADT files processed by the analyzer.
        /// </summary>
        /// <returns>The list of processed ADT files.</returns>
        public List<AdtInfo> GetAdtFiles()
        {
            return _adtFiles;
        }

        /// <summary>
        /// Runs the unique ID analysis.
        /// </summary>
        public async Task AnalyzeAsync()
        {
            Console.WriteLine("Starting UniqueID analysis...");
            
            // Load ADT data from JSON files
            await LoadAdtDataAsync();
            
            // Identify clusters per map
            IdentifyMapClusters();
            
            // Identify global clusters across all maps
            IdentifyGlobalClusters();
            
            // Generate reports
            await GenerateTextReportAsync();
            await ReportGenerator.GenerateExcelReportAsync(_adtFiles, _mapClusters, _globalClusters, 
                _clusterGapThreshold, _outputDirectory);
            
            Console.WriteLine("UniqueID analysis complete!");
        }
        
        /// <summary>
        /// Loads ADT data from JSON results files.
        /// </summary>
        private async Task LoadAdtDataAsync()
        {
            Console.WriteLine("Loading ADT data from JSON files...");
            
            // Search for JSON files in the results directory and its subdirectories
            var jsonFiles = Directory.GetFiles(_resultsDirectory, "results.json", SearchOption.AllDirectories);
            
            foreach (var jsonFile in jsonFiles)
            {
                try
                {
                    // Extract map name from directory path
                    var dirName = Path.GetDirectoryName(jsonFile);
                    var mapName = dirName != null ? Path.GetFileName(dirName) : "Unknown";
                    
                    // Load JSON
                    var json = await File.ReadAllTextAsync(jsonFile);
                    var results = JsonSerializer.Deserialize<List<AdtResult>>(json, new JsonSerializerOptions
                    {
                        PropertyNameCaseInsensitive = true
                    });
                    
                    if (results == null)
                        continue;
                    
                    // Process each ADT result
                    foreach (var result in results)
                    {
                        if (result.UniqueIds == null || result.UniqueIds.Count == 0)
                            continue;
                        
                        var adtInfo = new AdtInfo(result.FileName, mapName, result.UniqueIds);
                        
                        // Process model placements and link them to uniqueIDs
                        if (result.ModelPlacements != null)
                        {
                            foreach (var placement in result.ModelPlacements)
                            {
                                string modelPath = placement.Name;
                                
                                // Create asset reference
                                var assetRef = new AssetReference(
                                    modelPath, 
                                    "Model", 
                                    placement.UniqueId, 
                                    result.FileName,
                                    mapName);
                                
                                // Add to the AdtInfo
                                if (!adtInfo.AssetsByUniqueId.TryGetValue(placement.UniqueId, out var assetList))
                                {
                                    assetList = new List<AssetReference>();
                                    adtInfo.AssetsByUniqueId[placement.UniqueId] = assetList;
                                }
                                
                                assetList.Add(assetRef);
                            }
                        }
                        
                        // Process WMO placements and link them to uniqueIDs
                        if (result.WmoPlacements != null)
                        {
                            foreach (var placement in result.WmoPlacements)
                            {
                                string wmoPath = placement.Name;
                                
                                // Create asset reference
                                var assetRef = new AssetReference(
                                    wmoPath, 
                                    "WMO", 
                                    placement.UniqueId, 
                                    result.FileName,
                                    mapName);
                                
                                // Add to the AdtInfo
                                if (!adtInfo.AssetsByUniqueId.TryGetValue(placement.UniqueId, out var assetList))
                                {
                                    assetList = new List<AssetReference>();
                                    adtInfo.AssetsByUniqueId[placement.UniqueId] = assetList;
                                }
                                
                                assetList.Add(assetRef);
                            }
                        }
                        
                        _adtFiles.Add(adtInfo);
                    }
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Error processing {jsonFile}: {ex.Message}");
                }
            }
            
            Console.WriteLine($"Loaded {_adtFiles.Count} ADT files with uniqueIDs.");
        }
        
        /// <summary>
        /// Identifies clusters of unique IDs for each map.
        /// </summary>
        private void IdentifyMapClusters()
        {
            Console.WriteLine("Identifying clusters for each map...");
            
            // Group ADTs by map
            var adtsByMap = _adtFiles.GroupBy(a => a.MapName);
            
            foreach (var mapGroup in adtsByMap)
            {
                var mapName = mapGroup.Key;
                var allIds = new List<int>();
                
                // Collect all unique IDs for this map
                foreach (var adt in mapGroup)
                {
                    allIds.AddRange(adt.UniqueIds);
                }
                
                // Sort IDs
                allIds = allIds.Distinct().OrderBy(id => id).ToList();
                
                // Find clusters
                var clusters = ClusterAnalyzer.FindClusters(allIds, _clusterThreshold, _clusterGapThreshold);
                
                // Associate ADTs and assets with each cluster
                foreach (var cluster in clusters)
                {
                    foreach (var adt in mapGroup)
                    {
                        var idsInCluster = adt.UniqueIds.Where(id => id >= cluster.MinId && id <= cluster.MaxId).ToList();
                        var countInCluster = idsInCluster.Count;
                        
                        if (countInCluster > 0)
                        {
                            // Add ADT file to cluster
                            cluster.AdtFiles.Add(adt.FileName);
                            cluster.IdCountsByAdt[adt.FileName] = countInCluster;
                            
                            // Add assets to cluster
                            foreach (var id in idsInCluster)
                            {
                                if (adt.AssetsByUniqueId.TryGetValue(id, out var assets))
                                {
                                    foreach (var asset in assets)
                                    {
                                        cluster.Assets.Add(asset);
                                    }
                                }
                            }
                        }
                    }
                }
                
                _mapClusters[mapName] = clusters;
                
                Console.WriteLine($"Map '{mapName}': {clusters.Count} clusters found with {clusters.Sum(c => c.Assets.Count)} unique assets");
            }
        }
        
        /// <summary>
        /// Identifies global clusters across all maps.
        /// </summary>
        private void IdentifyGlobalClusters()
        {
            Console.WriteLine("Identifying global clusters across all maps...");
            
            // Collect all unique IDs
            var allIds = _adtFiles
                .SelectMany(adt => adt.UniqueIds)
                .Distinct()
                .OrderBy(id => id)
                .ToList();
            
            // Find clusters
            _globalClusters = ClusterAnalyzer.FindClusters(allIds, _clusterThreshold * 3, _clusterGapThreshold * 2);
            
            // Associate maps, ADTs, and assets with each cluster
            foreach (var cluster in _globalClusters)
            {
                foreach (var adt in _adtFiles)
                {
                    var idsInCluster = adt.UniqueIds.Where(id => id >= cluster.MinId && id <= cluster.MaxId).ToList();
                    var countInCluster = idsInCluster.Count;
                    
                    if (countInCluster > 0)
                    {
                        // Add ADT file to cluster
                        cluster.AdtFiles.Add(adt.FileName);
                        cluster.IdCountsByAdt[adt.FileName] = countInCluster;
                        
                        // Add assets to cluster
                        foreach (var id in idsInCluster)
                        {
                            if (adt.AssetsByUniqueId.TryGetValue(id, out var assets))
                            {
                                foreach (var asset in assets)
                                {
                                    cluster.Assets.Add(asset);
                                }
                            }
                        }
                    }
                }
            }
            
            Console.WriteLine($"Found {_globalClusters.Count} global clusters with {_globalClusters.Sum(c => c.Assets.Count)} unique assets");
        }
        
        /// <summary>
        /// Generates a text report of the analysis.
        /// </summary>
        private async Task GenerateTextReportAsync()
        {
            Console.WriteLine("Generating text report...");
            
            var reportPath = Path.Combine(_outputDirectory, "unique_id_analysis.txt");
            
            using (var writer = new StreamWriter(reportPath))
            {
                await writer.WriteLineAsync($"ADT UniqueID Analysis Report - {DateTime.Now}");
                await writer.WriteLineAsync("=========================================");
                await writer.WriteLineAsync();
                
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
                        
                        // List most common assets (limited to top 20)
                        var topAssets = typeGroup
                            .GroupBy(a => a.AssetPath)
                            .Select(g => new { Path = g.Key, Count = g.Count() })
                            .OrderByDescending(a => a.Count)
                            .Take(20);
                        
                        foreach (var asset in topAssets)
                        {
                            await writer.WriteLineAsync($"    {asset.Path} (used {asset.Count} times)");
                        }
                        
                        // If there are more assets, note how many more
                        if (typeGroup.Count() > 20)
                        {
                            await writer.WriteLineAsync($"    ... and {typeGroup.Count() - 20} more {typeGroup.Key}s");
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
                            
                            // List most common assets (limited to top 10 for map clusters)
                            var topAssets = typeGroup
                                .GroupBy(a => a.AssetPath)
                                .Select(g => new { Path = g.Key, Count = g.Count() })
                                .OrderByDescending(a => a.Count)
                                .Take(10);
                            
                            foreach (var asset in topAssets)
                            {
                                await writer.WriteLineAsync($"    {asset.Path} (used {asset.Count} times)");
                            }
                            
                            // If there are more assets, note how many more
                            if (typeGroup.Count() > 10)
                            {
                                await writer.WriteLineAsync($"    ... and {typeGroup.Count() - 10} more {typeGroup.Key}s");
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
                        var ranges = ClusterAnalyzer.GetIdRanges(adt.UniqueIds, _clusterGapThreshold);
                        
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
                
                Console.WriteLine($"Text report written to {reportPath}");
            }
        }
    }
}