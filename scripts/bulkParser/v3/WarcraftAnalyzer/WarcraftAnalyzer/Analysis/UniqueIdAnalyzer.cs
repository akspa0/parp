using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using WarcraftAnalyzer.Files.ADT;

namespace WarcraftAnalyzer.Analysis
{
    /// <summary>
    /// Analyzes unique IDs from ADT files to identify patterns and clusters.
    /// </summary>
    public class UniqueIdAnalyzer
    {
        private readonly string _outputDirectory;
        private readonly int _clusterThreshold;
        private readonly int _gapThreshold;
        private readonly Dictionary<string, List<ADTFile>> _adtFilesByMap = new Dictionary<string, List<ADTFile>>();
        private readonly Dictionary<int, List<UniqueIdReference>> _uniqueIdReferences = new Dictionary<int, List<UniqueIdReference>>();

        /// <summary>
        /// Initializes a new instance of the <see cref="UniqueIdAnalyzer"/> class.
        /// </summary>
        /// <param name="outputDirectory">The directory to write analysis results to.</param>
        /// <param name="clusterThreshold">The minimum number of IDs to form a cluster.</param>
        /// <param name="gapThreshold">The maximum gap between IDs to be considered part of the same cluster.</param>
        public UniqueIdAnalyzer(string outputDirectory, int clusterThreshold = 10, int gapThreshold = 1000)
        {
            _outputDirectory = outputDirectory;
            _clusterThreshold = clusterThreshold;
            _gapThreshold = gapThreshold;
        }

        /// <summary>
        /// Adds an ADT file to the analyzer.
        /// </summary>
        /// <param name="adtFile">The ADT file to add.</param>
        /// <param name="mapName">The name of the map the ADT file belongs to.</param>
        public void AddAdtFile(ADTFile adtFile, string mapName)
        {
            if (!_adtFilesByMap.TryGetValue(mapName, out var adtFiles))
            {
                adtFiles = new List<ADTFile>();
                _adtFilesByMap[mapName] = adtFiles;
            }

            adtFiles.Add(adtFile);

            // Process unique IDs from the ADT file
            foreach (var uniqueId in adtFile.UniqueIds)
            {
                if (!_uniqueIdReferences.TryGetValue(uniqueId, out var references))
                {
                    references = new List<UniqueIdReference>();
                    _uniqueIdReferences[uniqueId] = references;
                }

                // Find model or WMO placement with this unique ID
                string assetPath = null;
                string type = null;

                // Check model placements
                var modelPlacement = adtFile.ModelPlacements.FirstOrDefault(p => p.UniqueId == uniqueId);
                if (modelPlacement != null)
                {
                    assetPath = modelPlacement.ModelReference?.Path;
                    type = "Model";
                }
                else
                {
                    // Check WMO placements
                    var wmoPlacement = adtFile.WmoPlacements.FirstOrDefault(p => p.UniqueId == uniqueId);
                    if (wmoPlacement != null)
                    {
                        assetPath = wmoPlacement.WmoReference?.Path;
                        type = "WMO";
                    }
                }

                references.Add(new UniqueIdReference
                {
                    Id = uniqueId,
                    MapName = mapName,
                    AdtFile = adtFile,
                    X = adtFile.XCoord,
                    Y = adtFile.YCoord,
                    Type = type,
                    AssetPath = assetPath
                });
            }
        }

        /// <summary>
        /// Gets the ADT files that have been added to the analyzer.
        /// </summary>
        /// <returns>A dictionary of ADT files by map name.</returns>
        public Dictionary<string, List<ADTFile>> GetAdtFiles()
        {
            return _adtFilesByMap;
        }

        /// <summary>
        /// Runs the analysis and generates reports.
        /// </summary>
        /// <param name="generateComprehensiveReport">Whether to generate a comprehensive report with all assets.</param>
        /// <returns>A task representing the asynchronous operation.</returns>
        public async Task AnalyzeAsync(bool generateComprehensiveReport = true)
        {
            Console.WriteLine("Starting unique ID analysis...");
            Console.WriteLine($"Found {_uniqueIdReferences.Count} unique IDs across {_adtFilesByMap.Count} maps.");

            // Create output directory if it doesn't exist
            Directory.CreateDirectory(_outputDirectory);

            // Generate summary report
            await GenerateSummaryReportAsync();

            // Generate map reports
            await GenerateMapReportsAsync();

            // Generate cluster report
            await GenerateClusterReportAsync();

            // Generate comprehensive report if requested
            if (generateComprehensiveReport)
            {
                await GenerateComprehensiveReportAsync();
            }

            Console.WriteLine("Analysis complete.");
        }

