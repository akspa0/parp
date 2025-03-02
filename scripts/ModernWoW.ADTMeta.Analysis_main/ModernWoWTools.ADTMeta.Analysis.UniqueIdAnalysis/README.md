# UniqueID Analyzer for ADT Files

This tool analyzes uniqueIDs from ADT analysis results, identifying clusters, tracking assets, and generating comprehensive reports.

## Features

- **Cluster Analysis**: Identifies clusters of uniqueIDs both per-map and globally
- **Asset Tracking**: Links uniqueIDs to their associated assets (models and WMOs)
- **Comprehensive Reporting**: Generates detailed text and Excel reports
- **Lowest ID Analysis**: Identifies the lowest uniqueID and its associated assets
- **Non-Clustered Data Tracking**: Tracks uniqueIDs that don't belong to any cluster
- **Timeline Analysis**: Visualizes how uniqueIDs evolved across maps

## Usage

```
UniqueIdAnalyzer <results_directory> <output_directory> [cluster_threshold] [gap_threshold] [-noadvanced] [-nocomprehensive]
```

### Parameters

- `results_directory`: Directory containing JSON results from ADT analysis
- `output_directory`: Directory to write analysis results to
- `cluster_threshold` (optional): Minimum number of IDs to form a cluster (default: 10)
- `gap_threshold` (optional): Maximum gap between IDs to be considered part of the same cluster (default: 1000)
- `-noadvanced` (optional): Skip advanced analysis for uniqueID collisions and unique assets
- `-nocomprehensive` (optional): Skip comprehensive reporting with all assets and non-clustered IDs

If parameters are not provided, the tool will prompt for them interactively.

## Output Files

The tool generates the following output files:

- `unique_id_analysis.txt`: Text report with cluster information, asset details, and non-clustered data
- `unique_id_analysis.xlsx`: Excel report with multiple worksheets:
  - Global Clusters: Overview of clusters across all maps
  - Map Clusters: Clusters identified within each map
  - ADT Data: Information about each ADT file
  - ID Distribution: Histogram of uniqueID distribution
  - Asset Distribution: How assets are distributed across clusters
  - Complete ID Mapping: Exhaustive mapping of every uniqueID to its associated assets
  - Detailed Assets: Comprehensive asset information
  - Lowest UniqueID: Information about the lowest uniqueID found
  - Non-Clustered IDs: Information about uniqueIDs that don't belong to any cluster

When advanced analysis is enabled, additional files are generated:
- `id_collisions.xlsx`: Analysis of uniqueID collisions across maps
- `development_timeline.xlsx`: Timeline analysis of uniqueID evolution

## Complete ID Mapping

The "Complete ID Mapping" worksheet provides an exhaustive view of what each uniqueID maps to. This worksheet:
- Lists every uniqueID in the dataset
- Shows all assets associated with each uniqueID
- Indicates whether each ID is part of a cluster

## Understanding the Results

### Clusters

Clusters represent groups of uniqueIDs that are close together numerically. They often correspond to specific development periods or content additions. The tool identifies:

- **Global Clusters**: Clusters across all maps
- **Map Clusters**: Clusters specific to each map

### Non-Clustered Data

Non-clustered data represents uniqueIDs that don't fit into any identified cluster. These may be:
- Outliers or special cases
- IDs from different development phases
- Manually assigned IDs

### Lowest ID Analysis

The lowest uniqueID analysis helps identify the earliest assets in the dataset, which can provide insights into the initial development phases.

## Development Notes

The tool is designed to handle large datasets efficiently. For very large datasets, consider:
- Increasing the cluster threshold to focus on more significant clusters
- Increasing the gap threshold if the data has larger gaps between related IDs
- Using the `-nocomprehensive` flag to generate more concise reports
