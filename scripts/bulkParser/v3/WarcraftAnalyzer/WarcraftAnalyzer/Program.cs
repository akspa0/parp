using System;
using System.IO;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.InteropServices;
using WarcraftAnalyzer.Files.WLW;
using WarcraftAnalyzer.Files.PM4;
using WarcraftAnalyzer.Files.PD4;
using WarcraftAnalyzer.Files.ADT;
using WarcraftAnalyzer.Files.Serialization;
using Warcraft.NET.Files.ADT;
using Warcraft.NET.Files.ADT.Terrain.Wotlk;

namespace WarcraftAnalyzer
{
    class Program
    {
        static int Main(string[] args)
        {
            if (args.Length < 1)
            {
                Console.WriteLine("Usage: WarcraftAnalyzer <file.pm4|file.pd4|file.wlw|file.wlm|file.wlq|file.adt> [output.json]");
                return 1;
            }

            var inputPath = args[0];
            var outputPath = args.Length > 1 ? args[1] : Path.ChangeExtension(inputPath, ".json");

            try
            {
                Console.WriteLine($"Reading file: {inputPath}");
                var fileData = File.ReadAllBytes(inputPath);
                Console.WriteLine($"File read successfully. Size: {fileData.Length} bytes");

                string json = null;

                // Determine file type from extension
                var extension = Path.GetExtension(inputPath).ToLowerInvariant();
                Console.WriteLine($"File extension: {extension}");

                switch (extension)
                {
                    case ".pm4":
                        Console.WriteLine("Creating PM4File object");
                        try
                        {
                            var pm4 = new Files.PM4.PM4File(fileData);
                            Console.WriteLine("PM4File object created successfully");
                            Console.WriteLine("Serializing PM4 to JSON");
                            json = JsonSerializer.SerializePM4(pm4);
                            Console.WriteLine("PM4 serialized to JSON successfully");
                        }
                        catch (Exception ex)
                        {
                            Console.WriteLine($"Error creating or serializing PM4File: {ex.Message}");
                            Console.WriteLine($"Stack trace: {ex.StackTrace}");
                            return 1;
                        }
                        break;

                    case ".pd4":
                        Console.WriteLine("Creating PD4File object");
                        try
                        {
                            var pd4 = new Files.PD4.PD4File(fileData);
                            Console.WriteLine("PD4File object created successfully");
                            Console.WriteLine("Serializing PD4 to JSON");
                            json = JsonSerializer.SerializePD4(pd4);
                            Console.WriteLine("PD4 serialized to JSON successfully");
                        }
                        catch (Exception ex)
                        {
                            Console.WriteLine($"Error creating or serializing PD4File: {ex.Message}");
                            Console.WriteLine($"Stack trace: {ex.StackTrace}");
                            return 1;
                        }
                        break;

                    case ".wlw":
                    case ".wlm":
                    case ".wlq":
                        Console.WriteLine($"Creating {extension.ToUpperInvariant().TrimStart('.')}File object");
                        try
                        {
                            var wlw = new WLWFile(fileData, extension);
                            Console.WriteLine($"{extension.ToUpperInvariant().TrimStart('.')}File object created successfully");
                            Console.WriteLine($"Serializing {extension.ToUpperInvariant().TrimStart('.')} to JSON");
                            json = JsonSerializer.SerializeWLW(wlw);
                            Console.WriteLine($"{extension.ToUpperInvariant().TrimStart('.')} serialized to JSON successfully");

                            // Export to OBJ
                            var objPath = Path.ChangeExtension(outputPath, ".obj");
                            Console.WriteLine($"Exporting to OBJ: {objPath}");
                            MeshExporter.ExportToObj(wlw, objPath);
                            Console.WriteLine("OBJ export completed successfully");

                            // Copy texture files to output directory
                            var textureFiles = new[] { "WaterBlue_1.png", "Blue_1.png", "Grey_1.png", "Red_1.png" };
                            var textureSourceDir = Path.GetFullPath(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "..", "..", "..", "..", "wlw"));
                            var textureDestDir = Path.GetDirectoryName(outputPath);

                            if (textureDestDir != null)
                            {
                                foreach (var textureFile in textureFiles)
                                {
                                    var sourcePath = Path.Combine(textureSourceDir, textureFile);
                                    var destPath = Path.Combine(textureDestDir, textureFile);

                                    if (File.Exists(sourcePath))
                                    {
                                        File.Copy(sourcePath, destPath, true);
                                        Console.WriteLine($"Copied texture: {textureFile}");
                                    }
                                }
                            }
                        }
                        catch (Exception ex)
                        {
                            Console.WriteLine($"Error creating or serializing {extension.ToUpperInvariant().TrimStart('.')}File: {ex.Message}");
                            Console.WriteLine($"Stack trace: {ex.StackTrace}");
                            return 1;
                        }
                        break;

                    case ".adt":
                        Console.WriteLine("Creating ADTFile object");
                        try
                        {
                            var adt = new Files.ADT.ADTFile(fileData, inputPath);
                            Console.WriteLine("ADTFile object created successfully");
                            Console.WriteLine("Serializing ADT to JSON");
                            json = JsonSerializer.SerializeADT(adt);
                            Console.WriteLine("ADT serialized to JSON successfully");
                            
                            // Export terrain data to OBJ if there are terrain chunks
                            if (adt.TerrainChunks.Count > 0 && adt.Terrain?.Chunks != null && adt.Terrain.Chunks.Length > 0)
                            {
                                var objPath = Path.ChangeExtension(outputPath, ".obj");
                                Console.WriteLine($"Exporting terrain to OBJ: {objPath}");
                                ExportTerrainToObj(adt, objPath);
                                Console.WriteLine("OBJ export completed successfully");
                            }
                        }
                        catch (Exception ex)
                        {
                            Console.WriteLine($"Error creating or serializing ADTFile: {ex.Message}");
                            Console.WriteLine($"Stack trace: {ex.StackTrace}");
                            return 1;
                        }
                        break;

                    default:
                        Console.WriteLine($"Unsupported file type: {extension}");
                        return 1;
                }

                // Write JSON output if we have it
                if (json != null)
                {
                    Console.WriteLine($"Writing JSON output to: {outputPath}");
                    File.WriteAllText(outputPath, json);
                }
                else
                {
                    Console.WriteLine("No JSON data was generated.");
                    return 1;
                }
                Console.WriteLine($"Successfully parsed {inputPath}");
                Console.WriteLine($"JSON output written to {outputPath}");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error processing file: {ex.Message}");
                Console.WriteLine($"Error type: {ex.GetType().FullName}");
                Console.WriteLine($"Stack trace: {ex.StackTrace}");
                if (ex.InnerException != null)
                {
                    Console.WriteLine($"Inner error: {ex.InnerException.Message}");
                    Console.WriteLine($"Inner error type: {ex.InnerException.GetType().FullName}");
                    Console.WriteLine($"Inner error stack trace: {ex.InnerException.StackTrace}");
                }
                return 1;
            }
            
