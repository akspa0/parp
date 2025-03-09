using System;
using System.Collections.Generic;
using System.IO;
using Warcraft.NET.Files.Structures;

namespace WarcraftAnalyzer.Files.ADT
{
    /// <summary>
    /// Represents an Alpha version ADT (Azeroth Terrain) file.
    /// This implementation handles the specific format used in the Alpha version of WoW.
    /// </summary>
    public class AlphaADTFile
    {
        /// <summary>
        /// Gets the file name.
        /// </summary>
        public string FileName { get; private set; }

        /// <summary>
        /// Gets the X coordinate.
        /// </summary>
        public int XCoord { get; private set; }

        /// <summary>
        /// Gets the Y coordinate.
        /// </summary>
        public int YCoord { get; private set; }

        /// <summary>
        /// Gets the list of model references (MDNM entries).
        /// </summary>
        public List<string> ModelReferences { get; private set; } = new List<string>();

        /// <summary>
        /// Gets the list of WMO references (MONM entries).
        /// </summary>
        public List<string> WmoReferences { get; private set; } = new List<string>();

        /// <summary>
        /// Gets the list of model placements.
        /// </summary>
        public List<AlphaModelPlacement> ModelPlacements { get; private set; } = new List<AlphaModelPlacement>();

        /// <summary>
        /// Gets the list of WMO placements.
        /// </summary>
        public List<AlphaWmoPlacement> WmoPlacements { get; private set; } = new List<AlphaWmoPlacement>();

        /// <summary>
        /// Gets the terrain data.
        /// </summary>
        public AlphaTerrainData TerrainData { get; private set; }

        /// <summary>
        /// Gets the list of errors encountered during parsing.
        /// </summary>
        public List<string> Errors { get; private set; } = new List<string>();

        /// <summary>
        /// Creates a new instance of the AlphaADTFile class.
        /// </summary>
        /// <param name="data">The raw file data.</param>
        /// <param name="fileName">The name of the file.</param>
        /// <param name="modelNames">Optional list of model names from WDT MDNM chunk.</param>
        /// <param name="wmoNames">Optional list of WMO names from WDT MONM chunk.</param>
        public AlphaADTFile(byte[] data, string fileName, IList<string> modelNames = null, IList<string> wmoNames = null)
        {
            if (data == null)
                throw new ArgumentNullException(nameof(data));

            if (string.IsNullOrEmpty(fileName))
                throw new ArgumentException("File name cannot be null or empty.", nameof(fileName));

            FileName = fileName;
            ExtractCoordinates(fileName);

            try
            {
                using (var reader = new BinaryReader(new MemoryStream(data)))
                {
                    ParseFile(reader, modelNames, wmoNames);
                }
            }
            catch (Exception ex)
            {
                Errors.Add($"Error parsing Alpha ADT file: {ex.Message}");
                throw;
            }
        }

        private void ExtractCoordinates(string fileName)
        {
            // Extract coordinates from filename (format: map_X_Y or similar)
            var parts = Path.GetFileNameWithoutExtension(fileName).Split('_');
            if (parts.Length >= 3 &&
                int.TryParse(parts[parts.Length - 2], out int x) &&
                int.TryParse(parts[parts.Length - 1], out int y))
            {
                XCoord = x;
                YCoord = y;
            }
        }

        private void ParseFile(BinaryReader reader, IList<string> modelNames, IList<string> wmoNames)
        {
            // Alpha ADT format parsing based on wowdev.wiki/Alpha
            while (reader.BaseStream.Position < reader.BaseStream.Length)
            {
                var chunkId = new string(reader.ReadChars(4));
                var chunkSize = reader.ReadUInt32();
                var chunkStart = reader.BaseStream.Position;

                switch (chunkId)
                {
                    case "MMDX": // Model filenames
                        if (modelNames == null) // Only parse if not provided from WDT
                        {
                            ParseStringList(reader, chunkSize, ModelReferences);
                        }
                        else
                        {
                            ModelReferences.AddRange(modelNames);
                        }
                        break;

                    case "MMID": // Model instance data
                        ParseModelInstances(reader, chunkSize);
                        break;

                    case "MWMO": // WMO filenames
                        if (wmoNames == null) // Only parse if not provided from WDT
                        {
                            ParseStringList(reader, chunkSize, WmoReferences);
                        }
                        else
                        {
                            WmoReferences.AddRange(wmoNames);
                        }
                        break;

                    case "MWID": // WMO instance data
                        ParseWmoInstances(reader, chunkSize);
                        break;

                    case "MTEX": // Texture filenames
                        var textureList = new List<string>();
                        ParseStringList(reader, chunkSize, textureList);
                        break;

                    case "MCNK": // Terrain chunks
                        ParseTerrainChunk(reader, chunkSize);
                        break;

                    default:
                        // Skip unknown chunk
                        reader.BaseStream.Position += chunkSize;
                        break;
                }

                // Ensure we're at the end of the chunk
                reader.BaseStream.Position = chunkStart + chunkSize;
            }
        }

