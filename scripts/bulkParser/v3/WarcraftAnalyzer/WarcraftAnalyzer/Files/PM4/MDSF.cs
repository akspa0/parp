using System.Collections.Generic;
using WarcraftAnalyzer.Files.PM4.Base;

namespace WarcraftAnalyzer.Files.PM4
{
    /// <summary>
    /// MDSF Chunk - Contains an array of uint32 values for PM4 geometry.
    /// Note: In files, this chunk may appear with a reversed signature as 'FSDM'.
    /// This follows WoW's chunk naming convention where chunks are often stored with reversed signatures
    /// but are documented and implemented using their forward notation.
    /// </summary>
    public class MDSF : IndexArrayChunk
    {
        /// <summary>
        /// Gets the forward notation signature for this chunk.
        /// </summary>
        public override string ForwardSignature { get; } = "MDSF";

        /// <summary>
        /// Gets the reversed notation signature as it may appear in files.
        /// </summary>
        protected override string ReverseSignature => "FSDM";

        /// <summary>
        /// Gets the list of values.
        /// </summary>
        public IReadOnlyList<uint> Values => Indices;

        /// <summary>
        /// Initializes a new instance of the <see cref="MDSF"/> class.
        /// </summary>
        public MDSF() : base()
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="MDSF"/> class.
        /// </summary>
        /// <param name="values">List of values</param>
        public MDSF(List<uint> values) : base(values)
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="MDSF"/> class.
        /// </summary>
        /// <param name="inData">ExtendedData.</param>
        public MDSF(byte[] inData) : base(inData)
        {
        }
    }
}