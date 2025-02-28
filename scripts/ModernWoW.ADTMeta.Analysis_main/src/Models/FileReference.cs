using System;

namespace ModernWoWTools.ADTMeta.Analysis.Models
{
    /// <summary>
    /// Represents the type of file reference.
    /// </summary>
    public enum FileReferenceType
    {
        /// <summary>
        /// A texture file reference.
        /// </summary>
        Texture,

        /// <summary>
        /// A model (M2) file reference.
        /// </summary>
        Model,

        /// <summary>
        /// A world model object (WMO) file reference.
        /// </summary>
        WorldModel
    }

    /// <summary>
    /// Represents a file reference found in an ADT file.
    /// </summary>
    public class FileReference
    {
        /// <summary>
        /// Gets or sets the original path as found in the ADT file.
        /// </summary>
        public string OriginalPath { get; set; } = string.Empty;

        /// <summary>
        /// Gets or sets the normalized path for consistent comparison.
        /// </summary>
        public string NormalizedPath { get; set; } = string.Empty;

        /// <summary>
        /// Gets or sets the type of reference.
        /// </summary>
        public FileReferenceType ReferenceType { get; set; }

        /// <summary>
        /// Gets or sets whether the reference is valid (exists in the listfile).
        /// </summary>
        public bool IsValid { get; set; }

        /// <summary>
        /// Gets or sets the repaired path if the reference is invalid and a repair was attempted.
        /// </summary>
        public string? RepairedPath { get; set; }

        /// <summary>
        /// Returns a string representation of the file reference.
        /// </summary>
        /// <returns>A string representation of the file reference.</returns>
        public override string ToString()
        {
            return $"{ReferenceType}: {OriginalPath} ({(IsValid ? "Valid" : "Invalid")})";
        }
    }
}