using System;
using System.Collections.Generic;

namespace ModernWoWTools.ADTMeta.Analysis.UniqueIdAnalysis
{
    /// <summary>
    /// Represents a cluster of unique IDs that might correspond to a specific time period.
    /// </summary>
    public class UniqueIdCluster
    {
        public int MinId { get; set; }
        public int MaxId { get; set; }
        public int Count { get; set; }
        public HashSet<string> AdtFiles { get; set; } = new HashSet<string>();
        public Dictionary<string, int> IdCountsByAdt { get; set; } = new Dictionary<string, int>();
        
        // Added to track asset references in the cluster
        public HashSet<AssetReference> Assets { get; set; } = new HashSet<AssetReference>();
        
        public double Density => (double)Count / (MaxId - MinId + 1);
        
        public override string ToString()
        {
            return $"Cluster {MinId}-{MaxId} ({Count} IDs, {AdtFiles.Count} ADTs, {Assets.Count} assets, Density: {Density:F2})";
        }
    }

    /// <summary>
    /// Simple representation of an ADT file with its unique IDs and asset placements.
    /// </summary>
    public class AdtInfo
    {
        public string FileName { get; set; }
        public string MapName { get; set; }
        public List<int> UniqueIds { get; set; } = new List<int>();
        
        // Added to track uniqueID to asset mapping
        public Dictionary<int, List<AssetReference>> AssetsByUniqueId { get; set; } = new Dictionary<int, List<AssetReference>>();
        
        public AdtInfo(string fileName, string mapName, List<int> uniqueIds)
        {
            FileName = fileName;
            MapName = mapName;
            UniqueIds = uniqueIds;
            AssetsByUniqueId = new Dictionary<int, List<AssetReference>>();
        }
    }

    /// <summary>
    /// Represents an asset reference (model or WMO) associated with a unique ID.
    /// </summary>
    public class AssetReference : IEquatable<AssetReference>
    {
        public string AssetPath { get; set; }
        public string Type { get; set; } // "Model" or "WMO"
        public int UniqueId { get; set; }
        public string AdtFile { get; set; }
        public string MapName { get; set; }
        
        public AssetReference(string assetPath, string type, int uniqueId, string adtFile, string mapName)
        {
            AssetPath = assetPath;
            Type = type;
            UniqueId = uniqueId;
            AdtFile = adtFile;
            MapName = mapName;
        }
        
        // Override Equals and GetHashCode to ensure proper HashSet behavior based on asset path
        public bool Equals(AssetReference other)
        {
            if (other == null)
                return false;
                
            return AssetPath == other.AssetPath && Type == other.Type;
        }
        
        public override bool Equals(object obj)
        {
            return Equals(obj as AssetReference);
        }
        
        public override int GetHashCode()
        {
            return (AssetPath + Type).GetHashCode();
        }
        
        public override string ToString()
        {
            return $"{Type}: {AssetPath} (ID: {UniqueId})";
        }
    }

    /// <summary>
    /// Simple class to deserialize ADT analysis results from JSON.
    /// </summary>
    public class AdtResult
    {
        public string FileName { get; set; }
        public string FilePath { get; set; }
        public int XCoord { get; set; }
        public int YCoord { get; set; }
        public uint AdtVersion { get; set; }
        public List<FileReference> TextureReferences { get; set; }
        public List<FileReference> ModelReferences { get; set; }
        public List<FileReference> WmoReferences { get; set; }
        public List<ModelPlacement> ModelPlacements { get; set; }
        public List<WmoPlacement> WmoPlacements { get; set; }
        public List<int> UniqueIds { get; set; }
    }
    
    /// <summary>
    /// Represents a file reference found in an ADT file.
    /// </summary>
    public class FileReference
    {
        public string OriginalPath { get; set; }
        public string NormalizedPath { get; set; }
        public string ReferenceType { get; set; }
        public bool IsValid { get; set; }
        public bool ExistsInListfile { get; set; }
        public string RepairedPath { get; set; }
    }
    
    /// <summary>
    /// Base class for model and WMO placements in an ADT file.
    /// </summary>
    public class Placement
    {
        public int UniqueId { get; set; }
        public int NameId { get; set; }
        public string Name { get; set; }
        public Dictionary<string, double> Position { get; set; }
        public Dictionary<string, double> Rotation { get; set; }
        public int Flags { get; set; }
    }
    
    /// <summary>
    /// Represents a model (M2) placement in an ADT file.
    /// </summary>
    public class ModelPlacement : Placement
    {
        public float Scale { get; set; }
    }
    
    /// <summary>
    /// Represents a world model object (WMO) placement in an ADT file.
    /// </summary>
    public class WmoPlacement : Placement
    {
        public int DoodadSet { get; set; }
        public int NameSet { get; set; }
    }
}