using System;
using System.Collections.Generic;
using System.Linq;

namespace ModernWoWTools.ADTMeta.Analysis.UniqueIdAnalysis
{
    /// <summary>
    /// Utility class for finding and analyzing clusters of IDs
    /// </summary>
    public static class ClusterAnalyzer
    {
        /// <summary>
        /// Finds clusters of unique IDs.
        /// </summary>
        /// <param name="ids">Sorted list of unique IDs</param>
        /// <param name="threshold">Minimum number of IDs to form a cluster</param>
        /// <param name="gapThreshold">Maximum gap between IDs to be considered part of the same cluster</param>
        /// <returns>List of identified clusters</returns>
        public static List<UniqueIdCluster> FindClusters(List<int> ids, int threshold, int gapThreshold)
        {
            var clusters = new List<UniqueIdCluster>();
            
            if (ids.Count == 0)
                return clusters;
            
            var sortedIds = ids.OrderBy(id => id).ToList();
            
            var currentCluster = new UniqueIdCluster
            {
                MinId = sortedIds[0],
                MaxId = sortedIds[0],
                Count = 1
            };
            
            for (int i = 1; i < sortedIds.Count; i++)
            {
                var gap = sortedIds[i] - sortedIds[i - 1];
                
                if (gap <= gapThreshold)
                {
                    // Continue current cluster
                    currentCluster.MaxId = sortedIds[i];
                    currentCluster.Count++;
                }
                else
                {
                    // End current cluster if it meets the threshold
                    if (currentCluster.Count >= threshold)
                    {
                        clusters.Add(currentCluster);
                    }
                    
                    // Start a new cluster
                    currentCluster = new UniqueIdCluster
                    {
                        MinId = sortedIds[i],
                        MaxId = sortedIds[i],
                        Count = 1
                    };
                }
            }
            
            // Add the last cluster if it meets the threshold
            if (currentCluster.Count >= threshold)
            {
                clusters.Add(currentCluster);
            }
            
            return clusters;
        }
        
        /// <summary>
        /// Gets ranges of IDs that are close together.
        /// </summary>
        /// <param name="ids">List of unique IDs</param>
        /// <param name="gapThreshold">Maximum gap between IDs to be considered in the same range</param>
        /// <returns>List of tuples containing (start, end, count) for each range</returns>
        public static List<Tuple<int, int, int>> GetIdRanges(List<int> ids, int gapThreshold)
        {
            var result = new List<Tuple<int, int, int>>();
            
            if (ids.Count == 0)
                return result;
            
            var sortedIds = ids.OrderBy(id => id).ToList();
            
            var rangeStart = sortedIds[0];
            var rangeEnd = sortedIds[0];
            var rangeCount = 1;
            
            for (int i = 1; i < sortedIds.Count; i++)
            {
                var gap = sortedIds[i] - sortedIds[i - 1];
                
                if (gap <= gapThreshold)
                {
                    // Continue current range
                    rangeEnd = sortedIds[i];
                    rangeCount++;
                }
                else
                {
                    // End current range
                    result.Add(new Tuple<int, int, int>(rangeStart, rangeEnd, rangeCount));
                    
                    // Start a new range
                    rangeStart = sortedIds[i];
                    rangeEnd = sortedIds[i];
                    rangeCount = 1;
                }
            }
            
            // Add the last range
            result.Add(new Tuple<int, int, int>(rangeStart, rangeEnd, rangeCount));
            
            return result;
        }
    }
}