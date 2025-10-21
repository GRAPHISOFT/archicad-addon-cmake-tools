import re
from pathlib import Path
import xml.etree.ElementTree as ET


USABLE_TRANSLATION_STATES = ['final', 'translated', 'signed-off', 'x-machine-translated']

XLIFF_NS = 'urn:oasis:names:tc:xliff:document:1.2'

XLIFF_NSMAP = { '': XLIFF_NS, 'gs': 'graphisoft:ac:xliff' }


def GetTrailingAndLeadingWhitespaces (text: str) -> tuple[str, str]:

    leading = re.match (r'^[\s]*', text).group ()
    trailing = re.search (r'[\s]*$', text).group ()

    if leading and trailing and text.strip () == '':
        return (leading, '')

    return (leading, trailing)


def GetTranslations (xlfPath: Path) -> dict[str, str]:
    result = {}

    xlfRoot = ET.parse (xlfPath).getroot ()

    for transUnit in xlfRoot.findall ('.//trans-unit', XLIFF_NSMAP):
        transUnitId = transUnit.get ('id')
        assert transUnitId is not None
        sourceElem = transUnit.find ('source', XLIFF_NSMAP)
        assert sourceElem is not None
        targetElem = transUnit.find ('target', XLIFF_NSMAP)
        state = targetElem.get ('state', XLIFF_NSMAP) if targetElem is not None else None

        if targetElem is not None and targetElem.text and state in USABLE_TRANSLATION_STATES:
            result[transUnitId] = targetElem.text
        else:
            result[transUnitId] = sourceElem.text

    return result


def GetMergedTranslations (childXlfPath: Path, parentXlfPath: Path | None) -> dict[str, str]:
    translations = GetTranslations (childXlfPath)
    if parentXlfPath is None:
        return translations
    parentTranslations = GetTranslations (parentXlfPath)
    return parentTranslations | translations


def TranslateJson (data, translations: dict[str, str]) -> None:
    if isinstance (data, dict):
        if 'dictId' in data:
            (leading, trailing) = GetTrailingAndLeadingWhitespaces (data['str'])
            result = translations[data['dictId']].replace ('\\n', '\n')
            data['str'] = leading + result + trailing

        for value in data.values ():
            TranslateJson (value, translations)
    
    elif isinstance (data, list):
        for item in data:
            TranslateJson (item, translations)
