using System;
using System.IO;
using System.Threading.Tasks;
using System.CommandLine;
using System.CommandLine.Invocation;
using ModernWoWTools.ADTMeta.Analysis.Services;
using ModernWoWTools.ADTMeta.Analysis.Utilities;

namespace ModernWoWTools.ADTMeta.Analysis
{
    /// <summary>
    /// The main program class.
    /// </summary>
    public class Program
    {
        /// <summary>
        /// The entry point for the application.
        /// </summary>
        /// <param name="args">The command-line arguments.</param>
        /// <returns>The exit code.</returns>
        public static async Task<int> Main(string[] args)
        {
            // Define options with names for easier access
            var directoryOption = new Option<string>(
                new[] { "--directory", "-d" },
                "The directory containing ADT files to analyze")
            {
                IsRequired = true
            };
            
            var listfileOption = new Option<string>(
                new[] { "--listfile", "-l" },
                "The path to the listfile for reference validation")
            {
                IsRequired = false
            };
            
            var outputOption = new Option<string>(
                new[] { "--output", "-o" },
                "The directory to write reports to")
            {
                IsRequired = false
            };
            
            var recursiveOption = new Option<bool>(
                new[] { "--recursive", "-r" },
                () => false,
                "Whether to search subdirectories")
            {
                IsRequired = false
            };
            
            var verboseOption = new Option<bool>(
                new[] { "--verbose", "-v" },
                () => false,
                "Whether to enable verbose logging")
            {
                IsRequired = false
            };
            
            var jsonOption = new Option<bool>(
                new[] { "--json", "-j" },
                () => false,
                "Whether to generate JSON reports")
            {
                IsRequired = false
            };
            
            var rootCommand = new RootCommand("ADT Analysis Tool")
            {
                directoryOption,
                listfileOption,
                outputOption,
                recursiveOption,
                verboseOption,
                jsonOption
            };

            rootCommand.SetHandler(async (InvocationContext context) =>
                {
                    // Get option values
                    var directory = context.ParseResult.GetValueForOption(directoryOption);
                    var listfile = context.ParseResult.GetValueForOption(listfileOption);
                    var output = context.ParseResult.GetValueForOption(outputOption);
                    var recursive = context.ParseResult.GetValueForOption(recursiveOption);
                    var verbose = context.ParseResult.GetValueForOption(verboseOption);
                    var json = context.ParseResult.GetValueForOption(jsonOption);

                    // Define variables outside the try block so they're accessible in the catch block
                    string logDirectory = output != null ? Path.Combine(output, "logs") : Path.Combine(directory, "logs");
                    ILoggingService logger = null;

                    try
                    {
                        // Set up logging
                        var logLevel = verbose ? LogLevel.Debug : LogLevel.Information;
                        var consoleLogger = new ConsoleLogger(logLevel);
                        var fileLogger = new FileLogger(Path.Combine(logDirectory, $"adt_analysis_{DateTime.Now:yyyyMMdd_HHmmss}.log"), logLevel);
                        logger = new CompositeLogger(consoleLogger, fileLogger);

                        // Set up services
                        var parser = new AdtParser(logger);
                        var validator = new ReferenceValidator(logger);
                        var reportGenerator = new ReportGenerator(logger);
                        var analyzer = new AdtAnalyzer(parser, validator, reportGenerator, logger);

                        if (json)
                        {
                            output = Path.Combine(output ?? directory, "json");
                        }

                        // Run analysis
                        await analyzer.AnalyzeDirectoryAsync(directory, listfile, output, recursive);

                        context.ExitCode = 0;
                    }
                    catch (Exception ex)
                    {
                        // Create a new logger if one wasn't already created
                        if (logger == null)
                        {
                            logger = new CompositeLogger(
                                new ConsoleLogger(LogLevel.Information), 
                                new FileLogger(Path.Combine(logDirectory, $"adt_analysis_{DateTime.Now:yyyyMMdd_HHmmss}.log"), LogLevel.Information)
                            );
                        }
                        
                        logger.LogError($"Error: {ex.Message}");
                        // Set exit code to 1 (error)
                        context.ExitCode = 1;
                    }
                });

            return await rootCommand.InvokeAsync(args);
        }
    }
}
