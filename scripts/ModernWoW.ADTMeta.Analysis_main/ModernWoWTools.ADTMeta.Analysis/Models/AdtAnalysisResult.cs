using System;
using System.Collections.Generic;
using System.Linq;

namespace ModernWoWTools.ADTMeta.Analysis.Models
{
    /// <summary>
    /// Represents the result of analyzing an ADT file.
    /// </summary>
    public class AdtAnalysisResult
    {
        /// <summary>
        /// Gets or sets the name of the ADT file.
        /// </summary>
        public string FileName { get; set; } = string.Empty;

        /// <summary>
        /// Gets or sets the path to the ADT file.
        /// </summary>
        public string FilePath { get; set; } = string.Empty;

        /// <summary>
        /// Gets or sets the X coordinate extracted from the filename.
        /// </summary>
        public int XCoord { get; set; }

        /// <summary>
        /// Gets or sets the Y coordinate extracted from the filename.
        /// </summary>
        public int YCoord { get; set; }

        /// <summary>
        /// Gets or sets the version of the ADT file.
        /// </summary>
        public uint AdtVersion { get; set; }

        /// <summary>
        /// Gets or sets the header information for the ADT file.
        /// </summary>
        public AdtHeader Header { get; set; } = new AdtHeader();

        /// <summary>
        /// Gets or sets the list of texture references found in the ADT file.
        /// </summary>
        public List<FileReference> TextureReferences { get; set; } = new List<FileReference>();

        /// <summary>
        /// Gets or sets the list of model references found in the ADT file.
        /// </summary>
        public List<FileReference> ModelReferences { get; set; } = new List<FileReference>();

        /// <summary>
        /// Gets or sets the list of WMO references found in the ADT file.
        /// </summary>
        public List<FileReference> WmoReferences { get; set; } = new List<FileReference>();

        /// <summary>
        /// Gets or sets the list of model placements found in the ADT file.
        /// </summary>
        public List<ModelPlacement> ModelPlacements { get; set; } = new List<ModelPlacement>();

        /// <summary>
        /// Gets or sets the list of WMO placements found in the ADT file.
        /// </summary>
        public List<WmoPlacement> WmoPlacements { get; set; } = new List<WmoPlacement>();

        /// <summary>
        /// Gets or sets the set of unique IDs found in the ADT file.
        /// </summary>
        public HashSet<int> UniqueIds { get; set; } = new HashSet<int>();

        /// <summary>
        /// Gets or sets the list of terrain chunks in the ADT file.
        /// </summary>
        public List<TerrainChunk> TerrainChunks { get; set; } = new List<TerrainChunk>();

        /// <summary>
        /// Gets or sets the list of errors encountered during parsing.
        /// </summary>
        public List<string> Errors { get; set; } = new List<string>();

        /// <summary>
        /// Gets all file references (textures, models, and WMOs) as a single collection.
        /// </summary>
        public IEnumerable<FileReference> AllReferences
        {
            get
            {
                return TextureReferences.Concat(ModelReferences).Concat(WmoReferences);
            }
        }

        /// <summary>
        /// Returns a string representation of the ADT analysis result.
        /// </summary>
        /// <returns>A string representation of the ADT analysis result.</returns>
        public override string ToString()
        {
            return $"{FileName} ({XCoord}_{YCoord}): " +
                   $"{TextureReferences.Count} textures, " +
                   $"{ModelReferences.Count} models, " +
                   $"{WmoReferences.Count} WMOs, " +
                   $"{TerrainChunks.Count} terrain chunks, " +
                   $"{UniqueIds.Count} unique IDs";
        }
    }
}