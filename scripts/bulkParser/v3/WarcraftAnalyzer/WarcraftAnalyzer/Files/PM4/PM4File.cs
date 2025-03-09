using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using Warcraft.NET.Files;
using Warcraft.NET.Files.Interfaces;
using MVER = Warcraft.NET.Files.ADT.Chunks.MVER;

namespace WarcraftAnalyzer.Files.PM4
{
    /// <summary>
    /// Represents a PM4 file, which is a server-side supplementary file to ADTs.
    /// These files are not shipped to the client and are used by the server only.
    /// </summary>
    public class PM4File
    {
        /// <summary>
        /// Gets the underlying ChunkedFile instance.
        /// </summary>
        private object _chunkedFile;

        /// <summary>
        /// Gets or sets the version chunk.
        /// </summary>
        public MVER Version { get; set; }

        /// <summary>
        /// Gets or sets the shadow data chunk.
        /// </summary>
        public MSHD ShadowData { get; set; }

        /// <summary>
        /// Gets or sets the vertex positions chunk.
        /// </summary>
        public MSPV VertexPositions { get; set; }

        /// <summary>
        /// Gets or sets the vertex indices chunk.
        /// </summary>
        public MSPI VertexIndices { get; set; }

        /// <summary>
        /// Gets or sets the normal coordinates chunk.
        /// </summary>
        public MSCN NormalCoordinates { get; set; }

        /// <summary>
        /// Gets or sets the links chunk.
        /// </summary>
        public MSLK Links { get; set; }

        /// <summary>
        /// Gets or sets the vertex data chunk.
        /// </summary>
        public MSVT VertexData { get; set; }

        /// <summary>
        /// Gets or sets the vertex indices chunk.
        /// </summary>
        public MSVI VertexIndices2 { get; set; }

        /// <summary>
        /// Gets or sets the surface data chunk.
        /// </summary>
        public MSUR SurfaceData { get; set; }

        /// <summary>
        /// Gets or sets the position data chunk.
        /// </summary>
        public MPRL PositionData { get; set; }

        /// <summary>
        /// Gets or sets the value pairs chunk.
        /// </summary>
        public MPRR ValuePairs { get; set; }

        /// <summary>
        /// Gets or sets the building data chunk.
        /// </summary>
        public MDBH BuildingData { get; set; }

        /// <summary>
        /// Gets or sets the simple data chunk.
        /// </summary>
        public MDOS SimpleData { get; set; }

        /// <summary>
        /// Gets or sets the final data chunk.
        /// </summary>
        public MDSF FinalData { get; set; }

        /// <summary>
        /// Gets the list of errors encountered during parsing.
        /// </summary>
        public List<string> Errors { get; private set; } = new List<string>();

        /// <summary>
        /// Gets the file name.
        /// </summary>
        public string FileName { get; private set; }

        /// <summary>
        /// Initializes a new instance of the <see cref="PM4File"/> class.
        /// </summary>
        public PM4File()
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="PM4File"/> class.
        /// </summary>
        /// <param name="inData">The binary data to load from.</param>
        /// <param name="fileName">Optional file name for reference.</param>
        public PM4File(byte[] inData, string fileName = null)
        {
            if (inData == null)
                throw new ArgumentNullException(nameof(inData));

            FileName = fileName;

            try
            {
                // Create a ChunkedFile instance directly
                Type chunkedFileType = typeof(ChunkedFile);
                _chunkedFile = Activator.CreateInstance(chunkedFileType);
                
                // Load the binary data using the LoadBinaryData method
                MethodInfo loadBinaryDataMethod = chunkedFileType.GetMethod("LoadBinaryData");
                if (loadBinaryDataMethod == null)
                {
                    throw new InvalidOperationException("Could not find LoadBinaryData method on ChunkedFile");
                }
                
                loadBinaryDataMethod.Invoke(_chunkedFile, new object[] { inData });
                
                // Extract chunks from the ChunkedFile instance
                ExtractChunksFromChunkedFile();
            }
            catch (Exception ex)
            {
                Errors.Add($"Error parsing PM4 file: {ex.Message}");
                if (ex.InnerException != null)
                {
                    Errors.Add($"Inner exception: {ex.InnerException.Message}");
                }
                
                // Fallback to manual chunk processing if reflection approach fails
                ProcessManually(inData);
            }
        }

