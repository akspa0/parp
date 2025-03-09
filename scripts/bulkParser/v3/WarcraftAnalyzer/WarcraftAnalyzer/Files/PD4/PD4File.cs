using System;
using System.Collections.Generic;
using System.IO;
using Warcraft.NET.Files.ADT.Chunks;
using Warcraft.NET.Files.Interfaces;
using WarcraftAnalyzer.Files.PD4.Chunks;

namespace WarcraftAnalyzer.Files.PD4
{
    /// <summary>
    /// Represents a PD4 file, which is the WMO equivalent of PM4 files.
    /// These files are not shipped to the client and are used by the server only.
    /// </summary>
    public class PD4File
    {
        /// <summary>
        /// Gets or sets the version chunk.
        /// </summary>
        public MVER Version { get; set; }

        /// <summary>
        /// Gets or sets the CRC chunk.
        /// Always 0 in version_48.
        /// </summary>
        public MCRC CRC { get; set; }

        /// <summary>
        /// Gets or sets the shadow data chunk.
        /// </summary>
        public PM4.MSHD ShadowData { get; set; }

        /// <summary>
        /// Gets or sets the vertex positions chunk.
        /// Contains an array of C3Vector vertices.
        /// </summary>
        public PM4.MSPV VertexPositions { get; set; }

        /// <summary>
        /// Gets or sets the vertex indices chunk.
        /// Contains indices into MSPV chunk.
        /// </summary>
        public PM4.MSPI VertexIndices { get; set; }

        /// <summary>
        /// Gets or sets the normal coordinates chunk.
        /// Not related to MSPV and MSLK.
        /// </summary>
        public PM4.MSCN NormalCoordinates { get; set; }

        /// <summary>
        /// Gets or sets the links chunk.
        /// Contains links between chunks with multiple fields.
        /// </summary>
        public PM4.MSLK Links { get; set; }

        /// <summary>
        /// Gets or sets the vertex data chunk.
        /// Contains vertex data with YXZ ordering.
        /// </summary>
        public PM4.MSVT VertexData { get; set; }

        /// <summary>
        /// Gets or sets the vertex indices chunk.
        /// Contains indices into MSVT chunk.
        /// </summary>
        public PM4.MSVI VertexIndices2 { get; set; }

        /// <summary>
        /// Gets or sets the surface data chunk.
        /// Contains surface data with multiple fields.
        /// </summary>
        public PM4.MSUR SurfaceData { get; set; }

        /// <summary>
        /// Gets the list of errors encountered during parsing.
        /// </summary>
        public List<string> Errors { get; private set; } = new List<string>();

        /// <summary>
        /// Initializes a new instance of the <see cref="PD4File"/> class.
        /// </summary>
        public PD4File()
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="PD4File"/> class.
        /// </summary>
        /// <param name="inData">The binary data to load from.</param>
        public PD4File(byte[] inData)
        {
            if (inData == null)
                throw new ArgumentNullException(nameof(inData));

            try
            {
                using (var ms = new MemoryStream(inData))
                using (var br = new BinaryReader(ms))
                {
                    while (ms.Position < ms.Length)
                    {
                        try
                        {
                            // Read chunk signature (4 bytes)
                            string signature = new string(br.ReadChars(4));
                            
                            // Read chunk size (4 bytes)
                            uint size = br.ReadUInt32();
                            
                            // Read chunk data
                            byte[] data = br.ReadBytes((int)size);
                            
                            // Process the chunk
                            ProcessChunk(signature, data);
                        }
                        catch (EndOfStreamException)
                        {
                            // End of file reached
                            break;
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                Errors.Add($"Error parsing PD4 file: {ex.Message}");
            }
        }

        /// <summary>
        /// Processes a chunk of data.
        /// </summary>
        /// <param name="signature">The chunk signature.</param>
        /// <param name="data">The chunk data.</param>
        protected void ProcessChunk(string signature, byte[] data)
        {
            switch (signature)
            {
                case "MVER":
                case "REVM":
                    Version = new MVER(data);
                    break;

                case "MCRC":
                case "CRCM":
                    CRC = new MCRC(data);
                    break;

                case "MSHD":
                case "DHSM":
                    ShadowData = new PM4.MSHD(data);
                    break;

                case "MSPV":
                case "VPSM":
                    VertexPositions = new PM4.MSPV(data);
                    break;

                case "MSPI":
                case "IPSM":
                    VertexIndices = new PM4.MSPI(data);
                    break;

                case "MSCN":
                case "NCSM":
                    NormalCoordinates = new PM4.MSCN(data);
                    break;

                case "MSLK":
                case "KLSM":
                    Links = new PM4.MSLK(data);
                    break;

                case "MSVT":
                case "TVSM":
                    VertexData = new PM4.MSVT(data);
                    break;

                case "MSVI":
                case "IVSM":
                    VertexIndices2 = new PM4.MSVI(data);
                    break;

                case "MSUR":
                case "RUSM":
                    SurfaceData = new PM4.MSUR(data);
                    break;
            }
        }

        /// <summary>
        /// Gets the chunks in this PD4 file.
        /// </summary>
        /// <returns>An enumerable of IIFFChunk objects.</returns>
        public IEnumerable<IIFFChunk> GetChunks()
        {
            if (Version != null)
                yield return Version;

            if (CRC != null)
                yield return CRC;

            if (ShadowData != null)
                yield return ShadowData;

            if (VertexPositions != null)
                yield return VertexPositions;

            if (VertexIndices != null)
                yield return VertexIndices;

            if (NormalCoordinates != null)
                yield return NormalCoordinates;

            if (Links != null)
                yield return Links;

            if (VertexData != null)
                yield return VertexData;

            if (VertexIndices2 != null)
                yield return VertexIndices2;

            if (SurfaceData != null)
                yield return SurfaceData;
        }
    }
}