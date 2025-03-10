using System;
using System.IO;
using WarcraftAnalyzer.Files.WLW;

namespace WarcraftAnalyzer
{
    class TestWLW
    {
        static void Main(string[] args)
        {
            if (args.Length < 1)
            {
                Console.WriteLine("Usage: TestWLW <file.wlw|file.wlm|file.wlq>");
                return;
            }

            var inputPath = args[0];
            
            try
            {
                Console.WriteLine($"Reading file: {inputPath}");
                var fileData = File.ReadAllBytes(inputPath);
                Console.WriteLine($"File read successfully. Size: {fileData.Length} bytes");
                
                var extension = Path.GetExtension(inputPath).ToLowerInvariant();
                Console.WriteLine($"File extension: {extension}");
                
                Console.WriteLine("Creating WLWFile object");
                var wlw = new WLWFile(fileData, extension);
                Console.WriteLine("WLWFile object created successfully");
                
                // Print basic information about the WLW file
                Console.WriteLine($"Version: {wlw.Version}");
                Console.WriteLine($"Unk06: {wlw.Unk06}");
                Console.WriteLine($"LiquidType: {wlw.LiquidType} ({(LiquidType)(wlw.LiquidType & 0xFFFF)})");
                Console.WriteLine($"BlockCount: {wlw.BlockCount}");
                Console.WriteLine($"Block2Count: {wlw.Block2Count}");
                Console.WriteLine($"Unknown: {wlw.Unknown}");
                Console.WriteLine($"IsMagma: {wlw.IsMagma}");
                Console.WriteLine($"IsQuality: {wlw.IsQuality}");
                
                // Print information about the first block if available
                if (wlw.Blocks.Count > 0)
                {
                    var block = wlw.Blocks[0];
                    Console.WriteLine("\nFirst Block:");
                    Console.WriteLine($"Coordinates: ({block.Coordinates.X}, {block.Coordinates.Y})");
                    Console.WriteLine($"First Vertex: ({block.Vertices[0].X}, {block.Vertices[0].Y}, {block.Vertices[0].Z})");
                    Console.WriteLine($"First Data Value: {block.Data[0]}");
                }
                
                Console.WriteLine("\nSuccessfully parsed WLW file");
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
            }
        }
    }
}