        private void ParseStringList(BinaryReader reader, uint size, List<string> list)
        {
            var endPos = reader.BaseStream.Position + size;
            while (reader.BaseStream.Position < endPos)
            {
                var str = ReadNullTerminatedString(reader);
                if (!string.IsNullOrEmpty(str))
                {
                    list.Add(str);
                }
            }
        }

        private void ParseModelInstances(BinaryReader reader, uint size)
        {
            var count = size / 36; // Size of each model instance entry
            for (int i = 0; i < count; i++)
            {
                var placement = new AlphaModelPlacement
                {
                    ModelIndex = reader.ReadInt32(),
                    Position = new C3Vector
                    {
                        X = reader.ReadSingle(),
                        Y = reader.ReadSingle(),
                        Z = reader.ReadSingle()
                    },
                    Rotation = new C3Vector
                    {
                        X = reader.ReadSingle(),
                        Y = reader.ReadSingle(),
                        Z = reader.ReadSingle()
                    },
                    Scale = reader.ReadSingle(),
                    Flags = reader.ReadUInt32()
                };

                if (placement.ModelIndex >= 0 && placement.ModelIndex < ModelReferences.Count)
                {
                    placement.ModelPath = ModelReferences[placement.ModelIndex];
                    ModelPlacements.Add(placement);
                }
            }
        }

        private void ParseWmoInstances(BinaryReader reader, uint size)
        {
            var count = size / 36; // Size of each WMO instance entry
            for (int i = 0; i < count; i++)
            {
                var placement = new AlphaWmoPlacement
                {
                    WmoIndex = reader.ReadInt32(),
                    Position = new C3Vector
                    {
                        X = reader.ReadSingle(),
                        Y = reader.ReadSingle(),
                        Z = reader.ReadSingle()
                    },
                    Rotation = new C3Vector
                    {
                        X = reader.ReadSingle(),
                        Y = reader.ReadSingle(),
                        Z = reader.ReadSingle()
                    },
                    Extents = new C3Vector
                    {
                        X = reader.ReadSingle(),
                        Y = reader.ReadSingle(),
                        Z = reader.ReadSingle()
                    }
                };

                if (placement.WmoIndex >= 0 && placement.WmoIndex < WmoReferences.Count)
                {
                    placement.WmoPath = WmoReferences[placement.WmoIndex];
                    WmoPlacements.Add(placement);
                }
            }
        }

        private void ParseTerrainChunk(BinaryReader reader, uint size)
        {
            TerrainData = new AlphaTerrainData();

            // Read header
            TerrainData.Flags = reader.ReadUInt32();
            TerrainData.AreaId = reader.ReadUInt32();
            TerrainData.Holes = reader.ReadUInt32();

            // Read heightmap (17x17 grid)
            for (int y = 0; y < 17; y++)
            {
                for (int x = 0; x < 17; x++)
                {
                    TerrainData.HeightMap[x, y] = reader.ReadSingle();
                }
            }

            // Read texture layers
            var layerCount = reader.ReadUInt32();
            for (int i = 0; i < layerCount; i++)
            {
                var layer = new AlphaTextureLayer
                {
                    TextureId = reader.ReadUInt32(),
                    EffectId = reader.ReadUInt32(),
                    Flags = reader.ReadUInt32(),
                    OffsetX = reader.ReadSingle(),
                    OffsetY = reader.ReadSingle(),
                    ScaleX = reader.ReadSingle(),
                    ScaleY = reader.ReadSingle()
                };
                TerrainData.TextureLayers.Add(layer);
            }

            // Read shadow map
            var shadowMapSize = reader.ReadUInt32();
            TerrainData.ShadowMap = reader.ReadBytes((int)shadowMapSize);

            // Read alpha maps
            var alphaMapCount = reader.ReadUInt32();
            for (int i = 0; i < alphaMapCount; i++)
            {
                var alphaMapSize = reader.ReadUInt32();
                TerrainData.AlphaMaps.Add(reader.ReadBytes((int)alphaMapSize));
            }

            // Read vertex colors
            var vertexColorCount = reader.ReadUInt32();
            for (int i = 0; i < vertexColorCount; i++)
            {
                TerrainData.VertexColors.Add(new C3Vector
                {
                    X = reader.ReadSingle(), // R
                    Y = reader.ReadSingle(), // G
                    Z = reader.ReadSingle()  // B
                });
            }
        }

