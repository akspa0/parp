using System.Collections.Generic;
using Warcraft.NET.Files.Structures;
using WarcraftAnalyzer.Files.PM4.Base;

namespace WarcraftAnalyzer.Files.PM4
{
    /// <summary>
    /// MSPV Chunk - Contains vertex positions for PM4 geometry.
    /// Note: In files, this chunk may appear with a reversed signature as 'VPSM'.
    /// This follows WoW's chunk naming convention where chunks are often stored with reversed signatures
    /// but are documented and implemented using their forward notation.
    /// </summary>
    public class MSPV : C3VectorArrayChunk
    {
        /// <summary>
        /// Gets the forward notation signature for this chunk.
        /// </summary>
        protected override string ForwardSignature => "MSPV";

        /// <summary>
        /// Gets the reversed notation signature as it may appear in files.
        /// </summary>
        protected override string ReverseSignature => "VPSM";

        /// <summary>
        /// Gets the list of vertex positions.
        /// </summary>
        public IReadOnlyList<C3Vector> Vertices => VectorArray;

        /// <summary>
        /// Initializes a new instance of the <see cref="MSPV"/> class.
        /// </summary>
        public MSPV() : base()
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="MSPV"/> class.
        /// </summary>
        /// <param name="vertices">List of vertex positions</param>
        public MSPV(List<C3Vector> vertices) : base(vertices)
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="MSPV"/> class.
        /// </summary>
        /// <param name="inData">ExtendedData.</param>
        public MSPV(byte[] inData) : base(inData)
        {
        }
    }
}
