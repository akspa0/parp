using System;
using System.Collections.Generic;
using System.Data.SQLite;
using System.IO;
using System.Threading.Tasks;
using ModernWoWTools.ADTMeta.Analysis.Models;
using ModernWoWTools.ADTMeta.Analysis.Utilities;

namespace ModernWoWTools.ADTMeta.Analysis.Services
{
    /// <summary>
    /// Service for storing ADT analysis results in a SQLite database.
    /// </summary>
    public class DatabaseService
    {
        private readonly string _connectionString;
        private readonly ILoggingService _logger;

        /// <summary>
        /// Creates a new instance of the DatabaseService class.
        /// </summary>
        /// <param name="databasePath">The path to the SQLite database file.</param>
        /// <param name="logger">The logging service to use.</param>
        public DatabaseService(string databasePath, ILoggingService logger)
        {
            if (string.IsNullOrEmpty(databasePath))
                throw new ArgumentException("Database path cannot be null or empty.", nameof(databasePath));

            _connectionString = $"Data Source={databasePath};Version=3;";
            _logger = logger ?? throw new ArgumentNullException(nameof(logger));
            
            InitializeDatabase();
        }

        /// <summary>
        /// Initializes the database schema.
        /// </summary>
        private void InitializeDatabase()
        {
            _logger.LogInfo("Initializing database...");
            
            using (var connection = new SQLiteConnection(_connectionString))
            {
                connection.Open();
                
                using (var transaction = connection.BeginTransaction())
                {
                    try
                    {
                        // Create adt_files table
                        using (var command = connection.CreateCommand())
                        {
                            command.CommandText = @"
                            CREATE TABLE IF NOT EXISTS adt_files (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                name TEXT,
                                folder_name TEXT,
                                x_coord INTEGER,
                                y_coord INTEGER
                            )";
                            command.ExecuteNonQuery();
                        }
                        
                        // Create textures table
                        using (var command = connection.CreateCommand())
                        {
                            command.CommandText = @"
                            CREATE TABLE IF NOT EXISTS textures (
                                adt_id INTEGER,
                                texture TEXT
                            )";
                            command.ExecuteNonQuery();
                        }
                        
                        // Create m2_models table
                        using (var command = connection.CreateCommand())
                        {
                            command.CommandText = @"
                            CREATE TABLE IF NOT EXISTS m2_models (
                                adt_id INTEGER,
                                model_name TEXT
                            )";
                            command.ExecuteNonQuery();
                        }
                        
                        // Create wmo_models table
                        using (var command = connection.CreateCommand())
                        {
                            command.CommandText = @"
                            CREATE TABLE IF NOT EXISTS wmo_models (
                                adt_id INTEGER,
                                wmo_name TEXT
                            )";
                            command.ExecuteNonQuery();
                        }
                        
                        // Create mddf table
                        using (var command = connection.CreateCommand())
                        {
                            command.CommandText = @"
                            CREATE TABLE IF NOT EXISTS mddf (
                                adt_id INTEGER,
                                uniqueId INTEGER,
                                model_name TEXT,
                                posX REAL,
                                posY REAL,
                                posZ REAL,
                                rotX REAL,
                                rotY REAL,
                                rotZ REAL,
                                scale REAL,
                                flags INTEGER
                            )";
                            command.ExecuteNonQuery();
                        }
                        
                        // Create modf table
                        using (var command = connection.CreateCommand())
                        {
                            command.CommandText = @"
                            CREATE TABLE IF NOT EXISTS modf (
                                adt_id INTEGER,
                                uniqueId INTEGER,
                                wmo_name TEXT,
                                posX REAL,
                                posY REAL,
                                posZ REAL,
                                rotX REAL,
                                rotY REAL,
                                rotZ REAL,
                                scale REAL,
                                flags INTEGER
                            )";
                            command.ExecuteNonQuery();
                        }
                        
                        transaction.Commit();
                        _logger.LogInfo("Database initialized successfully.");
                    }
                    catch (Exception ex)
                    {
                        transaction.Rollback();
                        _logger.LogError($"Error initializing database: {ex.Message}");
                        throw;
                    }
                }
            }
        }

