using System;
using System.IO;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using WarcraftAnalyzer.Files.WLW;
using WarcraftAnalyzer.Files.PM4;
using WarcraftAnalyzer.Files.PD4;
using WarcraftAnalyzer.Files.ADT;
using WarcraftAnalyzer.Files.WDT;
using WarcraftAnalyzer.Files.Serialization;
using WarcraftAnalyzer.Analysis;

namespace WarcraftAnalyzer
{
    /// <summary>
    /// The main program class.
    /// </summary>
    public class Program
    {
        /// <summary>
        /// The spinner characters for the progress indicator.
        /// </summary>
        private static readonly char[] SpinnerChars = { '|', '/', '-', '\\' };

        /// <summary>
        /// The entry point for the application.
        /// </summary>
        /// <param name="args">The command-line arguments.</param>
        /// <returns>The exit code.</returns>
        public static async Task<int> Main(string[] args)
        {
            // Default values
            string input = null;
            string output = null;
            string listfile = null;
            bool recursive = false;
            bool verbose = false;
            bool uniqueId = false;
            int clusterThreshold = 10;
            int gapThreshold = 1000;
            bool noComprehensive = false;

            // Parse command-line arguments
            for (int i = 0; i < args.Length; i++)
            {
                string arg = args[i];
                string nextArg = (i + 1 < args.Length) ? args[i + 1] : null;

                switch (arg)
                {
                    case "--input":
                    case "-i":
                        if (nextArg != null && !nextArg.StartsWith("-"))
                        {
                            input = nextArg;
                            i++;
                        }
                        break;

                    case "--output":
                    case "-o":
                        if (nextArg != null && !nextArg.StartsWith("-"))
                        {
                            output = nextArg;
                            i++;
                        }
                        break;

                    case "--listfile":
                    case "-l":
                        if (nextArg != null && !nextArg.StartsWith("-"))
                        {
                            listfile = nextArg;
                            i++;
                        }
                        break;

                    case "--recursive":
                    case "-r":
                        recursive = true;
                        break;

                    case "--verbose":
                    case "-v":
                        verbose = true;
                        break;

                    case "--uniqueid":
                    case "-u":
                        uniqueId = true;
                        break;

                    case "--cluster-threshold":
                    case "-ct":
                        if (nextArg != null && !nextArg.StartsWith("-") && int.TryParse(nextArg, out int ct))
                        {
                            clusterThreshold = ct;
                            i++;
                        }
                        break;

                    case "--gap-threshold":
                    case "-gt":
                        if (nextArg != null && !nextArg.StartsWith("-") && int.TryParse(nextArg, out int gt))
                        {
                            gapThreshold = gt;
                            i++;
                        }
                        break;

                    case "--no-comprehensive":
                    case "-nc":
                        noComprehensive = true;
                        break;

                    case "--help":
                    case "-h":
                        PrintHelp();
                        return 0;
                }
            }

            // Validate required arguments
            if (string.IsNullOrEmpty(input))
            {
                Console.WriteLine("Error: Input path is required.");
                PrintHelp();
                return 1;
            }

            try
            {
                // Ensure input path is properly formatted
                input = input.Trim('"', ' ');
                
                // Check if input is a file or directory
                bool isDirectory = Directory.Exists(input);
                bool isFile = File.Exists(input);
                
                if (!isDirectory && !isFile)
                {
                    Console.WriteLine($"Error: Input path '{input}' does not exist or is not accessible.");
                    return 1;
                }
                
                // Set default output if not specified
                if (output == null)
                {
                    if (isDirectory)
                    {
                        output = Path.Combine(input, "analysis");
                    }
                    else
                    {
                        output = Path.Combine(Path.GetDirectoryName(input), "analysis");
                    }
                }
                
                // Ensure output path is properly formatted
                output = output.Trim('"', ' ');
                
                if (verbose)
                {
                    Console.WriteLine($"Input: {input}");
                    Console.WriteLine($"Output: {output}");
                    Console.WriteLine($"Listfile: {listfile}");
                    Console.WriteLine($"Recursive: {recursive}");
                    Console.WriteLine($"Verbose: {verbose}");
                    Console.WriteLine($"UniqueID Analysis: {uniqueId}");
                    if (uniqueId)
                    {
                        Console.WriteLine($"Cluster Threshold: {clusterThreshold}");
                        Console.WriteLine($"Gap Threshold: {gapThreshold}");
                        Console.WriteLine($"Skip Comprehensive Reports: {noComprehensive}");
                    }
                }
                
                // Create output directory if it doesn't exist
                Directory.CreateDirectory(output);
                
                // Process based on input type
                if (isDirectory)
                {
                    // Process directory
                    await ProcessDirectoryAsync(input, output, listfile, recursive, verbose, uniqueId, clusterThreshold, gapThreshold, !noComprehensive);
                }
                else
                {
                    // Process single file
                    await ProcessFileAsync(input, output, verbose);
                }
                
                return 0;
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error: {ex.Message}");
                Console.WriteLine($"Stack trace: {ex.StackTrace}");
                return 1;
            }
        }

