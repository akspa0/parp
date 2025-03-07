using System.Collections.Generic;
using System.IO;
using System.Text;
using Warcraft.NET.Files.Interfaces;

namespace WarcraftAnalyzer.Files.PM4
{
    /// <summary>
    /// MDBF Chunk - Contains building filenames for PM4 geometry.
    /// Note: In files, this chunk may appear with a reversed signature as 'FBDM'.
    /// This follows WoW's chunk naming convention where chunks are often stored with reversed signatures
    /// but are documented and implemented using their forward notation.
    /// </summary>
    public class MDBF : IIFFChunk, IBinarySerializable
    {
        /// <summary>
        /// Gets the forward notation signature for this chunk.
        /// </summary>
        public const string ForwardSignature = "MDBF";

        /// <summary>
        /// Gets the reversed notation signature as it may appear in files.
        /// </summary>
        public const string ReverseSignature = "FBDM";

        /// <summary>
        /// Gets the list of filenames.
        /// </summary>
        public List<string> Filenames { get; } = new();

        /// <summary>
        /// Initializes a new instance of the <see cref="MDBF"/> class.
        /// </summary>
        public MDBF()
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="MDBF"/> class.
        /// </summary>
        /// <param name="filenames">List of filenames</param>
        public MDBF(List<string> filenames)
        {
            Filenames.AddRange(filenames);
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="MDBF"/> class.
        /// </summary>
        /// <param name="inData">ExtendedData.</param>
        public MDBF(byte[] inData)
        {
            LoadBinaryData(inData);
        }

        /// <inheritdoc/>
        public void LoadBinaryData(byte[] inData)
        {
            Filenames.Clear();

            using (var ms = new MemoryStream(inData))
            using (var br = new BinaryReader(ms))
            {
                while (br.BaseStream.Position < br.BaseStream.Length)
                {
                    var filename = ReadNullTerminatedString(br);
                    if (!string.IsNullOrEmpty(filename))
                    {
                        Filenames.Add(filename);
                    }
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
                foreach (var filename in Filenames)
                {
                    WriteNullTerminatedString(bw, filename);
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

        private static string ReadNullTerminatedString(BinaryReader br)
        {
            var bytes = new List<byte>();
            byte b;
            while ((b = br.ReadByte()) != 0)
            {
                bytes.Add(b);
            }
            return bytes.Count > 0 ? Encoding.UTF8.GetString(bytes.ToArray()) : string.Empty;
        }

        private static void WriteNullTerminatedString(BinaryWriter bw, string str)
        {
            if (!string.IsNullOrEmpty(str))
            {
                var bytes = Encoding.UTF8.GetBytes(str);
                bw.Write(bytes);
            }
            bw.Write((byte)0); // Null terminator
        }
    }
}