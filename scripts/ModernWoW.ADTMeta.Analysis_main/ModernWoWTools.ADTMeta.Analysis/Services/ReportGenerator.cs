using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using ModernWoWTools.ADTMeta.Analysis.Models;
using ModernWoWTools.ADTMeta.Analysis.Utilities;

namespace ModernWoWTools.ADTMeta.Analysis.Services
{
    /// <summary>
    /// Service for generating reports from ADT analysis results.
    /// </summary>
    public class ReportGenerator
    {
        private readonly ILoggingService _logger;
        private readonly TerrainDataCsvGenerator _terrainDataCsvGenerator;

        /// <summary>
        /// Creates a new instance of the ReportGenerator class.
        /// </summary>
        /// <param name="logger">The logging service to use.</param>
        public ReportGenerator(ILoggingService logger) 
        {
            _logger = logger ?? throw new ArgumentNullException(nameof(logger));
            _terrainDataCsvGenerator = new TerrainDataCsvGenerator(logger);
        }

        /// <summary>
        /// Generates all reports for the analysis results.
        /// </summary>
        /// <param name="results">The ADT analysis results.</param>
        /// <param name="summary">The analysis summary.</param>
        /// <param name="outputDirectory">The directory to write reports to.</param>
        /// <returns>A task representing the asynchronous operation.</returns>
        public async Task GenerateAllReportsAsync(List<AdtAnalysisResult> results, AnalysisSummary summary, string outputDirectory)
        {
            if (results == null)
                throw new ArgumentNullException(nameof(results));
            if (summary == null)
                throw new ArgumentNullException(nameof(summary));
            if (string.IsNullOrEmpty(outputDirectory))
                throw new ArgumentException("Output directory cannot be null or empty.", nameof(outputDirectory));

            // Create output directory if it doesn't exist
            if (!Directory.Exists(outputDirectory))
            {
                Directory.CreateDirectory(outputDirectory);
            }

            _logger.LogInfo($"Generating reports in {outputDirectory}...");

            // Generate reports
            await GenerateModelsReportAsync(results, outputDirectory);
            await GenerateTexturesReportAsync(results, outputDirectory);
            await GenerateMissingReferencesReportAsync(summary, outputDirectory);
            await GenerateDuplicateIdsReportAsync(summary, outputDirectory);
            await GenerateAreaIdsReportAsync(summary, outputDirectory);
            await GenerateSummaryReportAsync(summary, outputDirectory);
            await GenerateUidIniFileAsync(summary, outputDirectory);
            await GenerateJsonReportsAsync(results, summary, outputDirectory);
            await _terrainDataCsvGenerator.GenerateAllCsvReportsAsync(results, outputDirectory);
            await GenerateTerrainDataReportsAsync(results, outputDirectory);

            _logger.LogInfo("Report generation complete.");
        }

        /// <summary>
        /// Generates a report of all models found in the ADT files.
        /// </summary>
        /// <param name="results">The ADT analysis results.</param>
        /// <param name="outputDirectory">The directory to write the report to.</param>
        /// <returns>A task representing the asynchronous operation.</returns>
        private async Task GenerateModelsReportAsync(List<AdtAnalysisResult> results, string outputDirectory)
        {
            var filePath = Path.Combine(outputDirectory, "models.csv");
            _logger.LogDebug($"Generating models report: {filePath}");

            using (var writer = new StreamWriter(filePath, false, Encoding.UTF8))
            {
                await writer.WriteLineAsync("ADTFile,ModelType,ModelPath,IsValid,ExistsInListfile,RepairedPath");

                foreach (var result in results)
                {
                    foreach (var model in result.ModelReferences)
                    {
                        await writer.WriteLineAsync(
                            $"\"{result.FileName}\",\"M2\",\"{model.OriginalPath}\",{model.IsValid},{model.ExistsInListfile},\"{model.RepairedPath ?? string.Empty}\"");
                    }

                    foreach (var wmo in result.WmoReferences)
                    {
                        await writer.WriteLineAsync(
                            $"\"{result.FileName}\",\"WMO\",\"{wmo.OriginalPath}\",{wmo.IsValid},{wmo.ExistsInListfile},\"{wmo.RepairedPath ?? string.Empty}\"");
                    }
                }
            }
        }

