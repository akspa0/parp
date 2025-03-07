using System.Collections.Generic;
using Warcraft.NET.Files.Structures;
using WarcraftAnalyzer.Files.PM4.Base;

namespace WarcraftAnalyzer.Files.PM4
{
    /// <summary>
    /// MSVT Chunk - Contains vertex data for PM4 geometry.
    /// Note: In files, this chunk may appear with a reversed signature as 'TVSM'.
    /// This follows WoW's chunk naming convention where chunks are often stored with reversed signatures
    /// but are documented and implemented using their forward notation.
    /// </summary>
    public class MSVT : C3VectorArrayChunk
    {
        /// <summary>
        /// Gets the forward notation signature for this chunk.
        /// </summary>
        protected override string ForwardSignature => "MSVT";

        /// <summary>
        /// Gets the reversed notation signature as it may appear in files.
        /// </summary>
        protected override string ReverseSignature => "TVSM";

        /// <summary>
        /// Gets the list of vertices.
        /// Each vertex is stored as a C3Vector with int16 coordinates.
        /// These vertices are referenced by indices in the MSVI chunk.
        /// </summary>
        public IReadOnlyList<C3Vector> Vertices => VectorArray;

        /// <summary>
        /// Initializes a new instance of the <see cref="MSVT"/> class.
        /// </summary>
        public MSVT() : base()
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="MSVT"/> class.
        /// </summary>
        /// <param name="vertices">List of vertices</param>
        public MSVT(List<C3Vector> vertices) : base(vertices)
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="MSVT"/> class.
        /// </summary>
        /// <param name="inData">ExtendedData.</param>
        public MSVT(byte[] inData) : base(inData)
        {
        }
    }
}