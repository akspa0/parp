using System.Collections.Generic;
using System.IO;
using Warcraft.NET.Files.Structures;
using WarcraftAnalyzer.Files.PM4.Base;

namespace WarcraftAnalyzer.Files.PM4
{
    /// <summary>
    /// MPRL Chunk - Contains position data for PM4 geometry.
    /// Note: In files, this chunk may appear with a reversed signature as 'LRPM'.
    /// This follows WoW's chunk naming convention where chunks are often stored with reversed signatures
    /// but are documented and implemented using their forward notation.
    /// </summary>
    public class MPRL : FixedSizeEntryChunk<MPRL.PositionData>
    {
        /// <summary>
        /// Structure containing position data.
        /// </summary>
        public class PositionData
        {
            /// <summary>
            /// Gets or sets the first value at offset 0x00.
            /// </summary>
            public ushort Value0x00 { get; set; }

            /// <summary>
            /// Gets or sets the value at offset 0x02.
            /// </summary>
            public short Value0x02 { get; set; }

            /// <summary>
            /// Gets or sets the value at offset 0x04.
            /// </summary>
            public ushort Value0x04 { get; set; }

            /// <summary>
            /// Gets or sets the value at offset 0x06.
            /// </summary>
            public ushort Value0x06 { get; set; }

            /// <summary>
            /// Gets or sets the position vector.
            /// Note: The Y and Z coordinates are swapped in the file format.
            /// </summary>
            public C3Vector Position { get; set; } = new();

            /// <summary>
            /// Gets or sets the value at offset 0x14.
            /// </summary>
            public short Value0x14 { get; set; }

            /// <summary>
            /// Gets or sets the value at offset 0x16.
            /// </summary>
            public ushort Value0x16 { get; set; }
        }

        /// <summary>
        /// Gets the forward notation signature for this chunk.
        /// </summary>
        protected override string ForwardSignature => "MPRL";

        /// <summary>
        /// Gets the reversed notation signature as it may appear in files.
        /// </summary>
        protected override string ReverseSignature => "LRPM";

        /// <summary>
        /// Gets the size of each entry in bytes.
        /// 4 uint16s (8 bytes) + 3 floats (12 bytes) + 2 uint16s (4 bytes) = 24 bytes total
        /// </summary>
        protected override int EntrySize => 24;

        /// <summary>
        /// Gets the position data entries.
        /// </summary>
        public IReadOnlyList<PositionData> Positions => Entries;

        /// <summary>
        /// Initializes a new instance of the <see cref="MPRL"/> class.
        /// </summary>
        public MPRL() : base()
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="MPRL"/> class.
        /// </summary>
        /// <param name="entries">List of position data entries</param>
        public MPRL(List<PositionData> entries) : base(entries)
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="MPRL"/> class.
        /// </summary>
        /// <param name="inData">ExtendedData.</param>
        public MPRL(byte[] inData) : base(inData)
        {
        }

        /// <inheritdoc/>
        protected override PositionData ReadEntry(BinaryReader br)
        {
            var entry = new PositionData
            {
                Value0x00 = br.ReadUInt16(),
                Value0x02 = br.ReadInt16(),
                Value0x04 = br.ReadUInt16(),
                Value0x06 = br.ReadUInt16()
            };

            // Read position with Y and Z swapped
            var x = br.ReadSingle();
            var z = br.ReadSingle();
            var y = br.ReadSingle();
            entry.Position = new C3Vector(x, y, z);

            entry.Value0x14 = br.ReadInt16();
            entry.Value0x16 = br.ReadUInt16();

            return entry;
        }

        /// <inheritdoc/>
        protected override void WriteEntry(BinaryWriter bw, PositionData entry)
        {
            bw.Write(entry.Value0x00);
            bw.Write(entry.Value0x02);
            bw.Write(entry.Value0x04);
            bw.Write(entry.Value0x06);

            // Write position with Y and Z swapped
            bw.Write(entry.Position.X);
            bw.Write(entry.Position.Z);  // Z written before Y
            bw.Write(entry.Position.Y);

            bw.Write(entry.Value0x14);
            bw.Write(entry.Value0x16);
        }
    }
}