        /// <summary>
        /// Generates a report of all textures found in the ADT files.
        /// </summary>
        /// <param name="results">The ADT analysis results.</param>
        /// <param name="outputDirectory">The directory to write the report to.</param>
        /// <returns>A task representing the asynchronous operation.</returns>
        private async Task GenerateTexturesReportAsync(List<AdtAnalysisResult> results, string outputDirectory)
        {
            var filePath = Path.Combine(outputDirectory, "textures.csv");
            _logger.LogDebug($"Generating textures report: {filePath}");

            using (var writer = new StreamWriter(filePath, false, Encoding.UTF8))
            {
                await writer.WriteLineAsync("ADTFile,TexturePath,IsValid,ExistsInListfile,RepairedPath");

                foreach (var result in results)
                {
                    foreach (var texture in result.TextureReferences)
                    {
                        await writer.WriteLineAsync(
                            $"\"{result.FileName}\",\"{texture.OriginalPath}\",{texture.IsValid},{texture.ExistsInListfile},\"{texture.RepairedPath ?? string.Empty}\"");
                    }
                }
            }
        }

        /// <summary>
        /// Generates a report of all missing references found in the ADT files.
        /// </summary>
        /// <param name="summary">The analysis summary.</param>
        /// <param name="outputDirectory">The directory to write the report to.</param>
        /// <returns>A task representing the asynchronous operation.</returns>
        private async Task GenerateMissingReferencesReportAsync(AnalysisSummary summary, string outputDirectory)
        {
            if (summary.MissingReferenceMap.Count == 0)
            {
                _logger.LogDebug("No missing references found, skipping report.");
                return;
            }

            var filePath = Path.Combine(outputDirectory, $"missing_files_{DateTime.Now:yyyyMMdd_HHmmss}.txt");
            _logger.LogDebug($"Generating missing references report: {filePath}");

            using (var writer = new StreamWriter(filePath, false, Encoding.UTF8))
            {
                await writer.WriteLineAsync($"# Missing files report - {DateTime.Now:yyyy-MM-dd HH:mm:ss}");
                await writer.WriteLineAsync($"# Total missing files: {summary.MissingReferenceMap.Count}");
                await writer.WriteLineAsync();

                foreach (var missing in summary.MissingReferenceMap.OrderBy(m => m.Key))
                {
                    await writer.WriteLineAsync($"Missing file: {missing.Key}");
                    await writer.WriteLineAsync($"Referenced by: {string.Join(", ", missing.Value)}");
                    await writer.WriteLineAsync();
                }
            }
        }

        /// <summary>
        /// Generates a report of all duplicate unique IDs found in the ADT files.
        /// </summary>
        /// <param name="summary">The analysis summary.</param>
        /// <param name="outputDirectory">The directory to write the report to.</param>
        /// <returns>A task representing the asynchronous operation.</returns>
        private async Task GenerateDuplicateIdsReportAsync(AnalysisSummary summary, string outputDirectory)
        {
            if (summary.DuplicateIdSet.Count == 0)
            {
                _logger.LogDebug("No duplicate IDs found, skipping report.");
                return;
            }

            var filePath = Path.Combine(outputDirectory, $"duplicate_ids_{DateTime.Now:yyyyMMdd_HHmmss}.txt");
            _logger.LogDebug($"Generating duplicate IDs report: {filePath}");

            using (var writer = new StreamWriter(filePath, false, Encoding.UTF8))
            {
                await writer.WriteLineAsync($"# Duplicate unique IDs report - {DateTime.Now:yyyy-MM-dd HH:mm:ss}");
                await writer.WriteLineAsync($"# Total duplicate IDs: {summary.DuplicateIdSet.Count}");
                await writer.WriteLineAsync();

                foreach (var id in summary.DuplicateIdSet.OrderBy(id => id))
                {
                    await writer.WriteLineAsync($"Duplicate ID: {id}");

                    if (summary.DuplicateIdMap.TryGetValue(id, out var files))
                    {
                        await writer.WriteLineAsync($"Found in: {string.Join(", ", files)}");
                    }

                    await writer.WriteLineAsync();
        /// <summary>
        /// Generates a report of all area IDs found in the ADT files.
        /// </summary>
        /// <param name="summary">The analysis summary.</param>
        /// <param name="outputDirectory">The directory to write the report to.</param>
        /// <returns>A task representing the asynchronous operation.</returns>
        private async Task GenerateAreaIdsReportAsync(AnalysisSummary summary, string outputDirectory)
        {
            if (summary.AreaIdMap.Count == 0)
            {
                _logger.LogDebug("No area IDs found, skipping report.");
                return;
            }

            var filePath = Path.Combine(outputDirectory, $"area_ids_{DateTime.Now:yyyyMMdd_HHmmss}.txt");
            _logger.LogDebug($"Generating area IDs report: {filePath}");

            using (var writer = new StreamWriter(filePath, false, Encoding.UTF8))
            {
                await writer.WriteLineAsync($"# Area IDs report - {DateTime.Now:yyyy-MM-dd HH:mm:ss}");
                await writer.WriteLineAsync($"# Total unique area IDs: {summary.AreaIdMap.Count}");
                await writer.WriteLineAsync();

                foreach (var areaId in summary.AreaIdMap.OrderBy(a => a.Key))
                {
                    await writer.WriteLineAsync($"Area ID: {areaId.Key}");
                    await writer.WriteLineAsync($"Found in: {string.Join(", ", areaId.Value)}");
                    await writer.WriteLineAsync();
                }
            }
        }


                }
            }
        }

