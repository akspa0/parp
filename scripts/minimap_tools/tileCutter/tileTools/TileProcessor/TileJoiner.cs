using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading.Tasks;

namespace TileProcessor
{
    public static class TileJoiner
    {
        // Regex patterns for different tile types
        private static readonly Regex CoordinatePattern = new Regex(@"_(\d+)_(\d+)", RegexOptions.Compiled);
        private static readonly Regex LayerPattern = new Regex(@"_layer([1-3])$", RegexOptions.Compiled);
        private static readonly Regex HeightMapPattern = new Regex(@"_height$", RegexOptions.Compiled);
        
        // Combined pattern to extract coordinates and detect special types
        private static readonly Regex TilePattern = new Regex(@"_(\d+)_(\d+)(?:_layer\d+|_height)?\.png$", RegexOptions.Compiled);

        public static async Task StitchTiles(string inputFolder, int tileSize, string outputImagePath, bool createKrita, bool includeAlpha)
        {
            Console.WriteLine($"Joining tiles from folder: {inputFolder}");

            // Debug: List all files in the folder
            var allFilesInDirectory = Directory.GetFiles(inputFolder, "*.png");
            Console.WriteLine($"Found {allFilesInDirectory.Length} PNG files in folder:");
            foreach (var file in allFilesInDirectory.Take(10)) // Only show first 10 to avoid flooding console
            {
                Console.WriteLine($"  - {Path.GetFileName(file)}");
            }
            if (allFilesInDirectory.Length > 10)
            {
                Console.WriteLine($"  ... and {allFilesInDirectory.Length - 10} more files");
            }

            // Get a list of all image files in the input folder
            var allFiles = Directory.GetFiles(inputFolder, "*.png")
                .Select(path => new { Path = path, Filename = Path.GetFileName(path) })
                .ToList();

            // Filter files by type
            var baseTiles = allFiles
                .Where(file => !LayerPattern.IsMatch(Path.GetFileNameWithoutExtension(file.Path)) && 
                               !HeightMapPattern.IsMatch(Path.GetFileNameWithoutExtension(file.Path)))
                .ToList();

            var layerTiles = allFiles
                .Where(file => LayerPattern.IsMatch(Path.GetFileNameWithoutExtension(file.Path)))
                .ToList();

            var heightTiles = allFiles
                .Where(file => HeightMapPattern.IsMatch(Path.GetFileNameWithoutExtension(file.Path)))
                .ToList();

            Console.WriteLine($"Categorized files: {baseTiles.Count} base tiles, {layerTiles.Count} layer tiles, {heightTiles.Count} height tiles");

            if (baseTiles.Count == 0)
            {
                Console.WriteLine("No base tile files found in the input folder.");
                return;
            }

            // Extract coordinates from base tiles
            var tileIndices = new List<(int X, int Y, string Path)>();
            foreach (var file in baseTiles)
            {
                var match = CoordinatePattern.Match(file.Filename);
                if (match.Success && match.Groups.Count >= 3)
                {
                    int x = int.Parse(match.Groups[1].Value);
                    int y = int.Parse(match.Groups[2].Value);
                    tileIndices.Add((x, y, file.Path));
                }
                else
                {
                    Console.WriteLine($"File didn't match coordinate pattern: {file.Filename}");
                }
            }

            if (tileIndices.Count == 0)
            {
                Console.WriteLine("No tiles with valid coordinate pattern found.");
                return;
            }

            Console.WriteLine($"Found {tileIndices.Count} valid base tiles.");

            // Determine image dimensions
            int maxXIndex = tileIndices.Max(t => t.X);
            int maxYIndex = tileIndices.Max(t => t.Y);
            int newImageWidth = (maxXIndex + 1) * tileSize;
            int newImageHeight = (maxYIndex + 1) * tileSize;

            Console.WriteLine($"New image dimensions: {newImageWidth} x {newImageHeight}");

            // Create the stitched base image
            using var baseImage = new Bitmap(newImageWidth, newImageHeight);
            using var baseGraphics = Graphics.FromImage(baseImage);
            
            // Fill with white background
            baseGraphics.Clear(Color.White);

            // Paste each base tile
            foreach (var (x, y, path) in tileIndices)
            {
                using var tile = new Bitmap(path);
                int posX = x * tileSize;
                int posY = y * tileSize;
                baseGraphics.DrawImage(tile, posX, posY);
                Console.WriteLine($"Pasted base tile at: ({posX}, {posY})");
            }

            // Save the stitched base image
            baseImage.Save(outputImagePath, ImageFormat.Png);
            Console.WriteLine($"Base image saved at: {outputImagePath}");

            // Create dictionaries to hold layer and height images
            var layerImages = new Dictionary<int, Bitmap>();
            var layerGraphics = new Dictionary<int, Graphics>();
            Bitmap heightImage = null;
            Graphics heightGraphics = null;

            // Process alpha layers
            if (includeAlpha)
            {
                // Initialize layer images
                for (int layer = 1; layer <= 3; layer++)
                {
                    layerImages[layer] = new Bitmap(newImageWidth, newImageHeight);
                    layerGraphics[layer] = Graphics.FromImage(layerImages[layer]);
                    layerGraphics[layer].Clear(Color.White);
                }

                // Initialize height image if we have height tiles
                if (heightTiles.Count > 0)
                {
                    heightImage = new Bitmap(newImageWidth, newImageHeight);
                    heightGraphics = Graphics.FromImage(heightImage);
                    heightGraphics.Clear(Color.Black);
                }

                // Process layer tiles
                foreach (var file in layerTiles)
                {
                    var filenameWithoutExt = Path.GetFileNameWithoutExtension(file.Path);
                    var coordMatch = CoordinatePattern.Match(file.Filename);
                    var layerMatch = LayerPattern.Match(filenameWithoutExt);
                    
                    if (coordMatch.Success && layerMatch.Success)
                    {
                        int x = int.Parse(coordMatch.Groups[1].Value);
                        int y = int.Parse(coordMatch.Groups[2].Value);
                        int layer = int.Parse(layerMatch.Groups[1].Value);
                        
                        if (layer >= 1 && layer <= 3)
                        {
                            using var tile = new Bitmap(file.Path);
                            int posX = x * tileSize;
                            int posY = y * tileSize;
                            layerGraphics[layer].DrawImage(tile, posX, posY);
                            Console.WriteLine($"Pasted layer {layer} tile at: ({posX}, {posY})");
                        }
                    }
                    else
                    {
                        Console.WriteLine($"Layer file didn't match expected pattern: {file.Filename}");
                    }
                }

                // Process height tiles
                if (heightImage != null)
                {
                    foreach (var file in heightTiles)
                    {
                        var coordMatch = CoordinatePattern.Match(file.Filename);
                        
                        if (coordMatch.Success)
                        {
                            int x = int.Parse(coordMatch.Groups[1].Value);
                            int y = int.Parse(coordMatch.Groups[2].Value);
                            
                            using var tile = new Bitmap(file.Path);
                            int posX = x * tileSize;
                            int posY = y * tileSize;
                            heightGraphics.DrawImage(tile, posX, posY);
                            Console.WriteLine($"Pasted height tile at: ({posX}, {posY})");
                        }
                        else
                        {
                            Console.WriteLine($"Height file didn't match coordinate pattern: {file.Filename}");
                        }
                    }
                }

                // Save layer images
                string baseOutputPath = Path.Combine(
                    Path.GetDirectoryName(outputImagePath) ?? "",
                    Path.GetFileNameWithoutExtension(outputImagePath));
                
                for (int layer = 1; layer <= 3; layer++)
                {
                    string layerOutputPath = $"{baseOutputPath}_layer{layer}.png";
                    layerImages[layer].Save(layerOutputPath, ImageFormat.Png);
                    Console.WriteLine($"Layer {layer} image saved at: {layerOutputPath}");
                }

                // Save height image if it exists
                if (heightImage != null)
                {
                    string heightOutputPath = $"{baseOutputPath}_height.png";
                    heightImage.Save(heightOutputPath, ImageFormat.Png);
                    Console.WriteLine($"Height map saved at: {heightOutputPath}");
                }

                // Create Krita file if requested
                if (createKrita)
                {
                    await CreateKritaFile(outputImagePath, layerImages, heightImage);
                }

                // Dispose graphics objects
                foreach (var graphics in layerGraphics.Values)
                {
                    graphics.Dispose();
                }
                
                heightGraphics?.Dispose();
                
                // Dispose bitmap objects
                foreach (var image in layerImages.Values)
                {
                    image.Dispose();
                }
                
                heightImage?.Dispose();
            }
        }

