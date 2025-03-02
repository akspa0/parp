using System;

namespace ModernWoWTools.ADTMeta.Analysis.Models
{
    /// <summary>
    /// Represents the header information (MHDR chunk) of an ADT file.
    /// </summary>
    public class AdtHeader
    {
        /// <summary>
        /// Gets or sets the flags for the ADT file.
        /// </summary>
        public uint Flags { get; set; }

        /// <summary>
        /// Gets or sets whether the ADT has height data.
        /// </summary>
        public bool HasHeightData => (Flags & 0x1) != 0;

        /// <summary>
        /// Gets or sets whether the ADT has normal data.
        /// </summary>
        public bool HasNormalData => (Flags & 0x2) != 0;

        /// <summary>
        /// Gets or sets whether the ADT has liquid data.
        /// </summary>
        public bool HasLiquidData => (Flags & 0x4) != 0;

        /// <summary>
        /// Gets or sets whether the ADT has vertex shading.
        /// </summary>
        public bool HasVertexShading => (Flags & 0x8) != 0;

        /// <summary>
        /// Gets or sets the number of texture layers in the ADT.
        /// </summary>
        public int TextureLayerCount { get; set; }

        /// <summary>
        /// Gets or sets the number of terrain chunks in the ADT.
        /// </summary>
        public int TerrainChunkCount { get; set; }

        /// <summary>
        /// Gets or sets the number of model references in the ADT.
        /// </summary>
        public int ModelReferenceCount { get; set; }

        /// <summary>
        /// Gets or sets the number of WMO references in the ADT.
        /// </summary>
        public int WmoReferenceCount { get; set; }

        /// <summary>
        /// Gets or sets the number of model placements in the ADT.
        /// </summary>
        public int ModelPlacementCount { get; set; }

        /// <summary>
        /// Gets or sets the number of WMO placements in the ADT.
        /// </summary>
        public int WmoPlacementCount { get; set; }

        /// <summary>
        /// Gets or sets the number of doodad references in the ADT.
        /// </summary>
        public int DoodadReferenceCount { get; set; }
    }
}