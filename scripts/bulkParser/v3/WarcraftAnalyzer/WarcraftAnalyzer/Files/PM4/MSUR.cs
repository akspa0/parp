using System.Collections.Generic;
using System.IO;
using WarcraftAnalyzer.Files.PM4.Base;

namespace WarcraftAnalyzer.Files.PM4
{
    /// <summary>
    /// MSUR Chunk - Contains surface data for PM4 geometry.
    /// Note: In files, this chunk may appear with a reversed signature as 'RUSM'.
    /// This follows WoW's chunk naming convention where chunks are often stored with reversed signatures
    /// but are documented and implemented using their forward notation.
    /// </summary>
    public class MSUR : FixedSizeEntryChunk<MSUR.SurfaceData>
    {
        /// <summary>
        /// Structure containing surface data.
        /// </summary>
        public class SurfaceData
        {
            /// <summary>
            /// Gets or sets the first flag at offset 0x00.
            /// </summary>
            public byte Flag0x00 { get; set; }

            /// <summary>
            /// Gets or sets the second flag at offset 0x01.
            /// </summary>
            public byte Flag0x01 { get; set; }

            /// <summary>
            /// Gets or sets the third flag at offset 0x02.
            /// </summary>
            public byte Flag0x02 { get; set; }

            /// <summary>
            /// Gets or sets the fourth flag at offset 0x03.
            /// </summary>
            public byte Flag0x03 { get; set; }

            /// <summary>
            /// Gets or sets the first float value at offset 0x04.
            /// </summary>
            public float Value0x04 { get; set; }

            /// <summary>
            /// Gets or sets the second float value at offset 0x08.
            /// </summary>
            public float Value0x08 { get; set; }

            /// <summary>
            /// Gets or sets the third float value at offset 0x0c.
            /// </summary>
            public float Value0x0c { get; set; }

            /// <summary>
            /// Gets or sets the fourth float value at offset 0x10.
            /// </summary>
            public float Value0x10 { get; set; }

            /// <summary>
            /// Gets or sets the first index into MSVI chunk at offset 0x14.
            /// </summary>
            public uint MSVIFirstIndex { get; set; }

            /// <summary>
            /// Gets or sets the value at offset 0x18.
            /// </summary>
            public uint Value0x18 { get; set; }

            /// <summary>
            /// Gets or sets the value at offset 0x1c.
            /// </summary>
            public uint Value0x1c { get; set; }
        }

        /// <summary>
        /// Gets the forward notation signature for this chunk.
        /// </summary>
        protected override string ForwardSignature => "MSUR";

        /// <summary>
        /// Gets the reversed notation signature as it may appear in files.
        /// </summary>
        protected override string ReverseSignature => "RUSM";

        /// <summary>
        /// Gets the size of each entry in bytes.
        /// 4 bytes (flags) + 4 floats (16 bytes) + 3 uint32s (12 bytes) = 32 bytes total
        /// </summary>
        protected override int EntrySize => 32;

        /// <summary>
        /// Gets the surface data entries.
        /// </summary>
        public IReadOnlyList<SurfaceData> SurfaceEntries => Entries;

        /// <summary>
        /// Initializes a new instance of the <see cref="MSUR"/> class.
        /// </summary>
        public MSUR() : base()
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="MSUR"/> class.
        /// </summary>
        /// <param name="entries">List of surface data entries</param>
        public MSUR(List<SurfaceData> entries) : base(entries)
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="MSUR"/> class.
        /// </summary>
        /// <param name="inData">ExtendedData.</param>
        public MSUR(byte[] inData) : base(inData)
        {
        }

        /// <inheritdoc/>
        protected override SurfaceData ReadEntry(BinaryReader br)
        {
            return new SurfaceData
            {
                Flag0x00 = br.ReadByte(),
                Flag0x01 = br.ReadByte(),
                Flag0x02 = br.ReadByte(),
                Flag0x03 = br.ReadByte(),
                Value0x04 = br.ReadSingle(),
                Value0x08 = br.ReadSingle(),
                Value0x0c = br.ReadSingle(),
                Value0x10 = br.ReadSingle(),
                MSVIFirstIndex = br.ReadUInt32(),
                Value0x18 = br.ReadUInt32(),
                Value0x1c = br.ReadUInt32()
            };
        }

        /// <inheritdoc/>
        protected override void WriteEntry(BinaryWriter bw, SurfaceData entry)
        {
            bw.Write(entry.Flag0x00);
            bw.Write(entry.Flag0x01);
            bw.Write(entry.Flag0x02);
            bw.Write(entry.Flag0x03);
            bw.Write(entry.Value0x04);
            bw.Write(entry.Value0x08);
            bw.Write(entry.Value0x0c);
            bw.Write(entry.Value0x10);
            bw.Write(entry.MSVIFirstIndex);
            bw.Write(entry.Value0x18);
            bw.Write(entry.Value0x1c);
        }
    }
}