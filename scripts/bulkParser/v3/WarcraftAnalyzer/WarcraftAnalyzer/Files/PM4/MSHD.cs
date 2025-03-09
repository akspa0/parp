using System.Collections.Generic;
using System.IO; // Added missing using directive
using WarcraftAnalyzer.Files.PM4.Base;

namespace WarcraftAnalyzer.Files.PM4
{
    /// <summary>
    /// MSHD Chunk - Contains shadow data for PM4 geometry.
    /// Note: In files, this chunk may appear with a reversed signature as 'DHSM'.
    /// This follows WoW's chunk naming convention where chunks are often stored with reversed signatures
    /// but are documented and implemented using their forward notation.
    /// </summary>
    public class MSHD : FixedSizeEntryChunk<MSHD.ShadowData>
    {
        /// <summary>
        /// Structure containing shadow data.
        /// </summary>
        public class ShadowData
        {
            /// <summary>
            /// Gets or sets the value at offset 0x00.
            /// </summary>
            public uint Value0x00 { get; set; }

            /// <summary>
            /// Gets or sets the value at offset 0x04.
            /// </summary>
            public uint Value0x04 { get; set; }

            /// <summary>
            /// Gets or sets the value at offset 0x08.
            /// </summary>
            public uint Value0x08 { get; set; }

            /// <summary>
            /// Gets or sets the array of values at offset 0x0c.
            /// Always 0 in version_48, likely placeholders.
            /// </summary>
            public uint[] Values0x0c { get; set; } = new uint[5];
        }

        /// <summary>
        /// Gets the forward notation signature for this chunk.
        /// </summary>
        protected override string ForwardSignature => "MSHD";

        /// <summary>
        /// Gets the reversed notation signature as it may appear in files.
        /// </summary>
        protected override string ReverseSignature => "DHSM";

        /// <summary>
        /// Gets the size of each entry in bytes.
        /// 3 uint32s (12 bytes) + 5 uint32s (20 bytes) = 32 bytes total
        /// </summary>
        protected override int EntrySize => 32;

        /// <summary>
        /// Gets the shadow data entries.
        /// </summary>
        public IReadOnlyList<ShadowData> ShadowEntries => Entries;

        /// <summary>
        /// Initializes a new instance of the <see cref="MSHD"/> class.
        /// </summary>
        public MSHD() : base()
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="MSHD"/> class.
        /// </summary>
        /// <param name="entries">List of shadow data entries</param>
        public MSHD(List<ShadowData> entries) : base(entries)
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="MSHD"/> class.
        /// </summary>
        /// <param name="inData">ExtendedData.</param>
        public MSHD(byte[] inData) : base(inData)
        {
        }

        /// <inheritdoc/>
        protected override ShadowData ReadEntry(BinaryReader br)
        {
            var entry = new ShadowData
            {
                Value0x00 = br.ReadUInt32(),
                Value0x04 = br.ReadUInt32(),
                Value0x08 = br.ReadUInt32()
            };

            for (var i = 0; i < 5; i++)
            {
                entry.Values0x0c[i] = br.ReadUInt32();
            }

            return entry;
        }

        /// <inheritdoc/>
        protected override void WriteEntry(BinaryWriter bw, ShadowData entry)
        {
            bw.Write(entry.Value0x00);
            bw.Write(entry.Value0x04);
            bw.Write(entry.Value0x08);

            foreach (var value in entry.Values0x0c)
            {
                bw.Write(value);
            }
        }
    }
}