        private static async Task CreateKritaFile(string baseImagePath, Dictionary<int, Bitmap> layerImages, Bitmap heightImage)
        {
            string kritaFilePath = Path.Combine(
                Path.GetDirectoryName(baseImagePath) ?? "",
                $"{Path.GetFileNameWithoutExtension(baseImagePath)}.kra");

            var tempDir = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString());
            Directory.CreateDirectory(tempDir);
            
            try
            {
                // Create Krita file structure
                Directory.CreateDirectory(Path.Combine(tempDir, "data"));
                Directory.CreateDirectory(Path.Combine(tempDir, "previews"));
                
                // Create mergedimage.png (main image)
                File.Copy(baseImagePath, Path.Combine(tempDir, "mergedimage.png"));
                
                // Copy layer images
                File.Copy(baseImagePath, Path.Combine(tempDir, "data", "layer1.png"));
                
                // Create layer info list
                var layerInfo = new List<(int LayerNum, string Name, string Filename)>();
                layerInfo.Add((1, "Base Image", "layer1.png"));
                
                int layerIndex = 2;
                
                // Add alpha layers
                foreach (var kvp in layerImages)
                {
                    string layerFilename = $"layer{layerIndex}.png";
                    string colorChannel = kvp.Key == 1 ? "Red" : (kvp.Key == 2 ? "Green" : "Blue");
                    string layerName = $"Alpha Channel {colorChannel}";
                    
                    // Save the layer image
                    string layerPath = Path.Combine(tempDir, "data", layerFilename);
                    kvp.Value.Save(layerPath, ImageFormat.Png);
                    
                    layerInfo.Add((layerIndex, layerName, layerFilename));
                    layerIndex++;
                }
                
                // Add height layer if it exists
                if (heightImage != null)
                {
                    string heightFilename = $"layer{layerIndex}.png";
                    string heightPath = Path.Combine(tempDir, "data", heightFilename);
                    heightImage.Save(heightPath, ImageFormat.Png);
                    
                    layerInfo.Add((layerIndex, "Height Map", heightFilename));
                }
                
                // Create maindoc.xml
                var documentXml = CreateKritaDocumentXml(layerImages.Values.First().Width, 
                                                       layerImages.Values.First().Height, 
                                                       layerInfo);
                await File.WriteAllTextAsync(Path.Combine(tempDir, "maindoc.xml"), documentXml);
                
                // Create mimetype file
                await File.WriteAllTextAsync(Path.Combine(tempDir, "mimetype"), "application/x-krita");
                
                // Create the Krita file
                ZipFile.CreateFromDirectory(tempDir, kritaFilePath);
                
                Console.WriteLine($"Krita file created at: {kritaFilePath}");
            }
            finally
            {
                // Clean up the temp directory
                if (Directory.Exists(tempDir))
                {
                    Directory.Delete(tempDir, true);
                }
            }
        }
        
        private static string CreateKritaDocumentXml(int width, int height, List<(int LayerNum, string Name, string Filename)> layerInfo)
        {
            var xml = new StringBuilder();
            xml.AppendLine("<?xml version=\"1.0\" encoding=\"UTF-8\"?>");
            xml.AppendLine("<DOC xmlns=\"http://www.calligra.org/DTD/krita\">");
            xml.AppendLine($" <IMAGE width=\"{width}\" height=\"{height}\" colorspacename=\"RGBA\">");
            xml.AppendLine("  <LAYERS>");
            
            // Reverse the layer order so that base is on bottom
            foreach (var layer in layerInfo.OrderByDescending(l => l.LayerNum))
            {
                xml.AppendLine($"   <LAYER name=\"{layer.Name}\" filename=\"{layer.Filename}\" visible=\"1\">");
                xml.AppendLine("   </LAYER>");
            }
            
            xml.AppendLine("  </LAYERS>");
            xml.AppendLine(" </IMAGE>");
            xml.AppendLine("</DOC>");
            
            return xml.ToString();
        }
    }
}