        /// <summary>
        /// Generates a summary report of the analysis.
        /// </summary>
        /// <param name="summary">The analysis summary.</param>
        /// <param name="outputDirectory">The directory to write the report to.</param>
        /// <returns>A task representing the asynchronous operation.</returns>
        private async Task GenerateSummaryReportAsync(AnalysisSummary summary, string outputDirectory)
        {
            var filePath = Path.Combine(outputDirectory, "summary.txt");
            _logger.LogDebug($"Generating summary report: {filePath}");

            using (var writer = new StreamWriter(filePath, false, Encoding.UTF8))
            {
                await writer.WriteLineAsync($"# ADT Analysis Summary - {DateTime.Now:yyyy-MM-dd HH:mm:ss}");
                await writer.WriteLineAsync();
                await writer.WriteLineAsync($"Start time: {summary.StartTime:yyyy-MM-dd HH:mm:ss}");
                await writer.WriteLineAsync($"End time: {summary.EndTime:yyyy-MM-dd HH:mm:ss}");
                await writer.WriteLineAsync($"Duration: {summary.Duration.TotalSeconds:F2} seconds");
                await writer.WriteLineAsync();
                await writer.WriteLineAsync($"Total files: {summary.TotalFiles}");
                await writer.WriteLineAsync($"Processed files: {summary.ProcessedFiles}");
                await writer.WriteLineAsync($"Failed files: {summary.FailedFiles}");
                await writer.WriteLineAsync();
                await writer.WriteLineAsync($"Total texture references: {summary.TotalTextureReferences}");
                await writer.WriteLineAsync($"Total model references: {summary.TotalModelReferences}");
                await writer.WriteLineAsync($"Total WMO references: {summary.TotalWmoReferences}");
                await writer.WriteLineAsync($"Total model placements: {summary.TotalModelPlacements}");
                await writer.WriteLineAsync($"Total WMO placements: {summary.TotalWmoPlacements}");
                await writer.WriteLineAsync($"Total terrain chunks: {summary.TotalTerrainChunks}");
                await writer.WriteLineAsync($"Total texture layers: {summary.TotalTextureLayers}");
                await writer.WriteLineAsync($"Total doodad references: {summary.TotalDoodadReferences}");
                await writer.WriteLineAsync();
                await writer.WriteLineAsync($"Missing references: {summary.MissingReferences}");
                await writer.WriteLineAsync($"Files not in listfile: {summary.FilesNotInListfile}");
                await writer.WriteLineAsync($"Duplicate IDs: {summary.DuplicateIds}");
                await writer.WriteLineAsync($"Maximum unique ID: {summary.MaxUniqueId}");
                await writer.WriteLineAsync($"Parsing errors: {summary.ParsingErrors}");
                await writer.WriteLineAsync();
                await writer.WriteLineAsync($"Unique area IDs: {summary.AreaIdMap.Count}");
            }
        }

