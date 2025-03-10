using System;
using System.IO;
using WarcraftAnalyzer.Files.PM4;

namespace WarcraftAnalyzer
{
    class MinimalPM4Test
    {
        static void Main(string[] args)
        {
            Console.WriteLine("Minimal PM4 File Test");
            Console.WriteLine("=====================");
            
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
                else
                {
                    Console.WriteLine("PM4 file loaded successfully with no errors.");
                }
                
                Console.WriteLine("\nPM4 file processing completed.");
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