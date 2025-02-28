#!/usr/bin/env pwsh
# Build script for ADT Analysis Tool

# Set error action preference to stop on any error
$ErrorActionPreference = "Stop"

# Define colors for output
$Green = [ConsoleColor]::Green
$Red = [ConsoleColor]::Red
$Yellow = [ConsoleColor]::Yellow
$Cyan = [ConsoleColor]::Cyan

# Print header
Write-Host "`n=========================================" -ForegroundColor $Cyan
Write-Host "     ADT Analysis Tool Build Script" -ForegroundColor $Cyan
Write-Host "=========================================" -ForegroundColor $Cyan

# Check if dotnet is installed
try {
    $dotnetVersion = dotnet --version
    Write-Host "`n✓ .NET SDK version $dotnetVersion found" -ForegroundColor $Green
}
catch {
    Write-Host "`n❌ .NET SDK not found. Please install the .NET SDK from https://dotnet.microsoft.com/download" -ForegroundColor $Red
    exit 1
}

# Restore packages
Write-Host "`n→ Restoring NuGet packages..." -ForegroundColor $Yellow
try {
    dotnet restore
    Write-Host "✓ Packages restored successfully" -ForegroundColor $Green
}
catch {
    Write-Host "❌ Failed to restore packages: $_" -ForegroundColor $Red
    exit 1
}

# Build solution
Write-Host "`n→ Building solution..." -ForegroundColor $Yellow
try {
    dotnet build --configuration Release --no-restore
    Write-Host "✓ Build completed successfully" -ForegroundColor $Green
}
catch {
    Write-Host "❌ Build failed: $_" -ForegroundColor $Red
    exit 1
}

# Output success message
Write-Host "`n=========================================" -ForegroundColor $Cyan
Write-Host "     Build Completed Successfully!" -ForegroundColor $Cyan
Write-Host "=========================================" -ForegroundColor $Cyan

# Show executable path
$exePath = Join-Path (Get-Location) "ModernWoWTools.ADTMeta.Analysis\bin\Release\net8.0\ModernWoWTools.ADTMeta.Analysis.exe"
Write-Host "`nExecutable location:" -ForegroundColor $Yellow
Write-Host $exePath -ForegroundColor $Cyan

# Show usage example
Write-Host "`nUsage example:" -ForegroundColor $Yellow
Write-Host ".\ModernWoWTools.ADTMeta.Analysis\bin\Release\net8.0\ModernWoWTools.ADTMeta.Analysis.exe --directory <path_to_adt_files> [options]" -ForegroundColor $Cyan

Write-Host "`nFor more options, run:" -ForegroundColor $Yellow
Write-Host ".\ModernWoWTools.ADTMeta.Analysis\bin\Release\net8.0\ModernWoWTools.ADTMeta.Analysis.exe --help" -ForegroundColor $Cyan
Write-Host ""