        /// <summary>
        /// Prints the help message.
        /// </summary>
        private static void PrintHelp()
        {
            Console.WriteLine("WarcraftAnalyzer - A tool for analyzing World of Warcraft files");
            Console.WriteLine();
            Console.WriteLine("Usage: WarcraftAnalyzer [options]");
            Console.WriteLine();
            Console.WriteLine("Options:");
            Console.WriteLine("  --input, -i <path>              The input file or directory to analyze (required)");
            Console.WriteLine("  --output, -o <path>             The output directory for analysis results");
            Console.WriteLine("  --listfile, -l <path>           The path to the listfile for reference validation");
            Console.WriteLine("  --recursive, -r                 Whether to search subdirectories");
            Console.WriteLine("  --verbose, -v                   Whether to enable verbose logging");
            Console.WriteLine("  --uniqueid, -u                  Whether to perform unique ID analysis on ADT files");
            Console.WriteLine("  --cluster-threshold, -ct <int>  The threshold for clustering unique IDs (default: 10)");
            Console.WriteLine("  --gap-threshold, -gt <int>      The threshold for gaps between unique IDs (default: 1000)");
            Console.WriteLine("  --no-comprehensive, -nc         Whether to skip generating comprehensive reports");
            Console.WriteLine("  --help, -h                      Show this help message");
        }
        
