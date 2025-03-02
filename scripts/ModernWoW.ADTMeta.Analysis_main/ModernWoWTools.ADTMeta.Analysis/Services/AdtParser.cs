using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Numerics;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using ModernWoWTools.ADTMeta.Analysis.Models;
using ModernWoWTools.ADTMeta.Analysis.Utilities;
using Warcraft.NET.Files.ADT.Terrain.Wotlk;
using Warcraft.NET.Files.Structures;

namespace ModernWoWTools.ADTMeta.Analysis.Services
{
    /// <summary>
    /// Service for parsing ADT files using Warcraft.NET.
    /// </summary>
    public class AdtParser
    {
        private readonly ILoggingService _logger;

        /// <summary>
        /// Creates a new instance of the AdtParser class.
        /// </summary>
        /// <param name="logger">The logging service to use.</param>
        public AdtParser(ILoggingService logger)
        {
            _logger = logger ?? throw new ArgumentNullException(nameof(logger));
        }

        /// <summary>
        /// Parses an ADT file and extracts analysis data.
        /// </summary>
        /// <param name="filePath">The path to the ADT file.</param>
        /// <returns>The analysis result.</returns>
        public async Task<AdtAnalysisResult> ParseAdtFileAsync(string filePath)
        {
            _logger.LogInfo($"Parsing ADT file: {Path.GetFileName(filePath)}");

            var result = new AdtAnalysisResult
            {
                FileName = Path.GetFileName(filePath),
                FilePath = filePath
            };

            // Extract coordinates from filename
            if (PathUtility.TryExtractCoordinates(result.FileName, out var xCoord, out var yCoord))
            {
                result.XCoord = xCoord;
                result.YCoord = yCoord;
            }

            try
            {
                // Parse ADT file using Warcraft.NET
                var adtData = await Task.Run(() => new Terrain(File.ReadAllBytes(filePath)));
                result.AdtVersion = adtData.Version?.Version ?? 0;

                // Extract header information
                if (adtData.Header != null)
                {
                    result.Header.Flags = adtData.Header.Flags;
                    
                    // Count references and placements
                    result.Header.TextureLayerCount = adtData.Textures?.Filenames?.Count ?? 0;
                    result.Header.ModelReferenceCount = adtData.Models?.Filenames?.Count ?? 0;
                    result.Header.WmoReferenceCount = adtData.WorldModelObjects?.Filenames?.Count ?? 0;
                    result.Header.ModelPlacementCount = adtData.ModelPlacementInfo?.MDDFEntries?.Count ?? 0;
                    result.Header.WmoPlacementCount = adtData.WorldModelObjectPlacementInfo?.MODFEntries?.Count ?? 0;
                    
                    // Count terrain chunks
                    result.Header.TerrainChunkCount = adtData.MapChunks?.Count ?? 0;
                }

                // Process textures
                if (adtData.Textures?.Filenames != null)
                {
                    foreach (var texture in adtData.Textures.Filenames)
                    {
                        if (string.IsNullOrWhiteSpace(texture))
                            continue;

                        var reference = new FileReference
                        {
                            OriginalPath = texture,
                            NormalizedPath = PathUtility.NormalizePath(texture),
                            ReferenceType = FileReferenceType.Texture
                        };

                        result.TextureReferences.Add(reference);
                    }
                }

                // Process M2 models
                if (adtData.Models?.Filenames != null)
                {
                    foreach (var model in adtData.Models.Filenames)
                    {
                        if (string.IsNullOrWhiteSpace(model))
                            continue;

                        var reference = new FileReference
                        {
                            OriginalPath = model,
                            NormalizedPath = PathUtility.NormalizePath(model),
                            ReferenceType = FileReferenceType.Model
                        };

                        // Convert .mdx to .m2 if needed
                        if (reference.NormalizedPath.EndsWith(".mdx", StringComparison.OrdinalIgnoreCase))
                        {
                            reference.NormalizedPath = reference.NormalizedPath.Substring(0, reference.NormalizedPath.Length - 4) + ".m2";
                        }

                        result.ModelReferences.Add(reference);
                    }
                }

                // Process WMO models
                if (adtData.WorldModelObjects?.Filenames != null)
                {
                    foreach (var wmo in adtData.WorldModelObjects.Filenames)
                    {
                        if (string.IsNullOrWhiteSpace(wmo))
                            continue;

                        var reference = new FileReference
                        {
                            OriginalPath = wmo,
                            NormalizedPath = PathUtility.NormalizePath(wmo),
                            ReferenceType = FileReferenceType.WorldModel
                        };

                        result.WmoReferences.Add(reference);
                    }
                }

                // Process model instances
                if (adtData.ModelPlacementInfo?.MDDFEntries != null)
                {
                    foreach (var instance in adtData.ModelPlacementInfo.MDDFEntries)
                    {
                        var placement = new ModelPlacement
                        {
                            UniqueId = (int)instance.UniqueID,
                            NameId = (int)instance.NameId,
                            Position = new Vector3(instance.Position.X, instance.Position.Y, instance.Position.Z),
                            Rotation = new Vector3(instance.Rotation.Pitch, instance.Rotation.Yaw, instance.Rotation.Roll),
                            Scale = instance.ScalingFactor / 1024f,
                            Flags = (int)instance.Flags
                        };

                        // Get model name
                        if ((int)instance.NameId >= 0 && result.ModelReferences.Count > (int)instance.NameId)
                        {
                            placement.Name = result.ModelReferences[(int)instance.NameId].OriginalPath;
                        }
                        else
                        {
                            placement.Name = $"<unknown model {(int)instance.NameId}>";
                        }

                        result.ModelPlacements.Add(placement);
                        result.UniqueIds.Add((int)instance.UniqueID);
                    }
                }

                // Process WMO instances
                if (adtData.WorldModelObjectPlacementInfo?.MODFEntries != null)
                {
                    foreach (var instance in adtData.WorldModelObjectPlacementInfo.MODFEntries)
                    {
                        var placement = new WmoPlacement
                        {
                            UniqueId = instance.UniqueId,
                            NameId = (int)instance.NameId,
                            Position = new Vector3(instance.Position.X, instance.Position.Y, instance.Position.Z),
                            Rotation = new Vector3(instance.Rotation.Pitch, instance.Rotation.Yaw, instance.Rotation.Roll),
                            Flags = (int)instance.Flags,
                            DoodadSet = instance.DoodadSet,
                            NameSet = instance.NameSet
                        };

                        // Get WMO name
                        if ((int)instance.NameId >= 0 && result.WmoReferences.Count > (int)instance.NameId)
                        {
                            placement.Name = result.WmoReferences[(int)instance.NameId].OriginalPath;
                        }
                        else
                        {
                            placement.Name = $"<unknown WMO {(int)instance.NameId}>";
                        }

                        result.WmoPlacements.Add(placement);
                        result.UniqueIds.Add(instance.UniqueId);
                    }
                }

                // Process terrain chunks
                if (adtData.MapChunks != null)
                {
                    for (int i = 0; i < adtData.MapChunks.Count; i++)
                    {
                        var chunk = adtData.MapChunks[i];
                        if (chunk == null)
                            continue;

                        // Calculate chunk position in the grid (0-15, 0-15)
                        int chunkX = i % 16;
                        int chunkY = i / 16;

                        var terrainChunk = new TerrainChunk
                        {
                            Position = new Vector2(chunkX, chunkY),
                            WorldPosition = new Vector3(chunk.Header.Position.X, chunk.Header.Position.Y, chunk.Header.Position.Z),
                            AreaId = (int)chunk.Header.AreaId,
                            Flags = chunk.Header.Flags,
                            Holes = chunk.Header.Holes,
                            LiquidLevel = chunk.Header.LiquidLevel,
                            
                        };

                        // Extract height data
                        if (chunk.HeightMap != null)
                        {
                            foreach (var height in chunk.HeightMap.Heights)
                            {
                                terrainChunk.Heights.Add(height);
                            }
                        }

                        // Extract normal data if available
                        if (chunk.NormalMap != null && chunk.NormalMap.Normals != null)
                        {
                            foreach (var normal in chunk.NormalMap.Normals)
                            {
                                terrainChunk.Normals.Add(new Vector3(normal.X, normal.Y, normal.Z));
                            }
                        }

                        // Extract texture layers
                        if (chunk.TextureLayers != null)
                        {
                            foreach (var layer in chunk.TextureLayers)
                            {
                                var textureLayer = new TextureLayer
                                {
                                    TextureId = (int)layer.TextureId,
                                    Flags = layer.Flags,
                                    EffectId = (int)layer.EffectId,
                                    AlphaMapOffset = (int)layer.AlphaMapOffset,
                                    AlphaMapSize = (int)layer.AlphaMapSize
                                };
                                
                                // Get texture name if available
                                if ((int)layer.TextureId >= 0 && result.TextureReferences.Count > (int)layer.TextureId)
                                {
                                    textureLayer.TextureName = result.TextureReferences[(int)layer.TextureId].OriginalPath;
                                }
                                else
                                {
                                    textureLayer.TextureName = $"<unknown texture {(int)layer.TextureId}>";
                                }

                                terrainChunk.TextureLayers.Add(textureLayer);
                            }
                        }
                        
                        // Extract alpha maps if available
                        if (chunk.AlphaMaps != null && chunk.AlphaMaps.Count > 0)
                        {
                            for (int i = 0; i < Math.Min(terrainChunk.TextureLayers.Count, chunk.AlphaMaps.Count); i++)
                            {
                                if (i < terrainChunk.TextureLayers.Count && chunk.AlphaMaps[i] != null)
                                {
                                    terrainChunk.TextureLayers[i].AlphaMap = chunk.AlphaMaps[i];
                                }
                            }
                        }

                        // Extract doodad references
                        if (chunk.DoodadReferences != null && chunk.DoodadReferences.Indices != null)
                        {
                            foreach (var doodadRef in chunk.DoodadReferences.Indices)
                            {
                                terrainChunk.DoodadRefs.Add((int)doodadRef);
                            }
                        }

                        result.TerrainChunks.Add(terrainChunk);
                    }
                }

                _logger.LogInfo($"Successfully parsed {result.FileName}: " +
                               $"{result.TextureReferences.Count} textures, " +
                               $"{result.ModelReferences.Count} models, " +
                               $"{result.WmoReferences.Count} WMOs, " +
                               $"{result.TerrainChunks.Count} terrain chunks, " +
                               $"{result.UniqueIds.Count} unique IDs");

                return result;
            }
            catch (Exception ex)
            {
                _logger.LogError($"Error parsing {result.FileName}: {ex.Message}");
                result.Errors.Add(ex.Message);
                return result;
            }
        }
    }
}