using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Numerics;

namespace WarcraftAnalyzer.Files.WLW
{
    /// <summary>
    /// Represents a WLW (Water Level Water) file, which contains liquid data for the game world.
    /// Also handles WLM (magma) and WLQ (quality) variants.
    /// </summary>
    /// <remarks>
    /// Based on specifications from:
    /// - https://wowdev.wiki/WLW
    /// - https://wowdev.wiki/WLM
    /// - https://wowdev.wiki/WLQ
    /// </remarks>
    public class WLWFile
    {
        /// <summary>
        /// The magic number that identifies WLW/WLM/WLQ files ("LIQ*").
        /// </summary>
        private const string MAGIC_LIQ = "LIQ*"; // Standard format according to spec
        private const string MAGIC_QIL = "*QIL"; // Alternative format found in some files

        /// <summary>
        /// Gets or sets the file version (0, 1, or 2).
        /// </summary>
        public ushort Version { get; set; }

        /// <summary>
        /// Gets or sets an unknown value at offset 0x06 (always 1, probably part of version).
        /// </summary>
        public ushort Unk06 { get; set; }

        /// <summary>
        /// Gets or sets the liquid type.
        /// For version ≤ 1: Uses LiquidType enum
        /// For version 2: Uses DB/LiquidType ID
        /// </summary>
        public uint LiquidType { get; set; }

        /// <summary>
        /// Gets or sets the number of blocks.
        /// </summary>
        public uint BlockCount { get; set; }

        /// <summary>
        /// Gets or sets the blocks of liquid data.
        /// </summary>
        public List<LiquidBlock> Blocks { get; set; }

        /// <summary>
        /// Gets or sets the number of block2s (only seen in 'world/maps/azeroth/test.wlm').
        /// </summary>
        public uint Block2Count { get; set; }

        /// <summary>
        /// Gets or sets the block2 data (only seen in 'world/maps/azeroth/test.wlm').
        /// </summary>
        public List<LiquidBlock2> Block2s { get; set; }

        /// <summary>
        /// Gets or sets the unknown value (mostly 1, only present if version ≥ 1).
        /// </summary>
        public byte? Unknown { get; set; }

        /// <summary>
        /// Gets whether this is a WLM (magma) file.
        /// </summary>
        public bool IsMagma { get; private set; }

        /// <summary>
        /// Gets whether this is a WLQ (quality) file.
        /// </summary>
        public bool IsQuality { get; private set; }