        /// <summary>
        /// Generates a uid.ini file with the maximum unique ID.
        /// </summary>
        /// <param name="summary">The analysis summary.</param>
        /// <param name="outputDirectory">The directory to write the file to.</param>
        /// <returns>A task representing the asynchronous operation.</returns>
        private async Task GenerateUidIniFileAsync(AnalysisSummary summary, string outputDirectory)
            // Generate area IDs JSON
            await GenerateAreaIdsJsonAsync(summary, jsonDirectory);


        {
            var filePath = Path.Combine(outputDirectory, "uid.ini");
            _logger.LogDebug($"Generating uid.ini file: {filePath}");

            await File.WriteAllTextAsync(filePath, $"max_unique_id={summary.MaxUniqueId}\n");
        }

        /// <summary>
        /// Generates JSON reports for the analysis results.
        /// </summary>
        /// <param name="results">The ADT analysis results.</param>
        /// <param name="summary">The analysis summary.</param>
        /// <param name="outputDirectory">The directory to write the reports to.</param>
        /// <returns>A task representing the asynchronous operation.</returns>
        private async Task GenerateJsonReportsAsync(List<AdtAnalysisResult> results, AnalysisSummary summary, string outputDirectory)
        {
            _logger.LogDebug("Generating JSON reports...");

            // Create a JSON directory
            var jsonDirectory = Path.Combine(outputDirectory, "json");
            if (!Directory.Exists(jsonDirectory))
            {
                Directory.CreateDirectory(jsonDirectory);
            }

            // Generate summary JSON
            await GenerateSummaryJsonAsync(summary, jsonDirectory);

            // Generate results JSON
            await GenerateResultsJsonAsync(results, jsonDirectory);

            // Generate missing references JSON
            await GenerateMissingReferencesJsonAsync(summary, jsonDirectory);

            // Generate files not in listfile JSON
            await GenerateFilesNotInListfileJsonAsync(summary, jsonDirectory);

            // Generate duplicate IDs JSON
            await GenerateDuplicateIdsJsonAsync(summary, jsonDirectory);

            // Generate terrain data JSON
            await GenerateTerrainDataJsonAsync(results, jsonDirectory);

            _logger.LogDebug("JSON report generation complete.");
        }

        /// <summary>
        /// Generates a JSON file containing the analysis summary.
        /// </summary>
        /// <param name="summary">The analysis summary.</param>
        /// <param name="outputDirectory">The directory to write the file to.</param>
        /// <returns>A task representing the asynchronous operation.</returns>
        private async Task GenerateSummaryJsonAsync(AnalysisSummary summary, string outputDirectory)
        {
            var filePath = Path.Combine(outputDirectory, "summary.json");
            _logger.LogDebug($"Generating summary JSON: {filePath}");

            // Create a simplified summary object for JSON serialization
            var summaryJson = new
            {
                StartTime = summary.StartTime,
                EndTime = summary.EndTime,
                Duration = summary.Duration.TotalSeconds,
                TotalFiles = summary.TotalFiles,
                ProcessedFiles = summary.ProcessedFiles,
                FailedFiles = summary.FailedFiles,
                TotalTextureReferences = summary.TotalTextureReferences,
                TotalModelReferences = summary.TotalModelReferences,
                TotalWmoReferences = summary.TotalWmoReferences,
                TotalModelPlacements = summary.TotalModelPlacements,
                TotalWmoPlacements = summary.TotalWmoPlacements,
                TotalTerrainChunks = summary.TotalTerrainChunks,
                TotalTextureLayers = summary.TotalTextureLayers,
                TotalDoodadReferences = summary.TotalDoodadReferences,
                MissingReferences = summary.MissingReferences,
                FilesNotInListfile = summary.FilesNotInListfile,
                DuplicateIds = summary.DuplicateIds,
                MaxUniqueId = summary.MaxUniqueId,
                ParsingErrors = summary.ParsingErrors,
                UniqueAreaIds = summary.AreaIdMap.Count
            };

            var options = new JsonSerializerOptions { WriteIndented = true };
            var json = JsonSerializer.Serialize(summaryJson, options);
            await File.WriteAllTextAsync(filePath, json);
        }

