using System;
using System.IO;
using System.Collections.Generic;
using WarcraftAnalyzer.Files.PM4;
using WarcraftAnalyzer.Files.Serialization;
using Warcraft.NET.Files.Interfaces;

namespace WarcraftAnalyzer.Examples
{
    /// <summary>
    /// Example program demonstrating how to use the WarcraftAnalyzer library to analyze PM4 files.
    /// </summary>
    public class PM4AnalysisExample
    {
        public static void Main(string[] args)
        {
            if (args.Length < 1)
            {
                Console.WriteLine("Usage: PM4AnalysisExample <path_to_pm4_file> [output_directory]");
                return;
            }

            string pm4FilePath = args[0];
            string outputDirectory = args.Length > 1 ? args[1] : Path.GetDirectoryName(pm4FilePath);
            
            // Ensure output directory exists
            if (!Directory.Exists(outputDirectory))
            {
                Directory.CreateDirectory(outputDirectory);
            }

            try
            {
                // Step 1: Load the PM4 file
                Console.WriteLine($"Loading PM4 file: {pm4FilePath}");
                byte[] fileData = File.ReadAllBytes(pm4FilePath);
                
                // Create PM4File object which parses the file
                var pm4File = new PM4File(fileData, Path.GetFileName(pm4FilePath));
                Console.WriteLine($"PM4 file loaded successfully: {pm4File.FileName}");
                
                // Check for errors
                if (pm4File.Errors.Count > 0)
                {
                    Console.WriteLine("Errors encountered during parsing:");
                    foreach (var error in pm4File.Errors)
                    {
                        Console.WriteLine($"  - {error}");
                    }
                }
                
                // Step 2: Extract and display information from the PM4 file
                DisplayPM4Info(pm4File);
                
                // Step 3: Serialize to JSON
                string jsonOutputPath = Path.Combine(outputDirectory, Path.GetFileNameWithoutExtension(pm4FilePath) + ".json");
                Console.WriteLine($"Serializing PM4 to JSON: {jsonOutputPath}");
                string json = JsonSerializer.SerializePM4(pm4File);
                File.WriteAllText(jsonOutputPath, json);
                Console.WriteLine("JSON serialization completed successfully");
                
                Console.WriteLine("Analysis completed successfully");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error analyzing PM4 file: {ex.Message}");
                if (ex.InnerException != null)
                {
                    Console.WriteLine($"Inner Exception: {ex.InnerException.Message}");
                }
                Console.WriteLine($"Stack trace: {ex.StackTrace}");
            }
        }
        
        /// <summary>
        /// Displays information about the PM4 file.
        /// </summary>
        /// <param name="pm4File">The PM4 file to display information about.</param>
        private static void DisplayPM4Info(PM4File pm4File)
        {
            Console.WriteLine("\n=== PM4 File Information ===");
            Console.WriteLine($"File Name: {pm4File.FileName}");
            
            // Display version information if available
            if (pm4File.Version != null)
            {
                Console.WriteLine($"Version: {pm4File.Version.Version}");
            }
            
            // Display vertex positions if available
            if (pm4File.VertexPositions != null)
            {
                Console.WriteLine($"Vertex Positions: {pm4File.VertexPositions.Vertices.Count} entries");
            }
            
            // Display vertex indices if available
            if (pm4File.VertexIndices != null)
            {
                Console.WriteLine($"Vertex Indices: {pm4File.VertexIndices.VertexIndices.Count} entries");
            }
            
            // Display normal coordinates if available
            if (pm4File.NormalCoordinates != null)
            {
                Console.WriteLine($"Normal Coordinates: {pm4File.NormalCoordinates.Normals.Count} entries");
            }
            
            // Display links if available
            if (pm4File.Links != null)
            {
                Console.WriteLine("Links present");
            }
            
            // Display vertex data if available
            if (pm4File.VertexData != null)
            {
                Console.WriteLine("Vertex Data present");
            }
            
            // Display vertex indices 2 if available
            if (pm4File.VertexIndices2 != null)
            {
                Console.WriteLine("Vertex Indices 2 present");
            }
            
            // Display surface data if available
            if (pm4File.SurfaceData != null)
            {
                Console.WriteLine("Surface Data present");
            }
            
            // Display position data if available
            if (pm4File.PositionData != null)
            {
                Console.WriteLine("Position Data present");
            }
            
            // Display value pairs if available
            if (pm4File.ValuePairs != null)
            {
                Console.WriteLine("Value Pairs present");
            }
            
            // Display building data if available
            if (pm4File.BuildingData != null)
            {
                Console.WriteLine("Building Data present");
            }
            
            // Display simple data if available
            if (pm4File.SimpleData != null)
            {
                Console.WriteLine("Simple Data present");
            }
            
            // Display final data if available
            if (pm4File.FinalData != null)
            {
                Console.WriteLine("Final Data present");
            }
            
            // Display shadow data if available
            if (pm4File.ShadowData != null)
            {
                Console.WriteLine("Shadow Data present");
            }
            
            // Display all chunks
            Console.WriteLine("\nAll Chunks:");
            int chunkCount = 0;
            foreach (IIFFChunk chunk in pm4File.GetChunks())
            {
                if (chunk != null)
                {
                    chunkCount++;
                    Console.WriteLine($"  {chunkCount}. {chunk.GetType().Name} (Signature: {chunk.GetSignature()})");
                }
            }
            
            Console.WriteLine($"\nTotal chunks: {chunkCount}");
            Console.WriteLine("===========================\n");
        }
    }
}