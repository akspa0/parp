using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using ModernWoWTools.ADTMeta.Analysis.Models;
using ModernWoWTools.ADTMeta.Analysis.Utilities;

namespace ModernWoWTools.ADTMeta.Analysis.Services
{
    /// <summary>
    /// Service for generating CSV reports for terrain data.
    /// </summary>
    public class TerrainDataCsvGenerator
    {
        private readonly ILoggingService _logger;

        /// <summary>
        /// Creates a new instance of the TerrainDataCsvGenerator class.
        /// </summary>
        /// <param name="logger">The logging service to use.</param>
        public TerrainDataCsvGenerator(ILoggingService logger)
        {
            _logger = logger ?? throw new ArgumentNullException(nameof(logger));
        }

        /// <summary>
        /// Generates all CSV reports for terrain data.
        /// </summary>
        /// <param name="results">The ADT analysis results.</param>
        /// <param name="outputDirectory">The directory to write reports to.</param>
        /// <returns>A task representing the asynchronous operation.</returns>
        public async Task GenerateAllCsvReportsAsync(List<AdtAnalysisResult> results, string outputDirectory)
        {
            if (results == null)
                throw new ArgumentNullException(nameof(results));
            if (string.IsNullOrEmpty(outputDirectory))
                throw new ArgumentException("Output directory cannot be null or empty.", nameof(outputDirectory));

            // Create output directory if it doesn't exist
            if (!Directory.Exists(outputDirectory))
            {
                Directory.CreateDirectory(outputDirectory);
            }

            // Create a CSV directory
            var csvDirectory = Path.Combine(outputDirectory, "csv");
            if (!Directory.Exists(csvDirectory))
            {
                Directory.CreateDirectory(csvDirectory);
            }

            _logger.LogInfo($"Generating terrain data CSV reports in {csvDirectory}...");

            // Generate heightmap CSV
            await GenerateHeightmapCsvAsync(results, csvDirectory);

            // Generate normal vectors CSV
            await GenerateNormalVectorsCsvAsync(results, csvDirectory);

            // Generate texture layer CSV
            await GenerateTextureLayerCsvAsync(results, csvDirectory);

            // Generate alpha maps CSV
            await GenerateAlphaMapsCsvAsync(results, csvDirectory);

            _logger.LogInfo("Terrain data CSV report generation complete.");
        }

        /// <summary>
        /// Generates a CSV file containing heightmap data.
        /// </summary>
        /// <param name="results">The ADT analysis results.</param>
        /// <param name="outputDirectory">The directory to write the file to.</param>
        /// <returns>A task representing the asynchronous operation.</returns>
        private async Task GenerateHeightmapCsvAsync(List<AdtAnalysisResult> results, string outputDirectory)
        {
            var filePath = Path.Combine(outputDirectory, "heightmaps.csv");
            _logger.LogDebug($"Generating heightmap CSV: {filePath}");

            using (var writer = new StreamWriter(filePath, false, Encoding.UTF8))
            {
                // Write header
                await writer.WriteLineAsync("FileName,ChunkX,ChunkY,WorldX,WorldY,WorldZ,X,Y,Height");

                // Write data
                foreach (var result in results)
                {
                    foreach (var chunk in result.TerrainChunks)
                    {
                        for (int y = 0; y < 17; y++)
                        {
                            for (int x = 0; x < 17; x++)
                            {
                                int index = y * 17 + x;
                                if (index < chunk.Heights.Count)
                                {
                                    await writer.WriteLineAsync($"{result.FileName},{chunk.Position.X},{chunk.Position.Y},{chunk.WorldPosition.X},{chunk.WorldPosition.Y},{chunk.WorldPosition.Z},{x},{y},{chunk.Heights[index]}");
                                }
                            }
                        }
                    }
                }
            }
        }

