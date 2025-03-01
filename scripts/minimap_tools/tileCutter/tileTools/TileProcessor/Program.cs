using System;
using System.CommandLine;
using System.Threading.Tasks;

namespace TileProcessor
{
    class Program
    {
        static async Task<int> Main(string[] args)
        {
            var rootCommand = new RootCommand("Process image tiles - cut and join with level support");

            // Create subcommands for cut and join operations
            var cutCommand = new Command("cut", "Cut an image into tiles");
            var joinCommand = new Command("join", "Join tiles into a single image");
            rootCommand.AddCommand(cutCommand);
            rootCommand.AddCommand(joinCommand);

            // Cut command options
            var inputImageOption = new Option<string>(
                "--input-image",
                "Path to the input image") { IsRequired = true };
            
            var outputFolderOption = new Option<string>(
                "--output-folder",
                "Path to the output folder") { IsRequired = true };
            
            var tileSizeOption = new Option<int>(
                "--tile-size",
                () => 128,
                "Size of each tile");
            
            var prefixOption = new Option<string>(
                "--prefix",
                "Prefix for the output filenames") { IsRequired = true };
            
            var noCombineOption = new Option<bool>(
                "--no-combine",
                () => false,
                "Do not combine the outputs at the end");
            
            var vcolOption = new Option<bool>(
                "--vcol",
                () => false,
                "Generate vertex color maps");

            var createKritaOption = new Option<bool>(
                "--create-krita",
                () => true,
                "Create a Krita file with all layers");

            cutCommand.AddOption(inputImageOption);
            cutCommand.AddOption(outputFolderOption);
            cutCommand.AddOption(tileSizeOption);
            cutCommand.AddOption(prefixOption);
            cutCommand.AddOption(noCombineOption);
            cutCommand.AddOption(vcolOption);
            cutCommand.AddOption(createKritaOption);

            cutCommand.SetHandler(async (inputImagePath, outputFolder, tileSize, prefix, noCombine, vcol, createKrita) =>
            {
                await TileCutter.ProcessImage(inputImagePath, outputFolder, tileSize, prefix, !noCombine, vcol, createKrita);
            }, 
            inputImageOption, outputFolderOption, tileSizeOption, prefixOption, noCombineOption, vcolOption, createKritaOption);

            // Join command options
            var inputFolderOption = new Option<string>(
                "--input-folder",
                "Path to the folder containing image tiles") { IsRequired = true };
            
            var outputImageOption = new Option<string>(
                "--output-image",
                "Path to save the output image") { IsRequired = true };
            
            var joinTileSizeOption = new Option<int>(
                "--tile-size",
                () => 257,
                "Size of each tile");

            var includeAlphaLayersOption = new Option<bool>(
                "--include-alpha",
                () => true,
                "Include alpha layers in the join process");

            joinCommand.AddOption(inputFolderOption);
            joinCommand.AddOption(outputImageOption);
            joinCommand.AddOption(joinTileSizeOption);
            joinCommand.AddOption(createKritaOption);
            joinCommand.AddOption(includeAlphaLayersOption);

            joinCommand.SetHandler(async (inputFolder, outputImage, tileSize, createKrita, includeAlpha) =>
            {
                await TileJoiner.StitchTiles(inputFolder, tileSize, outputImage, createKrita, includeAlpha);
            },
            inputFolderOption, outputImageOption, joinTileSizeOption, createKritaOption, includeAlphaLayersOption);

            // Parse the command line arguments and execute the appropriate command
            return await rootCommand.InvokeAsync(args);
        }
    }
}