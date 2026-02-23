import platform
import re
from pathlib import Path


def FillLocalizationMappingTable (devKitPath: Path) -> dict[str, str]:
    # Dynamically generate a mapping table from GSLocalization.h
    pattern = None
    system = platform.system ()
    if system == 'Windows':
        pattern = r'#define\s+VERSION_APPENDIX\s+"([A-Z]+)"[\s\S]*?#define\s+WIN_LANGCHARSET_STR\s+"([^"]+)"'
    elif  system == 'Darwin':
        pattern = r'#define\s+VERSION_APPENDIX\s+"([A-Z]+)"[\s\S]*?#define\s+MAC_REGION_NAME\s+"([^"]+)"'
    
    assert pattern, 'Platform is not supported'

    gsLocalizationPath = devKitPath / 'Inc' / 'GSLocalization.h'
    with open(gsLocalizationPath, 'r', encoding='utf-8') as f:
        gsLocalizationContent = f.read ()

    patternRegex = re.compile (pattern, re.MULTILINE)
    return { m.group(1): m.group(2) for m in patternRegex.finditer (gsLocalizationContent) }