        /// <summary>
        /// Generates a summary report with basic statistics.
        /// </summary>
        /// <returns>A task representing the asynchronous operation.</returns>
        private async Task GenerateSummaryReportAsync()
        {
            Console.WriteLine("Generating summary report...");

            var sb = new StringBuilder();
            sb.AppendLine("# Unique ID Analysis Summary");
            sb.AppendLine();
            sb.AppendLine($"Analysis Date: {DateTime.Now}");
            sb.AppendLine($"Cluster Threshold: {_clusterThreshold}");
            sb.AppendLine($"Gap Threshold: {_gapThreshold}");
            sb.AppendLine();

            sb.AppendLine("## Maps");
            sb.AppendLine();
            sb.AppendLine("| Map | ADT Files | Unique IDs |");
            sb.AppendLine("|-----|-----------|-----------|");

            var mapStats = new Dictionary<string, (int AdtCount, int UniqueIdCount)>();
            foreach (var map in _adtFilesByMap)
            {
                var uniqueIdCount = map.Value.Sum(adt => adt.UniqueIds.Count);
                mapStats[map.Key] = (map.Value.Count, uniqueIdCount);
                sb.AppendLine($"| {map.Key} | {map.Value.Count} | {uniqueIdCount} |");
            }

            sb.AppendLine();
            sb.AppendLine("## Unique ID Statistics");
            sb.AppendLine();
            sb.AppendLine($"Total Unique IDs: {_uniqueIdReferences.Count}");
            sb.AppendLine($"Total References: {_uniqueIdReferences.Values.Sum(refs => refs.Count)}");
            sb.AppendLine();

            // ID range statistics
            var ids = _uniqueIdReferences.Keys.OrderBy(id => id).ToList();
            if (ids.Count > 0)
            {
                sb.AppendLine($"Minimum ID: {ids.First()}");
                sb.AppendLine($"Maximum ID: {ids.Last()}");
                sb.AppendLine($"Range: {ids.Last() - ids.First()}");
                sb.AppendLine();
            }

            // Write the report
            var reportPath = Path.Combine(_outputDirectory, "summary.md");
            await File.WriteAllTextAsync(reportPath, sb.ToString());

            Console.WriteLine($"Summary report written to {reportPath}");
        }

        /// <summary>
        /// Generates reports for each map.
        /// </summary>
        /// <returns>A task representing the asynchronous operation.</returns>
        private async Task GenerateMapReportsAsync()
        {
            Console.WriteLine("Generating map reports...");

            var mapsDir = Path.Combine(_outputDirectory, "maps");
            Directory.CreateDirectory(mapsDir);

            foreach (var map in _adtFilesByMap)
            {
                var sb = new StringBuilder();
                sb.AppendLine($"# {map.Key} Unique ID Analysis");
                sb.AppendLine();
                sb.AppendLine($"ADT Files: {map.Value.Count}");
                sb.AppendLine();

                // Group unique IDs by type
                var uniqueIdsByType = new Dictionary<string, List<int>>();
                foreach (var adt in map.Value)
                {
                    foreach (var uniqueId in adt.UniqueIds)
                    {
                        // Find the type for this unique ID
                        string type = "Unknown";
                        
                        // Check model placements
                        var modelPlacement = adt.ModelPlacements.FirstOrDefault(p => p.UniqueId == uniqueId);
                        if (modelPlacement != null)
                        {
                            type = "Model";
                        }
                        else
                        {
                            // Check WMO placements
                            var wmoPlacement = adt.WmoPlacements.FirstOrDefault(p => p.UniqueId == uniqueId);
                            if (wmoPlacement != null)
                            {
                                type = "WMO";
                            }
                        }

                        if (!uniqueIdsByType.TryGetValue(type, out var ids))
                        {
                            ids = new List<int>();
                            uniqueIdsByType[type] = ids;
                        }

                        if (!ids.Contains(uniqueId))
                        {
                            ids.Add(uniqueId);
                        }
                    }
                }

                // Write unique IDs by type
                sb.AppendLine("## Unique IDs by Type");
                sb.AppendLine();
                sb.AppendLine("| Type | Count |");
                sb.AppendLine("|------|-------|");
                foreach (var type in uniqueIdsByType.OrderByDescending(t => t.Value.Count))
                {
                    sb.AppendLine($"| {type.Key} | {type.Value.Count} |");
                }
                sb.AppendLine();

                // Write the report
                var reportPath = Path.Combine(mapsDir, $"{map.Key}.md");
                await File.WriteAllTextAsync(reportPath, sb.ToString());

                Console.WriteLine($"Map report written to {reportPath}");
            }
        }