        /// <summary>
        /// Generates a JSON file containing the files not in the listfile.
        /// </summary>
        /// <param name="summary">The analysis summary.</param>
        /// <param name="outputDirectory">The directory to write the file to.</param>
        /// <returns>A task representing the asynchronous operation.</returns>
        private async Task GenerateFilesNotInListfileJsonAsync(AnalysisSummary summary, string outputDirectory)
        {
            var filePath = Path.Combine(outputDirectory, "files_not_in_listfile.json");
            _logger.LogDebug($"Generating files not in listfile JSON: {filePath}");

            // Create a simplified files not in listfile object for JSON serialization
            var filesNotInListfileJson = summary.FilesNotInListfileMap.Select(m => new
            {
                Path = m.Key,
                ReferencedBy = m.Value.ToList()
            }).ToList();

            var options = new JsonSerializerOptions { WriteIndented = true };
            var json = JsonSerializer.Serialize(filesNotInListfileJson, options);
            await File.WriteAllTextAsync(filePath, json);
        }

        /// <summary>
        /// Generates a JSON file containing the analysis results.
        /// </summary>
        /// <param name="results">The ADT analysis results.</param>
        /// <param name="outputDirectory">The directory to write the file to.</param>
        /// <returns>A task representing the asynchronous operation.</returns>
        private async Task GenerateResultsJsonAsync(List<AdtAnalysisResult> results, string outputDirectory)
        {
            var filePath = Path.Combine(outputDirectory, "results.json");
            _logger.LogDebug($"Generating results JSON: {filePath}");

            // Create a simplified results object for JSON serialization
            var resultsJson = results.Select(r => new
            {
                FileName = r.FileName,
                FilePath = r.FilePath,
                XCoord = r.XCoord,
                YCoord = r.YCoord,
                AdtVersion = r.AdtVersion,
                TextureReferences = r.TextureReferences.Select(t => new
                {
                    OriginalPath = t.OriginalPath,
                    NormalizedPath = t.NormalizedPath,
                    ExistsInListfile = t.ExistsInListfile,
                    IsValid = t.IsValid,
                    RepairedPath = t.RepairedPath
                }).ToList(),
                ModelReferences = r.ModelReferences.Select(m => new
                {
                    OriginalPath = m.OriginalPath,
                    NormalizedPath = m.NormalizedPath,
                    ExistsInListfile = m.ExistsInListfile,
                    IsValid = m.IsValid,
                    RepairedPath = m.RepairedPath
                }).ToList(),
                WmoReferences = r.WmoReferences.Select(w => new
                {
                    OriginalPath = w.OriginalPath,
                    NormalizedPath = w.NormalizedPath,
                    ExistsInListfile = w.ExistsInListfile,
                    IsValid = w.IsValid,
                    RepairedPath = w.RepairedPath
                }).ToList(),
                ModelPlacements = r.ModelPlacements.Select(p => new
                {
                    UniqueId = p.UniqueId,
                    NameId = p.NameId,
                    Name = p.Name,
                    Position = new { X = p.Position.X, Y = p.Position.Y, Z = p.Position.Z },
                    Rotation = new { X = p.Rotation.X, Y = p.Rotation.Y, Z = p.Rotation.Z },
                    Scale = p.Scale,
                    Flags = p.Flags
                }).ToList(),
                WmoPlacements = r.WmoPlacements.Select(p => new
                {
                    UniqueId = p.UniqueId,
                    NameId = p.NameId,
                    Name = p.Name,
                    Position = new { X = p.Position.X, Y = p.Position.Y, Z = p.Position.Z },
                    Rotation = new { X = p.Rotation.X, Y = p.Rotation.Y, Z = p.Rotation.Z },
                    DoodadSet = p.DoodadSet,
                    NameSet = p.NameSet,
                    Flags = p.Flags
                }).ToList(),
                UniqueIds = r.UniqueIds.ToList(),
                Header = new
                {
                    Flags = r.Header.Flags,
        /// <summary>
        /// Generates a JSON file containing the area IDs.
        /// </summary>
        /// <param name="summary">The analysis summary.</param>
        /// <param name="outputDirectory">The directory to write the file to.</param>
        /// <returns>A task representing the asynchronous operation.</returns>
        private async Task GenerateAreaIdsJsonAsync(AnalysisSummary summary, string outputDirectory)
        {
            var filePath = Path.Combine(outputDirectory, "area_ids.json");
            _logger.LogDebug($"Generating area IDs JSON: {filePath}");

            // Create a simplified area IDs object for JSON serialization
            var areaIdsJson = summary.AreaIdMap.Select(area => new
            {
                AreaId = area.Key,
                FoundIn = area.Value.ToList()
            }).ToList();

            var options = new JsonSerializerOptions { WriteIndented = true };
            var json = JsonSerializer.Serialize(areaIdsJson, options);
            await File.WriteAllTextAsync(filePath, json);
        }

                    HasHeightData = r.Header.HasHeightData,
                    HasNormalData = r.Header.HasNormalData,
                    HasLiquidData = r.Header.HasLiquidData,
                    HasVertexShading = r.Header.HasVertexShading,
                    TextureLayerCount = r.Header.TextureLayerCount,
                    TerrainChunkCount = r.Header.TerrainChunkCount,
                    ModelReferenceCount = r.Header.ModelReferenceCount,
                    WmoReferenceCount = r.Header.WmoReferenceCount,
                    ModelPlacementCount = r.Header.ModelPlacementCount,
                    WmoPlacementCount = r.Header.WmoPlacementCount,
                    DoodadReferenceCount = r.Header.DoodadReferenceCount
                },
                TerrainChunks = r.TerrainChunks.Select(c => new
                {
                    Position = new { X = c.Position.X, Y = c.Position.Y },
                    AreaId = c.AreaId,
                    Flags = c.Flags,
                    Holes = c.Holes,
                    LiquidLevel = c.LiquidLevel,
                    TextureLayerCount = c.TextureLayers.Count,
                    DoodadRefCount = c.DoodadRefs.Count
                }).ToList(),
                Errors = r.Errors
            }).ToList();

            var options = new JsonSerializerOptions { WriteIndented = true };
            var json = JsonSerializer.Serialize(resultsJson, options);
            await File.WriteAllTextAsync(filePath, json);
        }

