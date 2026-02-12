import re

def FillLocalizationMappingTable (devKitPath, pattern: str) -> str:
    # Dynamically generate a mapping table from GSLocalization.h
    gsLocalizationPath = devKitPath / 'Inc' / 'GSLocalization.h'
    with open(gsLocalizationPath, 'r', encoding='utf-8') as f:
        gsLocalizationContent = f.read ()

    if not pattern:
        return {}

    patternRegex = re.compile (pattern, re.MULTILINE)
    return { m.group(1): m.group(2) for m in patternRegex.finditer (gsLocalizationContent) }