        /// <summary>
        /// Generates a report of ID clusters.
        /// </summary>
        /// <returns>A task representing the asynchronous operation.</returns>
        private async Task GenerateClusterReportAsync()
        {
            Console.WriteLine("Generating cluster report...");

            var sb = new StringBuilder();
            sb.AppendLine("# Unique ID Clusters");
            sb.AppendLine();
            sb.AppendLine($"Cluster Threshold: {_clusterThreshold}");
            sb.AppendLine($"Gap Threshold: {_gapThreshold}");
            sb.AppendLine();

            // Find clusters
            var clusters = FindClusters();
            sb.AppendLine($"Found {clusters.Count} clusters.");
            sb.AppendLine();

            // Write clusters
            foreach (var cluster in clusters)
            {
                sb.AppendLine($"## Cluster {cluster.StartId} - {cluster.EndId}");
                sb.AppendLine();
                sb.AppendLine($"Range: {cluster.StartId} - {cluster.EndId}");
                sb.AppendLine($"Count: {cluster.Count}");
                sb.AppendLine($"Density: {cluster.Density:F2}%");
                sb.AppendLine();

                // Write cluster IDs
                sb.AppendLine("### IDs");
                sb.AppendLine();
                sb.AppendLine("| ID | References | Maps | Types |");
                sb.AppendLine("|----|-----------:|------|-------|");

                foreach (var id in cluster.Ids.OrderBy(id => id))
                {
                    if (_uniqueIdReferences.TryGetValue(id, out var references))
                    {
                        var maps = references.Select(r => r.MapName).Distinct().OrderBy(m => m);
                        var types = references.Select(r => r.Type).Where(t => t != null).Distinct().OrderBy(t => t);
                        sb.AppendLine($"| {id} | {references.Count} | {string.Join(", ", maps)} | {string.Join(", ", types)} |");
                    }
                }
                sb.AppendLine();
            }

            // Write the report
            var reportPath = Path.Combine(_outputDirectory, "clusters.md");
            await File.WriteAllTextAsync(reportPath, sb.ToString());

            Console.WriteLine($"Cluster report written to {reportPath}");
        }

        /// <summary>
        /// Generates a comprehensive report with all unique IDs and their references.
        /// </summary>
        /// <returns>A task representing the asynchronous operation.</returns>
        private async Task GenerateComprehensiveReportAsync()
        {
            Console.WriteLine("Generating comprehensive report...");

            var sb = new StringBuilder();
            sb.AppendLine("# Comprehensive Unique ID Report");
            sb.AppendLine();
            sb.AppendLine($"Total Unique IDs: {_uniqueIdReferences.Count}");
            sb.AppendLine($"Total References: {_uniqueIdReferences.Values.Sum(refs => refs.Count)}");
            sb.AppendLine();

            // Write all unique IDs
            sb.AppendLine("## All Unique IDs");
            sb.AppendLine();
            sb.AppendLine("| ID | References | Maps | Types | Assets |");
            sb.AppendLine("|----|-----------:|------|-------|--------|");

            foreach (var id in _uniqueIdReferences.Keys.OrderBy(id => id))
            {
                var references = _uniqueIdReferences[id];
                var maps = references.Select(r => r.MapName).Distinct().OrderBy(m => m);
                var types = references.Select(r => r.Type).Where(t => t != null).Distinct().OrderBy(t => t);
                var assets = references.Select(r => r.AssetPath).Where(a => a != null).Distinct().OrderBy(a => a);
                sb.AppendLine($"| {id} | {references.Count} | {string.Join(", ", maps)} | {string.Join(", ", types)} | {string.Join(", ", assets)} |");
            }
            sb.AppendLine();

            // Write the report
            var reportPath = Path.Combine(_outputDirectory, "comprehensive.md");
            await File.WriteAllTextAsync(reportPath, sb.ToString());

            Console.WriteLine($"Comprehensive report written to {reportPath}");
        }

        /// <summary>
        /// Finds clusters of unique IDs.
        /// </summary>
        /// <returns>A list of clusters.</returns>
        private List<Cluster> FindClusters()
        {
            var clusters = new List<Cluster>();
            var ids = _uniqueIdReferences.Keys.OrderBy(id => id).ToList();

            if (ids.Count == 0)
            {
                return clusters;
            }

            var currentCluster = new Cluster { StartId = ids[0], EndId = ids[0], Ids = new List<int> { ids[0] } };
            
            for (int i = 1; i < ids.Count; i++)
            {
                var id = ids[i];
                var previousId = ids[i - 1];
                
                if (id - previousId <= _gapThreshold)
                {
                    // Add to current cluster
                    currentCluster.EndId = id;
                    currentCluster.Ids.Add(id);
                }
                else
                {
                    // Check if current cluster meets threshold
                    if (currentCluster.Ids.Count >= _clusterThreshold)
                    {
                        clusters.Add(currentCluster);
                    }
                    
                    // Start a new cluster
                    currentCluster = new Cluster { StartId = id, EndId = id, Ids = new List<int> { id } };
                }
            }
            
            // Check if the last cluster meets threshold
            if (currentCluster.Ids.Count >= _clusterThreshold)
            {
                clusters.Add(currentCluster);
            }
            
            return clusters;
        }

        /// <summary>
        /// Represents a reference to a unique ID in an ADT file.
        /// </summary>
        private class UniqueIdReference
        {
            public int Id { get; set; }
            public string MapName { get; set; }
            public ADTFile AdtFile { get; set; }
            public int X { get; set; }
            public int Y { get; set; }
            public string Type { get; set; }
            public string AssetPath { get; set; }
        }

        /// <summary>
        /// Represents a cluster of unique IDs.
        /// </summary>
        private class Cluster
        {
            public int StartId { get; set; }
            public int EndId { get; set; }
            public List<int> Ids { get; set; }
            public int Count => Ids.Count;
            public double Density => (double)Count / (EndId - StartId + 1) * 100;
        }
    }
}