        /// <summary>
        /// Generates a CSV file containing normal vector data.
        /// </summary>
        /// <param name="results">The ADT analysis results.</param>
        /// <param name="outputDirectory">The directory to write the file to.</param>
        /// <returns>A task representing the asynchronous operation.</returns>
        private async Task GenerateNormalVectorsCsvAsync(List<AdtAnalysisResult> results, string outputDirectory)
        {
            var filePath = Path.Combine(outputDirectory, "normal_vectors.csv");
            _logger.LogDebug($"Generating normal vectors CSV: {filePath}");

            using (var writer = new StreamWriter(filePath, false, Encoding.UTF8))
            {
                // Write header
                await writer.WriteLineAsync("FileName,ChunkX,ChunkY,WorldX,WorldY,WorldZ,Index,NormalX,NormalY,NormalZ");

                // Write data
                foreach (var result in results)
                {
                    foreach (var chunk in result.TerrainChunks)
                    {
                        for (int i = 0; i < chunk.Normals.Count; i++)
                        {
                            var normal = chunk.Normals[i];
                            await writer.WriteLineAsync($"{result.FileName},{chunk.Position.X},{chunk.Position.Y},{chunk.WorldPosition.X},{chunk.WorldPosition.Y},{chunk.WorldPosition.Z},{i},{normal.X},{normal.Y},{normal.Z}");
                        }
                    }
                }
            }
        }

        /// <summary>
        /// Generates a CSV file containing texture layer data.
        /// </summary>
        /// <param name="results">The ADT analysis results.</param>
        /// <param name="outputDirectory">The directory to write the file to.</param>
        /// <returns>A task representing the asynchronous operation.</returns>
        private async Task GenerateTextureLayerCsvAsync(List<AdtAnalysisResult> results, string outputDirectory)
        {
            var filePath = Path.Combine(outputDirectory, "texture_layers.csv");
            _logger.LogDebug($"Generating texture layer CSV: {filePath}");

            using (var writer = new StreamWriter(filePath, false, Encoding.UTF8))
            {
                // Write header
                await writer.WriteLineAsync("FileName,ChunkX,ChunkY,WorldX,WorldY,WorldZ,LayerIndex,TextureId,TextureName,Flags,EffectId,AlphaMapOffset,AlphaMapSize");

                // Write data
                foreach (var result in results)
                {
                    foreach (var chunk in result.TerrainChunks)
                    {
                        for (int i = 0; i < chunk.TextureLayers.Count; i++)
                        {
                            var layer = chunk.TextureLayers[i];
                            await writer.WriteLineAsync($"{result.FileName},{chunk.Position.X},{chunk.Position.Y},{chunk.WorldPosition.X},{chunk.WorldPosition.Y},{chunk.WorldPosition.Z},{i},{layer.TextureId},\"{layer.TextureName}\",{layer.Flags},{layer.EffectId},{layer.AlphaMapOffset},{layer.AlphaMapSize}");
                        }
                    }
                }
            }
        }

        /// <summary>
        /// Generates a CSV file containing alpha map data.
        /// </summary>
        /// <param name="results">The ADT analysis results.</param>
        /// <param name="outputDirectory">The directory to write the file to.</param>
        /// <returns>A task representing the asynchronous operation.</returns>
        private async Task GenerateAlphaMapsCsvAsync(List<AdtAnalysisResult> results, string outputDirectory)
        {
            var filePath = Path.Combine(outputDirectory, "alpha_maps.csv");
            _logger.LogDebug($"Generating alpha maps CSV: {filePath}");

            using (var writer = new StreamWriter(filePath, false, Encoding.UTF8))
            {
                // Write header
                await writer.WriteLineAsync("FileName,ChunkX,ChunkY,LayerIndex,X,Y,Alpha");

                // Write data
                foreach (var result in results)
                {
                    foreach (var chunk in result.TerrainChunks)
                    {
                        for (int layerIndex = 0; layerIndex < chunk.TextureLayers.Count; layerIndex++)
                        {
                            var layer = chunk.TextureLayers[layerIndex];
                            if (layer.AlphaMap != null && layer.AlphaMap.Length > 0)
                            {
                                // Alpha maps are typically 64x64 or 128x128
                                int size = (int)Math.Sqrt(layer.AlphaMap.Length);
                                if (size * size == layer.AlphaMap.Length)
                                {
                                    for (int y = 0; y < size; y++)
                                    {
                                        for (int x = 0; x < size; x++)
                                        {
                                            int index = y * size + x;
                                            if (index < layer.AlphaMap.Length)
                                            {
                                                await writer.WriteLineAsync($"{result.FileName},{chunk.Position.X},{chunk.Position.Y},{layerIndex},{x},{y},{layer.AlphaMap[index]}");
                                            }
                                        }
                                    }
                                }
                                else
                                {
                                    // If not a perfect square, just output the raw data
                                    for (int i = 0; i < layer.AlphaMap.Length; i++)
                                    {
                                        await writer.WriteLineAsync($"{result.FileName},{chunk.Position.X},{chunk.Position.Y},{layerIndex},0,{i},{layer.AlphaMap[i]}");
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}