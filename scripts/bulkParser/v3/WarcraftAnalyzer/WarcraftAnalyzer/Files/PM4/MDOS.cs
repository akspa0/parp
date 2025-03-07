using System.IO;
using Warcraft.NET.Files.Interfaces;

namespace WarcraftAnalyzer.Files.PM4
{
    /// <summary>
    /// MDOS Chunk - Contains a single uint32 value for PM4 geometry.
    /// Note: In files, this chunk may appear with a reversed signature as 'SODM'.
    /// This follows WoW's chunk naming convention where chunks are often stored with reversed signatures
    /// but are documented and implemented using their forward notation.
    /// </summary>
    public class MDOS : IIFFChunk, IBinarySerializable
    {
        /// <summary>
        /// Gets the forward notation signature for this chunk.
        /// </summary>
        public const string ForwardSignature = "MDOS";

        /// <summary>
        /// Gets the reversed notation signature as it may appear in files.
        /// </summary>
        public const string ReverseSignature = "SODM";

        /// <summary>
        /// Gets or sets the value stored in this chunk.
        /// </summary>
        public uint Value { get; set; }

        /// <summary>
        /// Initializes a new instance of the <see cref="MDOS"/> class.
        /// </summary>
        public MDOS()
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="MDOS"/> class.
        /// </summary>
        /// <param name="value">The value to store</param>
        public MDOS(uint value)
        {
            Value = value;
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="MDOS"/> class.
        /// </summary>
        /// <param name="inData">ExtendedData.</param>
        public MDOS(byte[] inData)
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