        /// <summary>
        /// Initializes a new instance of the <see cref="WLWFile"/> class.
        /// </summary>
        public WLWFile()
        {
            Blocks = new List<LiquidBlock>();
            Block2s = new List<LiquidBlock2>();
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="WLWFile"/> class.
        /// </summary>
        /// <param name="data">The binary data to load from.</param>
        /// <param name="extension">The file extension to determine type (.wlw, .wlm, or .wlq).</param>
        public WLWFile(byte[] data, string extension = ".wlw") : this()
        {
            // Determine file type from extension
            extension = extension.ToLowerInvariant();
            IsMagma = extension == ".wlm";
            IsQuality = extension == ".wlq";

            using (var reader = new BinaryReader(new MemoryStream(data)))
            {
                // Read magic number (can be stored as "LIQ*" or "*QIL" in the file)
                var magic = new string(new[] {
                    (char)reader.ReadByte(),
                    (char)reader.ReadByte(),
                    (char)reader.ReadByte(),
                    (char)reader.ReadByte()
                });

                if (magic != MAGIC_LIQ && magic != MAGIC_QIL)
                {
                    throw new InvalidDataException($"Invalid WLW file magic: {magic}. Expected: {MAGIC_LIQ} or {MAGIC_QIL}");
                }

                // Read header
                Version = reader.ReadUInt16();
                Unk06 = reader.ReadUInt16();
                
                // Read liquid type - in the spec this is either a uint16_t or a uint32_t
                // We'll read it as a uint32_t to be safe
                LiquidType = reader.ReadUInt32();

                // Force liquid type to magma for WLM files as per spec
                if (IsMagma)
                {
                    LiquidType = 6; // Magma type
                }

                BlockCount = reader.ReadUInt32();

                // Read blocks
                for (int i = 0; i < BlockCount; i++)
                {
                    var block = new LiquidBlock();

                    // Read 16 vertices (4x4 grid)
                    for (int j = 0; j < 16; j++)
                    {
                        block.Vertices[j] = new Vector3(
                            reader.ReadSingle(), // X
                            reader.ReadSingle(), // Y
                            reader.ReadSingle()  // Z
                        );
                    }

                    // Read coordinates
                    block.Coordinates = new Vector2(
                        reader.ReadSingle(), // X
                        reader.ReadSingle()  // Y
                    );

                    // Skip blocks with invalid coordinates in WLQ files
                    if (IsQuality && (block.Coordinates.X > 32767 || block.Coordinates.Y > 32767))
                    {
                        // Skip remaining block data
                        reader.BaseStream.Position += 80 * 2; // 80 ushorts
                        continue;
                    }

                    // Read 80 height values (0x50 uint16_t values as per spec)
                    for (int j = 0; j < 80; j++)
                    {
                        block.Data[j] = reader.ReadUInt16();
                    }

                    Blocks.Add(block);
                }

                // Read block2 count if there's more data
                if (reader.BaseStream.Position < reader.BaseStream.Length)
                {
                    Block2Count = reader.ReadUInt32();

                    // Read block2s
                    for (int i = 0; i < Block2Count; i++)
                    {
                        var block2 = new LiquidBlock2
                        {
                            // Read C3Vector _unk00 as per spec
                            Unk00 = new Vector3(
                                reader.ReadSingle(),
                                reader.ReadSingle(),
                                reader.ReadSingle()
                            ),
                            // Read C2Vector _unk0C as per spec
                            Unk0C = new Vector2(
                                reader.ReadSingle(),
                                reader.ReadSingle()
                            ),
                            // Read char _unk14[0x38] as per spec (4 floats then 0 filled)
                            Unk14 = reader.ReadBytes(0x38)
                        };

                        Block2s.Add(block2);
                    }

                    // Read final unknown byte if version >= 1 as per spec
                    if (Version >= 1 && reader.BaseStream.Position < reader.BaseStream.Length)
                    {
                        Unknown = reader.ReadByte();
                    }
                }
            }
        }

        /// <summary>
        /// Gets the appropriate texture and color for the current liquid type.
        /// </summary>
        /// <returns>A tuple containing the texture filename and color.</returns>
        public (string texture, Vector4 color) GetLiquidTypeInfo()
        {
            // Convert to ushort for dictionary lookup since our enum is based on ushort
            ushort liquidTypeKey = (ushort)(LiquidType & 0xFFFF);
            
            return MeshExporter.LiquidTypeInfo.ContainsKey(liquidTypeKey)
                ? MeshExporter.LiquidTypeInfo[liquidTypeKey]
                : MeshExporter.LiquidTypeInfo[2]; // Default to Unknown type
        }
    }

    /// <summary>
    /// Represents a block of liquid data.
    /// </summary>
    public class LiquidBlock
    {
        /// <summary>
        /// Gets or sets the vertices of the liquid block (16 vertices forming a 4x4 grid).
        /// The grid starts in the lower right corner:
        /// 15 14 13 12
        /// 11 10  9  8
        ///  7  6  5  4
        ///  3  2  1  0
        /// </summary>
        public Vector3[] Vertices { get; set; }

        /// <summary>
        /// Gets or sets the coordinates of the block.
        /// </summary>
        public Vector2 Coordinates { get; set; }

        /// <summary>
        /// Gets or sets the block data (80 height values).
        /// </summary>
        public ushort[] Data { get; set; }

        /// <summary>
        /// Initializes a new instance of the <see cref="LiquidBlock"/> class.
        /// </summary>
        public LiquidBlock()
        {
            Vertices = new Vector3[16];
            Data = new ushort[80];
        }
    }

    /// <summary>
    /// Represents a block2 structure (only seen in 'world/maps/azeroth/test.wlm').
    /// </summary>
    public class LiquidBlock2
    {
        /// <summary>
        /// Gets or sets the unknown Vector3 at offset 0x00.
        /// </summary>
        public Vector3 Unk00 { get; set; }

        /// <summary>
        /// Gets or sets the unknown Vector2 at offset 0x0C.
        /// </summary>
        public Vector2 Unk0C { get; set; }

        /// <summary>
        /// Gets or sets the unknown data at offset 0x14 (4 floats then 0 filled).
        /// </summary>
        public byte[] Unk14 { get; set; } = new byte[0x38];
    }

    /// <summary>
    /// Liquid types used in WLW files version ≤ 1.
    /// </summary>
    public enum LiquidType : ushort
    {
        /// <summary>
        /// Still water.
        /// </summary>
        Still = 0,

        /// <summary>
        /// Ocean water.
        /// </summary>
        Ocean = 1,

        /// <summary>
        /// Unknown type (used by 'Shadowmoon Pools 02.wlm').
        /// </summary>
        Unknown = 2,

        /// <summary>
        /// Slow/river water.
        /// </summary>
        River = 4,

        /// <summary>
        /// Magma/lava.
        /// </summary>
        Magma = 6,

        /// <summary>
        /// Fast flowing water.
        /// </summary>
        FastFlowing = 8
    }
}