        private static string ReadNullTerminatedString(BinaryReader reader)
        {
            var chars = new List<char>();
            char c;
            while ((c = reader.ReadChar()) != '\0')
            {
                chars.Add(c);
            }
            return new string(chars.ToArray());
        }
    }

    public class AlphaModelPlacement
    {
        public int ModelIndex { get; set; }
        public string ModelPath { get; set; }
        public C3Vector Position { get; set; }
        public C3Vector Rotation { get; set; }
        public float Scale { get; set; }
        public uint Flags { get; set; }
    }

    public class AlphaWmoPlacement
    {
        public int WmoIndex { get; set; }
        public string WmoPath { get; set; }
        public C3Vector Position { get; set; }
        public C3Vector Rotation { get; set; }
        public C3Vector Extents { get; set; }
    }

    /// <summary>
    /// Represents terrain data in the Alpha ADT format.
    /// Based on wowdev.wiki/Alpha documentation.
    /// </summary>
    public class AlphaTerrainData
    {
        /// <summary>
        /// Gets or sets the terrain height data.
        /// 17x17 grid of height values.
        /// </summary>
        public float[,] HeightMap { get; set; } = new float[17, 17];

        /// <summary>
        /// Gets or sets the terrain flags.
        /// </summary>
        public uint Flags { get; set; }

        /// <summary>
        /// Gets or sets the area ID.
        /// </summary>
        public uint AreaId { get; set; }

        /// <summary>
        /// Gets or sets the terrain holes.
        /// </summary>
        public uint Holes { get; set; }

        /// <summary>
        /// Gets or sets the texture layer data.
        /// </summary>
        public List<AlphaTextureLayer> TextureLayers { get; set; } = new List<AlphaTextureLayer>();

        /// <summary>
        /// Gets or sets the shadow map data.
        /// </summary>
        public byte[] ShadowMap { get; set; }

        /// <summary>
        /// Gets or sets the alpha maps for texture blending.
        /// </summary>
        public List<byte[]> AlphaMaps { get; set; } = new List<byte[]>();

        /// <summary>
        /// Gets or sets the vertex colors.
        /// </summary>
        public List<C3Vector> VertexColors { get; set; } = new List<C3Vector>();
    }

    /// <summary>
    /// Represents a texture layer in the Alpha ADT format.
    /// </summary>
    public class AlphaTextureLayer
    {
        /// <summary>
        /// Gets or sets the texture filename index.
        /// </summary>
        public uint TextureId { get; set; }

        /// <summary>
        /// Gets or sets the effect ID.
        /// </summary>
        public uint EffectId { get; set; }

        /// <summary>
        /// Gets or sets the texture flags.
        /// </summary>
        public uint Flags { get; set; }

        /// <summary>
        /// Gets or sets the texture offset X.
        /// </summary>
        public float OffsetX { get; set; }

        /// <summary>
        /// Gets or sets the texture offset Y.
        /// </summary>
        public float OffsetY { get; set; }

        /// <summary>
        /// Gets or sets the texture scale X.
        /// </summary>
        public float ScaleX { get; set; }

        /// <summary>
        /// Gets or sets the texture scale Y.
        /// </summary>
        public float ScaleY { get; set; }
    }
}