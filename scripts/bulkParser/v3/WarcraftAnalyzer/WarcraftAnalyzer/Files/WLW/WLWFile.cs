using System;
using System.Collections.Generic;
using System.IO;
using System.Numerics;

namespace WarcraftAnalyzer.Files.WLW
{
    /// <summary>
    /// Represents the type of liquid in a WLW file.
    /// </summary>
    public enum LiquidType : uint
    {
        /// <summary>
        /// Water liquid type.
        /// </summary>
        Water = 0,

        /// <summary>
        /// Ocean liquid type.
        /// </summary>
        Ocean = 1,

        /// <summary>
        /// Magma liquid type.
        /// </summary>
        Magma = 2,

        /// <summary>
        /// Slime liquid type.
        /// </summary>
        Slime = 3
    }

    /// <summary>
    /// Represents a liquid block in a WLW file.
    /// </summary>
    public class LiquidBlock
    {
        /// <summary>
        /// Gets or sets the vertices of the liquid block.
        /// </summary>
        public float[] Vertices { get; set; }

        /// <summary>
        /// Gets or sets the texture coordinates of the liquid block.
        /// </summary>
        public float[] Coordinates { get; set; }

        /// <summary>
        /// Gets or sets additional data for the liquid block.
        /// </summary>
        public byte[] Data { get; set; }
    }

    /// <summary>
    /// Represents a secondary liquid block in a WLW file.
    /// </summary>
    public class LiquidBlock2
    {
        /// <summary>
        /// Gets or sets the first unknown value.
        /// </summary>
        public uint Unk00 { get; set; }

        /// <summary>
        /// Gets or sets the second unknown value.
        /// </summary>
        public uint Unk0C { get; set; }

        /// <summary>
        /// Gets or sets the third unknown value.
        /// </summary>
        public uint Unk14 { get; set; }
    }

    /// <summary>
    /// Represents a WLW (Water Liquid Wave) file, or related water mesh formats (WLQ, WLM).
    /// </summary>
    public class WLWFile
    {
        /// <summary>
        /// Gets the file name.
        /// </summary>
        public string FileName { get; private set; }

        /// <summary>
        /// Gets the file extension.
        /// </summary>
        public string FileExtension { get; private set; }

        /// <summary>
        /// Gets the version of the WLW file.
        /// </summary>
        public uint Version { get; private set; }

        /// <summary>
        /// Gets the unknown value at offset 0x06.
        /// </summary>
        public ushort Unk06 { get; private set; }

        /// <summary>
        /// Gets the liquid type.
        /// </summary>
        public uint LiquidType { get; private set; }

        /// <summary>
        /// Gets the number of liquid blocks.
        /// </summary>
        public uint BlockCount { get; private set; }

        /// <summary>
        /// Gets the liquid blocks.
        /// </summary>
        public List<LiquidBlock> Blocks { get; private set; } = new List<LiquidBlock>();

        /// <summary>
        /// Gets the number of secondary liquid blocks.
        /// </summary>
        public uint Block2Count { get; private set; }

        /// <summary>
        /// Gets the secondary liquid blocks.
        /// </summary>
        public List<LiquidBlock2> Block2s { get; private set; } = new List<LiquidBlock2>();

        /// <summary>
        /// Gets the unknown value.
        /// </summary>
        public uint Unknown { get; private set; }

        /// <summary>
        /// Gets whether this is a magma liquid.
        /// </summary>
        public bool IsMagma { get; private set; }

        /// <summary>
        /// Gets whether this is a quality liquid.
        /// </summary>
        public bool IsQuality { get; private set; }

        /// <summary>
        /// Gets the list of vertices in the water mesh.
        /// </summary>
        public List<Vector3> Vertices { get; private set; } = new List<Vector3>();

        /// <summary>
        /// Gets the list of texture coordinates in the water mesh.
        /// </summary>
        public List<Vector2> TexCoords { get; private set; } = new List<Vector2>();

        /// <summary>
        /// Gets the list of normals in the water mesh.
        /// </summary>
        public List<Vector3> Normals { get; private set; } = new List<Vector3>();

