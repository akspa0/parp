using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Threading.Tasks;
using Warcraft.NET.Files.ADT;
using Warcraft.NET.Files.ADT.Entries;
using Warcraft.NET.Files.ADT.Terrain;
using Warcraft.NET.Files.ADT.Terrain.MCNK;
using Warcraft.NET.Files.ADT.Terrain.Wotlk;

namespace WarcraftAnalyzer.Files.ADT
{
    /// <summary>
    /// Represents an ADT (Azeroth Terrain) file.
    /// </summary>
    public class ADTFile : ITerrainFile
    {
        /// <summary>
        /// Gets the terrain data from the ADT file.
        /// </summary>
        public Terrain Terrain { get; private set; }

        /// <summary>
        /// Gets the file name.
        /// </summary>
        public string FileName { get; private set; }

        /// <summary>
        /// Gets the X coordinate extracted from the filename.
        /// </summary>
        public int XCoord { get; private set; }

        /// <summary>
        /// Gets the Y coordinate extracted from the filename.
        /// </summary>
        public int YCoord { get; private set; }

        /// <summary>
        /// Gets the list of texture references found in the ADT file.
        /// </summary>
        public List<FileReference> TextureReferences { get; private set; } = new List<FileReference>();

        /// <summary>
        /// Gets the list of model references found in the ADT file.
        /// </summary>
        public List<FileReference> ModelReferences { get; private set; } = new List<FileReference>();

        /// <summary>
        /// Gets the list of WMO references found in the ADT file.
        /// </summary>
        public List<FileReference> WmoReferences { get; private set; } = new List<FileReference>();

        /// <summary>
        /// Gets the list of model placements found in the ADT file.
        /// </summary>
        public List<ModelPlacement> ModelPlacements { get; private set; } = new List<ModelPlacement>();

        /// <summary>
        /// Gets the list of WMO placements found in the ADT file.
        /// </summary>
        public List<WmoPlacement> WmoPlacements { get; private set; } = new List<WmoPlacement>();

        /// <summary>
        /// Gets the set of unique IDs found in the ADT file.
        /// </summary>
        public HashSet<int> UniqueIds { get; private set; } = new HashSet<int>();

        /// <summary>
        /// Gets the list of terrain chunks in the ADT file.
        /// </summary>
        public List<TerrainChunk> TerrainChunks { get; private set; } = new List<TerrainChunk>();

        /// <summary>
        /// Gets the list of errors encountered during parsing.
        /// </summary>
        public List<string> Errors { get; private set; } = new List<string>();

        /// <summary>
        /// Creates a new instance of the ADTFile class.
        /// </summary>
        /// <param name="fileData">The raw file data.</param>
        /// <param name="fileName">The name of the file.</param>
        public ADTFile(byte[] fileData, string fileName)
        {
            if (fileData == null)
                throw new ArgumentNullException(nameof(fileData));

            if (string.IsNullOrEmpty(fileName))
                throw new ArgumentException("File name cannot be null or empty.", nameof(fileName));

            FileName = fileName;
            
            try
            {
                // Create the Terrain object with the file data
                Terrain = new Terrain(fileData);
                
                // Ensure MCIN chunk is properly loaded
                if (Terrain.MapChunkOffsets == null)
                {
                    Errors.Add("MCIN chunk is missing or could not be loaded.");
                }
                
                // Extract coordinates from filename
                if (TryExtractCoordinates(fileName, out var xCoord, out var yCoord))
                {
                    XCoord = xCoord;
                    YCoord = yCoord;
                }
                
                // Process the terrain data
                ProcessTerrain();
            }
            catch (Exception ex)
            {
                Errors.Add($"Error parsing ADT file: {ex.Message}");
            }
        }

