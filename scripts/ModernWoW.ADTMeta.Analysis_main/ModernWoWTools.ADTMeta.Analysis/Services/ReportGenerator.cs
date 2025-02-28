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

        /// <summary>
        /// Creates a new instance of the ReportGenerator class.
        /// </summary>
        /// <param name="logger">The logging service to use.</param>
        public ReportGenerator(ILoggingService logger)
        {
            _logger = logger ?? throw new ArgumentNullException(nameof(logger));
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
            await GenerateSummaryReportAsync(summary, outputDirectory);
            await GenerateUidIniFileAsync(summary, outputDirectory);
            await GenerateJsonReportsAsync(results, summary, outputDirectory);

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

                    // Include repaired path if available
                    if (summary.FilesNotInListfileMap.TryGetValue(missing.Key, out var repairedPath))
                    {
                        await writer.WriteLineAsync($"Repaired path: {repairedPath}");
                    }

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
                await writer.WriteLineAsync();
                await writer.WriteLineAsync($"Missing references: {summary.MissingReferences}");
                await writer.WriteLineAsync($"Files not in listfile: {summary.FilesNotInListfile}");
                await writer.WriteLineAsync($"Duplicate IDs: {summary.DuplicateIds}");
                await writer.WriteLineAsync($"Maximum unique ID: {summary.MaxUniqueId}");
            }
        }

        /// <summary>
        /// Generates a uid.ini file with the maximum unique ID.
        /// </summary>
        /// <param name="summary">The analysis summary.</param>
        /// <param name="outputDirectory">The directory to write the file to.</param>
        /// <returns>A task representing the asynchronous operation.</returns>
        private async Task GenerateUidIniFileAsync(AnalysisSummary summary, string outputDirectory)
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
                MissingReferences = summary.MissingReferences,
                FilesNotInListfile = summary.FilesNotInListfile,
                DuplicateIds = summary.DuplicateIds,
                MaxUniqueId = summary.MaxUniqueId
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
                UniqueIds = r.UniqueIds.ToList()
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
}