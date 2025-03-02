using System;
using System.Collections.Generic;
using System.Threading.Tasks;

namespace ModernWoWTools.ADTMeta.Analysis.UniqueIdAnalysis
{
    /// <summary>
    /// Facade class for generating reports from the analysis results.
    /// This class delegates to the specialized report generator classes.
    /// </summary>
    public static class ReportGenerator
    {
        /// <summary>
        /// Generates an Excel report of the analysis. This method delegates to the ExcelReportGenerator class.
        /// </summary>
        public static async Task GenerateExcelReportAsync(
            List<AdtInfo> adtFiles,
            Dictionary<string, List<UniqueIdCluster>> mapClusters,
            List<UniqueIdCluster> globalClusters,
            bool comprehensive,
            int clusterGapThreshold, 
            string outputDirectory) 
        {
            // Delegate to the ExcelReportGenerator
            var excelReportGenerator = new ExcelReportGenerator(
                adtFiles, mapClusters, globalClusters, clusterGapThreshold, outputDirectory, comprehensive);
            await excelReportGenerator.GenerateAsync();
        }
    }
}