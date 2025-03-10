# WarcraftAnalyzer

**WarcraftAnalyzer** is a C# command-line tool for analyzing various World of Warcraft files. It parses game data files—such as ADT (including split ADTs), PD4, PM4, water mesh files (WLW, WLQ, WLM), and WDT—and generates JSON reports. When applicable, it also exports terrain data to OBJ format for further inspection.

## Features

- **ADT File Analysis**  
  Processes both standard ADT files and split ADT files (with associated `_obj` and `_tex` components). Exports detailed JSON reports and optionally converts terrain data to OBJ format.
  
- **PD4 & PM4 File Analysis**  
  Parses PD4 (and PM4) files to output their content in JSON format.
  
- **Water Mesh Processing**  
  Supports water mesh files (WLW, WLQ, WLM) and automatically copies associated texture files.
  
- **WDT File Processing**  
  Analyzes WDT files for World of Warcraft maps.
  
- **Unique ID Analysis (Optional)**  
  When enabled, performs additional analysis on ADT files using unique identifiers, with configurable clustering and gap thresholds.
  
- **Recursive Directory Processing**  
  Supports analyzing entire directories and their subdirectories.
  
- **Verbose Logging**  
  Provides detailed console output for debugging and progress monitoring.

## Prerequisites

- [.NET SDK](https://dotnet.microsoft.com/download) – Ensure you have a compatible version of .NET (e.g., .NET 5/6) installed.
- A C# development environment such as Visual Studio, JetBrains Rider, or Visual Studio Code.

## Installation

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/akspa0/parp.git
   cd parp/scripts/bulkParser/v3/WarcraftAnalyzer/WarcraftAnalyzer
   ```

2. **Build the Project:**

   - **Using the .NET CLI:**
     ```bash
     dotnet build
     ```
   - **Or,** open the solution (`.sln`) file in your preferred IDE and build the project.

## Usage

WarcraftAnalyzer is driven entirely via command-line options.

### Basic Command Syntax

```bash
WarcraftAnalyzer.exe [options]
```

### Options

- `--input, -i <path>`  
  **(Required)** Specifies the input file or directory to analyze.

- `--output, -o <path>`  
  Specifies the output directory for analysis results. If not provided, a subdirectory named `analysis` is created within the input's directory.

- `--listfile, -l <path>`  
  The path to a listfile used for reference validation.

- `--recursive, -r`  
  Enables recursive search for files in subdirectories (applicable when the input is a directory).

- `--verbose, -v`  
  Enables verbose logging, which prints detailed progress and debugging information to the console.

- `--uniqueid, -u`  
  Enables unique ID analysis on ADT files, which includes clustering of unique IDs.

- `--cluster-threshold, -ct <int>`  
  Sets the clustering threshold for unique ID analysis (default: 10).

- `--gap-threshold, -gt <int>`  
  Sets the gap threshold between unique IDs for analysis (default: 1000).

- `--no-comprehensive, -nc`  
  Skips generating comprehensive reports.

- `--help, -h`  
  Displays the help message with usage instructions.

### Example Commands

- **Analyze a Single File:**

  ```bash
  WarcraftAnalyzer.exe -i "C:\WoW\Logs\example.adt" -o "C:\WoW\Analysis" -v
  ```

- **Analyze a Directory Recursively with Unique ID Analysis:**

  ```bash
  WarcraftAnalyzer.exe -i "C:\WoW\Logs" -r -u -ct 15 -gt 1200 -v
  ```

## Output

- **JSON Reports:**  
  For every processed file, a corresponding JSON file is generated with parsed data.

- **Terrain OBJ Exports:**  
  When an ADT file contains terrain chunks, an OBJ file is exported for visualization.

- **Organized Directory Structure:**  
  The output directory will be organized into subdirectories (e.g., `ADT`, `PD4`, `PM4`, `WaterMeshes`, `WDT`, and `UniqueID` if applicable) based on the file type.

## Error Handling & Logging

- Errors and warnings are printed to the console.
- In verbose mode, detailed logs help diagnose processing issues.
- The tool maintains counts of successfully processed files and errors, which are displayed upon completion.

## Contributing

Contributions are welcome! To contribute:

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Implement your changes with clear documentation.
4. Submit a pull request for review.