        /// <summary>
        /// Generates a JSON file containing the missing references.
        /// </summary>
        /// <param name="summary">The analysis summary.</param>
        /// <param name="outputDirectory">The directory to write the file to.</param>
        /// <returns>A task representing the asynchronous operation.</returns>
        private async Task GenerateMissingReferencesJsonAsync(AnalysisSummary summary, string outputDirectory)
        {
            var filePath = Path.Combine(outputDirectory, "missing_references.json");
            _logger.LogDebug($"Generating missing references JSON: {filePath}");

            // Create a simplified missing references object for JSON serialization
            var missingReferencesJson = summary.MissingReferenceMap.Select(m => new
            {
                Path = m.Key,
                ReferencedBy = m.Value.ToList(),
                ExistsInListfile = false
            }).ToList();

            var options = new JsonSerializerOptions { WriteIndented = true };
            var json = JsonSerializer.Serialize(missingReferencesJson, options);
            await File.WriteAllTextAsync(filePath, json);
        }

        /// <summary>
        /// Generates a JSON file containing the duplicate IDs.
        /// </summary>
        /// <param name="summary">The analysis summary.</param>
        /// <param name="outputDirectory">The directory to write the file to.</param>
        /// <returns>A task representing the asynchronous operation.</returns>
        private async Task GenerateDuplicateIdsJsonAsync(AnalysisSummary summary, string outputDirectory)
        {
            var filePath = Path.Combine(outputDirectory, "duplicate_ids.json");
            _logger.LogDebug($"Generating duplicate IDs JSON: {filePath}");

            // Create a simplified duplicate IDs object for JSON serialization
            var duplicateIdsJson = summary.DuplicateIdSet.Select(id => new
            {
                Id = id,
                FoundIn = summary.DuplicateIdMap.TryGetValue(id, out var files) ? files.ToList() : new List<string>()
            }).ToList();

            var options = new JsonSerializerOptions { WriteIndented = true };
            var json = JsonSerializer.Serialize(duplicateIdsJson, options);
            await File.WriteAllTextAsync(filePath, json);
        }
    }

    /// <summary>
    /// Generates detailed reports for terrain data (heightmaps and textures).
    /// </summary>
    /// <param name="results">The ADT analysis results.</param>
    /// <param name="outputDirectory">The directory to write the reports to.</param>
    /// <returns>A task representing the asynchronous operation.</returns>
    private async Task GenerateTerrainDataReportsAsync(List<AdtAnalysisResult> results, string outputDirectory)
    {
        _logger.LogDebug("Generating terrain data reports...");

        // Create a terrain data directory
        var terrainDirectory = Path.Combine(outputDirectory, "terrain_data");
        if (!Directory.Exists(terrainDirectory))
        {
            Directory.CreateDirectory(terrainDirectory);
        }

        // Generate heightmap reports
        await GenerateHeightmapReportsAsync(results, terrainDirectory);

        // Generate texture layer reports
        await GenerateTextureLayerReportsAsync(results, terrainDirectory);

        _logger.LogDebug("Terrain data report generation complete.");
    }

