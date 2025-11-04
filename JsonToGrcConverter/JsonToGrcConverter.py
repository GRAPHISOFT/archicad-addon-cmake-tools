import json
from pathlib import Path
from .Common import (
    GrcOutputBuilder,
    UnsupportedResourceTypeError,
    MACRO_NAME_WIDTH,
    MACRO_VALUE_WIDTH,
    CheckIfAllKeysWereHandled,
    GetConditionAsIfDef,
    GetConditionEnd,
)
from .ACNFConverter import ConvertACNF
from .ACP0Converter import ConvertACP0
from .CMNDConverter import ConvertCMND
from .DATAConverter import ConvertDATA
from .DHLPConverter import ConvertDHLP
from .FILEConverter import ConvertFILE
from .FTGPConverter import ConvertFTGP
from .FTYPConverter import ConvertFTYP
from .GALRConverter import ConvertGALR
from .GCSRConverter import ConvertGCSR
from .GDLGConverter import ConvertGDLG
from .GICNConverter import ConvertGICN
from .MDIDConverter import ConvertMDID
from .STRSConverter import ConvertSTRS
from .TEXTConverter import ConvertTEXT


def ConvertJsonDataToGrcString (jsonData: dict, targetAcVersion: int, ignoredResourceTypes: list[str] = []) -> str:
    outputBuilder = GrcOutputBuilder ()

    outputBuilder.AddLine ('#include "DGDefs.h"')
    if 'MDID' in jsonData:
        outputBuilder.AddLine ('#include "MDIDs_modules.h"')
    outputBuilder.AddLine ()

    if 'macroDictionary' in jsonData:
        for macro in jsonData.pop ('macroDictionary'):
            condition = macro.get ('#condition')
            if condition:
                outputBuilder.AddLine (GetConditionAsIfDef (condition))
            outputBuilder.AddLine (f'#define {macro["macro"]:<{MACRO_NAME_WIDTH}} {macro["value"]:>{MACRO_VALUE_WIDTH}}')
            if condition:
                outputBuilder.AddLine (GetConditionEnd ())
        outputBuilder.AddLine ()

    for resourceType, resources in jsonData.items ():
        assert isinstance (resources, list)

        if resourceType in ignoredResourceTypes:
            continue

        for resource in resources:
            assert isinstance (resource, dict)

            resourceTypeConverterMapping = {
                'ACNF': ConvertACNF,
                'ACP0': ConvertACP0,
                'CMND': ConvertCMND,
                'DATA': ConvertDATA,
                'DHLP': ConvertDHLP,
                'FILE': ConvertFILE,
                'FTGP': ConvertFTGP,
                'FTYP': ConvertFTYP,
                'GALR': ConvertGALR,
                'GCSR': ConvertGCSR,
                'GDLG': ConvertGDLG,
                'GICN': ConvertGICN,
                'MDID': ConvertMDID,
                'STRS': ConvertSTRS,
                'TEXT': ConvertTEXT,
            }

            if resourceType not in resourceTypeConverterMapping:
                raise UnsupportedResourceTypeError (resourceType)

            resourceTypeConverterMapping[resourceType] (outputBuilder, resource, targetAcVersion)

            CheckIfAllKeysWereHandled (resource)

            outputBuilder.AddLine ()

    return outputBuilder.GetResult ()


def ConvertJsonFileToGrcString (inputFile: Path, targetAcVersion: int, ignoredResourceTypes: list[str] = []) -> str:
    with open (inputFile, 'r', encoding='utf-8') as f:
        jsonData = json.load (f)

    return ConvertJsonDataToGrcString (jsonData, targetAcVersion, ignoredResourceTypes)
