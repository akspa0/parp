using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using ModernWoWTools.ADTMeta.Analysis.Models;
using ModernWoWTools.ADTMeta.Analysis.Utilities;

namespace ModernWoWTools.ADTMeta.Analysis.Services
{
    /// <summary>
    /// Service for analyzing ADT files.
    /// </summary>
    public class AdtAnalyzer
    {
        private readonly AdtParser _parser;
        private readonly ReferenceValidator _validator;
        private readonly ReportGenerator _reportGenerator;
        private readonly ILoggingService _logger;

        /// <summary>
        /// Creates a new instance of the AdtAnalyzer class.
        /// </summary>
        /// <param name="parser">The ADT parser to use.</param>
        /// <param name="validator">The reference validator to use.</param>
        /// <param name="reportGenerator">The report generator to use.</param>
        /// <param name="logger">The logging service to use.</param>
        public AdtAnalyzer(
            AdtParser parser,
            ReferenceValidator validator,
            ReportGenerator reportGenerator,
            ILoggingService logger)
        {
            _parser = parser ?? throw new ArgumentNullException(nameof(parser));
            _validator = validator ?? throw new ArgumentNullException(nameof(validator));
            _reportGenerator = reportGenerator ?? throw new ArgumentNullException(nameof(reportGenerator));
            _logger = logger ?? throw new ArgumentNullException(nameof(logger));
        }

