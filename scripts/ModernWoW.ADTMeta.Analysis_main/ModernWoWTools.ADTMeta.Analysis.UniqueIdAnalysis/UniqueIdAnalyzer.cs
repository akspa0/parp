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
        private List<int> _nonClusteredIds = new List<int>();
        private Dictionary<int, List<AssetReference>> _nonClusteredAssets = new Dictionary<int, List<AssetReference>>();
        private bool _generateComprehensiveReport = true;
        
        /// <summary>
        /// Creates a new instance of the UniqueIdAnalyzer class.
        /// </summary>
        /// <param name="resultsDirectory">Directory containing JSON results from ADT analysis</param>
        /// <param name="outputDirectory">Directory to write analysis results to</param>
        /// <param name="clusterThreshold">Minimum number of IDs to form a cluster</param>
        /// <param name="clusterGapThreshold">Maximum gap between IDs to be considered part of the same cluster</param>
        /// <param name="generateComprehensiveReport">Whether to generate a comprehensive report with all assets</param>
        public UniqueIdAnalyzer(
            string resultsDirectory,
            string outputDirectory,
            int clusterThreshold = 10,
            int clusterGapThreshold = 1000,
            bool generateComprehensiveReport = true)
        {
            _resultsDirectory = resultsDirectory;
            _outputDirectory = outputDirectory;
            _clusterThreshold = clusterThreshold;
            _clusterGapThreshold = clusterGapThreshold;
            _generateComprehensiveReport = generateComprehensiveReport;
            
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
        /// <param name="generateComprehensiveReport">Whether to generate a comprehensive report with all assets</param>
        public async Task AnalyzeAsync(bool generateComprehensiveReport = true)
        {
            Console.WriteLine("Starting UniqueID analysis...");
            
            // Load ADT data from JSON files
            await LoadAdtDataAsync();
            
            // Identify clusters per map
            IdentifyMapClusters();
            
            // Identify global clusters across all maps
            IdentifyGlobalClusters();
            
            // Identify non-clustered IDs if generating comprehensive report
            if (generateComprehensiveReport)
            {
                IdentifyNonClusteredIds();
            }
            
            // Generate reports
            // Create and use the text report generator
            var textReportGenerator = new TextReportGenerator(
                _adtFiles, _mapClusters, _globalClusters, _nonClusteredIds, _nonClusteredAssets,
                _outputDirectory, generateComprehensiveReport);
            await textReportGenerator.GenerateAsync();
            
            // Create and use the Excel report generator
            var excelReportGenerator = new ExcelReportGenerator(
                _adtFiles, _mapClusters, _globalClusters, _clusterGapThreshold, _outputDirectory, generateComprehensiveReport);
            await excelReportGenerator.GenerateAsync();
            
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
                                
                                // Extract position data
                                double posX = 0, posY = 0, posZ = 0;
                                if (placement.Position != null)
                                {
                                    placement.Position.TryGetValue("X", out posX);
                                    placement.Position.TryGetValue("Y", out posY);
                                    placement.Position.TryGetValue("Z", out posZ);
                                }
                                
                                // Create asset reference
                                var assetRef = new AssetReference(
                                    modelPath, 
                                    "Model", 
                                    placement.UniqueId, 
                                    result.FileName,
                                    mapName,
                                    posX, posY, posZ,
                                    placement.Scale);
                                
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
                                
                                // Extract position data
                                double posX = 0, posY = 0, posZ = 0;
                                if (placement.Position != null)
                                {
                                    placement.Position.TryGetValue("X", out posX);
                                    placement.Position.TryGetValue("Y", out posY);
                                    placement.Position.TryGetValue("Z", out posZ);
                                }
                                
                                // Create asset reference
                                var assetRef = new AssetReference(
                                    wmoPath, 
                                    "WMO", 
                                    placement.UniqueId, 
                                    result.FileName,
                                    mapName,
                                    posX, posY, posZ);
                                
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
        /// Identifies uniqueIDs that don't belong to any cluster.
        /// </summary>
        private void IdentifyNonClusteredIds()
        {
            Console.WriteLine("Identifying non-clustered uniqueIDs...");
            
            // Get all uniqueIDs
            var allIds = _adtFiles
                .SelectMany(adt => adt.UniqueIds)
                .Distinct()
                .OrderBy(id => id)
                .ToList();
            
            // Get all IDs that are part of global clusters
            var clusteredIds = new HashSet<int>();
            foreach (var cluster in _globalClusters)
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
            _nonClusteredIds = allIds
                .Where(id => !clusteredIds.Contains(id))
                .OrderBy(id => id)
                .ToList();
            
            // Find assets associated with non-clustered IDs
            foreach (var id in _nonClusteredIds)
            {
                var assetsForId = new List<AssetReference>();
                
                foreach (var adt in _adtFiles)
                {
                    if (adt.AssetsByUniqueId.TryGetValue(id, out var assets))
                    {
                        assetsForId.AddRange(assets);
                    }
                }
                
                if (assetsForId.Count > 0)
                {
                    _nonClusteredAssets[id] = assetsForId;
                }
            }
            
            Console.WriteLine($"Found {_nonClusteredIds.Count} non-clustered uniqueIDs with {_nonClusteredAssets.Values.Sum(a => a.Count)} assets");
        }
    }
}