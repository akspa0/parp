#include <iostream>
#include <string>
#include <cstring>
#include <fstream>
#include <wowfiles/Wdt.h>
#include <wowfiles/Wdl.h>
#include <wowfiles/alpha/WdtAlpha.h>
#include <wowfiles/lichking/AdtLk.h>
#include <wowfiles/cataclysm/AdtCata.h>
#include <wowfiles/cataclysm/AdtCataTerrain.h>
#include <wowfiles/cataclysm/AdtCataTextures.h>
#include <wowfiles/cataclysm/AdtCataObjects.h>
#include <utilities/Utilities.h>

int main(int argc, char **argv) {
    if (argc < 2) {
        std::cerr << "Error: No input file provided!" << std::endl;
        return 1;
    }

    std::string wdtName(argv[1]);
    WdtAlpha testWdtAlpha(wdtName);

    Wdt testWdt(testWdtAlpha.toWdt());
    testWdt.toFile();

    std::vector<int> adtsNums(testWdtAlpha.getExistingAdtsNumbers());
    std::vector<int> adtsOffsets(testWdtAlpha.getAdtOffsetsInMain());

    std::vector<std::string> mdnmNames(testWdtAlpha.getMdnmFileNames());
    std::vector<std::string> monmNames(testWdtAlpha.getMonmFileNames());

    const int adtTotalNum(adtsNums.size());
    int currentAdt;

    for (currentAdt = 0; currentAdt < adtTotalNum; ++currentAdt) {
        AdtAlpha testAdt(AdtAlpha(wdtName, adtsOffsets[adtsNums[currentAdt]], adtsNums[currentAdt]));

        AdtLk testAdtLk(testAdt.toAdtLk(mdnmNames, monmNames));
        testAdtLk.toFile();
    }

    return 0;
}