        /// <summary>
        /// Extracts chunks from the ChunkedFile instance using reflection.
        /// </summary>
        private void ExtractChunksFromChunkedFile()
        {
            if (_chunkedFile == null)
                return;

            try
            {
                // Get the Chunks property from the ChunkedFile instance
                PropertyInfo chunksProperty = _chunkedFile.GetType().GetProperty("Chunks");
                if (chunksProperty == null)
                {
                    Errors.Add("Could not find Chunks property on ChunkedFile");
                    return;
                }

                // Get the chunks dictionary
                var chunks = chunksProperty.GetValue(_chunkedFile) as System.Collections.IDictionary;
                if (chunks == null)
                {
                    Errors.Add("Chunks property is not a dictionary");
                    return;
                }

                // Extract chunks by signature
                foreach (var key in chunks.Keys)
                {
                    string signature = key.ToString();
                    var chunk = chunks[key] as IIFFChunk;
                    
                    if (chunk != null)
                    {
                        AssignChunkBySignature(signature, chunk);
                    }
                }
            }
            catch (Exception ex)
            {
                Errors.Add($"Error extracting chunks: {ex.Message}");
                if (ex.InnerException != null)
                {
                    Errors.Add($"Inner exception: {ex.InnerException.Message}");
                }
            }
        }

        /// <summary>
        /// Assigns a chunk to the appropriate property based on its signature.
        /// </summary>
        /// <param name="signature">The chunk signature.</param>
        /// <param name="chunk">The chunk to assign.</param>
        private void AssignChunkBySignature(string signature, IIFFChunk chunk)
        {
            switch (signature)
            {
                case "MVER":
                case "REVM":
                    Version = chunk as MVER;
                    break;

                case "MSHD":
                case "DHSM":
                    ShadowData = chunk as MSHD;
                    break;

                case "MSPV":
                case "VPSM":
                    VertexPositions = chunk as MSPV;
                    break;

                case "MSPI":
                case "IPSM":
                    VertexIndices = chunk as MSPI;
                    break;

                case "MSCN":
                case "NCSM":
                    NormalCoordinates = chunk as MSCN;
                    break;

                case "MSLK":
                case "KLSM":
                    Links = chunk as MSLK;
                    break;

                case "MSVT":
                case "TVSM":
                    VertexData = chunk as MSVT;
                    break;

                case "MSVI":
                case "IVSM":
                    VertexIndices2 = chunk as MSVI;
                    break;

                case "MSUR":
                case "RUSM":
                    SurfaceData = chunk as MSUR;
                    break;

                case "MPRL":
                case "LRPM":
                    PositionData = chunk as MPRL;
                    break;

                case "MPRR":
                case "RRPM":
                    ValuePairs = chunk as MPRR;
                    break;

                case "MDBH":
                case "HBDM":
                    BuildingData = chunk as MDBH;
                    break;

                case "MDOS":
                case "SODM":
                    SimpleData = chunk as MDOS;
                    break;

                case "MDSF":
                case "FSDM":
                    FinalData = chunk as MDSF;
                    break;
            }
        }

        /// <summary>
        /// Processes the file manually if the reflection approach fails.
        /// </summary>
        /// <param name="inData">The binary data to process.</param>
        private void ProcessManually(byte[] inData)
        {
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
                Errors.Add($"Error in manual processing: {ex.Message}");
                if (ex.InnerException != null)
                {
                    Errors.Add($"Inner exception: {ex.InnerException.Message}");
                }
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

                case "MSHD":
                case "DHSM":
                    ShadowData = new MSHD(data);
                    break;

                case "MSPV":
                case "VPSM":
                    VertexPositions = new MSPV(data);
                    break;

                case "MSPI":
                case "IPSM":
                    VertexIndices = new MSPI(data);
                    break;

                case "MSCN":
                case "NCSM":
                    NormalCoordinates = new MSCN(data);
                    break;

                case "MSLK":
                case "KLSM":
                    Links = new MSLK(data);
                    break;

                case "MSVT":
                case "TVSM":
                    VertexData = new MSVT(data);
                    break;

                case "MSVI":
                case "IVSM":
                    VertexIndices2 = new MSVI(data);
                    break;

                case "MSUR":
                case "RUSM":
                    SurfaceData = new MSUR(data);
                    break;

                case "MPRL":
                case "LRPM":
                    PositionData = new MPRL(data);
                    break;

                case "MPRR":
                case "RRPM":
                    ValuePairs = new MPRR(data);
                    break;

                case "MDBH":
                case "HBDM":
                    BuildingData = new MDBH(data);
                    break;

                case "MDOS":
                case "SODM":
                    SimpleData = new MDOS(data);
                    break;

                case "MDSF":
                case "FSDM":
                    FinalData = new MDSF(data);
                    break;
            }
        }

        /// <summary>
        /// Gets the chunks in this PM4 file.
        /// </summary>
        /// <returns>An enumerable of IIFFChunk objects.</returns>
        public IEnumerable<IIFFChunk> GetChunks()
        {
            if (Version != null)
                yield return Version;

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

            if (PositionData != null)
                yield return PositionData;

            if (ValuePairs != null)
                yield return ValuePairs;

            if (BuildingData != null)
                yield return BuildingData;

            if (SimpleData != null)
                yield return SimpleData;

            if (FinalData != null)
                yield return FinalData;
        }
    }
}