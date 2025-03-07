using System.Collections.Generic;
using Warcraft.NET.Files.Structures;
using WarcraftAnalyzer.Files.PM4.Base;

namespace WarcraftAnalyzer.Files.PM4
{
    /// <summary>
    /// MSCN Chunk - Contains normal coordinates for PM4 geometry.
    /// Note: In files, this chunk may appear with a reversed signature as 'NCSM'.
    /// This follows WoW's chunk naming convention where chunks are often stored with reversed signatures
    /// but are documented and implemented using their forward notation.
    /// </summary>
    public class MSCN : C3VectorArrayChunk
    {
        /// <summary>
        /// Gets the forward notation signature for this chunk.
        /// </summary>
        protected override string ForwardSignature => "MSCN";

        /// <summary>
        /// Gets the reversed notation signature as it may appear in files.
        /// </summary>
        protected override string ReverseSignature => "NCSM";

        /// <summary>
        /// Gets the list of normal coordinates.
        /// </summary>
        public IReadOnlyList<C3Vector> Normals => VectorArray;

        /// <summary>
        /// Initializes a new instance of the <see cref="MSCN"/> class.
        /// </summary>
        public MSCN() : base()
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="MSCN"/> class.
        /// </summary>
        /// <param name="normals">List of normal coordinates</param>
        public MSCN(List<C3Vector> normals) : base(normals)
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="MSCN"/> class.
        /// </summary>
        /// <param name="inData">ExtendedData.</param>
        public MSCN(byte[] inData) : base(inData)
        {
        }
    }
}