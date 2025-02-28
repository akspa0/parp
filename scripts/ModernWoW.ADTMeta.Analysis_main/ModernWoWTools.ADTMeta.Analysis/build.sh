#!/bin/bash
# Build script for ADT Analysis Tool

# Exit on error
set -e

# Define colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Print header
echo -e "\n${CYAN}=========================================${NC}"
echo -e "${CYAN}     ADT Analysis Tool Build Script${NC}"
echo -e "${CYAN}=========================================${NC}"

# Check if dotnet is installed
if command -v dotnet &> /dev/null; then
    DOTNET_VERSION=$(dotnet --version)
    echo -e "\n${GREEN}✓ .NET SDK version $DOTNET_VERSION found${NC}"
else
    echo -e "\n${RED}❌ .NET SDK not found. Please install the .NET SDK from https://dotnet.microsoft.com/download${NC}"
    exit 1
fi

# Restore packages
echo -e "\n${YELLOW}→ Restoring NuGet packages...${NC}"
if dotnet restore; then
    echo -e "${GREEN}✓ Packages restored successfully${NC}"
else
    echo -e "${RED}❌ Failed to restore packages${NC}"
    exit 1
fi

# Build solution
echo -e "\n${YELLOW}→ Building solution...${NC}"
if dotnet build --configuration Release --no-restore; then
    echo -e "${GREEN}✓ Build completed successfully${NC}"
else
    echo -e "${RED}❌ Build failed${NC}"
    exit 1
fi

# Output success message
echo -e "\n${CYAN}=========================================${NC}"
echo -e "${CYAN}     Build Completed Successfully!${NC}"
echo -e "${CYAN}=========================================${NC}"

# Show executable path
EXEC_PATH="$(pwd)/ModernWoWTools.ADTMeta.Analysis/bin/Release/net8.0/ModernWoWTools.ADTMeta.Analysis"
echo -e "\n${YELLOW}Executable location:${NC}"
echo -e "${CYAN}$EXEC_PATH${NC}"

# Show usage example
echo -e "\n${YELLOW}Usage example:${NC}"
echo -e "${CYAN}dotnet $EXEC_PATH.dll --directory <path_to_adt_files> [options]${NC}"

echo -e "\n${YELLOW}For more options, run:${NC}"
echo -e "${CYAN}dotnet $EXEC_PATH.dll --help${NC}"
echo ""

# Make the script executable
chmod +x "$EXEC_PATH" 2>/dev/null || true