            return 0;
        }

        /// <summary>
        /// Exports terrain data from an ADT file to OBJ format.
        /// </summary>
        /// <param name="adt">The ADT file containing terrain data.</param>
        /// <param name="outputPath">The path to write the OBJ file to.</param>
        private static void ExportTerrainToObj(Files.ADT.ADTFile adt, string outputPath)
        {
            using var writer = new StreamWriter(outputPath);
            
            // Write OBJ header
            writer.WriteLine("# Terrain data exported from ADT file");
            writer.WriteLine($"# File: {adt.FileName}");
            writer.WriteLine($"# Coordinates: {adt.XCoord}_{adt.YCoord}");
            writer.WriteLine();
            
            // Write material library reference
            writer.WriteLine("mtllib terrain.mtl");
            writer.WriteLine();
            
            // Track vertex indices (OBJ indices are 1-based)
            int vertexIndex = 1;
            
            // Process each terrain chunk
            foreach (var terrainChunk in adt.TerrainChunks)
            {
                // Skip chunks with no terrain data
                if (terrainChunk == null)
                    continue;
                
                // Write chunk header
                writer.WriteLine($"# Chunk {terrainChunk.X}_{terrainChunk.Y}");
                writer.WriteLine($"g chunk_{terrainChunk.X}_{terrainChunk.Y}");
                
                // Get height data from the Terrain object
                var heightData = adt.Terrain.Chunks[terrainChunk.Y * 16 + terrainChunk.X]?.Heightmap?.Vertices;
                if (heightData == null)
                    continue;
                
                // Write vertices
                for (int y = 0; y < 17; y++)
                {
                    for (int x = 0; x < 17; x++)
                    {
                        // Calculate world coordinates
                        float worldX = (adt.XCoord * 533.33333f) + (terrainChunk.X * 33.33333f) + (x * 33.33333f / 16);
                        float worldZ = (adt.YCoord * 533.33333f) + (terrainChunk.Y * 33.33333f) + (y * 33.33333f / 16);
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
                foreach (var terrainChunk in adt.TerrainChunks)
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