        /// <summary>
        /// Analyzes all ADT files in a directory.
        /// </summary>
        /// <param name="directoryPath">The directory containing ADT files.</param>
        /// <param name="listfilePath">The path to the listfile for reference validation.</param>
        /// <param name="outputDirectory">The directory to write reports to.</param>
        /// <param name="recursive">Whether to search subdirectories.</param>
        /// <returns>A summary of the analysis.</returns>
        public async Task<AnalysisSummary> AnalyzeDirectoryAsync(
            string directoryPath,
            string? listfilePath = null,
            string? outputDirectory = null,
            bool recursive = false)
        {
            if (string.IsNullOrEmpty(directoryPath))
                throw new ArgumentException("Directory path cannot be null or empty.", nameof(directoryPath));

            if (!Directory.Exists(directoryPath))
                throw new DirectoryNotFoundException($"Directory not found: {directoryPath}");

            // Set default output directory if not specified
            outputDirectory ??= Path.Combine(directoryPath, "analysis_output");

            // Create output directory if it doesn't exist
            if (!Directory.Exists(outputDirectory))
            {
                Directory.CreateDirectory(outputDirectory);
            }

            _logger.LogInfo($"Analyzing ADT files in {directoryPath}...");
            _logger.LogInfo($"Output directory: {outputDirectory}");

            // Initialize summary
            var summary = new AnalysisSummary();

            // Load listfile if provided
            var knownGoodFiles = await _validator.LoadListfileAsync(listfilePath);

            // Find all ADT files
            var searchOption = recursive ? SearchOption.AllDirectories : SearchOption.TopDirectoryOnly;
            var adtFiles = Directory.GetFiles(directoryPath, "*.adt", searchOption);
            summary.TotalFiles = adtFiles.Length;

            _logger.LogInfo($"Found {adtFiles.Length} ADT files.");

            // Process each ADT file
            var results = new List<AdtAnalysisResult>();
            foreach (var adtFile in adtFiles)
            {
                try
                {
                    var result = await AnalyzeFileAsync(adtFile, knownGoodFiles);
                    results.Add(result);
                    summary.ProcessedFiles++;

                    // Update summary statistics
                    summary.TotalTextureReferences += result.TextureReferences.Count;
                    summary.TotalModelReferences += result.ModelReferences.Count;
                    summary.TotalWmoReferences += result.WmoReferences.Count;
                    summary.TotalModelPlacements += result.ModelPlacements.Count;
                    summary.TotalWmoPlacements += result.WmoPlacements.Count;
                    summary.TotalTerrainChunks += result.TerrainChunks.Count;
                    summary.ParsingErrors += result.Errors.Count;
                    
                    // Count texture layers and doodad references
                    foreach (var chunk in result.TerrainChunks)
                    {
                        summary.TotalTextureLayers += chunk.TextureLayers.Count;
                        summary.TotalDoodadReferences += chunk.DoodadRefs.Count;
                        
                        // Track area IDs
                        if (chunk.AreaId > 0)
                        {
                            if (!summary.AreaIdMap.TryGetValue(chunk.AreaId, out var areaFiles))
                            {
                                areaFiles = new HashSet<string>();
                                summary.AreaIdMap[chunk.AreaId] = areaFiles;
                            }
                            areaFiles.Add(result.FileName);
                        }
                    }

                    // Track missing references
                    foreach (var reference in result.AllReferences.Where(r => !r.IsValid))
                    {
                        summary.MissingReferences++;
                        if (!summary.MissingReferenceMap.TryGetValue(reference.NormalizedPath, out var referencingFiles))
                        {
                            referencingFiles = new HashSet<string>();
                            summary.MissingReferenceMap[reference.NormalizedPath] = referencingFiles;
                        }
                        referencingFiles.Add(result.FileName);

                        // Track files not in the listfile
                        if (!reference.ExistsInListfile)
                        {
                            summary.FilesNotInListfile++;
                            if (!summary.FilesNotInListfileMap.TryGetValue(reference.NormalizedPath, out var notInListfileFiles))
                            {
                                notInListfileFiles = new HashSet<string>();
                                summary.FilesNotInListfileMap[reference.NormalizedPath] = notInListfileFiles;
                            }
                            notInListfileFiles.Add(result.FileName);
                        }
                    }

                    // Track duplicate unique IDs
                    foreach (var uniqueId in result.UniqueIds)
                    {
                        if (uniqueId > summary.MaxUniqueId)
                        {
                            summary.MaxUniqueId = uniqueId;
                        }

                        if (!summary.DuplicateIdMap.TryGetValue(uniqueId, out var files))
                        {
                            files = new HashSet<string>();
                            summary.DuplicateIdMap[uniqueId] = files;
                        }
                        else
                        {
                            // This is a duplicate
                            if (!summary.DuplicateIdSet.Contains(uniqueId))
                            {
                                summary.DuplicateIdSet.Add(uniqueId);
                                summary.DuplicateIds++;
                            }
                        }
                        files.Add(result.FileName);
                    }
                }
                catch (Exception ex)
                {
                    _logger.LogError($"Error analyzing {Path.GetFileName(adtFile)}: {ex.Message}");
                    summary.FailedFiles++;
                }
            }

            // Complete summary
            summary.Complete();

            // Generate reports
            await _reportGenerator.GenerateAllReportsAsync(results, summary, outputDirectory);

            _logger.LogInfo($"Analysis complete. Processed {summary.ProcessedFiles} files in {summary.Duration.TotalSeconds:F2} seconds.");
            _logger.LogInfo($"Found {summary.MissingReferences} missing references, {summary.FilesNotInListfile} files not in listfile, and {summary.DuplicateIds} duplicate unique IDs.");

            return summary;
        }

        /// <summary>
        /// Analyzes a single ADT file.
        /// </summary>
        /// <param name="filePath">The path to the ADT file.</param>
        /// <param name="knownGoodFiles">The set of known good files for reference validation.</param>
        /// <returns>The analysis result.</returns>
        public async Task<AdtAnalysisResult> AnalyzeFileAsync(string filePath, HashSet<string> knownGoodFiles)
        {
            if (string.IsNullOrEmpty(filePath))
                throw new ArgumentException("File path cannot be null or empty.", nameof(filePath));

            if (!File.Exists(filePath))
                throw new FileNotFoundException($"File not found: {filePath}");

            // Parse ADT file
            var result = await _parser.ParseAdtFileAsync(filePath);

            // Validate references
            _validator.ValidateReferences(result, knownGoodFiles);

            return result;
        }
    }
}