using System;
using System.IO;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Threading.Tasks;
using System.Linq;
using WarcraftAnalyzer.Files.WLW;
using WarcraftAnalyzer.Files.PM4;
using WarcraftAnalyzer.Files.PD4;
using WarcraftAnalyzer.Files.ADT;
using WarcraftAnalyzer.Files.WDT;
using WarcraftAnalyzer.Files.Serialization;
using Warcraft.NET.Files.ADT;
using Warcraft.NET.Files.ADT.Terrain.Wotlk;

namespace WarcraftAnalyzer
{
    class Program
    {
        /// <summary>
        /// The spinner characters for the progress indicator.
        /// </summary>
        private static readonly char[] SpinnerChars = { '|', '/', '-', '\\' };

        static int Main(string[] args)
        {
            if (args.Length < 1)
            {
                Console.WriteLine("Usage: WarcraftAnalyzer <file.pm4|file.pd4|file.wlw|file.wlm|file.wlq|file.adt|file.wdt> [output.json]");
                Console.WriteLine("       WarcraftAnalyzer --split-adt <base_adt_file> [--obj <obj_file>] [--tex <tex_file>] [output.json]");
                Console.WriteLine("       WarcraftAnalyzer --correlate <input_directory> [output_file.md] [--recursive]");
                Console.WriteLine("       WarcraftAnalyzer --uniqueid-analysis <input_directory> [output_directory] [--cluster-threshold=10] [--gap-threshold=1000] [--recursive] [--no-comprehensive]");
                Console.WriteLine("       WarcraftAnalyzer --directory <directory> [--listfile <listfile>] [--output <output>] [--recursive] [--verbose] [--json]");
                return 1;
            }

            try
            {
                // Check command type based on first argument
                if (args[0] == "--split-adt" || args[0] == "-s")
                {
                    return RunSplitADTAnalysisAsync(args);
                }
                else if (args[0] == "--correlate" || args[0] == "-c")
                {
                    return RunCorrelationAnalysisAsync(args);
                }
                else if (args[0] == "--directory" || args[0] == "-d")
                {
                    return RunDirectoryAnalysisAsync(args);
                }
                else if (args[0] == "--uniqueid-analysis" || args[0] == "-u")
                {
                    return RunUniqueIdAnalysisAsync(args);
                }
                else
                {
                    // Single file analysis
                    return RunSingleFileAnalysisAsync(args);
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error: {ex.Message}");
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
        }

        /// <summary>
        /// Runs analysis on a single file.
        /// </summary>
        /// <param name="args">The command-line arguments.</param>
        /// <returns>The exit code.</returns>
        private static int RunSingleFileAnalysisAsync(string[] args)
        {
            // Parse command-line arguments
            string inputPath = args[0];
            string outputPath = null;
            string listfilePath = null;
            bool verbose = false;
            bool recursive = false;
            bool json = false;
            
            // Process additional arguments
            for (int i = 1; i < args.Length; i++)
            {
                if (args[i] == "--listfile" || args[i] == "-l")
                {
                    if (i + 1 < args.Length)
                    {
                        listfilePath = args[i + 1];
                        i++;
                    }
                }
                else if (args[i] == "--output" || args[i] == "-o")
                {
                    if (i + 1 < args.Length)
                    {
                        outputPath = args[i + 1];
                        i++;
                    }
                }
                else if (args[i] == "--recursive" || args[i] == "-r")
                {
                    recursive = true;
                }
                else if (args[i] == "--verbose" || args[i] == "-v")
                {
                    verbose = true;
                }
                else if (args[i] == "--json" || args[i] == "-j")
                {
                    json = true;
                }
                else if (!args[i].StartsWith("--") && outputPath == null)
                {
                    // If it's not a flag and we don't have an output path yet, treat it as the output path
                    outputPath = args[i];
                }
            }
            
            // If no output path is specified, use the input path with .json extension
            if (outputPath == null)
            {
                outputPath = Path.ChangeExtension(inputPath, ".json");
            }

            try
            {
                if (verbose)
                {
                    Console.WriteLine($"Input path: {inputPath}");
                    Console.WriteLine($"Output path: {outputPath}");
                    Console.WriteLine($"Listfile path: {listfilePath}");
                    Console.WriteLine($"Recursive: {recursive}");
                    Console.WriteLine($"Verbose: {verbose}");
                    Console.WriteLine($"JSON: {json}");
                }
                
                Console.WriteLine($"Reading file: {inputPath}");
                var fileData = File.ReadAllBytes(inputPath);
                Console.WriteLine($"File read successfully. Size: {fileData.Length} bytes");

                string jsonOutput = null;

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
                            jsonOutput = JsonSerializer.SerializePM4(pm4);
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
                            jsonOutput = JsonSerializer.SerializePD4(pd4);
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
                            jsonOutput = JsonSerializer.SerializeWLW(wlw);
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
                        // Check if this is a split ADT file (has _obj or _tex suffix)
                        var fileNameWithoutExt = Path.GetFileNameWithoutExtension(inputPath);
                        if (fileNameWithoutExt.EndsWith("_obj") || fileNameWithoutExt.EndsWith("_tex"))
                        {
                            Console.WriteLine("This appears to be a split ADT file. For best results, use --split-adt option.");
                        }
                        
                        try
                        {
                            var adt = new Files.ADT.ADTFile(fileData, inputPath);
                            Console.WriteLine("ADTFile object created successfully");
                            Console.WriteLine("Serializing ADT to JSON");
                            jsonOutput = JsonSerializer.SerializeADT(adt);
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

                    case ".wdt":
                        Console.WriteLine("Creating WDTFile object");
                        try
                        {
                            var wdt = new Files.WDT.WDTFile(fileData, inputPath);
                            Console.WriteLine("WDTFile object created successfully");
                            Console.WriteLine("Serializing WDT to JSON");
                            jsonOutput = JsonSerializer.SerializeWDT(wdt);
                            Console.WriteLine("WDT serialized to JSON successfully");

                            // If this is an Alpha WDT, output additional files
                            if (wdt.Version == WDTVersion.Alpha)
                            {
                                var baseOutputPath = Path.Combine(
                                    Path.GetDirectoryName(outputPath),
                                    Path.GetFileNameWithoutExtension(outputPath)
                                );

                                // Output model and object names
                                if (wdt.ModelNames.Count > 0)
                                {
                                    var mdnmPath = baseOutputPath + "_models.txt";
                                    File.WriteAllLines(mdnmPath, wdt.ModelNames);
                                    Console.WriteLine($"Model names written to: {mdnmPath}");
                                }

                                if (wdt.WorldObjectNames.Count > 0)
                                {
                                    var monmPath = baseOutputPath + "_objects.txt";
                                    File.WriteAllLines(monmPath, wdt.WorldObjectNames);
                                    Console.WriteLine($"World object names written to: {monmPath}");
                                }
                            }
                        }
                        catch (Exception ex)
                        {
                            Console.WriteLine($"Error creating or serializing WDTFile: {ex.Message}");
                            Console.WriteLine($"Stack trace: {ex.StackTrace}");
                            return 1;
                        }
                        break;

                    default:
                        Console.WriteLine($"Unsupported file type: {extension}");
                        return 1;
                }

                // Write JSON output if we have it
                if (jsonOutput != null)
                {
                    Console.WriteLine($"Writing JSON output to: {outputPath}");
                    File.WriteAllText(outputPath, jsonOutput);
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
        /// Runs the analysis on a directory of files.
        /// </summary>
        /// <param name="args">The command-line arguments.</param>
        /// <returns>The exit code.</returns>
        private static int RunDirectoryAnalysisAsync(string[] args)
        {
            if (args.Length < 2)
            {
                Console.WriteLine("Error: Directory is required for directory-based analysis.");
                Console.WriteLine("Usage: WarcraftAnalyzer --directory <directory> [--listfile <listfile>] [--output <output>] [--recursive] [--verbose] [--json]");
                return 1;
            }
            
            try
            {
                string directory = args[1];
                string listfile = null;
                string output = null;
                bool recursive = false;
                bool verbose = false;
                // bool jsonFormat = false; // Removed unused variable
                
                // Parse options
                for (int i = 2; i < args.Length; i++)
                {
                    if (args[i] == "--listfile" || args[i] == "-l")
                    {
                        if (i + 1 < args.Length)
                        {
                            listfile = args[i + 1];
                            i++;
                        }
                    }
                    else if (args[i] == "--output" || args[i] == "-o")
                    {
                        if (i + 1 < args.Length)
                        {
                            output = args[i + 1];
                            i++;
                        }
                    }
                    else if (args[i] == "--recursive" || args[i] == "-r")
                    {
                        recursive = true;
                    }
                    else if (args[i] == "--verbose" || args[i] == "-v")
                    {
                        verbose = true;
                    }
                    // else if (args[i] == "--json" || args[i] == "-j")
                    // {
                    //     jsonFormat = true;
                    // }
                }
                
                // Set default output directory if not specified
                if (output == null)
                {
                    output = Path.Combine(directory, "analysis");
                }
                // No else needed - output is already set correctly
                
                // Ensure directory paths are properly formatted
                directory = directory.Trim('"', ' ');
                output = output.Trim('"', ' ');
                
                if (verbose)
                {
                    Console.WriteLine($"Using directory: {directory}");
                    Console.WriteLine($"Using output directory: {output}");
                    Console.WriteLine($"Recursive: {recursive}");
                    Console.WriteLine($"Verbose: {verbose}");
                }
                
                // Create output directory if it doesn't exist
                try
                {
                    Directory.CreateDirectory(output);
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Error creating output directory: {ex.Message}");
                    return 1;
                }
                
                // Find ADT files in the directory
                var searchOption = recursive ? SearchOption.AllDirectories : SearchOption.TopDirectoryOnly;
                var adtFiles = Directory.GetFiles(directory, "*.adt", searchOption)
                    .Where(f => !Path.GetFileNameWithoutExtension(f).EndsWith("_obj") && 
                                !Path.GetFileNameWithoutExtension(f).EndsWith("_tex"))
                    .ToArray();
                
                var splitAdtBaseFiles = adtFiles.ToList();
                var objFiles = Directory.GetFiles(directory, "*_obj.adt", searchOption);
                var texFiles = Directory.GetFiles(directory, "*_tex.adt", searchOption);
                var pm4Files = Directory.GetFiles(directory, "*.pm4", searchOption);
                var pd4Files = Directory.GetFiles(directory, "*.pd4", searchOption);
                var wlwFiles = Directory.GetFiles(directory, "*.wlw", searchOption);
                var wlqFiles = Directory.GetFiles(directory, "*.wlq", searchOption);
                var wlmFiles = Directory.GetFiles(directory, "*.wlm", searchOption);
                var waterMeshFiles = wlwFiles.Concat(wlqFiles).Concat(wlmFiles).ToArray();
                var wdtFiles = Directory.GetFiles(directory, "*.wdt", searchOption);
                
                if (verbose)
                {
                    Console.WriteLine($"Found {adtFiles.Length} base ADT files");
                    Console.WriteLine($"Found {objFiles.Length} obj ADT files");
                    Console.WriteLine($"Found {texFiles.Length} tex ADT files");
                    Console.WriteLine($"Found {pm4Files.Length} PM4 files");
                    Console.WriteLine($"Found {pd4Files.Length} PD4 files");
                    Console.WriteLine($"Found {waterMeshFiles.Length} water mesh files ({wlwFiles.Length} WLW, {wlqFiles.Length} WLQ, {wlmFiles.Length} WLM)");
                    Console.WriteLine($"Found {wdtFiles.Length} WDT files");
                }
                
                // Process each file
                int successCount = 0;
                int errorCount = 0;
                int totalFiles = adtFiles.Length + pm4Files.Length + pd4Files.Length + waterMeshFiles.Length + wdtFiles.Length;
                int processedFiles = 0;
                
                // Setup progress reporting
                Console.WriteLine($"Processing {totalFiles} files...");
                var progressBar = !verbose;
                var lastProgressUpdate = DateTime.Now;
                var progressUpdateInterval = TimeSpan.FromMilliseconds(500); // Update progress every 500ms
                
                // Process ADT files
                foreach (var file in adtFiles)
                {
                    try
                    {
                        var outputFile = Path.Combine(output, Path.GetFileNameWithoutExtension(file) + ".json");
                        if (verbose)
                        {
                            Console.WriteLine($"Processing ADT file: {file}");
                            Console.WriteLine($"Output file: {outputFile}");
                        }
                        
                        // Check if this is a split ADT file
                        var baseName = Path.GetFileNameWithoutExtension(file);
                        var objFile = objFiles.FirstOrDefault(f => Path.GetFileNameWithoutExtension(f) == baseName + "_obj");
                        var texFile = texFiles.FirstOrDefault(f => Path.GetFileNameWithoutExtension(f) == baseName + "_tex");
                        
                        if (objFile != null || texFile != null)
                        {
                            if (verbose)
                            {
                                Console.WriteLine($"Detected split ADT file with components:");
                                Console.WriteLine($"  Base: {file}");
                                Console.WriteLine($"  Obj: {objFile ?? "Not found"}");
                                Console.WriteLine($"  Tex: {texFile ?? "Not found"}");
                            }
                            
                            // Read the files
                            var baseFileData = File.ReadAllBytes(file);
                            byte[] objFileData = null;
                            byte[] texFileData = null;
                            
                            if (objFile != null)
                            {
                                objFileData = File.ReadAllBytes(objFile);
                            }
                            
                            if (texFile != null)
                            {
                                texFileData = File.ReadAllBytes(texFile);
                            }
                            
                            // Create SplitADTFile object
                            var splitAdt = new Files.ADT.SplitADTFile(baseFileData, objFileData, texFileData, Path.GetFileName(file));
                            
                            // Serialize to JSON
                            var jsonOutput = JsonSerializer.SerializeSplitADT(splitAdt);
                            
                            // Write JSON output
                            File.WriteAllText(outputFile, jsonOutput);
                        }
                        else
                        {
                            // Regular ADT file
                            // Read the file
                            var fileData = File.ReadAllBytes(file);
                            
                            // Create ADT file object
                            var adt = new Files.ADT.ADTFile(fileData, Path.GetFileName(file));
                            
                            // Serialize to JSON
                            var jsonOutput = JsonSerializer.SerializeADT(adt);
                            
                            // Write JSON output
                            File.WriteAllText(outputFile, jsonOutput);
                        }
                        
                        successCount++;
                        processedFiles++;
                        UpdateProgress(processedFiles, totalFiles, ref lastProgressUpdate, progressUpdateInterval, progressBar);
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine($"Error processing {file}: {ex.Message}");
                        errorCount++;
                        processedFiles++;
                        UpdateProgress(processedFiles, totalFiles, ref lastProgressUpdate, progressUpdateInterval, progressBar);
                    }
                }
                
                // Process PM4 files
                foreach (var file in pm4Files)
                {
                    try
                    {
                        var outputFile = Path.Combine(output, Path.GetFileNameWithoutExtension(file) + ".json");
                        if (verbose)
                        {
                            Console.WriteLine($"Processing PM4 file: {file}");
                            Console.WriteLine($"Output file: {outputFile}");
                        }
                        
                        // Read the file
                        var fileData = File.ReadAllBytes(file);
                        
                        // Create PM4 file object
                        var pm4 = new Files.PM4.PM4File(fileData);
                        
                        // Serialize to JSON
                        var jsonOutput = JsonSerializer.SerializePM4(pm4);
                        
                        // Write JSON output
                        File.WriteAllText(outputFile, jsonOutput);
                        
                        successCount++;
                        processedFiles++;
                        UpdateProgress(processedFiles, totalFiles, ref lastProgressUpdate, progressUpdateInterval, progressBar);
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine($"Error processing {file}: {ex.Message}");
                        errorCount++;
                        processedFiles++;
                        UpdateProgress(processedFiles, totalFiles, ref lastProgressUpdate, progressUpdateInterval, progressBar);
                    }
                }
                
                // Process PD4 files
                foreach (var file in pd4Files)
                {
                    try
                    {
                        var outputFile = Path.Combine(output, Path.GetFileNameWithoutExtension(file) + ".json");
                        if (verbose)
                        {
                            Console.WriteLine($"Processing PD4 file: {file}");
                            Console.WriteLine($"Output file: {outputFile}");
                        }
                        
                        // Read the file
                        var fileData = File.ReadAllBytes(file);
                        
                        // Create PD4 file object
                        var pd4 = new Files.PD4.PD4File(fileData);
                        
                        // Serialize to JSON
                        var jsonOutput = JsonSerializer.SerializePD4(pd4);
                        
                        // Write JSON output
                        File.WriteAllText(outputFile, jsonOutput);
                        
                        successCount++;
                        processedFiles++;
                        UpdateProgress(processedFiles, totalFiles, ref lastProgressUpdate, progressUpdateInterval, progressBar);
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine($"Error processing {file}: {ex.Message}");
                        errorCount++;
                        processedFiles++;
                        UpdateProgress(processedFiles, totalFiles, ref lastProgressUpdate, progressUpdateInterval, progressBar);
                    }
                }
                
                // Process water mesh files (WLW, WLQ, WLM)
                if (waterMeshFiles.Length > 0)
                {
                    // Create WaterMeshes directory
                    var waterMeshesDir = Path.Combine(output, "WaterMeshes");
                    Directory.CreateDirectory(waterMeshesDir);
                    
                    // Copy texture files to WaterMeshes directory
                    var textureFiles = new[] { "WaterBlue_1.png", "Blue_1.png", "Charcoal_1.png", "Green_1.png", "Red_1.png", "Yellow_1.png" };
                    var textureSourceDir = Path.GetFullPath(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "..", "..", "..", "..", "wlw"));
                    
                    foreach (var textureFile in textureFiles)
                    {
                        var sourcePath = Path.Combine(textureSourceDir, textureFile);
                        var destPath = Path.Combine(waterMeshesDir, textureFile);
                        
                        if (File.Exists(sourcePath))
                        {
                            try
                            {
                                File.Copy(sourcePath, destPath, true);
                                if (verbose)
                                {
                                    Console.WriteLine($"Copied texture: {textureFile}");
                                }
                            }
                            catch (Exception ex)
                            {
                                Console.WriteLine($"Error copying texture {textureFile}: {ex.Message}");
                            }
                        }
                    }
                    
                    // Process each water mesh file
                    foreach (var file in waterMeshFiles)
                    {
                        try
                        {
                            var outputFile = Path.Combine(waterMeshesDir, Path.GetFileNameWithoutExtension(file) + ".json");
                            var objOutputFile = Path.Combine(waterMeshesDir, Path.GetFileNameWithoutExtension(file) + ".obj");
                            
                            if (verbose)
                            {
                                Console.WriteLine($"Processing water mesh file: {file}");
                                Console.WriteLine($"Output JSON: {outputFile}");
                                Console.WriteLine($"Output OBJ: {objOutputFile}");
                            }
                            
                            // Read the file
                            var fileData = File.ReadAllBytes(file);
                            
                            // Create WLW file object
                            var wlw = new Files.WLW.WLWFile(fileData, Path.GetExtension(file));
                            
                            // Serialize to JSON
                            var jsonOutput = JsonSerializer.SerializeWLW(wlw);
                            
                            // Write JSON output
                            File.WriteAllText(outputFile, jsonOutput);
                            
                            // Export to OBJ
                            MeshExporter.ExportToObj(wlw, objOutputFile);
                            
                            successCount++;
                            processedFiles++;
                            UpdateProgress(processedFiles, totalFiles, ref lastProgressUpdate, progressUpdateInterval, progressBar);
                        }
                        catch (Exception ex)
                        {
                            Console.WriteLine($"Error processing {file}: {ex.Message}");
                            errorCount++;
                            processedFiles++;
                            UpdateProgress(processedFiles, totalFiles, ref lastProgressUpdate, progressUpdateInterval, progressBar);
                        }
                    }
                }
                
                // Process WDT files
                foreach (var file in wdtFiles)
                {
                    try
                    {
                        var outputFile = Path.Combine(output, Path.GetFileNameWithoutExtension(file) + ".json");
                        if (verbose)
                        {
                            Console.WriteLine($"Processing WDT file: {file}");
                            Console.WriteLine($"Output file: {outputFile}");
                        }
                        
                        // Read the file
                        var fileData = File.ReadAllBytes(file);
                        
                        // Create WDT file object
                        var wdt = new Files.WDT.WDTFile(fileData, Path.GetFileName(file));
                        
                        // Serialize to JSON
                        var jsonOutput = JsonSerializer.SerializeWDT(wdt);
                        
                        // Write JSON output
                        File.WriteAllText(outputFile, jsonOutput);
                        
                        successCount++;
                        processedFiles++;
                        UpdateProgress(processedFiles, totalFiles, ref lastProgressUpdate, progressUpdateInterval, progressBar);
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine($"Error processing {file}: {ex.Message}");
                        errorCount++;
                        processedFiles++;
                        UpdateProgress(processedFiles, totalFiles, ref lastProgressUpdate, progressUpdateInterval, progressBar);
                    }
                }
                
                // Clear progress bar line if we were showing one
                if (progressBar)
                {
                    ClearProgressBar();
                }
                
                Console.WriteLine($"Directory analysis complete.");
                Console.WriteLine($"Successfully processed {successCount} files.");
                Console.WriteLine($"Failed to process {errorCount} files.");
                Console.WriteLine($"Results written to {output}");
                
                return 0;
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error running directory analysis: {ex.Message}");
                Console.WriteLine($"Stack trace: {ex.StackTrace}");
                return 1;
            }
        }

        /// <summary>
        /// Runs the unique ID analysis on a directory of ADT files.
        /// </summary>
        /// <param name="args">The command-line arguments.</param>
        /// <returns>The exit code.</returns>
        private static int RunUniqueIdAnalysisAsync(string[] args)
        {
            if (args.Length < 2)
            {
                Console.WriteLine("Error: Input directory is required for unique ID analysis.");
                Console.WriteLine("Usage: WarcraftAnalyzer --uniqueid-analysis <input_directory> [output_directory] [--cluster-threshold=10] [--gap-threshold=1000] [--recursive] [--no-comprehensive]");
                return 1;
            }

            try
            {
                string inputDirectory = args[1];
                string outputDirectory = null;
                
                // Parse options
                int clusterThreshold = 10;
                int gapThreshold = 1000;
                bool recursive = false;
                bool generateComprehensiveReport = true;
                bool verbose = false;
                
                for (int i = 2; i < args.Length; i++)
                {
                    if (args[i] == "--output" || args[i] == "-o")
                    {
                        if (i + 1 < args.Length)
                        {
                            outputDirectory = args[i + 1];
                            i++;
                        }
                    }
                    else if (args[i].StartsWith("--cluster-threshold="))
                    {
                        if (int.TryParse(args[i].Substring("--cluster-threshold=".Length), out int threshold))
                        {
                            clusterThreshold = threshold;
                        }
                    }
                    else if (args[i].StartsWith("--gap-threshold="))
                    {
                        if (int.TryParse(args[i].Substring("--gap-threshold=".Length), out int threshold))
                        {
                            gapThreshold = threshold;
                        }
                    }
                    else if (args[i] == "--recursive" || args[i] == "-r")
                    {
                        recursive = true;
                    }
                    else if (args[i] == "--no-comprehensive" || args[i] == "-nc")
                    {
                        generateComprehensiveReport = false;
                    }
                    else if (args[i] == "--verbose" || args[i] == "-v")
                    {
                        verbose = true;
                    }
                }
                
                // Set default output directory if not specified
                if (outputDirectory == null)
                {
                    outputDirectory = Path.Combine(inputDirectory, "uniqueid_analysis");
                }
                // No else needed - outputDirectory is already set correctly
                
                // Ensure directory paths are properly formatted
                inputDirectory = inputDirectory.Trim('"', ' ');
                outputDirectory = outputDirectory.Trim('"', ' ');
                
                if (verbose)
                {
                    Console.WriteLine($"Using input directory: {inputDirectory}");
                    Console.WriteLine($"Using output directory: {outputDirectory}");
                    Console.WriteLine($"Cluster threshold: {clusterThreshold}");
                    Console.WriteLine($"Gap threshold: {gapThreshold}");
                    Console.WriteLine($"Recursive: {recursive}");
                    Console.WriteLine($"Comprehensive report: {generateComprehensiveReport}");
                }
                
                // Create output directory if it doesn't exist
                try
                {
                    Directory.CreateDirectory(outputDirectory);
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Error creating output directory: {ex.Message}");
                    return 1;
                }
                
                // Run the analyzer
                Analysis.UniqueIdAnalyzerCLI.RunAsync(
                    inputDirectory,
                    outputDirectory,
                    clusterThreshold,
                    gapThreshold,
                    recursive,
                    generateComprehensiveReport).Wait();
                
                return 0;
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error running unique ID analysis: {ex.Message}");
                Console.WriteLine($"Stack trace: {ex.StackTrace}");
                return 1;
            }
        }

        /// <summary>
        /// Runs the analysis on a split ADT file.
        /// </summary>
        /// <param name="args">The command-line arguments.</param>
        /// <returns>The exit code.</returns>
        private static int RunSplitADTAnalysisAsync(string[] args)
        {
            if (args.Length < 2)
            {
                Console.WriteLine("Error: Base ADT file is required for split ADT analysis.");
                Console.WriteLine("Usage: WarcraftAnalyzer --split-adt <base_adt_file> [--obj <obj_file>] [--tex <tex_file>] [output.json]");
                return 1;
            }

            try
            {
                string baseAdtPath = args[1];
                string objFilePath = null;
                string texFilePath = null;
                string outputPath = null;
                bool verbose = false;

                // Process additional arguments
                for (int i = 2; i < args.Length; i++)
                {
                    if (args[i] == "--obj" || args[i] == "-o")
                    {
                        if (i + 1 < args.Length)
                        {
                            objFilePath = args[i + 1];
                            i++;
                        }
                    }
                    else if (args[i] == "--tex" || args[i] == "-t")
                    {
                        if (i + 1 < args.Length)
                        {
                            texFilePath = args[i + 1];
                            i++;
                        }
                    }
                    else if (args[i] == "--verbose" || args[i] == "-v")
                    {
                        verbose = true;
                    }
                    else if (!args[i].StartsWith("--") && outputPath == null)
                    {
                        // If it's not a flag and we don't have an output path yet, treat it as the output path
                        outputPath = args[i];
                    }
                }

                // If no output path is specified, use the base ADT path with .json extension
                if (outputPath == null)
                {
                    outputPath = Path.ChangeExtension(baseAdtPath, ".json");
                }

                // If obj or tex paths are not specified, try to infer them from the base path
                if (objFilePath == null)
                {
                    var baseNameWithoutExt = Path.GetFileNameWithoutExtension(baseAdtPath);
                    var baseDir = Path.GetDirectoryName(baseAdtPath);
                    var inferredObjPath = Path.Combine(baseDir, baseNameWithoutExt + "_obj.adt");
                    
                    if (File.Exists(inferredObjPath))
                    {
                        objFilePath = inferredObjPath;
                        Console.WriteLine($"Found obj file: {objFilePath}");
                    }
                    else
                    {
                        Console.WriteLine("No obj file specified and could not infer path. Some data may be missing.");
                    }
                }

                if (texFilePath == null)
                {
                    var baseNameWithoutExt = Path.GetFileNameWithoutExtension(baseAdtPath);
                    var baseDir = Path.GetDirectoryName(baseAdtPath);
                    var inferredTexPath = Path.Combine(baseDir, baseNameWithoutExt + "_tex.adt");
                    
                    if (File.Exists(inferredTexPath))
                    {
                        texFilePath = inferredTexPath;
                        Console.WriteLine($"Found tex file: {texFilePath}");
                    }
                    else
                    {
                        Console.WriteLine("No tex file specified and could not infer path. Some data may be missing.");
                    }
                }

                if (verbose)
                {
                    Console.WriteLine($"Base ADT path: {baseAdtPath}");
                    Console.WriteLine($"Obj file path: {objFilePath}");
                    Console.WriteLine($"Tex file path: {texFilePath}");
                    Console.WriteLine($"Output path: {outputPath}");
                }

                // Read the files
                Console.WriteLine($"Reading base ADT file: {baseAdtPath}");
                var baseAdtData = File.ReadAllBytes(baseAdtPath);
                Console.WriteLine($"Base ADT file read successfully. Size: {baseAdtData.Length} bytes");

                byte[] objFileData = null;
                if (!string.IsNullOrEmpty(objFilePath) && File.Exists(objFilePath))
                {
                    Console.WriteLine($"Reading obj file: {objFilePath}");
                    objFileData = File.ReadAllBytes(objFilePath);
                    Console.WriteLine($"Obj file read successfully. Size: {objFileData.Length} bytes");
                }

                byte[] texFileData = null;
                if (!string.IsNullOrEmpty(texFilePath) && File.Exists(texFilePath))
                {
                    Console.WriteLine($"Reading tex file: {texFilePath}");
                    texFileData = File.ReadAllBytes(texFilePath);
                    Console.WriteLine($"Tex file read successfully. Size: {texFileData.Length} bytes");
                }

                // Create SplitADTFile object
                Console.WriteLine("Creating SplitADTFile object");
                var splitAdt = new Files.ADT.SplitADTFile(baseAdtData, objFileData, texFileData, Path.GetFileName(baseAdtPath));
                Console.WriteLine("SplitADTFile object created successfully");

                // Serialize to JSON
                Console.WriteLine("Serializing Split ADT to JSON");
                var jsonOutput = JsonSerializer.SerializeSplitADT(splitAdt);
                Console.WriteLine("Split ADT serialized to JSON successfully");

                // Write JSON output
                Console.WriteLine($"Writing JSON output to: {outputPath}");
                File.WriteAllText(outputPath, jsonOutput);
                Console.WriteLine($"JSON output written to {outputPath}");

                // Export terrain data to OBJ if there are terrain chunks
                if (splitAdt.TerrainChunks.Count > 0)
                {
                    var objPath = Path.ChangeExtension(outputPath, ".obj");
                    Console.WriteLine($"Exporting terrain to OBJ: {objPath}");
                    ExportTerrainToObj(splitAdt, objPath);
                    Console.WriteLine("OBJ export completed successfully");
                }

                return 0;
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error processing split ADT files: {ex.Message}");
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
        }
        
        /// <summary>
        /// Runs the correlation analysis between PM4 and ADT files.
        /// </summary>
        /// <param name="args">The command-line arguments.</param>
        /// <returns>The exit code.</returns>
        private static int RunCorrelationAnalysisAsync(string[] args)
        {
            if (args.Length < 2)
            {
                Console.WriteLine("Error: Input directory is required for correlation analysis.");
                Console.WriteLine("Usage: WarcraftAnalyzer --correlate <input_directory> [output_file.md] [--recursive]");
                return 1;
            }
            
            try
            {
                string inputDirectory = args[1];
                string outputFile = null;
                bool recursive = false;
                
                // Parse options
                for (int i = 2; i < args.Length; i++)
                {
                    if (args[i] == "--recursive" || args[i] == "-r")
                    {
                        recursive = true;
                    }
                    else if (!args[i].StartsWith("--") && outputFile == null)
                    {
                        outputFile = args[i];
                    }
                }
                
                // Set default output file if not specified
                if (outputFile == null)
                {
                    outputFile = Path.Combine(inputDirectory, "correlation_report.md");
                }
                
                // Ensure directory paths are properly formatted
                inputDirectory = inputDirectory.Trim('"', ' ');
                outputFile = outputFile.Trim('"', ' ');
                
                Console.WriteLine($"Analyzing directory: {inputDirectory}");
                Console.WriteLine($"Output file: {outputFile}");
                Console.WriteLine($"Recursive: {recursive}");
                
                // Find correlations
                Console.WriteLine("Finding correlations between PM4 and ADT files...");
                var correlations = Analysis.FileCorrelator.CorrelatePM4AndADT(inputDirectory, recursive);
                
                // Generate report
                Console.WriteLine("Generating correlation report...");
                var report = Analysis.FileCorrelator.GenerateCorrelationReport(correlations);
                
                // Write report to file
                Console.WriteLine($"Writing report to {outputFile}...");
                File.WriteAllText(outputFile, report);
                
                Console.WriteLine($"Correlation analysis complete. Found {correlations.Count} correlations.");
                Console.WriteLine($"Report written to {outputFile}");
                
                return 0;
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error running correlation analysis: {ex.Message}");
                Console.WriteLine($"Stack trace: {ex.StackTrace}");
                return 1;
            }
        }

        /// <summary>
        /// Exports terrain data from an ADT file to OBJ format.
        /// </summary>
        /// <param name="adt">The ADT file containing terrain data.</param>
        /// <param name="outputPath">The path to write the OBJ file to.</param>
        private static void ExportTerrainToObj(Files.ADT.ADTFile adt, string outputPath)
        {
            ExportTerrainToObjInternal(adt, outputPath);
        }

        private static void ExportTerrainToObj(Files.ADT.SplitADTFile adt, string outputPath)
        {
            ExportTerrainToObjInternal(adt, outputPath);
        }

        private static void ExportTerrainToObjInternal(dynamic adt, string outputPath)
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
        
        /// <summary>
        /// Updates the progress indicator.
        /// </summary>
        /// <param name="current">The current progress value.</param>
        /// <param name="total">The total progress value.</param>
        /// <param name="lastUpdate">The time of the last update.</param>
        /// <param name="updateInterval">The minimum time between updates.</param>
        /// <param name="showProgressBar">Whether to show a progress bar.</param>
        private static void UpdateProgress(int current, int total, ref DateTime lastUpdate, TimeSpan updateInterval, bool showProgressBar)
        {
            // Only update at the specified interval to avoid console flickering
            if (DateTime.Now - lastUpdate < updateInterval && current < total)
                return;
                
            lastUpdate = DateTime.Now;
            
            if (showProgressBar)
            {
                // Calculate percentage
                int percent = (int)((double)current / total * 100);
                
                // Build progress bar with spinner
                int progressBarWidth = 40;
                int spinnerIndex = current % SpinnerChars.Length;
                int filledWidth = (int)((double)current / total * progressBarWidth);
                
                string progressBar = "[" + new string('#', filledWidth) + new string(' ', progressBarWidth - filledWidth) + "]";
                
                // Build status text
                string status = $"{current}/{total} files processed ({percent}%) {SpinnerChars[spinnerIndex]}";
                
                // Write progress
                Console.Write($"\r{progressBar} {status}");
                
                // If we're done, add a newline
                if (current >= total)
                {
                    Console.WriteLine();
                }
            }
        }
        
        /// <summary>
        /// Clears the progress bar line.
        /// </summary>
        private static void ClearProgressBar()
        {
            Console.Write("\r" + new string(' ', Console.WindowWidth - 1) + "\r");
        }
    }
}