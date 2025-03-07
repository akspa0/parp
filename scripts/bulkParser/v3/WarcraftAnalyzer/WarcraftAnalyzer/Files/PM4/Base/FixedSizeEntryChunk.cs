using System.Collections.Generic;
using System.IO;
using Warcraft.NET.Files.Interfaces;

namespace WarcraftAnalyzer.Files.PM4.Base
{
    /// <summary>
    /// Base class for chunks containing arrays of fixed-size entries.
    /// </summary>
    /// <typeparam name="T">The type of entries in this chunk.</typeparam>
    public abstract class FixedSizeEntryChunk<T> : IIFFChunk, IBinarySerializable
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
        /// Gets the size of each entry in bytes.
        /// </summary>
        protected abstract int EntrySize { get; }

        /// <summary>
        /// Gets the list of entries.
        /// </summary>
        protected List<T> Entries { get; } = new();

        /// <summary>
        /// Initializes a new instance of the <see cref="FixedSizeEntryChunk{T}"/> class.
        /// </summary>
        protected FixedSizeEntryChunk()
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="FixedSizeEntryChunk{T}"/> class.
        /// </summary>
        /// <param name="entries">List of entries</param>
        protected FixedSizeEntryChunk(List<T> entries)
        {
            Entries.AddRange(entries);
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="FixedSizeEntryChunk{T}"/> class.
        /// </summary>
        /// <param name="inData">ExtendedData.</param>
        protected FixedSizeEntryChunk(byte[] inData)
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
                while (br.BaseStream.Position < br.BaseStream.Length)
                {
                    Entries.Add(ReadEntry(br));
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
            return (uint)(Entries.Count * EntrySize);
        }

        /// <inheritdoc/>
        public byte[] Serialize(long offset = 0)
        {
            using (var ms = new MemoryStream())
            using (var bw = new BinaryWriter(ms))
            {
                foreach (var entry in Entries)
                {
                    WriteEntry(bw, entry);
                }

                return ms.ToArray();
            }
        }

        /// <summary>
        /// Reads a single entry from the binary reader.
        /// </summary>
        /// <param name="br">The binary reader to read from.</param>
        /// <returns>The read entry.</returns>
        protected abstract T ReadEntry(BinaryReader br);

        /// <summary>
        /// Writes a single entry to the binary writer.
        /// </summary>
        /// <param name="bw">The binary writer to write to.</param>
        /// <param name="entry">The entry to write.</param>
        protected abstract void WriteEntry(BinaryWriter bw, T entry);

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