using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using Warcraft.NET.Files.ADT;
using Warcraft.NET.Files.ADT.Entries;
using Warcraft.NET.Files.ADT.Terrain;
using Warcraft.NET.Files.ADT.Terrain.MCNK;
using Warcraft.NET.Files.Structures;

namespace WarcraftAnalyzer.Files.ADT
{
    /// <summary>
    /// Represents a modern split ADT (Azeroth Terrain) file with its associated _obj and _tex files.
    /// </summary>
    public class SplitADTFile
    {
        /// <summary>
        /// Gets the main terrain data from the ADT file.
        /// </summary>
        public object Terrain { get; private set; }

        /// <summary>
        /// Gets the object data from the _obj file.
        /// </summary>
        public object ObjectData { get; private set; }

        /// <summary>
        /// Gets the texture data from the _tex file.
        /// </summary>
        public object TextureData { get; private set; }

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
        /// Creates a new instance of the SplitADTFile class.
        /// </summary>
        /// <param name="mainFileData">The raw file data for the main ADT file.</param>
        /// <param name="objFileData">The raw file data for the _obj ADT file.</param>
        /// <param name="texFileData">The raw file data for the _tex ADT file.</param>
        /// <param name="fileName">The name of the file.</param>
        public SplitADTFile(byte[] mainFileData, byte[] objFileData, byte[] texFileData, string fileName)
        {
            if (mainFileData == null)
                throw new ArgumentNullException(nameof(mainFileData));

            if (string.IsNullOrEmpty(fileName))
                throw new ArgumentException("File name cannot be null or empty.", nameof(fileName));

            FileName = fileName;
            
            try
            {
                // Create the Terrain objects with the file data using reflection
                Type terrainType = Type.GetType("Warcraft.NET.Files.ADT.Terrain.Terrain, Warcraft.NET");
                if (terrainType == null)
                {
                    // Try to find the type in loaded assemblies
                    foreach (var assembly in AppDomain.CurrentDomain.GetAssemblies())
                    {
                        terrainType = assembly.GetType("Warcraft.NET.Files.ADT.Terrain.Terrain");
                        if (terrainType != null)
                            break;
                    }
                }

                if (terrainType == null)
                {
                    throw new InvalidOperationException("Could not find Terrain type in Warcraft.NET");
                }

                // Create instances using reflection
                Terrain = Activator.CreateInstance(terrainType, new object[] { mainFileData });
                
                if (objFileData != null)
                {
                    ObjectData = Activator.CreateInstance(terrainType, new object[] { objFileData });
                }
                
                if (texFileData != null)
                {
                    TextureData = Activator.CreateInstance(terrainType, new object[] { texFileData });
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
                Errors.Add($"Error parsing Split ADT file: {ex.Message}");
            }
        }

        /// <summary>
        /// Processes the terrain data to extract references and other information.
        /// </summary>
        private void ProcessTerrain()
        {
            if (Terrain == null)
                return;

            // Process textures from MTEX chunk if available (from main or tex file)
            ProcessTextureReferences();
            
            // Process models from MMDX chunk if available (from main or obj file)
            ProcessModelReferences();
            
            // Process WMOs from MWMO chunk if available (from main or obj file)
            ProcessWmoReferences();
            
            // Process model placements from MDDF chunk if available (from main or obj file)
            ProcessModelPlacements();
            
            // Process WMO placements from MODF chunk if available (from main or obj file)
            ProcessWmoPlacements();
            
            // Process terrain chunks
            ProcessTerrainChunks();
        }

        /// <summary>
        /// Processes texture references from MTEX chunk.
        /// </summary>
        private void ProcessTextureReferences()
        {
            // Try main file first
            var mtexChunk = Terrain.GetType().GetProperty("MTEX")?.GetValue(Terrain) as dynamic;
            if (mtexChunk == null && TextureData != null)
            {
                // Try texture file if main file doesn't have MTEX
                mtexChunk = TextureData.GetType().GetProperty("MTEX")?.GetValue(TextureData) as dynamic;
            }

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
        }

        /// <summary>
        /// Processes model references from MMDX chunk.
        /// </summary>
        private void ProcessModelReferences()
        {
            // Try main file first
            var mmdxChunk = Terrain.GetType().GetProperty("MMDX")?.GetValue(Terrain) as dynamic;
            if (mmdxChunk == null && ObjectData != null)
            {
                // Try object file if main file doesn't have MMDX
                mmdxChunk = ObjectData.GetType().GetProperty("MMDX")?.GetValue(ObjectData) as dynamic;
            }

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
        }

        /// <summary>
        /// Processes WMO references from MWMO chunk.
        /// </summary>
        private void ProcessWmoReferences()
        {
            // Try main file first
            var mwmoChunk = Terrain.GetType().GetProperty("MWMO")?.GetValue(Terrain) as dynamic;
            if (mwmoChunk == null && ObjectData != null)
            {
                // Try object file if main file doesn't have MWMO
                mwmoChunk = ObjectData.GetType().GetProperty("MWMO")?.GetValue(ObjectData) as dynamic;
            }

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
        }

        /// <summary>
        /// Processes model placements from MDDF chunk.
        /// </summary>
        private void ProcessModelPlacements()
        {
            // Try main file first
            var mddfChunk = Terrain.GetType().GetProperty("MDDF")?.GetValue(Terrain) as dynamic;
            if (mddfChunk == null && ObjectData != null)
            {
                // Try object file if main file doesn't have MDDF
                mddfChunk = ObjectData.GetType().GetProperty("MDDF")?.GetValue(ObjectData) as dynamic;
            }

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
                            var position = (C3Vector)positionProp.GetValue(instance);
                            var rotation = (C3Vector)rotationProp.GetValue(instance);
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
        }

        /// <summary>
        /// Processes WMO placements from MODF chunk.
        /// </summary>
        private void ProcessWmoPlacements()
        {
            // Try main file first
            var modfChunk = Terrain.GetType().GetProperty("MODF")?.GetValue(Terrain) as dynamic;
            if (modfChunk == null && ObjectData != null)
            {
                // Try object file if main file doesn't have MODF
                modfChunk = ObjectData.GetType().GetProperty("MODF")?.GetValue(ObjectData) as dynamic;
            }

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
                            var position = (C3Vector)positionProp.GetValue(instance);
                            var rotation = (C3Vector)rotationProp.GetValue(instance);
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
        }

        /// <summary>
        /// Processes terrain chunks from MCNK chunks.
        /// </summary>
        private void ProcessTerrainChunks()
        {
            // Process terrain chunks using reflection
            if (Terrain != null)
            {
                var chunksProperty = Terrain.GetType().GetProperty("Chunks");
                if (chunksProperty == null)
                {
                    Errors.Add("Could not find Chunks property on Terrain object");
                    return;
                }

                var chunks = chunksProperty.GetValue(Terrain) as Array;
                if (chunks == null)
                {
                    Errors.Add("Chunks property is null or not an array");
                    return;
                }

                for (int y = 0; y < 16; y++)
                {
                    for (int x = 0; x < 16; x++)
                    {
                        var chunk = chunks.GetValue(y * 16 + x);
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
                            ProcessTextureLayersForChunk(chunk, terrainChunk);

                            // Process doodad references
                            ProcessDoodadReferencesForChunk(chunk, terrainChunk);

                            TerrainChunks.Add(terrainChunk);
                        }
                    }
                }
            }
        }

        /// <summary>
        /// Processes texture layers for a terrain chunk.
        /// </summary>
        private void ProcessTextureLayersForChunk(dynamic chunk, TerrainChunk terrainChunk)
        {
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
        }

        /// <summary>
        /// Processes doodad references for a terrain chunk.
        /// </summary>
        private void ProcessDoodadReferencesForChunk(dynamic chunk, TerrainChunk terrainChunk)
        {
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
            
            // Remove _obj or _tex suffix if present
            baseName = baseName.Replace("_obj", "").Replace("_tex", "");

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
}