    /// <summary>
    /// Generates reports for heightmap data.
    /// </summary>
    /// <param name="results">The ADT analysis results.</param>
    /// <param name="outputDirectory">The directory to write the reports to.</param>
    /// <returns>A task representing the asynchronous operation.</returns>
    private async Task GenerateHeightmapReportsAsync(List<AdtAnalysisResult> results, string outputDirectory)
    {
        var filePath = Path.Combine(outputDirectory, "heightmaps.txt");
        _logger.LogDebug($"Generating heightmap report: {filePath}");

        using (var writer = new StreamWriter(filePath, false, Encoding.UTF8))
        {
            await writer.WriteLineAsync($"# Heightmap Data Report - {DateTime.Now:yyyy-MM-dd HH:mm:ss}");
            await writer.WriteLineAsync();

            foreach (var result in results)
            {
                await writer.WriteLineAsync($"## {result.FileName}");
                await writer.WriteLineAsync();

                foreach (var chunk in result.TerrainChunks)
                {
                    await writer.WriteLineAsync($"### Chunk ({chunk.Position.X}, {chunk.Position.Y})");
                    await writer.WriteLineAsync($"World Position: ({chunk.WorldPosition.X}, {chunk.WorldPosition.Y}, {chunk.WorldPosition.Z})");
                    await writer.WriteLineAsync($"Area ID: {chunk.AreaId}");
                    await writer.WriteLineAsync($"Flags: 0x{chunk.Flags:X8}");
                    await writer.WriteLineAsync($"Holes: 0x{chunk.Holes:X8}");
                    await writer.WriteLineAsync($"Liquid Level: {chunk.LiquidLevel}");
                    await writer.WriteLineAsync();
                    
                    // Output heightmap data
                    await writer.WriteLineAsync(chunk.GetHeightmapString());
                    await writer.WriteLineAsync();
                }
            }
        }
    }

    /// <summary>
    /// Generates reports for texture layer data.
    /// </summary>
    /// <param name="results">The ADT analysis results.</param>
    /// <param name="outputDirectory">The directory to write the reports to.</param>
    /// <returns>A task representing the asynchronous operation.</returns>
    private async Task GenerateTextureLayerReportsAsync(List<AdtAnalysisResult> results, string outputDirectory)
    {
        var filePath = Path.Combine(outputDirectory, "texture_layers.txt");
        _logger.LogDebug($"Generating texture layer report: {filePath}");

        using (var writer = new StreamWriter(filePath, false, Encoding.UTF8))
        {
            await writer.WriteLineAsync($"# Texture Layer Data Report - {DateTime.Now:yyyy-MM-dd HH:mm:ss}");
            await writer.WriteLineAsync();

            foreach (var result in results)
            {
                await writer.WriteLineAsync($"## {result.FileName}");
                await writer.WriteLineAsync();

                foreach (var chunk in result.TerrainChunks)
                {
                    await writer.WriteLineAsync($"### Chunk ({chunk.Position.X}, {chunk.Position.Y})");
                    await writer.WriteLineAsync($"Texture Layers: {chunk.TextureLayers.Count}");
                    await writer.WriteLineAsync();

                    for (int i = 0; i < chunk.TextureLayers.Count; i++)
                    {
                        var layer = chunk.TextureLayers[i];
                        await writer.WriteLineAsync($"#### Layer {i}");
                        await writer.WriteLineAsync($"Texture ID: {layer.TextureId}");
                        await writer.WriteLineAsync($"Texture Name: {layer.TextureName}");
                        await writer.WriteLineAsync($"Flags: 0x{layer.Flags:X8}");
                        await writer.WriteLineAsync($"Effect ID: {layer.EffectId}");
                        await writer.WriteLineAsync($"Alpha Map Offset: {layer.AlphaMapOffset}");
                        await writer.WriteLineAsync($"Alpha Map Size: {layer.AlphaMapSize}");
                        await writer.WriteLineAsync();
                        
                        // Output alpha map data
                        await writer.WriteLineAsync(layer.GetAlphaMapString());
                        await writer.WriteLineAsync();
                    }
                }
            }
        }
    }