        /// <summary>
        /// Processes a directory of files.
        /// </summary>
        /// <param name="directory">The directory to process.</param>
        /// <param name="output">The output directory.</param>
        /// <param name="listfile">The listfile path.</param>
        /// <param name="recursive">Whether to search subdirectories.</param>
        /// <param name="verbose">Whether to enable verbose logging.</param>
        /// <param name="uniqueId">Whether to perform unique ID analysis.</param>
        /// <param name="clusterThreshold">The threshold for clustering unique IDs.</param>
        /// <param name="gapThreshold">The threshold for gaps between unique IDs.</param>
        /// <param name="generateComprehensiveReport">Whether to generate comprehensive reports.</param>
        /// <returns>A task representing the asynchronous operation.</returns>
        private static async Task ProcessDirectoryAsync(string directory, string output, string listfile, bool recursive, bool verbose, bool uniqueId, int clusterThreshold, int gapThreshold, bool generateComprehensiveReport)
        {
            // Find files in the directory
            var searchOption = recursive ? SearchOption.AllDirectories : SearchOption.TopDirectoryOnly;
            
            // Get all ADT files (excluding split parts)
            var adtFiles = Directory.GetFiles(directory, "*.adt", searchOption)
                .Where(f => !Path.GetFileNameWithoutExtension(f).EndsWith("_obj") && 
                            !Path.GetFileNameWithoutExtension(f).EndsWith("_tex"))
                .ToArray();
            
            // Get split ADT files
            var objFiles = Directory.GetFiles(directory, "*_obj.adt", searchOption);
            var texFiles = Directory.GetFiles(directory, "*_tex.adt", searchOption);
            
            // Get other file types
            var pm4Files = Directory.GetFiles(directory, "*.pm4", searchOption);
            var pd4Files = Directory.GetFiles(directory, "*.pd4", searchOption);
            var wlwFiles = Directory.GetFiles(directory, "*.wlw", searchOption);
            var wlqFiles = Directory.GetFiles(directory, "*.wlq", searchOption);
            var wlmFiles = Directory.GetFiles(directory, "*.wlm", searchOption);
            var waterMeshFiles = wlwFiles.Concat(wlqFiles).Concat(wlmFiles).ToArray();
            var wdtFiles = Directory.GetFiles(directory, "*.wdt", searchOption);
            
            // Create subdirectories for each file type
            var adtOutputDir = Path.Combine(output, "ADT");
            var pm4OutputDir = Path.Combine(output, "PM4");
            var pd4OutputDir = Path.Combine(output, "PD4");
            var waterMeshOutputDir = Path.Combine(output, "WaterMeshes");
            var wdtOutputDir = Path.Combine(output, "WDT");
            var uniqueIdOutputDir = Path.Combine(output, "UniqueID");
            
            Directory.CreateDirectory(adtOutputDir);
            Directory.CreateDirectory(pm4OutputDir);
            Directory.CreateDirectory(pd4OutputDir);
            Directory.CreateDirectory(waterMeshOutputDir);
            Directory.CreateDirectory(wdtOutputDir);
            
            if (uniqueId)
            {
                Directory.CreateDirectory(uniqueIdOutputDir);
            }
            
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
            
            // Process each file type
            int totalFiles = adtFiles.Length + pm4Files.Length + pd4Files.Length + waterMeshFiles.Length + wdtFiles.Length;
            int processedFiles = 0;
            int successCount = 0;
            int errorCount = 0;
            
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
                    var outputFile = Path.Combine(adtOutputDir, Path.GetFileNameWithoutExtension(file) + ".json");
                    if (verbose)
                    {
                        Console.WriteLine($"Processing ADT file: {file}");
                        Console.WriteLine($"Output file: {outputFile}");
                    }
                    
                    // Check if this is a split ADT file
                    var baseName = Path.GetFileNameWithoutExtension(file);
                    var objFile = objFiles.FirstOrDefault(f => Path.GetFileNameWithoutExtension(f) == baseName + "_obj");
                    var texFile = texFiles.FirstOrDefault(f => Path.GetFileNameWithoutExtension(f) == baseName + "_tex");
                    
                    if (verbose)
                    {
                        Console.WriteLine($"Processing ADT file: {file}");
                        Console.WriteLine($"Base name: {baseName}");
                        Console.WriteLine($"Looking for obj file: {baseName + "_obj"}");
                        Console.WriteLine($"Looking for tex file: {baseName + "_tex"}");
                        Console.WriteLine($"Found obj file: {(objFile != null ? "Yes" : "No")}");
                        Console.WriteLine($"Found tex file: {(texFile != null ? "Yes" : "No")}");
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
                    
                    // Create ADT file object (handles both regular and split ADTs)
                    if (objFileData != null || texFileData != null)
                    {
                        if (verbose)
                        {
                            Console.WriteLine($"Processing as split ADT file with components:");
                            Console.WriteLine($"  Base: {file}");
                            Console.WriteLine($"  Obj: {objFile ?? "Not found"}");
                            Console.WriteLine($"  Tex: {texFile ?? "Not found"}");
                        }
                        
                        try
                        {
                            if (verbose)
                            {
                                Console.WriteLine("Creating SplitADTFile instance...");
                                Console.WriteLine($"  Base file size: {baseFileData.Length} bytes");
                                Console.WriteLine($"  Obj file size: {(objFileData != null ? objFileData.Length : 0)} bytes");
                                Console.WriteLine($"  Tex file size: {(texFileData != null ? texFileData.Length : 0)} bytes");
                            }
                            
                            var splitAdt = new SplitADTFile(baseFileData, objFileData, texFileData, Path.GetFileName(file), verbose);
                            
                            if (verbose)
                            {
                                Console.WriteLine("SplitADTFile instance created successfully");
                                Console.WriteLine($"  Terrain chunks: {splitAdt.TerrainChunks.Count}");
                                Console.WriteLine($"  Errors: {splitAdt.Errors.Count}");
                                
                                if (splitAdt.Errors.Count > 0)
                                {
                                    Console.WriteLine("Errors encountered during split ADT processing:");
                                    foreach (var error in splitAdt.Errors)
                                    {
                                        Console.WriteLine($"  - {error}");
                                    }
                                }
                            }
                            
                            // Serialize to JSON
                            var jsonOutput = JsonSerializer.SerializeSplitADT(splitAdt);
                            
                            // Write JSON output
                            File.WriteAllText(outputFile, jsonOutput);
                            
                            // Export terrain data to OBJ if there are terrain chunks
                            if (splitAdt.TerrainChunks.Count > 0)
                            {
                                var objPath = Path.ChangeExtension(outputFile, ".obj");
                                if (verbose)
                                {
                                    Console.WriteLine($"Exporting terrain to OBJ: {objPath}");
                                }
                                ExportTerrainToObj(splitAdt, objPath);
                            }
                        }
                        catch (Exception ex)
                        {
                            Console.WriteLine($"Error creating SplitADTFile: {ex.Message}");
                            throw;
                        }
                    }
                    else
                    {
                        var adt = new ADTFile(baseFileData, Path.GetFileName(file));
                        
                        // Serialize to JSON
                        var jsonOutput = JsonSerializer.SerializeADT(adt);
                        
                        // Write JSON output
                        File.WriteAllText(outputFile, jsonOutput);
                        
                        // Export terrain data to OBJ if there are terrain chunks
                        if (adt.TerrainChunks.Count > 0)
                        {
                            var objPath = Path.ChangeExtension(outputFile, ".obj");
                            if (verbose)
                            {
                                Console.WriteLine($"Exporting terrain to OBJ: {objPath}");
                            }
                            ExportTerrainToObj(adt, objPath);
                        }
                    }
                    
                    
                    successCount++;
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Error processing {file}: {ex.Message}");
                    errorCount++;
                }
                
                processedFiles++;
                UpdateProgress(processedFiles, totalFiles, ref lastProgressUpdate, progressUpdateInterval, progressBar);
            }
            
