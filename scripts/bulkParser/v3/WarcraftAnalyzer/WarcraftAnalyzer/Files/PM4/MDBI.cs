using System.Collections.Generic;
using WarcraftAnalyzer.Files.PM4.Base;

namespace WarcraftAnalyzer.Files.PM4
{
    /// <summary>
    /// MDBI Chunk - Contains building index data for PM4 geometry.
    /// Note: In files, this chunk may appear with a reversed signature as 'IBDM'.
    /// This follows WoW's chunk naming convention where chunks are often stored with reversed signatures
    /// but are documented and implemented using their forward notation.
    /// </summary>
    public class MDBI : IndexArrayChunk
    {
        /// <summary>
        /// Gets the forward notation signature for this chunk.
        /// </summary>
        public override string ForwardSignature { get; } = "MDBI";

        /// <summary>
        /// Gets the reversed notation signature as it may appear in files.
        /// </summary>
        protected override string ReverseSignature => "IBDM";

        /// <summary>
        /// Gets the list of building indices.
        /// Each index represents a destructible building reference.
        /// </summary>
        public IReadOnlyList<uint> BuildingIndices => Indices;

        /// <summary>
        /// Gets the destructible building index if this chunk contains exactly one index.
        /// </summary>
        public uint? DestructibleBuildingIndex => Indices.Count == 1 ? Indices[0] : null;

        /// <summary>
        /// Initializes a new instance of the <see cref="MDBI"/> class.
        /// </summary>
        public MDBI() : base()
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="MDBI"/> class.
        /// </summary>
        /// <param name="indices">List of building indices</param>
        public MDBI(List<uint> indices) : base(indices)
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="MDBI"/> class.
        /// </summary>
        /// <param name="inData">ExtendedData.</param>
        public MDBI(byte[] inData) : base(inData)
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="MDBI"/> class with a single building index.
        /// </summary>
        /// <param name="buildingIndex">The destructible building index.</param>
        public MDBI(uint buildingIndex) : base(new List<uint> { buildingIndex })
        {
        }
    }
}