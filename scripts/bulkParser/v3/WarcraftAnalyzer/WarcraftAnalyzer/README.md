# WarcraftAnalyzer

**WarcraftAnalyzer** is a C# application designed to parse and analyze various World of Warcraft binary file formats, providing insights into game data structures. It leverages the [Warcraft.NET](https://github.com/ModernWoWTools/Warcraft.NET) library to handle the intricacies of these formats.

## Features

- **Parsing Capabilities**: Supports reading and interpreting multiple World of Warcraft file formats, including:
  - **ADT Files**: Terrain data files.
  - **PD4 Files**: Specific data structures used in the game.
  - **PM4 Files**: Various model and texture data files.

- **Modular Design**: Organized codebase with dedicated modules for each file type, facilitating easy maintenance and expansion.

## Prerequisites

- [.NET 8.0 SDK](https://dotnet.microsoft.com/download/dotnet/8.0): Ensure that your development environment is set up with .NET 8.0, as both WarcraftAnalyzer and Warcraft.NET target this version.

- **Warcraft.NET Library**: The project references the [Warcraft.NET](https://github.com/ModernWoWTools/Warcraft.NET) library, which is expected to be located in the parent directory relative to WarcraftAnalyzer:
  ```
  ../Warcraft.NET/Warcraft.NET.csproj
  ```
  Ensure that this path is correct or adjust the project reference accordingly.

## Getting Started

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/akspa0/parp.git
   ```
   Navigate to the WarcraftAnalyzer directory:
   ```bash
   cd parp/scripts/bulkParser/v3/WarcraftAnalyzer/WarcraftAnalyzer
   ```

2. **Verify Warcraft.NET Reference**:
   Ensure that the `Warcraft.NET` library is correctly referenced in your project. The `WarcraftAnalyzer.csproj` should contain:
   ```xml
   <ItemGroup>
     <ProjectReference Include="..\Warcraft.NET\Warcraft.NET.csproj" />
   </ItemGroup>
   ```
   Adjust the path if your directory structure differs.

3. **Build the Project**:
   Use the .NET CLI to build the project:
   ```bash
   dotnet build
   ```
   This will restore dependencies and compile the application.

4. **Run the Application**:
   After a successful build, execute the application:
   ```bash
   dotnet run
   ```
   Follow the on-screen instructions to analyze your World of Warcraft data files.

## Contributing

Contributions are welcome! If you encounter issues or have suggestions for improvements, please open an issue or submit a pull request.


## Acknowledgments

- [Warcraft.NET](https://github.com/ModernWoWTools/Warcraft.NET): For providing the foundational library to interact with World of Warcraft file formats.
- [WoWDev Wiki](https://wowdev.wiki/): For extensive documentation and resources on World of Warcraft's file structures.
```
