using System.Collections.Generic;
using System.IO;
using System.Text;
using Warcraft.NET.Files.Interfaces;

namespace WarcraftAnalyzer.Files.PM4
{
    /// <summary>
    /// MDBH Chunk - Contains hierarchical building data for PM4 geometry.
    /// Note: In files, this chunk may appear with a reversed signature as 'HBDM'.
    /// This follows WoW's chunk naming convention where chunks are often stored with reversed signatures
    /// but are documented and implemented using their forward notation.
    /// </summary>
    public class MDBH : IIFFChunk, IBinarySerializable
    {
        /// <summary>
        /// Structure containing building data with sub-chunks.
        /// </summary>
        public class BuildingData
        {
            /// <summary>
            /// Gets or sets the building indices from the MDBI sub-chunk.
            /// </summary>
            public List<uint> Indices { get; set; } = new();

            /// <summary>
            /// Gets or sets the filenames from the MDBF sub-chunk.
            /// </summary>
            public List<string> Filenames { get; set; } = new();
        }

        /// <summary>
        /// Gets the forward notation signature for this chunk.
        /// </summary>
        public const string ForwardSignature = "MDBH";

        /// <summary>
        /// Gets the reversed notation signature as it may appear in files.
        /// </summary>
        public const string ReverseSignature = "HBDM";

        /// <summary>
        /// Gets or sets the number of building entries.
        /// </summary>
        public uint Count { get; set; }

        /// <summary>
        /// Gets the list of building data entries.
        /// </summary>
        public List<BuildingData> Entries { get; } = new();

        /// <summary>
        /// Initializes a new instance of the <see cref="MDBH"/> class.
        /// </summary>
        public MDBH()
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="MDBH"/> class.
        /// </summary>
        /// <param name="entries">List of building data entries</param>
        public MDBH(List<BuildingData> entries)
        {
            Count = (uint)entries.Count;
            Entries.AddRange(entries);
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="MDBH"/> class.
        /// </summary>
        /// <param name="inData">ExtendedData.</param>
        public MDBH(byte[] inData)
        {
            LoadBinaryData(inData);
        }

        /// <inheritdoc/>
        public void LoadBinaryData(byte[] inData)
        {
            Entries.Clear();

            using (var ms = new MemoryStream(inData))
            using (var br = new BinaryReader(ms))
            {
                Count = br.ReadUInt32();

                for (var i = 0; i < Count; i++)
                {
                    var entry = new BuildingData();

                    while (br.BaseStream.Position < br.BaseStream.Length)
                    {
                        // Try to read sub-chunk header
                        if (br.BaseStream.Position + 8 > br.BaseStream.Length)
                            break;

                        var subChunkId = Encoding.UTF8.GetString(br.ReadBytes(4));
                        var subChunkSize = br.ReadUInt32();

                        if (br.BaseStream.Position + subChunkSize > br.BaseStream.Length)
                            break;

                        var subChunkData = br.ReadBytes((int)subChunkSize);

                        // Process sub-chunks
                        switch (subChunkId)
                        {
                            case "MDBI":
                            case "IBDM": // Handle reversed signature
                                var mdbi = new MDBI(subChunkData);
                                entry.Indices.AddRange(mdbi.BuildingIndices);
                                break;

                            case "MDBF":
                            case "FBDM": // Handle reversed signature
                                var mdbf = new MDBF(subChunkData);
                                entry.Filenames.AddRange(mdbf.Filenames);
                                break;
                        }
                    }

                    Entries.Add(entry);
                }
            }
        }

        /// <inheritdoc/>
        public string GetSignature()
        {
            return ForwardSignature;
        }

        /// <inheritdoc/>
        public uint GetSize()
        {
            return (uint)Serialize().Length;
        }

        /// <inheritdoc/>
        public byte[] Serialize(long offset = 0)
        {
            using (var ms = new MemoryStream())
            using (var bw = new BinaryWriter(ms))
            {
                bw.Write(Count);

                foreach (var entry in Entries)
                {
                    // Write MDBI sub-chunk if there are indices
                    if (entry.Indices.Count > 0)
                    {
                        var mdbi = new MDBI(entry.Indices);
                        var mdbiData = mdbi.Serialize();
                        bw.Write(Encoding.UTF8.GetBytes(mdbi.ForwardSignature));
                        bw.Write((uint)mdbiData.Length);
                        bw.Write(mdbiData);
                    }

                    // Write MDBF sub-chunk if there are filenames
                    if (entry.Filenames.Count > 0)
                    {
                        var mdbf = new MDBF(entry.Filenames);
                        var mdbfData = mdbf.Serialize();
                        bw.Write(Encoding.UTF8.GetBytes(MDBF.ForwardSignature));
                        bw.Write((uint)mdbfData.Length);
                        bw.Write(mdbfData);
                    }
                }

                return ms.ToArray();
            }
        }

        /// <summary>
        /// Checks if the given signature matches either the forward or reversed notation of this chunk.
        /// </summary>
        /// <param name="signature">The signature to check.</param>
        /// <returns>True if the signature matches either notation, false otherwise.</returns>
        public static bool IsValidSignature(string signature)
        {
            return signature == ForwardSignature || signature == ReverseSignature;
        }
    }
}