            // Process PD4 files first (they're faster than PM4)
            
            // Process PD4 files
            foreach (var file in pd4Files)
            {
                try
                {
                    var outputFile = Path.Combine(pd4OutputDir, Path.GetFileNameWithoutExtension(file) + ".json");
                    if (verbose)
                    {
                        Console.WriteLine($"Processing PD4 file: {file}");
                        Console.WriteLine($"Output file: {outputFile}");
                    }
                    
                    // Read the file
                    var fileData = File.ReadAllBytes(file);
                    
                    // Create PD4 file object
                    var pd4 = new PD4File(fileData);
                    
                    // Serialize to JSON
                    var jsonOutput = JsonSerializer.SerializePD4(pd4);
                    
                    // Write JSON output
                    File.WriteAllText(outputFile, jsonOutput);
                    
                    successCount++;
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Error processing {file}: {ex.Message}");
                    errorCount++;
                }
                
                processedFiles++;
                UpdateProgress(processedFiles, totalFiles, ref lastProgressUpdate, progressUpdateInterval, progressBar);
            }
            
            // Process water mesh files (WLW, WLQ, WLM)
            if (waterMeshFiles.Length > 0)
            {
                // Copy texture files to WaterMeshes directory
                var textureFiles = new[] { "WaterBlue_1.png", "Blue_1.png", "Charcoal_1.png", "Green_1.png", "Red_1.png", "Yellow_1.png" };
                var textureSourceDir = Path.GetFullPath(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "..", "..", "..", "..", "wlw"));
                
                foreach (var textureFile in textureFiles)
                {
                    var sourcePath = Path.Combine(textureSourceDir, textureFile);
                    var destPath = Path.Combine(waterMeshOutputDir, textureFile);
                    
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
                        var outputFile = Path.Combine(waterMeshOutputDir, Path.GetFileNameWithoutExtension(file) + ".json");
                        var objOutputFile = Path.Combine(waterMeshOutputDir, Path.GetFileNameWithoutExtension(file) + ".obj");
                        
                        if (verbose)
                        {
                            Console.WriteLine($"Processing water mesh file: {file}");
                            Console.WriteLine($"Output JSON: {outputFile}");
                            Console.WriteLine($"Output OBJ: {objOutputFile}");
                        }
                        
                        // Read the file
                        var fileData = File.ReadAllBytes(file);
                        
                        // Create WLW file object
                        var wlw = new WLWFile(fileData, Path.GetExtension(file));
                        
                        // Serialize to JSON
                        var jsonOutput = JsonSerializer.SerializeWLW(wlw);
                        
                        // Write JSON output
                        File.WriteAllText(outputFile, jsonOutput);
                        
                        // Export to OBJ
                        MeshExporter.ExportToObj(wlw, objOutputFile);
                        
                        successCount++;
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine($"Error processing {file}: {ex.Message}");
                        errorCount++;
                    }
                    
