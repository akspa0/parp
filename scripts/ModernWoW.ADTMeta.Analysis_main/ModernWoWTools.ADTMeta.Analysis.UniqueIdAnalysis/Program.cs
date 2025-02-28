using System;
using System.Threading.Tasks;

namespace ModernWoWTools.ADTMeta.Analysis.UniqueIdAnalysis
{
    /// <summary>
    /// Entry point class for the application.
    /// </summary>
    public class Program
    {
        /// <summary>
        /// Entry point for the application.
        /// </summary>
        public static async Task Main(string[] args)
        {
            Console.WriteLine("ADT UniqueID Analyzer");
            Console.WriteLine("====================");
            
            string resultsDir;
            string outputDir;
            int clusterThreshold = 10;
            int gapThreshold = 1000;
            
            if (args.Length < 2)
            {
                Console.WriteLine("Usage: UniqueIdAnalyzer <results_directory> <output_directory> [cluster_threshold] [gap_threshold]");
                Console.WriteLine();
                Console.Write("Enter results directory: ");
                resultsDir = Console.ReadLine();
                
                Console.Write("Enter output directory: ");
                outputDir = Console.ReadLine();
                
                Console.Write("Enter cluster threshold (minimum IDs for a cluster, default 10): ");
                var thresholdInput = Console.ReadLine();
                if (!string.IsNullOrEmpty(thresholdInput) && int.TryParse(thresholdInput, out var threshold))
                {
                    clusterThreshold = threshold;
                }
                
                Console.Write("Enter gap threshold (maximum gap between IDs in a cluster, default 1000): ");
                var gapInput = Console.ReadLine();
                if (!string.IsNullOrEmpty(gapInput) && int.TryParse(gapInput, out var gap))
                {
                    gapThreshold = gap;
                }
            }
            else
            {
                resultsDir = args[0];
                outputDir = args[1];
                
                if (args.Length > 2 && int.TryParse(args[2], out var threshold))
                {
                    clusterThreshold = threshold;
                }
                
                if (args.Length > 3 && int.TryParse(args[3], out var gap))
                {
                    gapThreshold = gap;
                }
            }
            
            // Run the analyzer
            var analyzer = new UniqueIdAnalyzer(resultsDir, outputDir, clusterThreshold, gapThreshold);
            await analyzer.AnalyzeAsync();
            
            Console.WriteLine("Analysis complete. Press any key to exit...");
            Console.ReadKey();
        }
    }
}