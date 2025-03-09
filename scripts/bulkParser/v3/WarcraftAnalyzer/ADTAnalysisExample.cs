using System;
using System.IO;
using System.Collections.Generic;
using WarcraftAnalyzer.Files.ADT;
using WarcraftAnalyzer.Files.Serialization;
using Warcraft.NET.Files.ADT;

namespace WarcraftAnalyzer.Examples
{
    /// <summary>
    /// Example program demonstrating how to use the WarcraftAnalyzer library to analyze ADT files.
    /// </summary>
    public class ADTAnalysisExample
    {
        public static void Main(string[] args)
        {
            if (args.Length < 1)
            {
                Console.WriteLine("Usage: ADTAnalysisExample <path_to_adt_file> [output_directory]");
                return;
            }

            string adtFilePath = args[0];
            string outputDirectory = args.Length > 1 ? args[1] : Path.GetDirectoryName(adtFilePath);
            
            // Ensure output directory exists
            if (!Directory.Exists(outputDirectory))
            {
                Directory.CreateDirectory(outputDirectory);
            }

            try
            {
                // Step 1: Load the ADT file
                Console.WriteLine($"Loading ADT file: {adtFilePath}");
                byte[] fileData = File.ReadAllBytes(adtFilePath);
                
                // Create ADTFile object which parses the file
                var adtFile = new ADTFile(fileData, Path.GetFileName(adtFilePath));
                Console.WriteLine($"ADT file loaded successfully. Coordinates: {adtFile.XCoord}_{adtFile.YCoord}");
                
                // Step 2: Extract and display information from the ADT file
                DisplayADTInfo(adtFile);
                
                // Step 3: Serialize to JSON
                string jsonOutputPath = Path.Combine(outputDirectory, Path.GetFileNameWithoutExtension(adtFilePath) + ".json");
                Console.WriteLine($"Serializing ADT to JSON: {jsonOutputPath}");
                string json = JsonSerializer.SerializeADT(adtFile);
                File.WriteAllText(jsonOutputPath, json);
                Console.WriteLine("JSON serialization completed successfully");
                
                // Step 4: Export terrain to OBJ if terrain data exists
                if (adtFile.TerrainChunks.Count > 0 && adtFile.Terrain?.Chunks != null && adtFile.Terrain.Chunks.Length > 0)
                {
                    string objOutputPath = Path.Combine(outputDirectory, Path.GetFileNameWithoutExtension(adtFilePath) + ".obj");
                    Console.WriteLine($"Exporting terrain to OBJ: {objOutputPath}");
                    ExportTerrainToObj(adtFile, objOutputPath);
                    Console.WriteLine("OBJ export completed successfully");
                }
                
                Console.WriteLine("Analysis completed successfully");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error analyzing ADT file: {ex.Message}");
                Console.WriteLine($"Stack trace: {ex.StackTrace}");
            }
        }
        
        /// <summary>
        /// Displays information about the ADT file.
        /// </summary>
        /// <param name="adtFile">The ADT file to display information about.</param>
        private static void DisplayADTInfo(ADTFile adtFile)
        {
            Console.WriteLine("\n=== ADT File Information ===");
            Console.WriteLine($"File Name: {adtFile.FileName}");
            Console.WriteLine($"Coordinates: {adtFile.XCoord}_{adtFile.YCoord}");
            
            // Display texture references
            Console.WriteLine($"\nTexture References: {adtFile.TextureReferences.Count}");
            foreach (var texture in adtFile.TextureReferences)
            {
                Console.WriteLine($"  - {texture.Path}");
            }
            
            // Display model references
            Console.WriteLine($"\nModel References: {adtFile.ModelReferences.Count}");
            foreach (var model in adtFile.ModelReferences)
            {
                Console.WriteLine($"  - {model.Path}");
            }
            
            // Display WMO references
            Console.WriteLine($"\nWMO References: {adtFile.WmoReferences.Count}");
            foreach (var wmo in adtFile.WmoReferences)
            {
                Console.WriteLine($"  - {wmo.Path}");
            }
            
            // Display model placements
            Console.WriteLine($"\nModel Placements: {adtFile.ModelPlacements.Count}");
            
            // Display WMO placements
            Console.WriteLine($"\nWMO Placements: {adtFile.WmoPlacements.Count}");
            
            // Display terrain chunks
            Console.WriteLine($"\nTerrain Chunks: {adtFile.TerrainChunks.Count}");
            
            // Display unique IDs
            Console.WriteLine($"\nUnique IDs: {adtFile.UniqueIds.Count}");
            
            Console.WriteLine("===========================\n");
        }
        
