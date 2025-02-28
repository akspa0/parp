using System;
using System.Numerics;

namespace ModernWoWTools.ADTMeta.Analysis.Models
{
    /// <summary>
    /// Base class for model and WMO placements in an ADT file.
    /// </summary>
    public abstract class Placement
    {
        /// <summary>
        /// Gets or sets the unique ID of the placement.
        /// </summary>
        public int UniqueId { get; set; }

        /// <summary>
        /// Gets or sets the name ID (index into the model/WMO reference list).
        /// </summary>
        public int NameId { get; set; }

        /// <summary>
        /// Gets or sets the name of the model/WMO.
        /// </summary>
        public string Name { get; set; } = string.Empty;

        /// <summary>
        /// Gets or sets the position of the placement.
        /// </summary>
        public Vector3 Position { get; set; }

        /// <summary>
        /// Gets or sets the rotation of the placement.
        /// </summary>
        public Vector3 Rotation { get; set; }

        /// <summary>
        /// Gets or sets the flags of the placement.
        /// </summary>
        public int Flags { get; set; }
    }

    /// <summary>
    /// Represents a model (M2) placement in an ADT file.
    /// </summary>
    public class ModelPlacement : Placement
    {
        /// <summary>
        /// Gets or sets the scale of the model.
        /// </summary>
        public float Scale { get; set; }
    }

    /// <summary>
    /// Represents a world model object (WMO) placement in an ADT file.
    /// </summary>
    public class WmoPlacement : Placement
    {
        /// <summary>
        /// Gets or sets the doodad set index.
        /// </summary>
        public int DoodadSet { get; set; }

        /// <summary>
        /// Gets or sets the name set index.
        /// </summary>
        public int NameSet { get; set; }
    }
}