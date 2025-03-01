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
    public static class TileCutter
    {
        private static readonly Regex LayerPattern = new Regex(@"_layer([1-3])$", RegexOptions.Compiled);
        private static readonly Regex HeightMapPattern = new Regex(@"_height$", RegexOptions.Compiled);

        public static async Task ProcessImage(string inputImagePath, string outputFolder, int tileSize, string prefix, 
            bool combine, bool vcol, bool createKrita)
        {
            Console.WriteLine($"Processing image: {inputImagePath}");
            
            // Ensure output directory exists
            Directory.CreateDirectory(outputFolder);

            // Group input files by their base name (without specific suffixes)
            var inputFiles = Directory.GetFiles(Path.GetDirectoryName(inputImagePath) ?? ".", "*.png")
                .GroupBy(path => GetBaseFileName(path))
                .ToDictionary(g => g.Key, g => g.ToList());

            var mainImagePath = inputImagePath;
            if (inputFiles.ContainsKey(GetBaseFileName(inputImagePath)))
            {
                var fileGroup = inputFiles[GetBaseFileName(inputImagePath)];
                mainImagePath = fileGroup.FirstOrDefault(f => !IsLayerFile(f) && !IsHeightFile(f)) ?? inputImagePath;
            }

            using var originalImage = new Bitmap(mainImagePath);
            var nonBlankTiles = new List<(int Left, int Upper, int Right, int Lower, string BaseName)>();

            int numTilesX = originalImage.Width / tileSize;
            int numTilesY = originalImage.Height / tileSize;

            Console.WriteLine($"Number of tiles to process: {numTilesX} x {numTilesY}");

            // Process main image
            for (int y = 0; y < numTilesY; y++)
            {
                for (int x = 0; x < numTilesX; x++)
                {
                    int left = x * tileSize;
                    int upper = y * tileSize;
                    int right = left + tileSize;
                    int lower = upper + tileSize;

                    using var tile = new Bitmap(tileSize, tileSize);
                    using var tileGraphics = Graphics.FromImage(tile);
                    
                    // Copy the tile from the original image
                    tileGraphics.DrawImage(originalImage, 
                        new Rectangle(0, 0, tileSize, tileSize),
                        new Rectangle(left, upper, tileSize, tileSize),
                        GraphicsUnit.Pixel);

                    if (!IsBlankOrWhite(tile))
                    {
                        string suffix = vcol ? "_vcol" : "";
                        string tileName = $"{prefix}_{x}_{y}";
                        string tilePath = Path.Combine(outputFolder, $"{tileName}{suffix}.png");
                        
                        tile.Save(tilePath, ImageFormat.Png);
                        Console.WriteLine($"Processed tile {x}_{y} saved at: {tilePath}");
                        
                        nonBlankTiles.Add((left, upper, right, lower, tileName));
                        
                        // Process layer files for the current tile
                        ProcessLayerFiles(inputFiles, left, upper, tileSize, outputFolder, 
                            $"{prefix}_{x}_{y}", vcol);

                        // Process height files for the current tile if they exist
                        ProcessHeightFiles(inputFiles, left, upper, tileSize, outputFolder,
                            $"{prefix}_{x}_{y}", vcol);
                    }
                }
            }

            if (combine)
            {
                var newImagePath = Path.Combine(outputFolder, $"{prefix}_new.png");
                BuildNewImage(originalImage, nonBlankTiles, tileSize, newImagePath);
                
                if (createKrita)
                {
                    await CreateKritaFile(outputFolder, prefix, nonBlankTiles);
                }

                ZipOutputFolder(inputImagePath, outputFolder, newImagePath);
            }
        }

        private static void ProcessLayerFiles(Dictionary<string, List<string>> inputFiles, 
            int left, int upper, int tileSize, string outputFolder, string tileBaseName, bool vcol)
        {
            foreach (var levelFileGroup in inputFiles.Values)
            {
                foreach (var levelFile in levelFileGroup.Where(IsLayerFile))
                {
                    var levelMatch = LayerPattern.Match(Path.GetFileNameWithoutExtension(levelFile));
                    if (levelMatch.Success)
                    {
                        string levelNum = levelMatch.Groups[1].Value;
                        using var levelImage = new Bitmap(levelFile);
                        using var levelTile = new Bitmap(tileSize, tileSize);
                        using var levelTileGraphics = Graphics.FromImage(levelTile);
                        
                        // Copy the tile from the level image
                        levelTileGraphics.DrawImage(levelImage, 
                            new Rectangle(0, 0, tileSize, tileSize),
                            new Rectangle(left, upper, tileSize, tileSize),
                            GraphicsUnit.Pixel);

                        if (!IsBlankOrWhite(levelTile))
                        {
                            string suffix = vcol ? "_vcol" : "";
                            string levelTilePath = Path.Combine(outputFolder, $"{tileBaseName}_layer{levelNum}{suffix}.png");
                            levelTile.Save(levelTilePath, ImageFormat.Png);
                            Console.WriteLine($"Processed layer{levelNum} tile saved at: {levelTilePath}");
                        }
                    }
                }
            }
        }

        private static void ProcessHeightFiles(Dictionary<string, List<string>> inputFiles,
            int left, int upper, int tileSize, string outputFolder, string tileBaseName, bool vcol)
        {
            foreach (var heightFileGroup in inputFiles.Values)
            {
                foreach (var heightFile in heightFileGroup.Where(IsHeightFile))
                {
                    using var heightImage = new Bitmap(heightFile);
                    using var heightTile = new Bitmap(tileSize, tileSize);
                    using var heightTileGraphics = Graphics.FromImage(heightTile);
                    
                    // Copy the tile from the height image
                    heightTileGraphics.DrawImage(heightImage, 
                        new Rectangle(0, 0, tileSize, tileSize),
                        new Rectangle(left, upper, tileSize, tileSize),
                        GraphicsUnit.Pixel);

                    if (!IsBlankOrWhite(heightTile))
                    {
                        string suffix = vcol ? "_vcol" : "";
                        string heightTilePath = Path.Combine(outputFolder, $"{tileBaseName}_height{suffix}.png");
                        heightTile.Save(heightTilePath, ImageFormat.Png);
                        Console.WriteLine($"Processed height tile saved at: {heightTilePath}");
                    }
                }
            }
        }

        private static bool IsLayerFile(string filePath)
        {
            return LayerPattern.IsMatch(Path.GetFileNameWithoutExtension(filePath));
        }

        private static bool IsHeightFile(string filePath)
        {
            return HeightMapPattern.IsMatch(Path.GetFileNameWithoutExtension(filePath));
        }

        private static string GetBaseFileName(string filePath)
        {
            string fileName = Path.GetFileNameWithoutExtension(filePath);
            fileName = LayerPattern.Replace(fileName, "");
            fileName = HeightMapPattern.Replace(fileName, "");
            return fileName;
        }

        private static bool IsBlankOrWhite(Bitmap image)
        {
            const int threshold = 240;
            
            // Calculate mean pixel intensity
            long totalIntensity = 0;
            int pixelCount = 0;
            
            for (int y = 0; y < image.Height; y++)
            {
                for (int x = 0; x < image.Width; x++)
                {
                    Color color = image.GetPixel(x, y);
                    int intensity = (color.R + color.G + color.B) / 3;
                    totalIntensity += intensity;
                    pixelCount++;
                }
            }
            
            if (pixelCount == 0)
                return true;
                
            double meanIntensity = (double)totalIntensity / pixelCount;
            return meanIntensity >= threshold;
        }

        private static void BuildNewImage(Bitmap originalImage, List<(int Left, int Upper, int Right, int Lower, string BaseName)> nonBlankTiles, 
            int tileSize, string newImagePath)
        {
            if (nonBlankTiles.Count == 0)
            {
                Console.WriteLine("No non-blank tiles found. Cannot create new image.");
                return;
            }

            int minX = nonBlankTiles.Min(t => t.Left);
            int minY = nonBlankTiles.Min(t => t.Upper);
            int maxX = nonBlankTiles.Max(t => t.Right);
            int maxY = nonBlankTiles.Max(t => t.Lower);

            int newWidth = maxX - minX;
            int newHeight = maxY - minY;

            Console.WriteLine($"New image dimensions: {newWidth} x {newHeight}");

            using var newImage = new Bitmap(newWidth, newHeight);
            using var newImageGraphics = Graphics.FromImage(newImage);
            
            // Fill with white background
            newImageGraphics.Clear(Color.White);
            
            foreach (var tile in nonBlankTiles)
            {
                int destX = tile.Left - minX;
                int destY = tile.Upper - minY;
                
                Console.WriteLine($"Pasting tile at coordinates: ({destX}, {destY})");
                
                // Copy the tile from the original image
                newImageGraphics.DrawImage(originalImage, 
                    new Rectangle(destX, destY, tileSize, tileSize),
                    new Rectangle(tile.Left, tile.Upper, tileSize, tileSize),
                    GraphicsUnit.Pixel);
            }

            newImage.Save(newImagePath, ImageFormat.Png);
            Console.WriteLine($"New image saved at: {newImagePath}");
        }

        private static async Task CreateKritaFile(string outputFolder, string prefix, 
            List<(int Left, int Upper, int Right, int Lower, string BaseName)> nonBlankTiles)
        {
            var tempDir = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString());
            Directory.CreateDirectory(tempDir);
            
            try
            {
                // Create Krita file structure
                Directory.CreateDirectory(Path.Combine(tempDir, "data"));
                Directory.CreateDirectory(Path.Combine(tempDir, "previews"));
                
                // Create mergedimage.png (main image)
                var mainImagePath = Path.Combine(outputFolder, $"{prefix}_new.png");
                if (File.Exists(mainImagePath))
                {
                    File.Copy(mainImagePath, Path.Combine(tempDir, "mergedimage.png"));
                }
                
                // Create maindoc.xml 
                var documentXml = CreateKritaDocumentXml(outputFolder, nonBlankTiles);
                await File.WriteAllTextAsync(Path.Combine(tempDir, "maindoc.xml"), documentXml);
                
                // Create mimetype file
                await File.WriteAllTextAsync(Path.Combine(tempDir, "mimetype"), "application/x-krita");
                
                // Copy all layer images
                var layerFolder = Path.Combine(tempDir, "data");
                
                // Main layer
                if (File.Exists(mainImagePath))
                {
                    File.Copy(mainImagePath, Path.Combine(layerFolder, "layer1.png"));
                }
                
                // Copy level layers and height layers
                int layerIndex = 2;
                
                // First, check for and add layer files
                foreach (var tile in nonBlankTiles)
                {
                    for (int level = 1; level <= 3; level++)
                    {
                        var levelPath = Path.Combine(outputFolder, $"{tile.BaseName}_layer{level}.png");
                        if (File.Exists(levelPath))
                        {
                            File.Copy(levelPath, Path.Combine(layerFolder, $"layer{layerIndex}.png"));
                            layerIndex++;
                        }
                    }
                }
                
                // Next, check for and add height files
                foreach (var tile in nonBlankTiles)
                {
                    var heightPath = Path.Combine(outputFolder, $"{tile.BaseName}_height.png");
                    if (File.Exists(heightPath))
                    {
                        File.Copy(heightPath, Path.Combine(layerFolder, $"layer{layerIndex}.png"));
                        layerIndex++;
                    }
                }
                
                // Create the Krita file (which is a zip file)
                var kritaPath = Path.Combine(outputFolder, $"{prefix}.kra");
                ZipFile.CreateFromDirectory(tempDir, kritaPath);
                
                Console.WriteLine($"Krita file created at: {kritaPath}");
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
        
        private static string CreateKritaDocumentXml(string outputFolder, 
            List<(int Left, int Upper, int Right, int Lower, string BaseName)> nonBlankTiles)
        {
            // This is a simplified XML structure for Krita
            string xml = @"<?xml version=""1.0"" encoding=""UTF-8""?>
<DOC xmlns=""http://www.calligra.org/DTD/krita"">
 <IMAGE width=""$WIDTH"" height=""$HEIGHT"" colorspacename=""RGBA"">
  <LAYERS>
   <LAYER name=""Background"" filename=""layer1.png"" visible=""1"">
   </LAYER>
";
            // Add layer layers
            int layerIndex = 2;
            foreach (var tile in nonBlankTiles)
            {
                for (int level = 1; level <= 3; level++)
                {
                    var levelPath = Path.Combine(outputFolder, $"{tile.BaseName}_layer{level}.png");
                    if (File.Exists(levelPath))
                    {
                        string colorChannel = level == 1 ? "Red" : (level == 2 ? "Green" : "Blue");
                        xml += $@"   <LAYER name=""{tile.BaseName} {colorChannel} Alpha"" filename=""layer{layerIndex}.png"" visible=""1"">
   </LAYER>
";
                        layerIndex++;
                    }
                }
            }
            
            // Add height layers
            foreach (var tile in nonBlankTiles)
            {
                var heightPath = Path.Combine(outputFolder, $"{tile.BaseName}_height.png");
                if (File.Exists(heightPath))
                {
                    xml += $@"   <LAYER name=""{tile.BaseName} Height Map"" filename=""layer{layerIndex}.png"" visible=""1"">
   </LAYER>
";
                    layerIndex++;
                }
            }

            xml += @"  </LAYERS>
 </IMAGE>
</DOC>";

            // Get image dimensions from the first file
            var mainImagePath = Path.Combine(outputFolder, $"{nonBlankTiles[0].BaseName}.png");
            if (File.Exists(mainImagePath))
            {
                using var img = new Bitmap(mainImagePath);
                xml = xml.Replace("$WIDTH", img.Width.ToString());
                xml = xml.Replace("$HEIGHT", img.Height.ToString());
            }
            else
            {
                xml = xml.Replace("$WIDTH", "1024");
                xml = xml.Replace("$HEIGHT", "1024");
            }

            return xml;
        }

        private static void ZipOutputFolder(string inputImagePath, string outputFolder, string newImagePath)
        {
            string inputFilename = Path.GetFileNameWithoutExtension(inputImagePath);
            string outputFolderName = Path.GetFileName(outputFolder);
            string zipFilename = $"{inputFilename}_{outputFolderName}.zip";

            using (var zipArchive = ZipFile.Open(zipFilename, ZipArchiveMode.Create))
            {
                foreach (var file in Directory.GetFiles(outputFolder))
                {
                    zipArchive.CreateEntryFromFile(file, Path.GetFileName(file));
                }
                
                // Add the new image file to the zip archive with a unique name if it's not already added
                string newImageFilename = $"{inputFilename}_new.png";
                if (File.Exists(newImagePath) && !zipArchive.Entries.Any(e => e.Name == newImageFilename))
                {
                    zipArchive.CreateEntryFromFile(newImagePath, newImageFilename);
                }
            }

            Console.WriteLine($"Output folder and new image zipped and saved as: {zipFilename}");
        }
    }
}