                    processedFiles++;
                    UpdateProgress(processedFiles, totalFiles, ref lastProgressUpdate, progressUpdateInterval, progressBar);
                }
            }
            
            // Process WDT files
            foreach (var file in wdtFiles)
            {
                try
                {
                    var outputFile = Path.Combine(wdtOutputDir, Path.GetFileNameWithoutExtension(file) + ".json");
                    if (verbose)
                    {
                        Console.WriteLine($"Processing WDT file: {file}");
                        Console.WriteLine($"Output file: {outputFile}");
                    }
                    
                    // Check file size to determine if it's an Alpha WDT
                    var fileInfo = new FileInfo(file);
                    bool isAlphaWdt = fileInfo.Length > 65536; // 64KB threshold
                    
                    if (verbose)
                    {
                        Console.WriteLine($"WDT file size: {fileInfo.Length} bytes");
                        Console.WriteLine($"Detected as {(isAlphaWdt ? "Alpha" : "Standard")} WDT");
                    }
                    
                    // Read the file
                    var fileData = File.ReadAllBytes(file);
                    
                    // Create WDT file object
                    var wdt = new WDTFile(fileData, Path.GetFileName(file));
                    
                    // Serialize to JSON
                    var jsonOutput = JsonSerializer.SerializeWDT(wdt);
                    
                    // Write JSON output
                    File.WriteAllText(outputFile, jsonOutput);
                    
                    successCount++;
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Error processing {file}: {ex.Message}");
                    errorCount++;
                }
                
                processedFiles++;
                UpdateProgress(processedFiles, totalFiles, ref lastProgressUpdate, progressUpdateInterval, progressBar);
            }
            
            // Process PM4 files last (since they're slower)
            foreach (var file in pm4Files)
            {
                try
                {
                    var outputFile = Path.Combine(pm4OutputDir, Path.GetFileNameWithoutExtension(file) + ".json");
                    if (verbose)
                    {
                        Console.WriteLine($"Processing PM4 file: {file}");
                        Console.WriteLine($"Output file: {outputFile}");
                    }
                    
                    // Read the file
                    var fileData = File.ReadAllBytes(file);
                    
                    // Create PM4 file object
                    var pm4 = new PM4File(fileData);
                    
                    // Serialize to JSON
                    var jsonOutput = JsonSerializer.SerializePM4(pm4);
                    
                    // Write JSON output
                    File.WriteAllText(outputFile, jsonOutput);
                    
                    successCount++;
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Error processing {file}: {ex.Message}");
                    errorCount++;
                }
                
                processedFiles++;
                UpdateProgress(processedFiles, totalFiles, ref lastProgressUpdate, progressUpdateInterval, progressBar);
            }
            
            // Run unique ID analysis if requested
            if (uniqueId && adtFiles.Length > 0)
            {
                if (verbose)
                {
                    Console.WriteLine("Running unique ID analysis...");
                }
                
                await UniqueIdAnalyzerCLI.RunAsync(
                    directory,
                    uniqueIdOutputDir,
                    clusterThreshold,
                    gapThreshold,
                    recursive,
                    generateComprehensiveReport);
            }
            
            // Generate correlation report
            if (pm4Files.Length > 0 && adtFiles.Length > 0)
            {
                if (verbose)
                {
                    Console.WriteLine("Generating correlation report...");
                }
                
                var correlations = FileCorrelator.CorrelatePM4AndADT(directory, recursive);
                var report = FileCorrelator.GenerateCorrelationReport(correlations);
                var correlationFile = Path.Combine(output, "correlation_report.md");
                File.WriteAllText(correlationFile, report);
                
                if (verbose)
                {
                    Console.WriteLine($"Correlation report written to {correlationFile}");
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
        }
        
        /// <summary>
        /// Processes a single file.
        /// </summary>
        /// <param name="filePath">The file to process.</param>
        /// <param name="outputDir">The output directory.</param>
        /// <param name="verbose">Whether to enable verbose logging.</param>
        /// <returns>A task representing the asynchronous operation.</returns>
        private static async Task ProcessFileAsync(string filePath, string outputDir, bool verbose)
        {
            // Create output directory if it doesn't exist
            Directory.CreateDirectory(outputDir);
            
            // Determine file type from extension
            var extension = Path.GetExtension(filePath).ToLowerInvariant();
            var fileName = Path.GetFileName(filePath);
            var fileNameWithoutExt = Path.GetFileNameWithoutExtension(filePath);
            
            // Create appropriate subdirectory based on file type
            string subDir;
            switch (extension)
            {
                case ".adt":
                    subDir = Path.Combine(outputDir, "ADT");
                    break;
                case ".pm4":
                    subDir = Path.Combine(outputDir, "PM4");
                    break;
                case ".pd4":
                    subDir = Path.Combine(outputDir, "PD4");
                    break;
                case ".wlw":
                case ".wlq":
                case ".wlm":
                    subDir = Path.Combine(outputDir, "WaterMeshes");
                    break;
                case ".wdt":
                    subDir = Path.Combine(outputDir, "WDT");
                    break;
                default:
                    subDir = outputDir;
                    break;
            }
            
            Directory.CreateDirectory(subDir);
            
            // Set output file path
            var outputFile = Path.Combine(subDir, fileNameWithoutExt + ".json");
            
            if (verbose)
            {
                Console.WriteLine($"Processing file: {filePath}");
                Console.WriteLine($"Output file: {outputFile}");
            }
            
            try
            {
                // Read the file
                var fileData = File.ReadAllBytes(filePath);
                
                // Process based on file type
                switch (extension)
                {
                    case ".adt":
                        // Check if this is a split ADT file
                        if (fileNameWithoutExt.EndsWith("_obj") || fileNameWithoutExt.EndsWith("_tex"))
                        {
                            Console.WriteLine("This appears to be a split ADT file part. Please process the base ADT file instead.");
                            return;
                        }
                        
                        // Check for split ADT components
                        var baseDir = Path.GetDirectoryName(filePath);
                        var objFilePath = Path.Combine(baseDir, fileNameWithoutExt + "_obj.adt");
                        var texFilePath = Path.Combine(baseDir, fileNameWithoutExt + "_tex.adt");
                        
                        if (verbose)
                        {
                            Console.WriteLine($"Looking for split ADT components:");
                            Console.WriteLine($"  Base file: {filePath}");
                            Console.WriteLine($"  Obj file path: {objFilePath}");
                            Console.WriteLine($"  Tex file path: {texFilePath}");
                            Console.WriteLine($"  Obj file exists: {File.Exists(objFilePath)}");
                            Console.WriteLine($"  Tex file exists: {File.Exists(texFilePath)}");
                        }
                        
                        byte[] objFileData = null;
                        byte[] texFileData = null;
                        
                        if (File.Exists(objFilePath))
                        {
                            objFileData = File.ReadAllBytes(objFilePath);
                            if (verbose)
                            {
                                Console.WriteLine($"Found and loaded obj file: {objFilePath}");
                            }
                        }
                        
                        if (File.Exists(texFilePath))
                        {
                            texFileData = File.ReadAllBytes(texFilePath);
                            if (verbose)
                            {
                                Console.WriteLine($"Found and loaded tex file: {texFilePath}");
                            }
                        }
                        
                        // Create ADT file object (handles both regular and split ADTs)
                        if (objFileData != null || texFileData != null)
                        {
                            try
                            {
                                if (verbose)
                                {
                                    Console.WriteLine("Creating SplitADTFile instance...");
                                    Console.WriteLine($"  Base file size: {fileData.Length} bytes");
                                    Console.WriteLine($"  Obj file size: {(objFileData != null ? objFileData.Length : 0)} bytes");
                                    Console.WriteLine($"  Tex file size: {(texFileData != null ? texFileData.Length : 0)} bytes");
                                }
                                
                                var splitAdt = new SplitADTFile(fileData, objFileData, texFileData, fileName, verbose);
                                
                                if (verbose)
                                {
                                    Console.WriteLine("SplitADTFile instance created successfully");
                                    Console.WriteLine($"  Terrain chunks: {splitAdt.TerrainChunks.Count}");
                                    Console.WriteLine($"  Errors: {splitAdt.Errors.Count}");
                                    
                                    if (splitAdt.Errors.Count > 0)
                                    {
                                        Console.WriteLine("Errors encountered during split ADT processing:");
                                        foreach (var error in splitAdt.Errors)
                                        {
                                            Console.WriteLine($"  - {error}");
                                        }
                                    }
                                }
                                
                                // Serialize to JSON
                                var jsonOutput = JsonSerializer.SerializeSplitADT(splitAdt);
                            
                                // Write JSON output
                                File.WriteAllText(outputFile, jsonOutput);
                                
                                // Export terrain data to OBJ if there are terrain chunks
                                if (splitAdt.TerrainChunks.Count > 0)
                                {
                                    var objPath = Path.ChangeExtension(outputFile, ".obj");
                                    if (verbose)
                                    {
                                        Console.WriteLine($"Exporting terrain to OBJ: {objPath}");
                                    }
                                    ExportTerrainToObj(splitAdt, objPath);
                                }
                            }
                            catch (Exception ex)
                            {
                                Console.WriteLine($"Error creating SplitADTFile: {ex.Message}");
                                throw;
                            }
                        }
                        else
                        {
                            var adt = new ADTFile(fileData, fileName);
                            
                            // Serialize to JSON
                            var jsonOutput = JsonSerializer.SerializeADT(adt);
                            
                            // Write JSON output
                            File.WriteAllText(outputFile, jsonOutput);
                            
                            // Export terrain data to OBJ if there are terrain chunks
                            if (adt.TerrainChunks.Count > 0)
                            {
                                var objPath = Path.ChangeExtension(outputFile, ".obj");
                                if (verbose)
                                {
                                    Console.WriteLine($"Exporting terrain to OBJ: {objPath}");
                                }
                                ExportTerrainToObj(adt, objPath);
                            }
                        }
                        break;
                        
                    case ".pm4":
                        var pm4 = new PM4File(fileData);
                        var pm4Json = JsonSerializer.SerializePM4(pm4);
                        File.WriteAllText(outputFile, pm4Json);
                        break;
                        
                    case ".pd4":
                        var pd4 = new PD4File(fileData);
                        var pd4Json = JsonSerializer.SerializePD4(pd4);
                        File.WriteAllText(outputFile, pd4Json);
                        break;
                        
                    case ".wlw":
                    case ".wlm":
                    case ".wlq":
                        var wlw = new WLWFile(fileData, extension);
                        var wlwJson = JsonSerializer.SerializeWLW(wlw);
                        File.WriteAllText(outputFile, wlwJson);
                        
                        // Export to OBJ
                        var objOutputFile = Path.ChangeExtension(outputFile, ".obj");
                        MeshExporter.ExportToObj(wlw, objOutputFile);
                        
                        // Copy texture files
                        var textureFiles = new[] { "WaterBlue_1.png", "Blue_1.png", "Charcoal_1.png", "Green_1.png", "Red_1.png", "Yellow_1.png" };
                        var textureSourceDir = Path.GetFullPath(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "..", "..", "..", "..", "wlw"));
                        
                        foreach (var textureFile in textureFiles)
                        {
                            var sourcePath = Path.Combine(textureSourceDir, textureFile);
                            var destPath = Path.Combine(subDir, textureFile);
                            
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
                        break;
                        
                    case ".wdt":
                        var wdt = new WDTFile(fileData, fileName);
                        var wdtJson = JsonSerializer.SerializeWDT(wdt);
                        File.WriteAllText(outputFile, wdtJson);
                        break;
                        
                    default:
                        Console.WriteLine($"Unsupported file type: {extension}");
                        return;
                }
                
                Console.WriteLine($"Successfully processed {filePath}");
                Console.WriteLine($"Output written to {outputFile}");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error processing {filePath}: {ex.Message}");
                throw;
            }
        }
        
        /// <summary>
        /// Exports terrain data from a terrain file to OBJ format.
        /// </summary>
        /// <param name="adt">The terrain file containing terrain data.</param>
        /// <param name="outputPath">The path to write the OBJ file to.</param>
        private static void ExportTerrainToObj(ITerrainFile adt, string outputPath)
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
                
                // Generate simple height data if not available
                float[,] heightMap = new float[17, 17];
                for (int y = 0; y < 17; y++)
                {
                    for (int x = 0; x < 17; x++)
                    {
                        // Use a simple height function if real data not available
                        heightMap[y, x] = 0; // Flat terrain as fallback
                    }
                }
                
                // Write vertices
                for (int y = 0; y < 17; y++)
                {
                    for (int x = 0; x < 17; x++)
                    {
                        // Calculate world coordinates
                        float worldX = (adt.XCoord * 533.33333f) + (terrainChunk.X * 33.33333f) + (x * 33.33333f / 16);
                        float worldZ = (adt.YCoord * 533.33333f) + (terrainChunk.Y * 33.33333f) + (y * 33.33333f / 16);
                        float worldY = heightMap[y, x];
                        
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