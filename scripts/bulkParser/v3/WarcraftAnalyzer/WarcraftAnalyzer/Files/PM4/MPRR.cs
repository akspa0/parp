using System.Collections.Generic;
using System.IO;
using WarcraftAnalyzer.Files.PM4.Base;

namespace WarcraftAnalyzer.Files.PM4
{
    /// <summary>
    /// MPRR Chunk - Contains pairs of uint16 values for PM4 geometry.
    /// Note: In files, this chunk may appear with a reversed signature as 'RRPM'.
    /// This follows WoW's chunk naming convention where chunks are often stored with reversed signatures
    /// but are documented and implemented using their forward notation.
    /// </summary>
    public class MPRR : FixedSizeEntryChunk<MPRR.ValuePair>
    {
        /// <summary>
        /// Structure containing a pair of uint16 values.
        /// </summary>
        public class ValuePair
        {
            /// <summary>
            /// Gets or sets the first value at offset 0x00.
            /// </summary>
            public ushort Value0x00 { get; set; }

            /// <summary>
            /// Gets or sets the second value at offset 0x02.
            /// </summary>
            public ushort Value0x02 { get; set; }
        }

        /// <summary>
        /// Gets the forward notation signature for this chunk.
        /// </summary>
        protected override string ForwardSignature => "MPRR";

        /// <summary>
        /// Gets the reversed notation signature as it may appear in files.
        /// </summary>
        protected override string ReverseSignature => "RRPM";

        /// <summary>
        /// Gets the size of each entry in bytes.
        /// 2 uint16s = 4 bytes total
        /// </summary>
        protected override int EntrySize => 4;

        /// <summary>
        /// Gets the value pairs.
        /// </summary>
        public IReadOnlyList<ValuePair> Pairs => Entries;

        /// <summary>
        /// Initializes a new instance of the <see cref="MPRR"/> class.
        /// </summary>
        public MPRR() : base()
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="MPRR"/> class.
        /// </summary>
        /// <param name="entries">List of value pairs</param>
        public MPRR(List<ValuePair> entries) : base(entries)
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="MPRR"/> class.
        /// </summary>
        /// <param name="inData">ExtendedData.</param>
        public MPRR(byte[] inData) : base(inData)
        {
        }

        /// <inheritdoc/>
        protected override ValuePair ReadEntry(BinaryReader br)
        {
            return new ValuePair
            {
                Value0x00 = br.ReadUInt16(),
                Value0x02 = br.ReadUInt16()
            };
        }

        /// <inheritdoc/>
        protected override void WriteEntry(BinaryWriter bw, ValuePair entry)
        {
            bw.Write(entry.Value0x00);
            bw.Write(entry.Value0x02);
        }
    }
}