        /// <summary>
        /// Processes the terrain data to extract references and other information.
        /// </summary>
        private void ProcessTerrain()
        {
            if (Terrain == null)
                return;

            // Process textures from MTEX chunk if available
            var mtexChunk = Terrain.GetType().GetProperty("MTEX")?.GetValue(Terrain) as dynamic;
            if (mtexChunk != null)
            {
                var textureNames = mtexChunk.GetType().GetProperty("Filenames")?.GetValue(mtexChunk) as IEnumerable<string>;
                if (textureNames != null)
                {
                    foreach (var texture in textureNames)
                    {
                        if (!string.IsNullOrEmpty(texture))
                        {
                            TextureReferences.Add(new FileReference
                            {
                                Path = texture,
                                NormalizedPath = NormalizePath(texture),
                                Type = ReferenceType.Texture
                            });
                        }
                    }
                }
            }

            // Process models from MMDX chunk if available
            var mmdxChunk = Terrain.GetType().GetProperty("MMDX")?.GetValue(Terrain) as dynamic;
            if (mmdxChunk != null)
            {
                var modelNames = mmdxChunk.GetType().GetProperty("Filenames")?.GetValue(mmdxChunk) as IEnumerable<string>;
                if (modelNames != null)
                {
                    foreach (var model in modelNames)
                    {
                        if (!string.IsNullOrEmpty(model))
                        {
                            ModelReferences.Add(new FileReference
                            {
                                Path = model,
                                NormalizedPath = NormalizePath(model),
                                Type = ReferenceType.Model
                            });
                        }
                    }
                }
            }

            // Process WMOs from MWMO chunk if available
            var mwmoChunk = Terrain.GetType().GetProperty("MWMO")?.GetValue(Terrain) as dynamic;
            if (mwmoChunk != null)
            {
                var wmoNames = mwmoChunk.GetType().GetProperty("Filenames")?.GetValue(mwmoChunk) as IEnumerable<string>;
                if (wmoNames != null)
                {
                    foreach (var wmo in wmoNames)
                    {
                        if (!string.IsNullOrEmpty(wmo))
                        {
                            WmoReferences.Add(new FileReference
                            {
                                Path = wmo,
                                NormalizedPath = NormalizePath(wmo),
                                Type = ReferenceType.Wmo
                            });
                        }
                    }
                }
            }

            // Process model placements from MDDF chunk if available
            var mddfChunk = Terrain.GetType().GetProperty("MDDF")?.GetValue(Terrain) as dynamic;
            if (mddfChunk != null)
            {
                var modelInstances = mddfChunk.GetType().GetProperty("Entries")?.GetValue(mddfChunk) as System.Collections.IEnumerable;
                if (modelInstances != null)
                {
                    foreach (var instance in modelInstances)
                    {
                        var nameIndexProp = instance.GetType().GetProperty("NameIndex");
                        var positionProp = instance.GetType().GetProperty("Position");
                        var rotationProp = instance.GetType().GetProperty("Rotation");
                        var scaleProp = instance.GetType().GetProperty("Scale");
                        var uniqueIdProp = instance.GetType().GetProperty("UniqueId");
                        
                        if (nameIndexProp != null && positionProp != null && rotationProp != null &&
                            scaleProp != null && uniqueIdProp != null)
                        {
                            int nameIndex = (int)nameIndexProp.GetValue(instance);
                            var position = (Warcraft.NET.Files.Structures.C3Vector)positionProp.GetValue(instance);
                            var rotation = (Warcraft.NET.Files.Structures.C3Vector)rotationProp.GetValue(instance);
                            float scale = (float)scaleProp.GetValue(instance);
                            int uniqueId = (int)uniqueIdProp.GetValue(instance);
                            
                            if (nameIndex < ModelReferences.Count)
                            {
                                ModelPlacements.Add(new ModelPlacement
                                {
                                    ModelReference = ModelReferences[nameIndex],
                                    Position = position,
                                    Rotation = rotation,
                                    Scale = scale,
                                    UniqueId = uniqueId
                                });

                                // Add unique ID
                                if (uniqueId > 0)
                                {
                                    UniqueIds.Add(uniqueId);
                                }
                            }
                        }
                    }
                }
            }

            // Process WMO placements from MODF chunk if available
            var modfChunk = Terrain.GetType().GetProperty("MODF")?.GetValue(Terrain) as dynamic;
            if (modfChunk != null)
            {
                var wmoInstances = modfChunk.GetType().GetProperty("Entries")?.GetValue(modfChunk) as System.Collections.IEnumerable;
                if (wmoInstances != null)
                {
                    foreach (var instance in wmoInstances)
                    {
                        var nameIndexProp = instance.GetType().GetProperty("NameIndex");
                        var positionProp = instance.GetType().GetProperty("Position");
                        var rotationProp = instance.GetType().GetProperty("Rotation");
                        var uniqueIdProp = instance.GetType().GetProperty("UniqueId");
                        
                        if (nameIndexProp != null && positionProp != null && rotationProp != null && uniqueIdProp != null)
                        {
                            int nameIndex = (int)nameIndexProp.GetValue(instance);
                            var position = (Warcraft.NET.Files.Structures.C3Vector)positionProp.GetValue(instance);
                            var rotation = (Warcraft.NET.Files.Structures.C3Vector)rotationProp.GetValue(instance);
                            int uniqueId = (int)uniqueIdProp.GetValue(instance);
                            
                            if (nameIndex < WmoReferences.Count)
                            {
                                WmoPlacements.Add(new WmoPlacement
                                {
                                    WmoReference = WmoReferences[nameIndex],
                                    Position = position,
                                    Rotation = rotation,
                                    UniqueId = uniqueId
                                });

                                // Add unique ID
                                if (uniqueId > 0)
                                {
                                    UniqueIds.Add(uniqueId);
                                }
                            }
                        }
                    }
                }
            }

            // Process MCIN chunk to get terrain chunk offsets
            var mcinChunk = Terrain.MapChunkOffsets;
            if (mcinChunk != null)
            {
                Console.WriteLine($"MCIN chunk found with {mcinChunk.Entries.Count} entries");
            }
            else
            {
                Errors.Add("MCIN chunk is missing or could not be loaded.");
            }
            
            // Process terrain chunks
            if (Terrain.Chunks != null)
            {
                for (int y = 0; y < 16; y++)
                {
                    for (int x = 0; x < 16; x++)
                    {
                        var chunk = Terrain.Chunks[y * 16 + x];
                        if (chunk != null)
                        {
                            // Create a new terrain chunk with coordinates
                            var terrainChunk = new TerrainChunk
                            {
                                X = x,
                                Y = y
                            };
                            
                            // Try to get MCNK header properties using reflection
                            var headerProp = chunk.GetType().GetProperty("Header");
                            if (headerProp != null)
                            {
                                var header = headerProp.GetValue(chunk);
                                if (header != null)
                                {
                                    // Get AreaId
                                    var areaIdProp = header.GetType().GetProperty("AreaId");
                                    if (areaIdProp != null)
                                    {
                                        terrainChunk.AreaId = (int)areaIdProp.GetValue(header);
                                    }
                                    
                                    // Get Flags
                                    var flagsProp = header.GetType().GetProperty("Flags");
                                    if (flagsProp != null)
                                    {
                                        terrainChunk.Flags = (int)flagsProp.GetValue(header);
                                    }
                                    
                                    // Get Holes
                                    var holesProp = header.GetType().GetProperty("Holes");
                                    if (holesProp != null)
                                    {
                                        terrainChunk.Holes = Convert.ToInt32(holesProp.GetValue(header));
                                    }
                                }
                            }

                            // Process texture layers
                            var mclyProp = chunk.GetType().GetProperty("MCLY");
                            if (mclyProp != null)
                            {
                                var mcly = mclyProp.GetValue(chunk);
                                if (mcly != null)
                                {
                                    var layersProp = mcly.GetType().GetProperty("Layers");
                                    if (layersProp != null)
                                    {
                                        var layers = layersProp.GetValue(mcly) as System.Collections.IEnumerable;
                                        if (layers != null)
                                        {
                                            foreach (var layer in layers)
                                            {
                                                var textureIdProp = layer.GetType().GetProperty("TextureId");
                                                var effectIdProp = layer.GetType().GetProperty("EffectId");
                                                var layerFlagsProp = layer.GetType().GetProperty("Flags");
                                                
                                                if (textureIdProp != null && effectIdProp != null && layerFlagsProp != null)
                                                {
                                                    int textureId = Convert.ToInt32(textureIdProp.GetValue(layer));
                                                    int effectId = Convert.ToInt32(effectIdProp.GetValue(layer));
                                                    int layerFlags = Convert.ToInt32(layerFlagsProp.GetValue(layer));
                                                    
                                                    if (textureId < TextureReferences.Count)
                                                    {
                                                        terrainChunk.TextureLayers.Add(new TextureLayer
                                                        {
                                                            TextureReference = TextureReferences[textureId],
                                                            EffectId = effectId,
                                                            Flags = layerFlags
                                                        });
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }

                            // Process doodad references
                            var mcrfProp = chunk.GetType().GetProperty("MCRF");
                            if (mcrfProp != null)
                            {
                                var mcrf = mcrfProp.GetValue(chunk);
                                if (mcrf != null)
                                {
                                    var doodadRefsProp = mcrf.GetType().GetProperty("DoodadReferences");
                                    if (doodadRefsProp != null)
                                    {
                                        var doodadRefs = doodadRefsProp.GetValue(mcrf) as System.Collections.IEnumerable;
                                        if (doodadRefs != null)
                                        {
                                            foreach (var doodadRef in doodadRefs)
                                            {
                                                terrainChunk.DoodadRefs.Add(Convert.ToInt32(doodadRef));
                                            }
                                        }
                                    }
                                }
                            }

                            TerrainChunks.Add(terrainChunk);
                        }
                    }
                }
            }
        }

        /// <summary>
        /// Attempts to extract X and Y coordinates from an ADT filename.
        /// </summary>
        /// <param name="fileName">The filename to parse.</param>
        /// <param name="xCoord">The extracted X coordinate.</param>
        /// <param name="yCoord">The extracted Y coordinate.</param>
        /// <returns>True if coordinates were successfully extracted, false otherwise.</returns>
        private bool TryExtractCoordinates(string fileName, out int xCoord, out int yCoord)
        {
            xCoord = 0;
            yCoord = 0;

            // Extract the base name without extension
            var baseName = Path.GetFileNameWithoutExtension(fileName);

            // Look for patterns like "map_X_Y" or "map_XX_YY"
            var parts = baseName.Split('_');
            if (parts.Length >= 3)
            {
                if (int.TryParse(parts[parts.Length - 2], out xCoord) && 
                    int.TryParse(parts[parts.Length - 1], out yCoord))
                {
                    return true;
                }
            }

            return false;
        }

        /// <summary>
        /// Normalizes a file path for consistent comparison.
        /// </summary>
        /// <param name="path">The path to normalize.</param>
        /// <returns>The normalized path.</returns>
        private string NormalizePath(string path)
        {
            if (string.IsNullOrEmpty(path))
                return string.Empty;

            // Convert to lowercase and replace backslashes with forward slashes
            return path.ToLowerInvariant().Replace('\\', '/');
        }
    }

    /// <summary>
    /// Represents a file reference in an ADT file.
    /// </summary>
    public class FileReference
    {
        /// <summary>
        /// Gets or sets the original path of the file.
        /// </summary>
        public string Path { get; set; }

        /// <summary>
        /// Gets or sets the normalized path for consistent comparison.
        /// </summary>
        public string NormalizedPath { get; set; }

        /// <summary>
        /// Gets or sets the type of the reference.
        /// </summary>
        public ReferenceType Type { get; set; }

        /// <summary>
        /// Gets or sets whether the reference is valid.
        /// </summary>
        public bool IsValid { get; set; } = true;

        /// <summary>
        /// Gets or sets whether the reference exists in the listfile.
        /// </summary>
        public bool ExistsInListfile { get; set; } = true;
    }

    /// <summary>
    /// Represents the type of a file reference.
    /// </summary>
    public enum ReferenceType
    {
        /// <summary>
        /// A texture reference.
        /// </summary>
        Texture,

        /// <summary>
        /// A model reference.
        /// </summary>
        Model,

        /// <summary>
        /// A WMO (World Map Object) reference.
        /// </summary>
        Wmo
    }

    /// <summary>
    /// Represents a model placement in an ADT file.
    /// </summary>
    public class ModelPlacement
    {
        /// <summary>
        /// Gets or sets the reference to the model file.
        /// </summary>
        public FileReference ModelReference { get; set; }

        /// <summary>
        /// Gets or sets the position of the model.
        /// </summary>
        public Warcraft.NET.Files.Structures.C3Vector Position { get; set; }

        /// <summary>
        /// Gets or sets the rotation of the model.
        /// </summary>
        public Warcraft.NET.Files.Structures.C3Vector Rotation { get; set; }

        /// <summary>
        /// Gets or sets the scale of the model.
        /// </summary>
        public float Scale { get; set; }

        /// <summary>
        /// Gets or sets the unique ID of the model.
        /// </summary>
        public int UniqueId { get; set; }
    }

    /// <summary>
    /// Represents a WMO placement in an ADT file.
    /// </summary>
    public class WmoPlacement
    {
        /// <summary>
        /// Gets or sets the reference to the WMO file.
        /// </summary>
        public FileReference WmoReference { get; set; }

        /// <summary>
        /// Gets or sets the position of the WMO.
        /// </summary>
        public Warcraft.NET.Files.Structures.C3Vector Position { get; set; }

        /// <summary>
        /// Gets or sets the rotation of the WMO.
        /// </summary>
        public Warcraft.NET.Files.Structures.C3Vector Rotation { get; set; }

        /// <summary>
        /// Gets or sets the unique ID of the WMO.
        /// </summary>
        public int UniqueId { get; set; }
    }

    /// <summary>
    /// Represents a terrain chunk in an ADT file.
    /// </summary>
    public class TerrainChunk
    {
        /// <summary>
        /// Gets or sets the X coordinate of the chunk.
        /// </summary>
        public int X { get; set; }

        /// <summary>
        /// Gets or sets the Y coordinate of the chunk.
        /// </summary>
        public int Y { get; set; }

        /// <summary>
        /// Gets or sets the area ID of the chunk.
        /// </summary>
        public int AreaId { get; set; }

        /// <summary>
        /// Gets or sets the flags of the chunk.
        /// </summary>
        public int Flags { get; set; }

        /// <summary>
        /// Gets or sets the holes in the chunk.
        /// </summary>
        public int Holes { get; set; }

        /// <summary>
        /// Gets or sets the texture layers in the chunk.
        /// </summary>
        public List<TextureLayer> TextureLayers { get; set; } = new List<TextureLayer>();

        /// <summary>
        /// Gets or sets the doodad references in the chunk.
        /// </summary>
        public List<int> DoodadRefs { get; set; } = new List<int>();
    }

    /// <summary>
    /// Represents a texture layer in a terrain chunk.
    /// </summary>
    public class TextureLayer
    {
        /// <summary>
        /// Gets or sets the reference to the texture file.
        /// </summary>
        public FileReference TextureReference { get; set; }

        /// <summary>
        /// Gets or sets the effect ID of the texture layer.
        /// </summary>
        public int EffectId { get; set; }

        /// <summary>
        /// Gets or sets the flags of the texture layer.
        /// </summary>
        public int Flags { get; set; }
    }
}