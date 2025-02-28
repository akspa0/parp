using System;
using System.Collections.Generic;
using System.IO;
using System.Threading.Tasks;
using ModernWoWTools.ADTMeta.Analysis.Models;
using ModernWoWTools.ADTMeta.Analysis.Utilities;

namespace ModernWoWTools.ADTMeta.Analysis.Services
{
    /// <summary>
    /// Service for validating file references against a listfile.
    /// </summary>
    public class ReferenceValidator
    {
        private readonly ILoggingService _logger;

        /// <summary>
        /// Creates a new instance of the ReferenceValidator class.
        /// </summary>
        /// <param name="logger">The logging service to use.</param>
        public ReferenceValidator(ILoggingService logger)
        {
            _logger = logger ?? throw new ArgumentNullException(nameof(logger));
        }

        /// <summary>
        /// Loads a listfile into a HashSet for fast lookups.
        /// </summary>
        /// <param name="listfilePath">The path to the listfile.</param>
        /// <returns>A HashSet containing the normalized paths from the listfile.</returns>
        public async Task<HashSet<string>> LoadListfileAsync(string? listfilePath)
        {
            var knownGoodFiles = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

            if (string.IsNullOrEmpty(listfilePath) || !File.Exists(listfilePath))
            {
                _logger.LogWarning($"Listfile not found or not specified: {listfilePath}. References will not be validated.");
                return knownGoodFiles;
            }

            _logger.LogInfo($"Loading listfile: {listfilePath}");

            try
            {
                foreach (var line in await File.ReadAllLinesAsync(listfilePath))
                {
                    // Handle different listfile formats
                    string path;
                    if (line.Contains(';'))
                    {
                        // Format: ID;Path
                        var parts = line.Split(';', 2);
                        if (parts.Length < 2)
                            continue;

                        path = parts[1].Trim();
                    }
                    else
                    {
                        // Format: Path
                        path = line.Trim();
                    }

                    if (!string.IsNullOrWhiteSpace(path))
                    {
                        var normalizedPath = PathUtility.NormalizePath(path);
                        knownGoodFiles.Add(normalizedPath);
                    }
                }

                _logger.LogInfo($"Loaded {knownGoodFiles.Count} known good files from {listfilePath}");
            }
            catch (Exception ex)
            {
                _logger.LogError($"Error loading listfile: {ex.Message}");
            }

            return knownGoodFiles;
        }

        /// <summary>
        /// Validates file references against a listfile.
        /// </summary>
        /// <param name="result">The ADT analysis result to validate.</param>
        /// <param name="knownGoodFiles">The set of known good files.</param>
        /// <returns>The number of invalid references found.</returns>
        public int ValidateReferences(AdtAnalysisResult result, HashSet<string> knownGoodFiles)
        {
            if (result == null)
                throw new ArgumentNullException(nameof(result));

            if (knownGoodFiles == null || knownGoodFiles.Count == 0)
            {
                // No listfile provided, mark all references as valid
                foreach (var reference in result.AllReferences)
                {
                    reference.IsValid = true;
                }
                return 0;
            }

            int invalidCount = 0;

            // Validate texture references
            foreach (var reference in result.TextureReferences)
            {
                reference.IsValid = knownGoodFiles.Contains(reference.NormalizedPath);
                reference.ExistsInListfile = reference.IsValid;
                if (!reference.IsValid)
                {
                    invalidCount++;
                }
            }

            // Validate model references
            foreach (var reference in result.ModelReferences)
            {
                reference.IsValid = knownGoodFiles.Contains(reference.NormalizedPath);
                reference.ExistsInListfile = reference.IsValid;
                if (!reference.IsValid)
                {
                    invalidCount++;
                }
            }

            // Validate WMO references
            foreach (var reference in result.WmoReferences)
            {
                reference.IsValid = knownGoodFiles.Contains(reference.NormalizedPath);
                reference.ExistsInListfile = reference.IsValid;
                if (!reference.IsValid)
                {
                    invalidCount++;
                }
            }

            return invalidCount;
        }
    }
}