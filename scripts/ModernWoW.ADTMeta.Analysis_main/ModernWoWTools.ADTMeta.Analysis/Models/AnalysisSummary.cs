using System;
using System.Collections.Generic;

namespace ModernWoWTools.ADTMeta.Analysis.Models
{
    /// <summary>
    /// Represents a summary of the analysis results for a collection of ADT files.
    /// </summary>
    public class AnalysisSummary
    {
        /// <summary>
        /// Gets or sets the total number of ADT files found.
        /// </summary>
        public int TotalFiles { get; set; }

        /// <summary>
        /// Gets or sets the number of ADT files successfully processed.
        /// </summary>
        public int ProcessedFiles { get; set; }

        /// <summary>
        /// Gets or sets the number of ADT files that failed to process.
        /// </summary>
        public int FailedFiles { get; set; }

        /// <summary>
        /// Gets or sets the total number of texture references found.
        /// </summary>
        public int TotalTextureReferences { get; set; }

        /// <summary>
        /// Gets or sets the total number of model references found.
        /// </summary>
        public int TotalModelReferences { get; set; }

        /// <summary>
        /// Gets or sets the total number of WMO references found.
        /// </summary>
        public int TotalWmoReferences { get; set; }

        /// <summary>
        /// Gets or sets the total number of model placements found.
        /// </summary>
        public int TotalModelPlacements { get; set; }

        /// <summary>
        /// Gets or sets the total number of WMO placements found.
        /// </summary>
        public int TotalWmoPlacements { get; set; }

        /// <summary>
        /// Gets or sets the total number of terrain chunks found.
        /// </summary>
        public int TotalTerrainChunks { get; set; }

        /// <summary>
        /// Gets or sets the total number of texture layers found.
        /// </summary>
        public int TotalTextureLayers { get; set; }

        /// <summary>
        /// Gets or sets the total number of doodad references found.
        /// </summary>
        public int TotalDoodadReferences { get; set; }

        /// <summary>
        /// Gets or sets the number of missing references found.
        /// </summary>
        public int MissingReferences { get; set; }

        /// <summary>
        /// Gets or sets the number of files not found in the listfile.
        /// </summary>
        public int FilesNotInListfile { get; set; }

        /// <summary>
        /// Gets or sets the number of duplicate unique IDs found.
        /// </summary>
        public int DuplicateIds { get; set; }

        /// <summary>
        /// Gets or sets the maximum unique ID found.
        /// </summary>
        public int MaxUniqueId { get; set; }

        /// <summary>
        /// Gets or sets the number of parsing errors encountered.
        /// </summary>
        public int ParsingErrors { get; set; }

        /// <summary>
        /// Gets or sets the duration of the analysis.
        /// </summary>
        public TimeSpan Duration { get; set; }

        /// <summary>
        /// Gets or sets the start time of the analysis.
        /// </summary>
        public DateTime StartTime { get; set; } = DateTime.Now;

        /// <summary>
        /// Gets or sets the end time of the analysis.
        /// </summary>
        public DateTime EndTime { get; set; }

        /// <summary>
        /// Gets or sets the map of missing references to the ADT files that reference them.
        /// </summary>
        public Dictionary<string, HashSet<string>> MissingReferenceMap { get; set; } = new Dictionary<string, HashSet<string>>();

        /// <summary>
        /// Gets or sets the map of files not in the listfile to the ADT files that reference them.
        /// </summary>
        public Dictionary<string, HashSet<string>> FilesNotInListfileMap { get; set; } = new Dictionary<string, HashSet<string>>();

        /// <summary>
        /// Gets or sets the set of duplicate unique IDs.
        /// </summary>
        public HashSet<int> DuplicateIdSet { get; set; } = new HashSet<int>();

        /// <summary>
        /// Gets or sets the map of duplicate unique IDs to the ADT files that contain them.
        /// </summary>
        public Dictionary<int, HashSet<string>> DuplicateIdMap { get; set; } = new Dictionary<int, HashSet<string>>();

        /// <summary>
        /// Gets or sets the map of area IDs to the ADT files that contain them.
        /// </summary>
        public Dictionary<int, HashSet<string>> AreaIdMap { get; set; } = new Dictionary<int, HashSet<string>>();

        /// <summary>
        /// Completes the summary by setting the end time and calculating the duration.
        /// </summary>
        public void Complete()
        {
            EndTime = DateTime.Now;
            Duration = EndTime - StartTime;
        }
    }
}