        /// <summary>
        /// Exports terrain data from an ADT file to OBJ format.
        /// </summary>
        /// <param name="adtFile">The ADT file containing terrain data.</param>
        /// <param name="outputPath">The path to write the OBJ file to.</param>
        private static void ExportTerrainToObj(ADTFile adtFile, string outputPath)
        {
            using var writer = new StreamWriter(outputPath);
            
            // Write OBJ header
            writer.WriteLine("# Terrain data exported from ADT file");
            writer.WriteLine($"# File: {adtFile.FileName}");
            writer.WriteLine($"# Coordinates: {adtFile.XCoord}_{adtFile.YCoord}");
            writer.WriteLine();
            
            // Write material library reference
            writer.WriteLine("mtllib terrain.mtl");
            writer.WriteLine();
            
            // Track vertex indices (OBJ indices are 1-based)
            int vertexIndex = 1;
            
            // Process each terrain chunk
            foreach (var terrainChunk in adtFile.TerrainChunks)
            {
                // Skip chunks with no terrain data
                if (terrainChunk == null)
                    continue;
                
                // Write chunk header
                writer.WriteLine($"# Chunk {terrainChunk.X}_{terrainChunk.Y}");
                writer.WriteLine($"g chunk_{terrainChunk.X}_{terrainChunk.Y}");
                
                // Get height data from the Terrain object
                var heightData = adtFile.Terrain.Chunks[terrainChunk.Y * 16 + terrainChunk.X]?.Heightmap?.Vertices;
                if (heightData == null)
                    continue;
                
                // Write vertices
                for (int y = 0; y < 17; y++)
                {
                    for (int x = 0; x < 17; x++)
                    {
                        // Calculate world coordinates
                        float worldX = (adtFile.XCoord * 533.33333f) + (terrainChunk.X * 33.33333f) + (x * 33.33333f / 16);
                        float worldZ = (adtFile.YCoord * 533.33333f) + (terrainChunk.Y * 33.33333f) + (y * 33.33333f / 16);
                        float worldY = heightData[y * 17 + x];
                        
                        // Write vertex
                        writer.WriteLine($"v {worldX} {worldY} {worldZ}");
                    }
                }
                
                // Write texture coordinates
                for (int y = 0; y < 17; y++)
                {
                    for (int x = 0; x < 17; x++)
                    {
                        float u = x / 16.0f;
                        float v = y / 16.0f;
                        writer.WriteLine($"vt {u} {v}");
                    }
                }
                
                // Write default normals (simplified)
                for (int y = 0; y < 17; y++)
                {
                    for (int x = 0; x < 17; x++)
                    {
                        // Default normal pointing up
                        writer.WriteLine("vn 0 1 0");
                    }
                }
                
                // Use the first texture layer if available
                if (terrainChunk.TextureLayers.Count > 0 && terrainChunk.TextureLayers[0].TextureReference != null)
                {
                    string textureName = Path.GetFileNameWithoutExtension(terrainChunk.TextureLayers[0].TextureReference.Path);
                    writer.WriteLine($"usemtl {textureName}");
                }
                else
                {
                    writer.WriteLine("usemtl default");
                }
                
                // Write faces
                for (int y = 0; y < 16; y++)
                {
                    for (int x = 0; x < 16; x++)
                    {
                        // Calculate vertex indices for this quad
                        int v1 = vertexIndex + y * 17 + x;
                        int v2 = vertexIndex + y * 17 + (x + 1);
                        int v3 = vertexIndex + (y + 1) * 17 + (x + 1);
                        int v4 = vertexIndex + (y + 1) * 17 + x;
                        
                        // Check if this part of the terrain has a hole
                        bool hasHole = false;
                        if (terrainChunk.Holes > 0)
                        {
                            int holeX = x / 4;
                            int holeY = y / 4;
                            int holeBit = 1 << (holeY * 4 + holeX);
                            hasHole = (terrainChunk.Holes & holeBit) != 0;
                        }
                        
                        if (!hasHole)
                        {
                            // Write two triangles for the quad with texture coordinates and normals
                            writer.WriteLine($"f {v1}/{v1}/{v1} {v2}/{v2}/{v2} {v3}/{v3}/{v3}");
                            writer.WriteLine($"f {v1}/{v1}/{v1} {v3}/{v3}/{v3} {v4}/{v4}/{v4}");
                        }
                    }
                }
                
                // Update vertex index for the next chunk
                vertexIndex += 17 * 17;
            }
            
            // Create a simple material file
            string mtlPath = Path.Combine(Path.GetDirectoryName(outputPath), "terrain.mtl");
            using (var mtlWriter = new StreamWriter(mtlPath))
            {
                mtlWriter.WriteLine("# Material definitions for terrain");
                mtlWriter.WriteLine();
                
                // Default material
                mtlWriter.WriteLine("newmtl default");
                mtlWriter.WriteLine("Ka 0.5 0.5 0.5");
                mtlWriter.WriteLine("Kd 0.5 0.5 0.5");
                mtlWriter.WriteLine("Ks 0.0 0.0 0.0");
                mtlWriter.WriteLine("d 1.0");
                mtlWriter.WriteLine("illum 1");
                mtlWriter.WriteLine();
                
                // Create materials for each unique texture
                var uniqueTextures = new HashSet<string>();
                foreach (var terrainChunk in adtFile.TerrainChunks)
                {
                    foreach (var layer in terrainChunk.TextureLayers)
                    {
                        if (layer.TextureReference != null)
                        {
                            string textureName = Path.GetFileNameWithoutExtension(layer.TextureReference.Path);
                            if (uniqueTextures.Add(textureName))
                            {
                                mtlWriter.WriteLine($"newmtl {textureName}");
                                mtlWriter.WriteLine("Ka 1.0 1.0 1.0");
                                mtlWriter.WriteLine("Kd 1.0 1.0 1.0");
                                mtlWriter.WriteLine("Ks 0.0 0.0 0.0");
                                mtlWriter.WriteLine("d 1.0");
                                mtlWriter.WriteLine("illum 1");
                                mtlWriter.WriteLine($"map_Kd {textureName}.png");
                                mtlWriter.WriteLine();
                            }
                        }
                    }
                }
            }
        }
    }
}