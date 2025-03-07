using System.Collections.Generic;
using WarcraftAnalyzer.Files.PM4.Base;

namespace WarcraftAnalyzer.Files.PM4
{
    /// <summary>
    /// MSPI Chunk - Contains indices referencing MSPV vertices.
    /// Note: In files, this chunk may appear with a reversed signature as 'IPSM'.
    /// This follows WoW's chunk naming convention where chunks are often stored with reversed signatures
    /// but are documented and implemented using their forward notation.
    /// </summary>
    public class MSPI : IndexArrayChunk
    {
        /// <summary>
        /// Gets the forward notation signature for this chunk.
        /// </summary>
        protected override string ForwardSignature => "MSPI";

        /// <summary>
        /// Gets the reversed notation signature as it may appear in files.
        /// </summary>
        protected override string ReverseSignature => "IPSM";

        /// <summary>
        /// Gets the list of vertex indices.
        /// Each index references a vertex in the MSPV chunk.
        /// </summary>
        public IReadOnlyList<uint> VertexIndices => Indices;

        /// <summary>
        /// Initializes a new instance of the <see cref="MSPI"/> class.
        /// </summary>
        public MSPI() : base()
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="MSPI"/> class.
        /// </summary>
        /// <param name="indices">List of vertex indices</param>
        public MSPI(List<uint> indices) : base(indices)
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="MSPI"/> class.
        /// </summary>
        /// <param name="inData">ExtendedData.</param>
        public MSPI(byte[] inData) : base(inData)
        {
        }
    }
}