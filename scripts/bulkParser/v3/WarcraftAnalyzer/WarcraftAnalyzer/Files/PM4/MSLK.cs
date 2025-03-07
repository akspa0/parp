using System.Collections.Generic;
using System.IO;
using WarcraftAnalyzer.Files.PM4.Base;

namespace WarcraftAnalyzer.Files.PM4
{
    /// <summary>
    /// MSLK Chunk - Contains link data between chunks for PM4 geometry.
    /// Note: In files, this chunk may appear with a reversed signature as 'KLSM'.
    /// This follows WoW's chunk naming convention where chunks are often stored with reversed signatures
    /// but are documented and implemented using their forward notation.
    /// </summary>
    public class MSLK : FixedSizeEntryChunk<MSLK.LinkData>
    {
        /// <summary>
        /// Structure containing link data between chunks.
        /// </summary>
        public class LinkData
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
            /// Gets or sets the value at offset 0x02.
            /// </summary>
            public ushort Value0x02 { get; set; }

            /// <summary>
            /// Gets or sets the value at offset 0x04.
            /// </summary>
            public uint Value0x04 { get; set; }

            /// <summary>
            /// Gets or sets the first index into the MSPI chunk.
            /// </summary>
            public uint MSPIFirstIndex { get; set; }

            /// <summary>
            /// Gets or sets the count of indices in the MSPI chunk.
            /// </summary>
            public byte MSPIIndexCount { get; set; }

            /// <summary>
            /// Gets or sets the value at offset 0x0c.
            /// </summary>
            public uint Value0x0c { get; set; }

            /// <summary>
            /// Gets or sets the value at offset 0x10.
            /// </summary>
            public ushort Value0x10 { get; set; }

            /// <summary>
            /// Gets or sets the value at offset 0x12.
            /// </summary>
            public ushort Value0x12 { get; set; }
        }

        /// <summary>
        /// Gets the forward notation signature for this chunk.
        /// </summary>
        protected override string ForwardSignature => "MSLK";

        /// <summary>
        /// Gets the reversed notation signature as it may appear in files.
        /// </summary>
        protected override string ReverseSignature => "KLSM";

        /// <summary>
        /// Gets the size of each entry in bytes.
        /// 2 bytes (flags) + 2 bytes (uint16) + 4 bytes (uint32) + 4 bytes (MSPI index) +
        /// 1 byte (MSPI count) + 4 bytes (uint32) + 4 bytes (2 uint16s) = 21 bytes total
        /// </summary>
        protected override int EntrySize => 21;

        /// <summary>
        /// Gets the link data entries.
        /// </summary>
        public IReadOnlyList<LinkData> Links => Entries;

        /// <summary>
        /// Initializes a new instance of the <see cref="MSLK"/> class.
        /// </summary>
        public MSLK() : base()
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="MSLK"/> class.
        /// </summary>
        /// <param name="entries">List of link data entries</param>
        public MSLK(List<LinkData> entries) : base(entries)
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="MSLK"/> class.
        /// </summary>
        /// <param name="inData">ExtendedData.</param>
        public MSLK(byte[] inData) : base(inData)
        {
        }

        /// <inheritdoc/>
        protected override LinkData ReadEntry(BinaryReader br)
        {
            try
            {
                Console.WriteLine("Starting to read MSLK entry");
                byte flag0x00 = br.ReadByte();
                Console.WriteLine($"Read Flag0x00: {flag0x00}");
                
                byte flag0x01 = br.ReadByte();
                Console.WriteLine($"Read Flag0x01: {flag0x01}");
                
                ushort value0x02 = br.ReadUInt16();
                Console.WriteLine($"Read Value0x02: {value0x02}");
                
                uint value0x04 = br.ReadUInt32();
                Console.WriteLine($"Read Value0x04: {value0x04}");
                
                uint mspiFirstIndex = br.ReadUInt32();
                Console.WriteLine($"Read MSPIFirstIndex: {mspiFirstIndex}");
                
                byte mspiIndexCount = br.ReadByte();
                Console.WriteLine($"Read MSPIIndexCount: {mspiIndexCount}");
                
                uint value0x0c = br.ReadUInt32();
                Console.WriteLine($"Read Value0x0c: {value0x0c}");
                
                ushort value0x10 = br.ReadUInt16();
                Console.WriteLine($"Read Value0x10: {value0x10}");
                
                ushort value0x12 = br.ReadUInt16();
                Console.WriteLine($"Read Value0x12: {value0x12}");

                Console.WriteLine("Successfully read MSLK entry");
                return new LinkData
                {
                    Flag0x00 = flag0x00,
                    Flag0x01 = flag0x01,
                    Value0x02 = value0x02,
                    Value0x04 = value0x04,
                    MSPIFirstIndex = mspiFirstIndex,
                    MSPIIndexCount = mspiIndexCount,
                    Value0x0c = value0x0c,
                    Value0x10 = value0x10,
                    Value0x12 = value0x12
                };
            }
            catch (EndOfStreamException ex)
            {
                Console.WriteLine($"EndOfStreamException occurred while reading MSLK entry: {ex.Message}");
                throw;
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Exception occurred while reading MSLK entry: {ex.Message}");
                throw;
            }
        }

        /// <inheritdoc/>
        protected override void WriteEntry(BinaryWriter bw, LinkData entry)
        {
            bw.Write(entry.Flag0x00);
            bw.Write(entry.Flag0x01);
            bw.Write(entry.Value0x02);
            bw.Write(entry.Value0x04);
            bw.Write(entry.MSPIFirstIndex);
            bw.Write(entry.MSPIIndexCount);
            bw.Write(entry.Value0x0c);
            bw.Write(entry.Value0x10);
            bw.Write(entry.Value0x12);
        }
    }
}