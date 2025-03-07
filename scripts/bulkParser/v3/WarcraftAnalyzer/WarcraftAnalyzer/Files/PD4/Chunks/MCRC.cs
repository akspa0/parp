using System.IO;
using Warcraft.NET.Files.Interfaces;

namespace WarcraftAnalyzer.Files.PD4.Chunks
{
    /// <summary>
    /// MCRC Chunk - Contains CRC data for PD4 files.
    /// Note: In files, this chunk may appear with a reversed signature as 'CRCM'.
    /// This follows WoW's chunk naming convention where chunks are often stored with reversed signatures
    /// but are documented and implemented using their forward notation.
    /// </summary>
    public class MCRC : IIFFChunk, IBinarySerializable
    {
        /// <summary>
        /// Gets the forward notation signature for this chunk.
        /// </summary>
        public const string ForwardSignature = "MCRC";

        /// <summary>
        /// Gets the reversed notation signature as it may appear in files.
        /// </summary>
        public const string ReverseSignature = "CRCM";

        /// <summary>
        /// Gets or sets the value at offset 0x00.
        /// Always 0 in version_48.
        /// </summary>
        public uint Value { get; set; }

        /// <summary>
        /// Initializes a new instance of the <see cref="MCRC"/> class.
        /// </summary>
        public MCRC()
        {
            Value = 0; // Always 0 in version_48
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="MCRC"/> class.
        /// </summary>
        /// <param name="value">The value to store</param>
        public MCRC(uint value)
        {
            Value = value;
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="MCRC"/> class.
        /// </summary>
        /// <param name="inData">ExtendedData.</param>
        public MCRC(byte[] inData)
        {
            LoadBinaryData(inData);
        }

        /// <inheritdoc/>
        public void LoadBinaryData(byte[] inData)
        {
            using (var ms = new MemoryStream(inData))
            using (var br = new BinaryReader(ms))
            {
                Value = br.ReadUInt32();
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
            return 4; // uint32 = 4 bytes
        }

        /// <inheritdoc/>
        public byte[] Serialize(long offset = 0)
        {
            using (var ms = new MemoryStream())
            using (var bw = new BinaryWriter(ms))
            {
                bw.Write(Value);
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