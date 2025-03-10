using System;
using System.IO;
using Warcraft.NET.Files.ADT;

namespace WarcraftAnalyzer.Tests
{
    /// <summary>
    /// A minimal test program for loading ADT files.
    /// </summary>
    public class MinimalADTTest
    {
        public static void Main(string[] args)
        {
            if (args.Length < 1)
            {
                Console.WriteLine("Usage: MinimalADTTest <path_to_adt_file>");
                return;
            }

            string adtFilePath = args[0];
            
            try
            {
                Console.WriteLine($"Loading ADT file: {adtFilePath}");
                byte[] fileData = File.ReadAllBytes(adtFilePath);
                
                // Create Terrain object which parses the file
                var terrain = new Terrain(fileData);
                Console.WriteLine($"ADT file loaded successfully.");
                
                // Display basic information
                Console.WriteLine("\n=== ADT File Information ===");
                
                // Check if MVER chunk exists
                var mverProp = terrain.GetType().GetProperty("MVER");
                if (mverProp != null)
                {
                    var mver = mverProp.GetValue(terrain);
                    if (mver != null)
                    {
                        var versionProp = mver.GetType().GetProperty("Version");
                        if (versionProp != null)
                        {
                            Console.WriteLine($"Version: {versionProp.GetValue(mver)}");
                        }
                    }
                }
                
                // Check if MCNK chunks exist
                if (terrain.Chunks != null)
                {
                    int validChunks = 0;
                    foreach (var chunk in terrain.Chunks)
                    {
                        if (chunk != null)
                        {
                            validChunks++;
                        }
                    }
                    Console.WriteLine($"Valid MCNK chunks: {validChunks} / {terrain.Chunks.Length}");
                }
                
                Console.WriteLine("===========================\n");
                Console.WriteLine("Test completed successfully");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error loading ADT file: {ex.Message}");
                Console.WriteLine($"Stack trace: {ex.StackTrace}");
            }
        }
    }
}