        /// <summary>
        /// Stores an ADT analysis result in the database.
        /// </summary>
        /// <param name="result">The ADT analysis result to store.</param>
        public async Task StoreAdtAnalysisResultAsync(AdtAnalysisResult result)
        {
            if (result == null)
                throw new ArgumentNullException(nameof(result));
            
            _logger.LogDebug($"Storing ADT analysis result for {result.FileName}...");
            
            using (var connection = new SQLiteConnection(_connectionString))
            {
                await connection.OpenAsync();
                
                using (var transaction = connection.BeginTransaction())
                {
                    try
                    {
                        // Insert ADT file info
                        long adtId;
                        using (var command = connection.CreateCommand())
                        {
                            command.CommandText = @"
                            INSERT INTO adt_files (name, folder_name, x_coord, y_coord)
                            VALUES (@name, @folder_name, @x_coord, @y_coord);
                            SELECT last_insert_rowid();";
                            command.Parameters.AddWithValue("@name", result.FileName);
                            command.Parameters.AddWithValue("@folder_name", Path.GetDirectoryName(result.FilePath));
                            command.Parameters.AddWithValue("@x_coord", result.XCoord);
                            command.Parameters.AddWithValue("@y_coord", result.YCoord);
                            adtId = (long)await command.ExecuteScalarAsync();
                        }
                        
                        // Insert textures
                        foreach (var texture in result.TextureReferences)
                        {
                            using (var command = connection.CreateCommand())
                            {
                                command.CommandText = @"
                                INSERT INTO textures (adt_id, texture)
                                VALUES (@adt_id, @texture)";
                                command.Parameters.AddWithValue("@adt_id", adtId);
                                command.Parameters.AddWithValue("@texture", texture.OriginalPath);
                                await command.ExecuteNonQueryAsync();
                            }
                        }
                        
                        // Insert M2 models
                        foreach (var model in result.ModelReferences)
                        {
                            using (var command = connection.CreateCommand())
                            {
                                command.CommandText = @"
                                INSERT INTO m2_models (adt_id, model_name)
                                VALUES (@adt_id, @model_name)";
                                command.Parameters.AddWithValue("@adt_id", adtId);
                                command.Parameters.AddWithValue("@model_name", model.OriginalPath);
                                await command.ExecuteNonQueryAsync();
                            }
                        }
                        
                        // Insert WMO models
                        foreach (var wmo in result.WmoReferences)
                        {
                            using (var command = connection.CreateCommand())
                            {
                                command.CommandText = @"
                                INSERT INTO wmo_models (adt_id, wmo_name)
                                VALUES (@adt_id, @wmo_name)";
                                command.Parameters.AddWithValue("@adt_id", adtId);
                                command.Parameters.AddWithValue("@wmo_name", wmo.OriginalPath);
                                await command.ExecuteNonQueryAsync();
                            }
                        }
                        
                        // Insert MDDF placements
                        foreach (var placement in result.ModelPlacements)
                        {
                            using (var command = connection.CreateCommand())
                            {
                                command.CommandText = @"
                                INSERT INTO mddf (adt_id, uniqueId, model_name, posX, posY, posZ, rotX, rotY, rotZ, scale, flags)
                                VALUES (@adt_id, @uniqueId, @model_name, @posX, @posY, @posZ, @rotX, @rotY, @rotZ, @scale, @flags)";
                                command.Parameters.AddWithValue("@adt_id", adtId);
                                command.Parameters.AddWithValue("@uniqueId", placement.UniqueId);
                                command.Parameters.AddWithValue("@model_name", placement.Name);
                                command.Parameters.AddWithValue("@posX", placement.Position.X);
                                command.Parameters.AddWithValue("@posY", placement.Position.Y);
                                command.Parameters.AddWithValue("@posZ", placement.Position.Z);
                                command.Parameters.AddWithValue("@rotX", placement.Rotation.X);
                                command.Parameters.AddWithValue("@rotY", placement.Rotation.Y);
                                command.Parameters.AddWithValue("@rotZ", placement.Rotation.Z);
                                command.Parameters.AddWithValue("@scale", placement.Scale);
                                command.Parameters.AddWithValue("@flags", placement.Flags);
                                await command.ExecuteNonQueryAsync();
                            }
                        }
                        
                        // Insert MODF placements
                        foreach (var placement in result.WmoPlacements)
                        {
                            using (var command = connection.CreateCommand())
                            {
                                command.CommandText = @"
                                INSERT INTO modf (adt_id, uniqueId, wmo_name, posX, posY, posZ, rotX, rotY, rotZ, scale, flags)
                                VALUES (@adt_id, @uniqueId, @wmo_name, @posX, @posY, @posZ, @rotX, @rotY, @rotZ, @scale, @flags)";
                                command.Parameters.AddWithValue("@adt_id", adtId);
                                command.Parameters.AddWithValue("@uniqueId", placement.UniqueId);
                                command.Parameters.AddWithValue("@wmo_name", placement.Name);
                                command.Parameters.AddWithValue("@posX", placement.Position.X);
                                command.Parameters.AddWithValue("@posY", placement.Position.Y);
                                command.Parameters.AddWithValue("@posZ", placement.Position.Z);
                                command.Parameters.AddWithValue("@rotX", placement.Rotation.X);
                                command.Parameters.AddWithValue("@rotY", placement.Rotation.Y);
                                command.Parameters.AddWithValue("@rotZ", placement.Rotation.Z);
                                command.Parameters.AddWithValue("@scale", placement.Scale);
                                command.Parameters.AddWithValue("@flags", placement.Flags);
                                await command.ExecuteNonQueryAsync();
                            }
                        }
                        
                        transaction.Commit();
                        _logger.LogDebug($"Stored ADT analysis result for {result.FileName} successfully.");
                    }
                    catch (Exception ex)
                    {
                        transaction.Rollback();
                        _logger.LogError($"Error storing ADT analysis result: {ex.Message}");
                        throw;
                    }
                }
            }
        }

        /// <summary>
        /// Stores multiple ADT analysis results in the database.
        /// </summary>
        /// <param name="results">The ADT analysis results to store.</param>
        public async Task StoreAdtAnalysisResultsAsync(IEnumerable<AdtAnalysisResult> results)
        {
            if (results == null)
                throw new ArgumentNullException(nameof(results));
            
            foreach (var result in results)
            {
                await StoreAdtAnalysisResultAsync(result);
            }
        }
    }
}