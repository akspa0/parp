using System.Collections.Generic;
using WarcraftAnalyzer.Files.PM4.Base;

namespace WarcraftAnalyzer.Files.PM4
{
    /// <summary>
    /// MSVI Chunk - Contains vertex indices for PM4 geometry.
    /// Note: In files, this chunk may appear with a reversed signature as 'IVSM'.
    /// This follows WoW's chunk naming convention where chunks are often stored with reversed signatures
    /// but are documented and implemented using their forward notation.
    /// </summary>
    public class MSVI : IndexArrayChunk
    {
        /// <summary>
        /// Gets the forward notation signature for this chunk.
        /// </summary>
        public override string ForwardSignature { get; } = "MSVI";

        /// <summary>
        /// Gets the reversed notation signature as it may appear in files.
        /// </summary>
        protected override string ReverseSignature => "IVSM";

        /// <summary>
        /// Gets the list of indices.
        /// Each index references a vertex in the corresponding MSVT chunk.
        /// </summary>
        public IReadOnlyList<uint> VertexIndices => Indices;

        /// <summary>
        /// Initializes a new instance of the <see cref="MSVI"/> class.
        /// </summary>
        public MSVI() : base()
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="MSVI"/> class.
        /// </summary>
        /// <param name="indices">List of vertex indices</param>
        public MSVI(List<uint> indices) : base(indices)
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="MSVI"/> class.
        /// </summary>
        /// <param name="inData">ExtendedData.</param>
        public MSVI(byte[] inData) : base(inData)
        {
        }
    }
}