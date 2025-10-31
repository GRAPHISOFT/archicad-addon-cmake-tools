import re


class ConditionHandlingNotImplementedError (Exception):
    """
    Raised when condition handling is not implemented for a certain case.
    For example the rect of dialog controls can have a condition, which we cannot convert yet.
    """
    pass


class UnsupportedResourceTypeError (Exception):
    """
    Raised when a resource type is not supported.
    This could happen if a new resource type in JSON is not supported here yet.
    """
    pass


class UnsupportedGDLGControlError (Exception):
    """
    Raised when a GDLG control is not supported.
    For example HTV.
    """
    pass


class UnsupportedGDLGControlPropertyError (Exception):
    """
    Raised when a GDLG control property is not supported.
    This could happen if a new property in JSON is not supported here yet.
    """
    pass


class IllegalStyleError (Exception):
    """
    ResConv rejects certain dialog styles that the JSON resource processing does not.
    For example a Model dialog cannot have top caption in GRC.
    """
    pass


class UnhandledJsonPropertyError (Exception):
    """
    Raised when some JSON properties are not handled.
    This could happen if a new key is introduced in the JSON resource and this script
    was not updated. The scripts removes keys from an object which are handled during
    conversion. At the end we check if all keys were removed thus handled in the
    conversion process.
    """
    pass


MACRO_NAME_WIDTH = 48
MACRO_VALUE_WIDTH = 8
GDLG_CONTROL_TYPE_WIDTH = 24
GDLH_TOOLTIP_WIDTH = 48
CMND_TEXT_WIDTH = 64
CMND_ID_WIDTH = 48
CMND_ICONID_WIDTH = 48


class GrcOutputBuilder:
    def __init__(self):
        self.result = ''

    def AddLine (self, line: str = '') -> None:
        self.result += f'{line}\n'

    def GetResult (self) -> str:
        return self.result


def CheckForNotImplementedConditionHandling (obj) -> None:
    if isinstance (obj, list):
        raise ConditionHandlingNotImplementedError (f'Condition handling is not implemented for:\n{obj}')
    if isinstance (obj, dict) and '#condition' in obj:
        raise ConditionHandlingNotImplementedError (f'Condition handling is not implemented for:\n{obj}')


def CheckIfAllKeysWereHandled (obj: dict) -> None:
    assert isinstance (obj, dict)

    if len (obj) != 0:
        raise UnhandledJsonPropertyError (list (obj.keys ()))


def MapPropertyToGrc (valueInJson: str | list, mapping: dict[str, str]) -> str:
    CheckForNotImplementedConditionHandling (valueInJson)

    assert isinstance (valueInJson, str)

    if valueInJson in mapping:
        return mapping[valueInJson]

    raise UnsupportedGDLGControlPropertyError (valueInJson)


def ExtractString (textObj: dict | str | None) -> str:
    CheckForNotImplementedConditionHandling (textObj)

    if isinstance (textObj, dict) and 'str' in textObj:
        result = textObj.pop ('str')
        textObj.pop ('dictId', None) # Has no equivalent in GRC.
        textObj.pop ('localized', None) # Has no equivalent in GRC.
        CheckIfAllKeysWereHandled (textObj)
        return result

    # Rarely we have a "#value" without a "#condition".
    if isinstance (textObj, dict) and '#value' in textObj and '#condition' not in textObj:
        result = textObj.pop ('#value')
        textObj.pop ('#comment', None) # Comment in this case is not supported.
        return ExtractString (result)

    if isinstance (textObj, str):
        return textObj

    if textObj is None:
        return ''

    raise RuntimeError (f'Invalid text object: {textObj}')


def EscapeString (text: str) -> str:
    CheckForNotImplementedConditionHandling (text)
    if not text:
        return '""'
    
    text = text.replace ('\\', '\\\\')
    text = text.replace ('\n', '\\n')
    text = text.replace ('\t', '\\t')
    text = text.replace ('"', '\\"')
    
    return f'"{text}"'


def ConvertToEscapedString (textObj: dict | str | None) -> str:
    s = ExtractString (textObj)
    return EscapeString (s)


def FormatComment (comment: str) -> str:
    if not comment:
        return ''

    # Rarely the "#comment" already contains '/*' and '*/' strings, which causes issues for the preprocessor.
    comment = comment.replace ('/*', '').replace ('*/', '').strip ()

    return f'/* {comment} */'


def FormatCommentLeadingSpace (comment: str) -> str:
    if not comment:
        return ''
    return f' {FormatComment (comment)}'


def GetItemIndexComment (index: int) -> str:
    return FormatComment (f'[{index:>3}]')


def ConvertComment (controlProps, leadingSpace = True) -> str:
    if leadingSpace:
        return FormatCommentLeadingSpace (controlProps.pop ('#comment', None))
    else:
        return FormatComment (controlProps.pop ('#comment', None))


def GetConditionAsIfDef (condition: str) -> str:
    split = re.split ('([&|()])', condition)
    
    result = []

    for tokenWithWhitespace in split:
        token = tokenWithWhitespace.strip ()
        if not token:
            continue

        if token == '(' or token == ')':
            result.append (token)
            continue

        if token == '&':
            result.append ('&&')
        elif token == '|':
            result.append ('||')
        elif token.startswith ('+'):
            result.append (f'defined ({token[1:]})')
        elif token.startswith ('-'):
            result.append (f'!defined ({token[1:]})')
        else:
            raise RuntimeError (f'Unknown token in condition: "{token}"')

    return f'#if {" ".join (result)}'


def GetConditionEnd () -> str:
    return '#endif'


def ConvertIconId (iconId: str) -> str:
    # Could be either a hardcoded identifier or an actual icon id.

    mapping = {
        '-1': 'NoIcon',
        'DGNoIcon': 'NoIcon',
        'DGErrorIcon': 'DG_ERROR_ICON',
        'DGInfoIcon': 'DG_INFORMATION_ICON',
        'DGWarningIcon': 'DG_WARNING_ICON',
        'DGFileIcon': 'DG_FILE_ICON',
        'DGTextFileIcon': 'DG_TEXTFILE_ICON',
        'DGFolderIcon': 'DG_FOLDER_ICON',
        'DGFolderOpenIcon': 'DG_FOLDEROPEN_ICON',
        'DGMyDocFolderIcon': 'DG_MYDOCFOLDER_ICON',
        'DGFavoritesIcon': 'DG_FAVORITES_ICON',
        'DGFloppyIcon': 'DG_FLOPPY_ICON',
        'DGCDDriveIcon': 'DG_CDDRIVE_ICON',
        'DGHDDIcon': 'DG_HDD_ICON',
        'DGNetDriveIcon': 'DG_NETDRIVE_ICON',
        'DGDesktopIcon': 'DG_DESKTOP_ICON',
        'DGRecycleBinIcon': 'DG_RECYCLEBIN_ICON',
        'DGEntireNetworkIcon': 'DG_ENTIRENETWORK_ICON',
        'DGFilledLeftIcon': 'DG_FILLED_LEFT_ICON',
        'DGFilledRightIcon': 'DG_FILLED_RIGHT_ICON',
        'DGFilledDownIcon': 'DG_FILLED_DOWN_ICON',
        'DGFishboneLeftIcon': 'DG_FISHBONE_LEFT_ICON',
        'DGFishboneRightIcon': 'DG_FISHBONE_RIGHT_ICON',
        'DGFishboneDownIcon': 'DG_FISHBONE_DOWN_ICON',
    }
    
    if iconId in mapping:
        return mapping[iconId]
    
    return iconId