        /// <summary>
        /// Gets the list of indices in the water mesh.
        /// </summary>
        public List<int> Indices { get; private set; } = new List<int>();

        /// <summary>
        /// Gets the list of errors encountered during parsing.
        /// </summary>
        public List<string> Errors { get; private set; } = new List<string>();

        /// <summary>
        /// Creates a new instance of the WLWFile class.
        /// </summary>
        /// <param name="fileData">The raw file data.</param>
        /// <param name="fileExtension">The file extension (e.g., ".wlw", ".wlq", ".wlm").</param>
        public WLWFile(byte[] fileData, string fileExtension)
        {
            if (fileData == null)
                throw new ArgumentNullException(nameof(fileData));

            if (string.IsNullOrEmpty(fileExtension))
                throw new ArgumentException("File extension cannot be null or empty.", nameof(fileExtension));

            FileExtension = fileExtension.ToLowerInvariant();
            FileName = "water_mesh" + FileExtension;

            try
            {
                // Parse the file based on its extension
                switch (FileExtension)
                {
                    case ".wlw":
                        ParseWLW(fileData);
                        break;
                    case ".wlq":
                        ParseWLQ(fileData);
                        break;
                    case ".wlm":
                        ParseWLM(fileData);
                        break;
                    default:
                        Errors.Add($"Unsupported file extension: {FileExtension}");
                        break;
                }
            }
            catch (Exception ex)
            {
                Errors.Add($"Error parsing water mesh file: {ex.Message}");
            }
        }

        /// <summary>
        /// Parses a WLW file.
        /// </summary>
        /// <param name="fileData">The raw file data.</param>
        private void ParseWLW(byte[] fileData)
        {
            using var ms = new MemoryStream(fileData);
            using var reader = new BinaryReader(ms);

            try
            {
                // Read header
                var signature = new string(reader.ReadChars(4));
                if (signature != "WLW0")
                {
                    Errors.Add($"Invalid WLW signature: {signature}");
                    return;
                }

                // Read version
                Version = reader.ReadUInt32();
                if (Version != 1)
                {
                    Errors.Add($"Unsupported WLW version: {Version}");
                    return;
                }

                // Read vertex count
                var vertexCount = reader.ReadUInt32();
                if (vertexCount > 65536) // Sanity check
                {
                    Errors.Add($"Vertex count too large: {vertexCount}");
                    return;
                }

                // Read vertices
                for (int i = 0; i < vertexCount; i++)
                {
                    float x = reader.ReadSingle();
                    float y = reader.ReadSingle();
                    float z = reader.ReadSingle();
                    Vertices.Add(new Vector3(x, y, z));

                    // Read texture coordinates
                    float u = reader.ReadSingle();
                    float v = reader.ReadSingle();
                    TexCoords.Add(new Vector2(u, v));
                }

                // Generate simple indices (triangle strip)
                for (int i = 0; i < vertexCount - 2; i++)
                {
                    Indices.Add(i);
                    Indices.Add(i + 1);
                    Indices.Add(i + 2);
                }

                // Generate simple normals (all pointing up)
                for (int i = 0; i < vertexCount; i++)
                {
                    Normals.Add(new Vector3(0, 1, 0));
                }
            }
            catch (Exception ex)
            {
                Errors.Add($"Error parsing WLW file: {ex.Message}");
            }
        }

        /// <summary>
        /// Parses a WLQ file.
        /// </summary>
        /// <param name="fileData">The raw file data.</param>
        private void ParseWLQ(byte[] fileData)
        {
            // WLQ is a simplified version of WLW
            // For now, we'll just use the same parsing logic
            ParseWLW(fileData);
        }

        /// <summary>
        /// Parses a WLM file.
        /// </summary>
        /// <param name="fileData">The raw file data.</param>
        private void ParseWLM(byte[] fileData)
        {
            // WLM is a more complex version of WLW
            // For now, we'll just use the same parsing logic
            ParseWLW(fileData);
        }
    }
}