using System.Collections.Generic;
using System.IO;
using Warcraft.NET.Files.Interfaces;

namespace WarcraftAnalyzer.Files.PM4.Base
{
    /// <summary>
    /// Base class for chunks containing arrays of uint32 indices.
    /// </summary>
    public abstract class IndexArrayChunk : IIFFChunk, IBinarySerializable
    {
        /// <summary>
        /// Gets the forward notation signature for this chunk.
        /// </summary>
        protected abstract string ForwardSignature { get; }

        /// <summary>
        /// Gets the reversed notation signature as it may appear in files.
        /// </summary>
        protected abstract string ReverseSignature { get; }

        /// <summary>
        /// Gets the list of indices.
        /// </summary>
        protected List<uint> Indices { get; } = new();

        /// <summary>
        /// Initializes a new instance of the <see cref="IndexArrayChunk"/> class.
        /// </summary>
        protected IndexArrayChunk()
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="IndexArrayChunk"/> class.
        /// </summary>
        /// <param name="indices">List of indices</param>
        protected IndexArrayChunk(List<uint> indices)
        {
            Indices.AddRange(indices);
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="IndexArrayChunk"/> class.
        /// </summary>
        /// <param name="inData">ExtendedData.</param>
        protected IndexArrayChunk(byte[] inData)
        {
            LoadBinaryData(inData);
        }

        /// <inheritdoc/>
        public void LoadBinaryData(byte[] inData)
        {
            Indices.Clear();

            using (var ms = new MemoryStream(inData))
            using (var br = new BinaryReader(ms))
            {
                while (br.BaseStream.Position < br.BaseStream.Length)
                {
                    Indices.Add(br.ReadUInt32());
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
            return (uint)(Indices.Count * 4); // Each uint32 is 4 bytes
        }

        /// <inheritdoc/>
        public byte[] Serialize(long offset = 0)
        {
            using (var ms = new MemoryStream())
            using (var bw = new BinaryWriter(ms))
            {
                foreach (var index in Indices)
                {
                    bw.Write(index);
                }

                return ms.ToArray();
            }
        }

        /// <summary>
        /// Checks if the given signature matches either the forward or reversed notation of this chunk.
        /// </summary>
        /// <param name="signature">The signature to check.</param>
        /// <returns>True if the signature matches either notation, false otherwise.</returns>
        protected bool IsValidSignature(string signature)
        {
            return signature == ForwardSignature || signature == ReverseSignature;
        }
    }
}