using System;
using System.Text.RegularExpressions;

namespace ModernWoWTools.ADTMeta.Analysis.Utilities
{
    /// <summary>
    /// Utility class for path-related operations.
    /// </summary>
    public static class PathUtility
    {
        private static readonly Regex AdtCoordinateRegex = new Regex(@"(\d+)_(\d+)\.adt$", RegexOptions.IgnoreCase);

        /// <summary>
        /// Normalizes a file path for consistent comparison.
        /// </summary>
        /// <param name="path">The path to normalize.</param>
        /// <returns>The normalized path.</returns>
        public static string NormalizePath(string path)
        {
            if (string.IsNullOrWhiteSpace(path))
            {
                return string.Empty;
            }

            // Normalize separators and casing
            var normalized = path.ToLowerInvariant().Replace('\\', '/');

            // Remove leading ./ or /
            normalized = normalized.TrimStart('.', '/');

            // Collapse multiple slashes
            while (normalized.Contains("//"))
            {
                normalized = normalized.Replace("//", "/");
            }

            return normalized;
        }

        /// <summary>
        /// Attempts to repair a path by applying common fixes.
        /// </summary>
        /// <param name="path">The path to repair.</param>
        /// <returns>The repaired path, or null if no repair was possible.</returns>
        public static string? RepairPath(string path)
        {
            if (string.IsNullOrWhiteSpace(path))
            {
                return null;
            }

            var normalized = NormalizePath(path);

            // Common repairs

            // 1. Fix case-sensitive extensions
            if (normalized.EndsWith(".mdx", StringComparison.OrdinalIgnoreCase) && !normalized.Contains('/'))
            {
                return normalized.Substring(0, normalized.Length - 4) + ".m2";
            }

            // 2. Handle missing "world/" or "texture/" prefixes
            if (!normalized.StartsWith("world/") &&
                !normalized.StartsWith("character/") &&
                !normalized.StartsWith("item/") &&
                !normalized.StartsWith("texture/"))
            {
                // Try adding world/ prefix for models
                if (normalized.EndsWith(".m2", StringComparison.OrdinalIgnoreCase) ||
                    normalized.EndsWith(".wmo", StringComparison.OrdinalIgnoreCase))
                {
                    return "world/" + normalized;
                }

                // Try adding texture/ prefix for textures
                if (normalized.EndsWith(".blp", StringComparison.OrdinalIgnoreCase))
                {
                    return "texture/" + normalized;
                }
            }

            // 3. Attempt to repair paths by finding a known-good alternative
            // (This part requires access to a list of known-good files, which is not available in this method)

            return null; // No repair was possible
        }

        /// <summary>
        /// Tries to extract X and Y coordinates from an ADT filename.
        /// </summary>
        /// <param name="fileName">The ADT filename.</param>
        /// <param name="xCoord">The extracted X coordinate.</param>
        /// <param name="yCoord">The extracted Y coordinate.</param>
        /// <returns>True if coordinates were successfully extracted, false otherwise.</returns>
        public static bool TryExtractCoordinates(string fileName, out int xCoord, out int yCoord)
        {
            xCoord = 0;
            yCoord = 0;

            if (string.IsNullOrWhiteSpace(fileName))
            {
                return false;
            }

            var match = AdtCoordinateRegex.Match(fileName);
            if (match.Success && match.Groups.Count >= 3)
            {
                if (int.TryParse(match.Groups[1].Value, out xCoord) &&
                    int.TryParse(match.Groups[2].Value, out yCoord))
                {
                    return true;
                }
            }

            return false;
        }
    }
}