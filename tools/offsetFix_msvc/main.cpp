#include <iostream>
#include <fstream>
#include "offsetFix.h"

int main(int argc, char* argv[]) {
    if (argc < 3) {
        std::cerr << "Usage: offsetFix <input.wdt> <output.wdt>\n";
        return 1;
    }

    std::fstream zoneFile(argv[1], std::ios::in | std::ios::out | std::ios::binary);
    if (!zoneFile) {
        std::cerr << "Error opening file: " << argv[1] << '\n';
        return 1;
    }

    OffsetFixData offData = {};
    // Initialize your offset values here
    // Example: offData.offset.x = 32; offData.offset.y = 32;

    try {
        findMCNKs(zoneFile, offData);
        findMDDFandMODF(zoneFile, offData);
        fixMCNKs(zoneFile, offData);
        fixDoodads(zoneFile, offData);
        fixWMOs(zoneFile, offData);
    } catch (const std::exception& e) {
        std::cerr << "Error processing file: " << e.what() << '\n';
        return 1;
    }

    // Save modified file
    zoneFile.close();
    std::ofstream outFile(argv[2], std::ios::binary);
    if (!outFile) {
        std::cerr << "Error creating output file: " << argv[2] << '\n';
        return 1;
    }

    std::ifstream inFile(argv[1], std::ios::binary);
    outFile << inFile.rdbuf();

    std::cout << "Successfully processed " << argv[1] << "\n";
    std::cout << "Output saved to " << argv[2] << "\n";

    return 0;
}