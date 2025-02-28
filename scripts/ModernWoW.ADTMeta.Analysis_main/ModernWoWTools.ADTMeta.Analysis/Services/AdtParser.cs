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

                _logger.LogInfo($"Successfully parsed {result.FileName}: " +
                               $"{result.TextureReferences.Count} textures, " +
                               $"{result.ModelReferences.Count} models, " +
                               $"{result.WmoReferences.Count} WMOs, " +
                               $"{result.UniqueIds.Count} unique IDs");

                return result;
            }
            catch (Exception ex)
            {
                _logger.LogError($"Error parsing {result.FileName}: {ex.Message}");
                throw;
            }
        }
    }
}