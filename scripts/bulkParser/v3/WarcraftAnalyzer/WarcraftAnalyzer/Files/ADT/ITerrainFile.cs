using System.Collections.Generic;

namespace WarcraftAnalyzer.Files.ADT
{
    /// <summary>
    /// Interface for terrain file types (ADTFile and SplitADTFile)
    /// </summary>
    public interface ITerrainFile
    {
        /// <summary>
        /// Gets the file name.
        /// </summary>
        string FileName { get; }

        /// <summary>
        /// Gets the X coordinate extracted from the filename.
        /// </summary>
        int XCoord { get; }

        /// <summary>
        /// Gets the Y coordinate extracted from the filename.
        /// </summary>
        int YCoord { get; }

        /// <summary>
        /// Gets the list of terrain chunks in the file.
        /// </summary>
        List<TerrainChunk> TerrainChunks { get; }
    }
}