using System;
using System.IO;
using WarcraftAnalyzer.Files.Serialization;

namespace WarcraftAnalyzer
{
    class Program
    {
        static void Main(string[] args)
        {
            if (args.Length < 1)
            {
                Console.WriteLine("Usage: WarcraftAnalyzer <file.pm4|file.pd4> [output.json]");
                return;
            }

            var inputPath = args[0];
            var outputPath = args.Length > 1 ? args[1] : Path.ChangeExtension(inputPath, ".json");

            try
            {
                var fileData = File.ReadAllBytes(inputPath);
                string json;

                // Determine file type from extension
                var extension = Path.GetExtension(inputPath).ToLowerInvariant();
                switch (extension)
                {
                    case ".pm4":
                        var pm4 = new Files.PM4.PM4File(fileData);
                        json = JsonSerializer.SerializePM4(pm4);
                        break;

                    case ".pd4":
                        var pd4 = new Files.PD4.PD4File(fileData);
                        json = JsonSerializer.SerializePD4(pd4);
                        break;

                    default:
                        Console.WriteLine($"Unsupported file type: {extension}");
                        return;
                }

                // Write JSON output
                File.WriteAllText(outputPath, json);
                Console.WriteLine($"Successfully parsed {inputPath}");
                Console.WriteLine($"JSON output written to {outputPath}");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error processing file: {ex.Message}");
                if (ex.InnerException != null)
                {
                    Console.WriteLine($"Inner error: {ex.InnerException.Message}");
                }
            }
        }
    }
}