    /// <summary>
    /// Generates JSON files for terrain data (heightmaps and textures).
    /// </summary>
    /// <param name="results">The ADT analysis results.</param>
    /// <param name="outputDirectory">The directory to write the files to.</param>
    /// <returns>A task representing the asynchronous operation.</returns>
    private async Task GenerateTerrainDataJsonAsync(List<AdtAnalysisResult> results, string outputDirectory)
    {
        _logger.LogDebug("Generating terrain data JSON...");

        // Create a terrain data directory
        var terrainDirectory = Path.Combine(outputDirectory, "terrain_data");
        if (!Directory.Exists(terrainDirectory))
        {
            Directory.CreateDirectory(terrainDirectory);
        }

        // Generate heightmap JSON
        await GenerateHeightmapJsonAsync(results, terrainDirectory);

        // Generate texture layer JSON
        await GenerateTextureLayerJsonAsync(results, terrainDirectory);

        _logger.LogDebug("Terrain data JSON generation complete.");
    }

    /// <summary>
    /// Generates a JSON file containing heightmap data.
    /// </summary>
    /// <param name="results">The ADT analysis results.</param>
    /// <param name="outputDirectory">The directory to write the file to.</param>
    /// <returns>A task representing the asynchronous operation.</returns>
    private async Task GenerateHeightmapJsonAsync(List<AdtAnalysisResult> results, string outputDirectory)
    {
        var filePath = Path.Combine(outputDirectory, "heightmaps.json");
        _logger.LogDebug($"Generating heightmap JSON: {filePath}");

        // Create a simplified heightmap object for JSON serialization
        var heightmapJson = results.Select(r => new
        {
            FileName = r.FileName,
            TerrainChunks = r.TerrainChunks.Select(c => new
            {
                Position = new { X = c.Position.X, Y = c.Position.Y },
                WorldPosition = new { X = c.WorldPosition.X, Y = c.WorldPosition.Y, Z = c.WorldPosition.Z },
                AreaId = c.AreaId,
                Flags = c.Flags,
                Holes = c.Holes,
                LiquidLevel = c.LiquidLevel,
                Heights = c.Heights.ToArray(),
                Normals = c.Normals.Select(n => new { X = n.X, Y = n.Y, Z = n.Z }).ToArray()
            }).ToArray()
        }).ToArray();

        var options = new JsonSerializerOptions { WriteIndented = true };
        var json = JsonSerializer.Serialize(heightmapJson, options);
        await File.WriteAllTextAsync(filePath, json);
    }

    /// <summary>
    /// Generates a JSON file containing texture layer data.
    /// </summary>
    /// <param name="results">The ADT analysis results.</param>
    /// <param name="outputDirectory">The directory to write the file to.</param>
    /// <returns>A task representing the asynchronous operation.</returns>
    private async Task GenerateTextureLayerJsonAsync(List<AdtAnalysisResult> results, string outputDirectory)
    {
        var filePath = Path.Combine(outputDirectory, "texture_layers.json");
        _logger.LogDebug($"Generating texture layer JSON: {filePath}");

        // Create a simplified texture layer object for JSON serialization
        var textureLayerJson = results.Select(r => new
        {
            FileName = r.FileName,
            TerrainChunks = r.TerrainChunks.Select(c => new
            {
                Position = new { X = c.Position.X, Y = c.Position.Y },
                TextureLayers = c.TextureLayers.Select(l => new
                {
                    TextureId = l.TextureId,
                    TextureName = l.TextureName,
                    Flags = l.Flags,
                    EffectId = l.EffectId,
                    AlphaMapOffset = l.AlphaMapOffset,
                    AlphaMapSize = l.AlphaMapSize,
                    // Don't include the raw alpha map data in JSON as it can be very large
                    AlphaMapLength = l.AlphaMap?.Length ?? 0
                }).ToArray()
            }).ToArray()
        }).ToArray();

        var options = new JsonSerializerOptions { WriteIndented = true };
        var json = JsonSerializer.Serialize(textureLayerJson, options);
        await File.WriteAllTextAsync(filePath, json);
    }
}