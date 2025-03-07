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
                Console.WriteLine($"Reading file: {inputPath}");
                var fileData = File.ReadAllBytes(inputPath);
                Console.WriteLine($"File read successfully. Size: {fileData.Length} bytes");

                string json;

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
                            return;
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
                            return;
                        }
                        break;

                    default:
                        Console.WriteLine($"Unsupported file type: {extension}");
                        return;
                }

                // Write JSON output
                Console.WriteLine($"Writing JSON output to: {outputPath}");
                File.WriteAllText(outputPath, json);
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
            }
        }
    }
}