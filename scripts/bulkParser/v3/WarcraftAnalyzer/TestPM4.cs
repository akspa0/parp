using System;
using System.IO;
using WarcraftAnalyzer.Files.PM4;
using Warcraft.NET.Files.Interfaces;

namespace WarcraftAnalyzer
{
    class TestPM4
    {
        static void Main(string[] args)
        {
            Console.WriteLine("PM4 File Test");
            Console.WriteLine("=============");
            
            try
            {
                // Path to the test PM4 file
                string filePath = Path.Combine("wow-development-orig", "development_00_00.pm4");
                
                if (!File.Exists(filePath))
                {
                    Console.WriteLine($"Error: File not found at {filePath}");
                    return;
                }
                
                Console.WriteLine($"Loading PM4 file: {filePath}");
                
                // Read the file data
                byte[] fileData = File.ReadAllBytes(filePath);
                Console.WriteLine($"File size: {fileData.Length} bytes");
                
                // Create a PM4File instance with the file data
                PM4File pm4File = new PM4File(fileData, Path.GetFileName(filePath));
                
                // Check for errors
                if (pm4File.Errors.Count > 0)
                {
                    Console.WriteLine("Errors encountered during parsing:");
                    foreach (var error in pm4File.Errors)
                    {
                        Console.WriteLine($"  - {error}");
                    }
                }
                
                // Display chunk information
                Console.WriteLine("\nChunks found in the PM4 file:");
                int chunkCount = 0;
                
                foreach (IIFFChunk chunk in pm4File.GetChunks())
                {
                    if (chunk != null)
                    {
                        chunkCount++;
                        Console.WriteLine($"  {chunkCount}. {chunk.GetType().Name} (Signature: {chunk.GetSignature()})");
                    }
                }
                
                if (chunkCount == 0)
                {
                    Console.WriteLine("  No chunks found in the file.");
                }
                
                Console.WriteLine($"\nTotal chunks: {chunkCount}");
                
                // Display specific chunk details if available
                if (pm4File.Version != null)
                {
                    Console.WriteLine($"\nVersion: {pm4File.Version.Version}");
                }
                
                if (pm4File.ShadowData != null)
                {
                    Console.WriteLine("\nShadow Data present");
                }
                
                if (pm4File.VertexPositions != null)
                {
                    Console.WriteLine($"\nVertex Positions: {pm4File.VertexPositions.Vertices.Count} entries");
                }
                
                if (pm4File.VertexIndices != null)
                {
                    Console.WriteLine($"\nVertex Indices: {pm4File.VertexIndices.VertexIndices.Count} entries");
                }
                
                if (pm4File.NormalCoordinates != null)
                {
                    Console.WriteLine($"\nNormal Coordinates: {pm4File.NormalCoordinates.Normals.Count} entries");
                }
                
                if (pm4File.Links != null)
                {
                    Console.WriteLine("\nLinks present");
                }
                
                if (pm4File.VertexData != null)
                {
                    Console.WriteLine("\nVertex Data present");
                }
                
                if (pm4File.VertexIndices2 != null)
                {
                    Console.WriteLine("\nVertex Indices 2 present");
                }
                
                if (pm4File.SurfaceData != null)
                {
                    Console.WriteLine("\nSurface Data present");
                }
                
                if (pm4File.PositionData != null)
                {
                    Console.WriteLine("\nPosition Data present");
                }
                
                if (pm4File.ValuePairs != null)
                {
                    Console.WriteLine("\nValue Pairs present");
                }
                
                if (pm4File.BuildingData != null)
                {
                    Console.WriteLine("\nBuilding Data present");
                }
                
                if (pm4File.SimpleData != null)
                {
                    Console.WriteLine("\nSimple Data present");
                }
                
                if (pm4File.FinalData != null)
                {
                    Console.WriteLine("\nFinal Data present");
                }
                
                Console.WriteLine("\nPM4 file processing completed successfully.");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error: {ex.Message}");
                if (ex.InnerException != null)
                {
                    Console.WriteLine($"Inner Exception: {ex.InnerException.Message}");
                }
                Console.WriteLine(ex.StackTrace);
            }
            
            Console.WriteLine("\nPress any key to exit...");
            Console.ReadKey();
        }
    }
}