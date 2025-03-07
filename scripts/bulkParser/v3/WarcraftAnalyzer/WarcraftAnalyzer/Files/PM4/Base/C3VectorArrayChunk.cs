using System.Collections.Generic;
using System.IO;
using Warcraft.NET.Files.Interfaces;
using Warcraft.NET.Files.Structures;

namespace WarcraftAnalyzer.Files.PM4.Base
{
    /// <summary>
    /// Base class for chunks containing arrays of C3Vector data.
    /// </summary>
    public abstract class C3VectorArrayChunk : IIFFChunk, IBinarySerializable
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
        /// Gets the list of vectors.
        /// </summary>
        protected List<C3Vector> VectorArray { get; } = new();

        /// <summary>
        /// Initializes a new instance of the <see cref="C3VectorArrayChunk"/> class.
        /// </summary>
        protected C3VectorArrayChunk()
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="C3VectorArrayChunk"/> class.
        /// </summary>
        /// <param name="vectors">List of vectors</param>
        protected C3VectorArrayChunk(List<C3Vector> vectors)
        {
            VectorArray.AddRange(vectors);
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="C3VectorArrayChunk"/> class.
        /// </summary>
        /// <param name="inData">ExtendedData.</param>
        protected C3VectorArrayChunk(byte[] inData)
        {
            LoadBinaryData(inData);
        }

        /// <inheritdoc/>
        public void LoadBinaryData(byte[] inData)
        {
            VectorArray.Clear();

            using (var ms = new MemoryStream(inData))
            using (var br = new BinaryReader(ms))
            {
                while (br.BaseStream.Position < br.BaseStream.Length)
                {
                    var vector = new C3Vector
                    {
                        X = br.ReadSingle(),
                        Y = br.ReadSingle(),
                        Z = br.ReadSingle()
                    };
                    VectorArray.Add(vector);
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
            return (uint)(VectorArray.Count * 12); // Each C3Vector is 12 bytes (3 floats)
        }

        /// <inheritdoc/>
        public byte[] Serialize(long offset = 0)
        {
            using (var ms = new MemoryStream())
            using (var bw = new BinaryWriter(ms))
            {
                foreach (var vector in VectorArray)
                {
                    bw.Write(vector.X);
                    bw.Write(vector.Y);
                    bw.Write(vector.Z);
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