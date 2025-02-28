# ModernWoWTools.ADTMeta.Analysis

A command-line tool for analyzing World of Warcraft ADT (terrain) files to extract and validate references to textures, models, and world model objects.

## Overview

ModernWoWTools.ADTMeta.Analysis is designed to help World of Warcraft modders and developers analyze terrain files (ADT) to:

- Extract references to textures, models (M2), and world model objects (WMO)
- Validate these references against a listfile
- Generate reports on file references and object placements
- Identify potential issues with terrain files

The tool is built on top of the Warcraft.NET library for parsing ADT files and provides a user-friendly command-line interface.

## Installation

### Prerequisites

- [.NET 8.0 SDK](https://dotnet.microsoft.com/download/dotnet/8.0) or later
- ModernWoWTools/ADTMeta (git submodule init && git submodule update)

### Building from Source

2. Build the project:
   ```
   dotnet build
   ```

3. Run the tool:
   ```
   dotnet run --project ModernWoWTools.ADTMeta.Analysis/ModernWoWTools.ADTMeta.Analysis.csproj -- [options]
   ```

## Usage

```
ModernWoWTools.ADTMeta.Analysis [options]
```

### Options

| Option | Alias | Description | Required |
|--------|-------|-------------|----------|
| `--directory` | `-d` | The directory containing ADT files to analyze | Yes |
| `--listfile` | `-l` | The path to the listfile for reference validation | No |
| `--output` | `-o` | The directory to write reports to | No |
| `--recursive` | `-r` | Whether to search subdirectories | No |
| `--verbose` | `-v` | Whether to enable verbose logging | No |
| `--json` | `-j` | Whether to generate JSON reports | No |

### Examples

Analyze all ADT files in a directory:
```
dotnet run --project ModernWoWTools.ADTMeta.Analysis/ModernWoWTools.ADTMeta.Analysis.csproj -- --directory "C:\WoW\ADTs"
```

Analyze ADT files with reference validation:
```
dotnet run --project ModernWoWTools.ADTMeta.Analysis/ModernWoWTools.ADTMeta.Analysis.csproj -- --directory "C:\WoW\ADTs" --listfile "C:\WoW\listfile.csv"
```

Generate JSON reports:
```
dotnet run --project ModernWoWTools.ADTMeta.Analysis/ModernWoWTools.ADTMeta.Analysis.csproj -- --directory "C:\WoW\ADTs" --output "C:\Reports" --json
```

## Features

### ADT Parsing

The tool parses ADT files using the Warcraft.NET library and extracts:

- Texture references (MTEX chunk)
- Model references (MMDX chunk)
- World model object references (MWMO chunk)
- Model placements (MDDF chunk)
- World model object placements (MODF chunk)

### Reference Validation

When a listfile is provided, the tool validates all extracted references against it to identify:

- Missing textures
- Missing models
- Missing world model objects

### Reporting

The tool generates reports in the following formats:

- Console output
- Log files
- JSON reports (when the `--json` option is used)

## Project Structure

- **Models**: Data structures for analysis results
- **Services**: Core functionality for parsing, validation, and reporting
- **Utilities**: Helper classes for logging, path handling, etc.

## Dependencies

- [Warcraft.NET](https://github.com/WowDevTools/Warcraft.NET): Library for parsing World of Warcraft file formats
- [System.CommandLine](https://github.com/dotnet/command-line-api): Library for building command-line applications

## Troubleshooting

### Common Issues

- **File not found errors**: Ensure that the paths to the ADT files and listfile are correct.
- **Invalid file format errors**: Ensure that the ADT files are valid and not corrupted.
- **Memory issues**: When processing large numbers of ADT files, consider increasing the memory allocation for the .NET runtime.

### Logging

The tool creates log files in the following locations:

- When an output directory is specified: `{output}/logs/adt_analysis_{timestamp}.log`
- When no output directory is specified: `{directory}/logs/adt_analysis_{timestamp}.log`

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- [WoWDevTools](https://github.com/WowDevTools) for the Warcraft.NET library
- The World of Warcraft modding community for their research and documentation on ADT file formats
