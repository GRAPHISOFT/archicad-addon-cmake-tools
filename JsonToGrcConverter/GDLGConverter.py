import copy

from .Common import (
    CheckForNotImplementedConditionHandling,
    CheckIfAllKeysWereHandled,
    ConvertComment,
    ConvertIconId,
    ConvertToEscapedString,
    EscapeString,
    FormatCommentLeadingSpace,
    GDLG_CONTROL_TYPE_WIDTH,
    GDLH_TOOLTIP_WIDTH,
    GetConditionAsIfDef,
    GetConditionEnd,
    GetItemIndexComment,
    GrcOutputBuilder,
    IllegalStyleError,
    MapPropertyToGrc,
    UnsupportedGDLGControlError,
)


def ConvertGrow (s: str) -> str:
    return MapPropertyToGrc (s, {
        'no': 'noGrow',
        'h': 'hGrow',
        'v': 'vGrow',
        'hv': 'grow'
    })


def ConvertClose (s: str) -> str:
    return MapPropertyToGrc (s, {
        'yes': 'close',
        'no': 'noClose'
    })


def ConvertCaption (s: str) -> str:
    return MapPropertyToGrc (s, {
        'top': 'topCaption',
        'left': 'leftCaption',
        'no': 'noCaption'
    })


def ConvertMinimize (s: str) -> str:
    return MapPropertyToGrc (s, {
        'no': 'noMinimize',
        'yes': 'minimize'
    })


def ConvertMaximize (s: str) -> str:
    return MapPropertyToGrc (s, {
        'no': 'noMaximize',
        'yes': 'maximize'
    })


def ConvertFrame (s: str) -> str:
    return MapPropertyToGrc (s, {
        'normal': 'normalFrame',
        'thick': 'thickFrame',
        'no': 'noFrame'
    })


def ConvertDialogTypeFlags (dialogType: str, dialogRes: dict) -> str:
    if dialogType == 'TabPage':
        if 'grow' in dialogRes:
            raise IllegalStyleError (f'Illegal grow property for dialog type {dialogType}')
        return ''

    elif dialogType == 'Modal':
        flags = []
        flags.append (ConvertGrow (dialogRes.pop ('grow', 'no')))
        # For modal dialogs 'topCaption' is the default, but we cannot specify it as it would result in an illegal style error in ResConv.
        if 'caption' in dialogRes:
            caption = ConvertCaption (dialogRes.pop ('caption'))
            if caption in ['topCaption', 'leftCaption']:
                raise IllegalStyleError (f"Illegal caption '{caption}' for dialog type '{dialogType}'")
            flags.append (caption)
        if 'frame' in dialogRes:
            flags.append (ConvertFrame (dialogRes.pop ('frame', 'normal')))
        return ' | '.join (flags)

    elif dialogType == 'Modeless':
        typeFlags = []
        if 'grow' in dialogRes:
            typeFlags.append (ConvertGrow (dialogRes.pop ('grow', 'no')))
        if 'caption' in dialogRes:
            typeFlags.append (ConvertCaption (dialogRes.pop ('caption', 'top')))
        if 'close' in dialogRes:
            typeFlags.append (ConvertClose (dialogRes.pop ('close', 'no')))
        if 'minimize' in dialogRes:
            typeFlags.append (ConvertMinimize (dialogRes.pop ('minimize', 'no')))
        if 'maximize' in dialogRes:
            typeFlags.append (ConvertMaximize (dialogRes.pop ('maximize', 'no')))
        if 'frame' in dialogRes:
            typeFlags.append (ConvertFrame (dialogRes.pop ('frame', 'normal')))
        return ' | '.join (typeFlags)

    elif dialogType == 'Palette':
        flags = []
        if 'grow' in dialogRes:
            flags.append (ConvertGrow (dialogRes.pop ('grow', 'no')))
        if 'caption' in dialogRes:
            flags.append (ConvertCaption (dialogRes.pop ('caption', 'top')))
        if 'close' in dialogRes:
            flags.append (ConvertClose (dialogRes.pop ('close', 'no')))
        if 'frame' in dialogRes:
            flags.append (ConvertFrame (dialogRes.pop ('frame', 'normal')))
        return ' | '.join (flags)

    raise RuntimeError (f'Unknown dialog type: {dialogType}')


def GetUsedAnchors (controls: list[dict]) -> list[str]:
    result = []

    for control in controls:
        controlType = list (control.keys ())[0]
        controlProps = control[controlType]

        if 'helpInfo' not in controlProps:
            continue

        # Intentionally no pop here, will happen later.
        if isinstance (controlProps.get ('helpInfo'), list):
            for helpInfo in controlProps.get ('helpInfo'):
                result.append (helpInfo['anchor'])
        else:
            result.append (controlProps.get ('helpInfo')['anchor'])

    return result


def GenerateUniqueAnchor (usedAnchors: list[str], controlType: str) -> str:
    controlIndex = 0
    uniqueAnchor = f'{controlType}_{controlIndex}'

    while uniqueAnchor in usedAnchors:
        uniqueAnchor = f'{controlType}_{controlIndex}'
        controlIndex += 1

    return uniqueAnchor


def ConvertDialogType (dialogType: str) -> str:
    return MapPropertyToGrc (dialogType, {
        'Modal': 'Modal',
        'Modeless': 'Modeless',
        'Palette': 'Palette',
        'TabPage': 'TabPage'
    })


def ConvertGDLG (outputBuilder: GrcOutputBuilder, resource: dict, targetAcVersion: int) -> None:
    resId = resource.pop ('#id')
    resource.pop ('localized', None) # No equivalent in GRC.
    name = ConvertToEscapedString (resource.pop ('name', None))
    size = resource.pop ('size')
    CheckForNotImplementedConditionHandling (size)
    width = size.pop ('w')
    height = size.pop ('h')
    CheckIfAllKeysWereHandled (size)

    dialogType = ConvertDialogType (resource.pop ('type'))
    dialogTypeFlags = ConvertDialogTypeFlags (dialogType, resource)
    comment = ConvertComment (resource)

    controls = resource.pop ('controls')

    # GDLG and GDLH resources are generated within this function, as GDLH is not a seperate resource in JSON.
    # All keys will be removed during ConvertGDLGControl, but we need the #conditions for the GDLH resource, so we make a copy first.
    controlsCopy = copy.deepcopy (controls)

    # "helpInfo" is optional in JSON, but its equivalent was mandatory in GRC.
    # We need to generate unique anchors for controls that don't have helpInfo.
    # This variable will contain the already defined anchors, so we can avoid duplication when generating unique ones.
    usedAnchors = GetUsedAnchors (controls)

    resourceCondition = resource.pop ('#condition', None)
    if resourceCondition:
        outputBuilder.AddLine (GetConditionAsIfDef (resourceCondition))

    outputBuilder.AddLine (f'\'GDLG\' {resId} {dialogType} {"|" + dialogTypeFlags if dialogTypeFlags else ""} 0 0 {width} {height} {name} {{{comment}')

    for control in controls:
        controlType = list (control.keys ())[0]
        controlProps = control[controlType]
        controlResId = int (controlProps.pop ('#id'))
        ConvertGDLGControl (outputBuilder, control, controlResId, targetAcVersion)

    outputBuilder.AddLine ('}')
    outputBuilder.AddLine ()

    dialogAnchor = resource.pop ('anchor')

    outputBuilder.AddLine (f'\'DLGH\' {resId} {dialogAnchor} {{{comment}')

    for i, control in enumerate (controls, 1):
        controlType = list (control.keys ())[0]
        controlProps = control[controlType]

        controlCondition = controlsCopy[i-1][controlType].pop ('#condition', None)
        controlResId = int (controlsCopy[i-1][controlType].pop ('#id'))
        if controlCondition:
            outputBuilder.AddLine (GetConditionAsIfDef (controlCondition))

        if 'helpInfo' in controlProps:
            helpInfo = controlProps.pop ('helpInfo')
            if isinstance (helpInfo, list):
                for anchorIndex, anchorItem in enumerate (helpInfo, 0):
                    anchorCondition = anchorItem.pop ('#condition', None)
                    if anchorCondition:
                        outputBuilder.AddLine (GetConditionAsIfDef (anchorCondition))
                    controlAnchor = anchorItem.pop ('anchor')
                    controlTooltip = ConvertToEscapedString (anchorItem.pop ('tooltip', ''))
                    anchorComment = FormatCommentLeadingSpace (anchorItem.pop ('#comment', None))
                    if anchorIndex == 0:
                        outputBuilder.AddLine (f'{controlResId:<2} {controlTooltip:<{GDLH_TOOLTIP_WIDTH}} {controlAnchor}{anchorComment}')
                    else:
                        outputBuilder.AddLine (f'     {controlTooltip:<{GDLH_TOOLTIP_WIDTH}} {controlAnchor}{anchorComment}')
                    if anchorCondition:
                        outputBuilder.AddLine (GetConditionEnd ())
                    CheckIfAllKeysWereHandled (anchorItem)
            else:
                controlAnchor = helpInfo.get ('anchor')
                controlTooltip = ConvertToEscapedString (helpInfo.get ('tooltip'))
                outputBuilder.AddLine (f'{i:<2} {controlTooltip:<{GDLH_TOOLTIP_WIDTH}} {controlAnchor}')
        else:
            controlAnchor = GenerateUniqueAnchor (usedAnchors, controlType)
            usedAnchors.append (controlAnchor)
            controlTooltip = '""'
            outputBuilder.AddLine (f'{i:<2} {controlTooltip:<{GDLH_TOOLTIP_WIDTH}} {controlAnchor}')

        if controlCondition:
            outputBuilder.AddLine (GetConditionEnd ())

    outputBuilder.AddLine ('}')

    if resourceCondition:
        outputBuilder.AddLine (GetConditionEnd ())

    CheckIfAllKeysWereHandled (resource)

    for i, control in enumerate (controls, 1):
        controlType = list (control.keys ())[0]
        controlProps = control[controlType]
        CheckIfAllKeysWereHandled (controlProps)


def ConvertRect (controlProps: dict) -> str:
    rect = controlProps.pop ('rect')

    CheckForNotImplementedConditionHandling (rect)

    x = rect.pop ('x')
    y = rect.pop ('y')
    w = rect.pop ('w')
    h = rect.pop ('h')

    CheckIfAllKeysWereHandled (rect)

    assert isinstance (x, int) and isinstance (y, int) and isinstance (w, int) and isinstance (h, int)

    return f'{x:>4} {y:>4} {w:>4} {h:>4}'


def ConvertFrameType (controlProps: dict) -> str:
    return MapPropertyToGrc (controlProps.pop ('frame', 'yes'), {
        'no': 'noFrame',
        'yes': 'frame'
    })


def ConvertBevelType (controlProps: dict, targetAcVersion: int) -> str:
    return MapPropertyToGrc (controlProps.pop ('appearance', 'roundedEdge'), {
        'roundedEdge': 'RoundedEdge' if targetAcVersion >= 29 else 'BevelEdge',
        'squaredEdge': 'SquaredEdge' if targetAcVersion >= 29 else 'RoundedBevelEdge'
    })


def ConvertFontSpec (controlProps: dict) -> str:
    return MapPropertyToGrc (controlProps.pop ('font', 'largePlain'), {
        'extraSmall': 'ExtraSmall',
        'smallPlain': 'SmallPlain',
        'smallItalic': 'SmallItalic',
        'smallUnderline': 'SmallUnderline',
        'smallBold': 'SmallBold',
        'smallShadow': 'SmallShadow',
        'smallOutline': 'SmallOutline',
        'largePlain': 'LargePlain',
        'largeItalic': 'LargeItalic',
        'largeUnderline': 'LargeUnderline',
        'largeBold': 'LargeBold',
        'largeShadow': 'LargeShadow',
        'largeOutline': 'LargeOutline'
    })


def ConvertEditBase (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    itemIndexComment = GetItemIndexComment (index)
    comment = ConvertComment (controlProps)

    fontSpec = ConvertFontSpec (controlProps)

    # SAMQuantityEdit is the only numeric edit control with a subType.
    if controlType == 'SAMQuantityEdit':
        subType = controlProps.pop ("subType") # The subtypes are identical in JSON and GRC.
    else:
        subType = None

    editStyles = ConvertEditStyles (controlProps)

    editMinStr = EscapeString (controlProps.pop ('minValue', ''))
    editMaxStr = EscapeString (controlProps.pop ('maxValue', ''))

    # /* [  1] */ IntEdit 10 10 100 20 LargePlain frame | update | relative | editable "0" "100" /* comment */
    outputBuilder.AddLine (f"{itemIndexComment} {controlType:<{GDLG_CONTROL_TYPE_WIDTH}} {ConvertRect (controlProps)} {fontSpec} {subType or ''} {editStyles} {editMinStr} {editMaxStr}{comment}")


def ConvertAngleEdit (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    return ConvertEditBase (outputBuilder, controlProps, index, controlType, targetAcVersion)


def ConvertAreaEdit (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    return ConvertEditBase (outputBuilder, controlProps, index, controlType, targetAcVersion)


def ConvertBrowser (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    itemIndexComment = GetItemIndexComment (index)
    comment = ConvertComment (controlProps)

    # /* [  1] */ Browser 10 10 100 20 /* comment */
    outputBuilder.AddLine (f"{itemIndexComment} {controlType:<{GDLG_CONTROL_TYPE_WIDTH}} {ConvertRect (controlProps)}{comment}")


def ConvertButton (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    itemIndexComment = GetItemIndexComment (index)
    comment = ConvertComment (controlProps)
    text = ConvertToEscapedString (controlProps.pop ('text'))
    fontSpec = ConvertFontSpec (controlProps)
    frameType = ConvertFrameType (controlProps)
    buttonBevelType = ConvertBevelType (controlProps, targetAcVersion)

    # /* [  1] */ Button 10 10 100 20 LargePlain frame RoundedEdge "Button Text" /* comment */
    outputBuilder.AddLine (f"{itemIndexComment} {controlType:<{GDLG_CONTROL_TYPE_WIDTH}} {ConvertRect (controlProps)} {fontSpec} {frameType} {buttonBevelType} {text}{comment}")


def ConvertAlignment (controlProps: dict) -> str:
    return MapPropertyToGrc (controlProps.pop ('alignment', 'top'), {
        'top': 'vTop',
        'center': 'vCenter',
        'bottom': 'vBottom'
    })


def ConvertTruncation (controlProps: dict) -> str:
    return MapPropertyToGrc (controlProps.pop ('truncation', 'no'), {
        'no': 'noTrunc',
        'end': 'truncEnd',
        'middle': 'truncMiddle'
    })


def ConvertTextStyles (controlProps: dict) -> str:
    flags = []
    flags.append (ConvertAlignment (controlProps))
    flags.append (ConvertTruncation (controlProps))
    return ' | '.join (flags)


def ConvertEdgeType (controlProps: dict) -> str:
    return MapPropertyToGrc (controlProps.pop ('edgeType', 'default'), {
        'default': 'Default',
        'staticEdge': 'StaticEdge',
        'clientEdge': 'ClientEdge',
        'modalFrame': 'ModalFrame'
    })


def ConvertStaticTextBase (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    itemIndexComment = GetItemIndexComment (index)
    comment = ConvertComment (controlProps)
    text = ConvertToEscapedString (controlProps.pop ('text', None))
    fontSpec = ConvertFontSpec (controlProps)
    textStyles = ConvertTextStyles (controlProps)
    edgeType = ConvertEdgeType (controlProps)

    # /* [  1] */ LeftText 10 10 100 20 LargePlain vCenter | noTrunc ClientEdge "LeftText Text" /* comment */
    outputBuilder.AddLine (f"{itemIndexComment} {controlType:<{GDLG_CONTROL_TYPE_WIDTH}} {ConvertRect (controlProps)} {fontSpec} {textStyles} {edgeType} {text}{comment}")


def ConvertCenterText (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    ConvertStaticTextBase (outputBuilder, controlProps, index, controlType, targetAcVersion)


def ConvertCheckBox (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    itemIndexComment = GetItemIndexComment (index)
    comment = ConvertComment (controlProps)
    text = ConvertToEscapedString (controlProps.pop ('text'))
    fontSpec = ConvertFontSpec (controlProps)

    # /* [  1] */ CheckBox 10 10 100 20 LargePlain "CheckBox Text" /* comment */ 
    outputBuilder.AddLine (f"{itemIndexComment} {controlType:<{GDLG_CONTROL_TYPE_WIDTH}} {ConvertRect (controlProps)} {fontSpec} {text}{comment}")


def ConvertDateControlType (controlProps: dict) -> str:
    return MapPropertyToGrc (controlProps.pop ('dateType', 'calendar'), {
        'calendar': 'Calendar',
        'standard': 'Standard'
    })


def ConvertDateControl (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    itemIndexComment = GetItemIndexComment (index)
    comment = ConvertComment (controlProps)
    dateControlType = ConvertDateControlType (controlProps)

    # /* [  1] */ DateControl 10 10 100 20 Calendar /* comment */ 
    outputBuilder.AddLine (f"{itemIndexComment} {controlType:<{GDLG_CONTROL_TYPE_WIDTH}} {ConvertRect (controlProps)} {dateControlType}{comment}")


def ConvertEditSpin (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    itemIndexComment = GetItemIndexComment (index)
    comment = ConvertComment (controlProps)
    spinEditCtrlId = controlProps.pop ('editId')

    # /* [  1] */ EditSpin 10 10 100 20 8 /* comment */ 
    outputBuilder.AddLine (f"{itemIndexComment} {controlType:<{GDLG_CONTROL_TYPE_WIDTH}} {ConvertRect (controlProps)} {spinEditCtrlId} {comment}")


def ConvertGroupBoxType (controlProps: dict) -> str:
    return MapPropertyToGrc (controlProps.pop ('groupBoxType'), {
        'primary': 'Primary',
        'secondary': 'Secondary'
    })


def ConvertGroupBox (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    itemIndexComment = GetItemIndexComment (index)
    comment = ConvertComment (controlProps)
    text = ConvertToEscapedString (controlProps.pop ('text'))
    groupBoxType = ConvertGroupBoxType (controlProps)
    fontSpec = ConvertFontSpec (controlProps)

    # /* [  1] */ GroupBox 10 10 100 20 LargePlain Primary "GroupBox Text" /* comment */
    outputBuilder.AddLine (f"{itemIndexComment} {controlType:<{GDLG_CONTROL_TYPE_WIDTH}} {ConvertRect (controlProps)} {fontSpec} {groupBoxType} {text}{comment}")


def ConvertIcon (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    itemIndexComment = GetItemIndexComment (index)
    comment = ConvertComment (controlProps)
    iconId = ConvertIconId (controlProps.pop ('iconId'))
    edgeType = ConvertEdgeType (controlProps)

    # /* [  1] */ Icon 10 10 100 20 32005 StaticEdge /* comment */
    outputBuilder.AddLine (f"{itemIndexComment} {controlType:<{GDLG_CONTROL_TYPE_WIDTH}} {ConvertRect (controlProps)} {iconId} {edgeType}{comment}")


def ConvertIconButton (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    itemIndexComment = GetItemIndexComment (index)
    comment = ConvertComment (controlProps)
    iconId = ConvertIconId (controlProps.pop ('iconId'))
    frameType = ConvertFrameType (controlProps)
    bevelType = ConvertBevelType (controlProps, targetAcVersion)

    # /* [  1] */ IconButton 10 10 100 20 32005 frame RoundedEdge /* comment */
    outputBuilder.AddLine (f"{itemIndexComment} {controlType:<{GDLG_CONTROL_TYPE_WIDTH}} {ConvertRect (controlProps)} {iconId} {frameType} {bevelType}{comment}")


def ConvertIconCheckBox (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    itemIndexComment = GetItemIndexComment (index)
    comment = ConvertComment (controlProps)
    iconId = ConvertIconId (controlProps.pop ('iconId'))

    # /* [  1] */ IconCheckBox 10 10 100 20 32005 32005 /* comment */
    outputBuilder.AddLine (f"{itemIndexComment} {controlType:<{GDLG_CONTROL_TYPE_WIDTH}} {ConvertRect (controlProps)} {iconId}{comment}")


def ConvertIconMenuCheck (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    itemIndexComment = GetItemIndexComment (index)
    comment = ConvertComment (controlProps)

    iconIds = []
    for item in controlProps.pop ('items', []):
        iconId = ConvertIconId (item.pop ('iconId'))
        iconIds.append (iconId)
        item.pop ('#comment', None) # Comment is not supported here.
        CheckIfAllKeysWereHandled (item)

    iconIdsStr = ' '.join (iconIds)

    bevelType = ConvertBevelType (controlProps, targetAcVersion)

    # /* [  1] */ IconMenuCheck 10 10 100 20 32005 32006 32007 RoundedEdge /* comment */
    outputBuilder.AddLine (f"{itemIndexComment} {controlType:<{GDLG_CONTROL_TYPE_WIDTH}} {ConvertRect (controlProps)} {iconIdsStr} {bevelType} {comment}")


def ConvertIconMenuRadio (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    itemIndexComment = GetItemIndexComment (index)
    comment = ConvertComment (controlProps)

    radioGroupId = controlProps.pop ('groupId')

    iconIds = []
    for item in controlProps.pop ('items', []):
        iconId = ConvertIconId (item.pop ('iconId'))
        iconIds.append (iconId)
        item.pop ('#comment', None) # Comment is not supported here.
        CheckIfAllKeysWereHandled (item)

    iconIdsStr = ' '.join (iconIds)

    bevelType = ConvertBevelType (controlProps, targetAcVersion)

    # /* [  1] */ IconMenuRadio 10 10 100 20 8 32005 32006 32007 RoundedEdge /* comment */
    outputBuilder.AddLine (f"{itemIndexComment} {controlType:<{GDLG_CONTROL_TYPE_WIDTH}} {ConvertRect (controlProps)} {radioGroupId} {iconIdsStr} {bevelType}{comment}")


def ConvertIconPushCheck (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    itemIndexComment = GetItemIndexComment (index)
    comment = ConvertComment (controlProps)
    iconId = ConvertIconId (controlProps.pop ('iconId'))
    frameType = ConvertFrameType (controlProps)
    bevelType = ConvertBevelType (controlProps, targetAcVersion)

    # /* [  1] */ IconPushCheck 10 10 100 20 32005 frame RoundedEdge /* comment */
    outputBuilder.AddLine (f"{itemIndexComment} {controlType:<{GDLG_CONTROL_TYPE_WIDTH}} {ConvertRect (controlProps)} {iconId} {frameType} {bevelType}{comment}")


def ConvertIconPushRadio (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    itemIndexComment = GetItemIndexComment (index)
    comment = ConvertComment (controlProps)
    radioGroupId = controlProps.pop ('groupId', None)
    iconId = ConvertIconId (controlProps.pop ('iconId'))
    bevelType = ConvertBevelType (controlProps, targetAcVersion)

    # /* [  1] */ IconPushRadio 10 10 100 20 8 32005 RoundedEdge /* comment */
    outputBuilder.AddLine (f"{itemIndexComment} {controlType:<{GDLG_CONTROL_TYPE_WIDTH}} {ConvertRect (controlProps)} {radioGroupId} {iconId} {bevelType}{comment}")


def ConvertIconRadioButton (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    itemIndexComment = GetItemIndexComment (index)
    comment = ConvertComment (controlProps)
    radioGroupId = controlProps.pop ('groupId', None)
    iconId = ConvertIconId (controlProps.pop ('iconId'))
    if 'appearance' in controlProps:
        raise UnsupportedGDLGControlError ('IconRadioButton with appearance property is not supported in GRC.')

    # /* [  1] */ IconRadioButton 10 10 100 20 8 32005 /* comment */
    outputBuilder.AddLine (f"{itemIndexComment} {controlType:<{GDLG_CONTROL_TYPE_WIDTH}} {ConvertRect (controlProps)} {radioGroupId} {iconId}{comment}")


def ConvertIntEdit (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    ConvertEditBase (outputBuilder, controlProps, index, controlType, targetAcVersion)


def ConvertLeftText (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    ConvertStaticTextBase (outputBuilder, controlProps, index, controlType, targetAcVersion)


def ConvertChangeFont (controlProps: dict) -> str:
    return MapPropertyToGrc (controlProps.pop ('changeFont', 'yes'), {
        'no': 'noChangeFont',
        'yes': 'changeFont'
    })


def ConvertLengthEditStyles (controlProps: dict) -> str:
    flags = []
    flags.append (ConvertChangeFont (controlProps))
    flags.append (ConvertFrameType (controlProps))
    flags.append (ConvertUpdate (controlProps))
    flags.append (ConvertRelative (controlProps))
    flags.append (ConvertReadOnly (controlProps))
    return ' | '.join (flags)


def ConvertLengthEdit (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    itemIndexComment = GetItemIndexComment (index)
    comment = ConvertComment (controlProps)
    fontSpec = ConvertFontSpec (controlProps)
    lengthEditStyle = ConvertLengthEditStyles (controlProps)
    editMinStr = EscapeString (controlProps.pop ('minValue', ''))
    editMaxStr = EscapeString (controlProps.pop ('maxValue', ''))

    # /* [  1] */ LengthEdit 10 10 100 20 LargePlain noChangeFont | frame | update | relative | editable "0" "100" /* comment */
    outputBuilder.AddLine (f"{itemIndexComment} {controlType:<{GDLG_CONTROL_TYPE_WIDTH}} {ConvertRect (controlProps)} {fontSpec} {lengthEditStyle} {editMinStr} {editMaxStr} {comment}")


def ConvertScroll (scrollStr: str) -> str:
    return MapPropertyToGrc (scrollStr, {
        'no': 'NoScroll',
        'h': 'HScroll',
        'v': 'VScroll',
        'hv': 'HVScroll'
    })


def ConvertMMPointEdit (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    return ConvertEditBase (outputBuilder, controlProps, index, controlType, targetAcVersion)


def ConvertUpdate (controlProps: dict) -> str:
    return MapPropertyToGrc (controlProps.pop ('update', 'delayed'), {
        'no': 'noUpdate',
        'delayed': 'update',
        'instant': 'noDelay'
    })


def ConvertRelative (controlProps: dict) -> str:
    return MapPropertyToGrc (controlProps.pop ('relative', 'no'), {
        'no': 'absolute',
        'yes': 'relative'
    })


def ConvertReadOnly (controlProps: dict) -> str:
    return MapPropertyToGrc (controlProps.pop ('readOnly', 'no'), {
        'no': 'editable',
        'yes': 'readOnly'
    })


def ConvertEditStyles (controlProps: dict) -> str:
    flags = []
    flags.append (ConvertFrameType (controlProps))
    flags.append (ConvertUpdate (controlProps))
    flags.append (ConvertRelative (controlProps))
    flags.append (ConvertReadOnly (controlProps))
    return ' | '.join (flags)


def ConvertMultiLineEdit (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    itemIndexComment = GetItemIndexComment (index)
    comment = ConvertComment (controlProps)
    fontSpec = ConvertFontSpec (controlProps)
    editStyles = ConvertEditStyles (controlProps)
    scrollType = ConvertScroll (controlProps.pop ('scroll', 'no')) # Optional for MultiLineEdit.

    # /* [  1] */ MultiLineEdit 10 10 100 20 LargePlain frame | update | relative | editable NoScroll /* comment */
    outputBuilder.AddLine (f"{itemIndexComment} {controlType:<{GDLG_CONTROL_TYPE_WIDTH}} {ConvertRect (controlProps)} {fontSpec} {editStyles} {scrollType}{comment}")


def ConvertMultiSelList (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    ConvertSelListBase (outputBuilder, controlProps, index, controlType, targetAcVersion)


def ConvertMultiSelListView (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    ConvertListViewBase (outputBuilder, controlProps, index, controlType, targetAcVersion)


def ConvertMultiSelTreeView (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    ConvertTreeViewBase (outputBuilder, controlProps, index, controlType, targetAcVersion)


def ConvertNormalTab (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    itemIndexComment = GetItemIndexComment (index)
    comment = ConvertComment (controlProps)
    
    # /* [  1] */ NormalTab 10 10 100 20 /* comment */
    #             1 32005 "Tab 1" /* tab comment */
    #             2 32006 "Tab 2" /* tab comment */
    outputBuilder.AddLine (f"{itemIndexComment} {controlType:<{GDLG_CONTROL_TYPE_WIDTH}} {ConvertRect (controlProps)}{comment}")

    for item in controlProps.pop ('items'):
        pageId = item.pop ('pageId')
        iconId = ConvertIconId (item.pop ('iconId'))
        text = ConvertToEscapedString (item.pop ('text'))
        itemComment = ConvertComment (item)
        outputBuilder.AddLine (f"            {pageId} {iconId} {text}{itemComment}")
        CheckIfAllKeysWereHandled (item)
    


def ConvertPasswordEdit (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    ConvertTextEditBase (outputBuilder, controlProps, index, controlType, targetAcVersion)


def ConvertPicture (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    itemIndexComment = GetItemIndexComment (index)
    comment = ConvertComment (controlProps)
    iconId = ConvertIconId (controlProps.pop ('iconId'))
    edgeType = ConvertEdgeType (controlProps)

    # /* [  1] */ Picture 10 10 100 20 32005 RoundedEdge /* comment */
    outputBuilder.AddLine (f"{itemIndexComment} {controlType:<{GDLG_CONTROL_TYPE_WIDTH}} {ConvertRect (controlProps)} {iconId} {edgeType}{comment}")


def ConvertPolarAngleEdit (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    return ConvertEditBase (outputBuilder, controlProps, index, controlType, targetAcVersion)


def ConvertPopupControl (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    itemIndexComment = GetItemIndexComment (index)
    comment = ConvertComment (controlProps)

    popupListHeight = controlProps.pop ('listHeight')
    popupTextOffset = controlProps.pop ('textOffset')

    # /* [  1] */ PopupControl 10 10 100 20 80 60 /* comment */
    #             32005 "Item 1" /* item comment */
    #             32006 "Item 2" /* item comment */
    outputBuilder.AddLine (f"{itemIndexComment} {controlType:<{GDLG_CONTROL_TYPE_WIDTH}} {ConvertRect (controlProps)} {popupListHeight} {popupTextOffset}{comment}")

    for item in controlProps.pop ('items', []):
        text = ConvertToEscapedString (item.pop ('text'))
        iconId = ConvertIconId (item.pop ('iconId'))
        itemComment = ConvertComment (item)
        outputBuilder.AddLine (f'            {iconId} {text}{itemComment}')
        CheckIfAllKeysWereHandled (item)


def ConvertPosIntEdit (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int):
    return ConvertEditBase (outputBuilder, controlProps, index, controlType, targetAcVersion)


def ConvertProgressBarFrame (controlProps: dict) -> str:
    return MapPropertyToGrc (controlProps.pop ('frameType', 'staticEdge'), {
        'staticEdge': 'StaticEdge',
        'clientEdge': 'ClientEdge',
        'modalFrame': 'ModalFrame'
    })


def ConvertProgressBar (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    itemIndexComment = GetItemIndexComment (index)
    comment = ConvertComment (controlProps)
    progressBarMinVal = controlProps.pop ('minValue')
    progressBarMaxVal = controlProps.pop ('maxValue')
    progressBarFrame = ConvertProgressBarFrame (controlProps)

    # /* [  1] */ ProgressBar 10 10 100 20 0 100 StaticEdge /* comment */
    outputBuilder.AddLine (f"{itemIndexComment} {controlType:<{GDLG_CONTROL_TYPE_WIDTH}} {ConvertRect (controlProps)} {progressBarMinVal} {progressBarMaxVal} {progressBarFrame}{comment}")


def ConvertPushCheck (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    itemIndexComment = GetItemIndexComment (index)
    comment = ConvertComment (controlProps)
    text = ConvertToEscapedString (controlProps.pop ('text'))
    fontSpec = ConvertFontSpec (controlProps)
    frameType = ConvertFrameType (controlProps)
    bevelType = ConvertBevelType (controlProps, targetAcVersion)

    # /* [  1] */ PushCheck 10 10 100 20 LargePlain frame RoundedEdge "PushCheck Text" /* comment */
    outputBuilder.AddLine (f"{itemIndexComment} {controlType:<{GDLG_CONTROL_TYPE_WIDTH}} {ConvertRect (controlProps)} {fontSpec} {frameType} {bevelType} {text}{comment}")


def ConvertPushRadio (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    itemIndexComment = GetItemIndexComment (index)
    comment = ConvertComment (controlProps)
    text = ConvertToEscapedString (controlProps.pop ('text'))
    fontSpec = ConvertFontSpec (controlProps)
    radioGroupId = controlProps.pop ('groupId')
    bevelType = ConvertBevelType (controlProps, targetAcVersion)

    # /* [  1] */ PushRadio 10 10 100 20 LargePlain 8 RoundedEdge "PushRadio Text" /* comment */
    outputBuilder.AddLine (f"{itemIndexComment} {controlType:<{GDLG_CONTROL_TYPE_WIDTH}} {ConvertRect (controlProps)} {fontSpec} {radioGroupId} {bevelType} {text}{comment}")


def ConvertRadioButton (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    itemIndexComment = GetItemIndexComment (index)
    comment = ConvertComment (controlProps)
    text = ConvertToEscapedString (controlProps.pop ('text'))
    fontSpec = ConvertFontSpec (controlProps)
    radioGroupId = controlProps.pop ('groupId')

    # /* [  1] */ RadioButton 10 10 100 20 LargePlain 8 "RadioButton Text" /* comment */
    outputBuilder.AddLine (f"{itemIndexComment} {controlType:<{GDLG_CONTROL_TYPE_WIDTH}} {ConvertRect (controlProps)} {fontSpec} {radioGroupId} {text}{comment}")


def ConvertRealEdit (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    return ConvertEditBase (outputBuilder, controlProps, index, controlType, targetAcVersion)


def ConvertRichEditStyles (controlProps: dict) -> str:
    flags = []
    flags.append (ConvertFrameType (controlProps))
    flags.append (ConvertReadOnly (controlProps))
    return ' | '.join (flags)


def ConvertRichEdit (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    itemIndexComment = GetItemIndexComment (index)
    comment = ConvertComment (controlProps)
    fontSpec = ConvertFontSpec (controlProps)
    richEditStyles = ConvertRichEditStyles (controlProps)
    scrollType = ConvertScroll (controlProps.pop ('scroll')) # Mandatory for RichEdit.

    # /* [  1] */ RichEdit 10 10 100 20 LargePlain frame | readOnly NoScroll /* comment */
    outputBuilder.AddLine (f"{itemIndexComment} {controlType:<{GDLG_CONTROL_TYPE_WIDTH}} {ConvertRect (controlProps)} {fontSpec} {richEditStyles} {scrollType}{comment}")


def ConvertRightText (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    ConvertStaticTextBase (outputBuilder, controlProps, index, controlType, targetAcVersion)


def ConvertRulerType (controlProps: dict) -> str:
    return MapPropertyToGrc (controlProps.pop ('rulerType'), {
        'editor': 'editor',
        'window': 'window',
        'table': 'table'
    })


def ConvertRuler (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    itemIndexComment = GetItemIndexComment (index)
    comment = ConvertComment (controlProps)

    rulerType = ConvertRulerType (controlProps)

    if rulerType == 'editor' or rulerType == 'table':
        editId = controlProps.pop ('editId')
    else:
        editId = ''

    # /* [  1] */ Ruler 10 10 100 20 editor 8 /* comment */
    outputBuilder.AddLine (f"{itemIndexComment} {controlType:<{GDLG_CONTROL_TYPE_WIDTH}} {ConvertRect (controlProps)} {rulerType} {editId}{comment}")


def ConvertProportional (controlProps: dict) -> str:
    return MapPropertyToGrc (controlProps.pop ('proportional', 'no'), {
        'yes': 'Proportional',
        'no': 'Normal'
    })


def ConvertFocusable (controlProps: dict) -> str:
    return MapPropertyToGrc (controlProps.pop ('focusable', 'yes'), {
        'yes': 'Focusable',
        'no': 'NonFocusable'
    })


def ConvertAutoScroll (controlProps: dict) -> str:
    return MapPropertyToGrc (controlProps.pop ('autoScroll', 'yes'), {
        'yes': 'AutoScroll',
        'no': 'NoAutoScroll'
    })


def ConvertScrollBarStyles (controlProps: dict) -> str:
    flags = []
    flags.append (ConvertProportional (controlProps))
    flags.append (ConvertFocusable (controlProps))
    flags.append (ConvertAutoScroll (controlProps))
    return ' | '.join (flags)


def ConvertScrollBar (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    itemIndexComment = GetItemIndexComment (index)
    comment = ConvertComment (controlProps)
    scrollBarPageSize = controlProps.pop ('pageSize')
    scrollBarMinVal = controlProps.pop ('minValue')
    scrollBarMaxVal = controlProps.pop ('maxValue')
    scrollBarStyles = ConvertScrollBarStyles (controlProps)

    # /* [  1] */ ScrollBar 10 10 100 20 10 0 100 Proportional | Focusable | AutoScroll /* comment */
    outputBuilder.AddLine (f"{itemIndexComment} {controlType:<{GDLG_CONTROL_TYPE_WIDTH}} {ConvertRect (controlProps)} {scrollBarPageSize} {scrollBarMinVal} {scrollBarMaxVal} {scrollBarStyles}{comment}")


def ConvertSeparator (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    itemIndexComment = GetItemIndexComment (index)
    comment = ConvertComment (controlProps)
    
    # /* [  1] */ Separator 10 10 100 20 /* comment */
    outputBuilder.AddLine (f"{itemIndexComment} {controlType:<{GDLG_CONTROL_TYPE_WIDTH}} {ConvertRect (controlProps)}{comment}")


def ConvertShortcutEdit (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    ConvertTextEditBase (outputBuilder, controlProps, index, controlType, targetAcVersion)


def ConvertSimpleTab (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    itemIndexComment = GetItemIndexComment (index)
    comment = ConvertComment (controlProps)
    frameType = ConvertFrameType (controlProps)

    # /* [  1] */ SimpleTab 10 10 100 20 frame /* comment */
    #             1 /* tab comment */
    #             2 /* tab comment */
    outputBuilder.AddLine (f"{itemIndexComment} {controlType:<{GDLG_CONTROL_TYPE_WIDTH}} {ConvertRect (controlProps)} {frameType}{comment}")

    for item in controlProps.pop ('items', []):
        pageId = item.pop ('pageId')
        itemComment = ConvertComment (item)
        outputBuilder.AddLine (f"            {pageId}{itemComment}")
        CheckIfAllKeysWereHandled (item)


def ConvertPartialItems (controlProps: dict) -> str:
    return MapPropertyToGrc (controlProps.pop ('partialItems'), {
        'yes': 'PartialItems',
        'no': 'NoPartialItems'
    })


def ConvertListFlags (controlProps: dict) -> str:
    result = []

    if controlProps.pop ('header', 'no') == 'yes':
        listHeaderHeight = controlProps.pop ('headerHeight')
        result.append (f'HasHeader {listHeaderHeight}')

    if (controlProps.pop ('frame', 'no') == 'yes'):
        result.append ('HasFrame')

    return ' '.join (result)


def ConvertSelListBase (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    itemIndexComment = GetItemIndexComment (index)
    comment = ConvertComment (controlProps)
    fontSpec = ConvertFontSpec (controlProps)
    partialItems = ConvertPartialItems (controlProps)
    scroll = ConvertScroll (controlProps.pop ('scroll', 'v'))
    listItemHeight = controlProps.pop ('itemHeight')
    listFlags = ConvertListFlags (controlProps)

    # /* [  1] */ SingleSelList 10 10 100 20 LargePlain PartialItems HVScroll 80 HasHeader 16 HasFrame /* comment */
    outputBuilder.AddLine (f"{itemIndexComment} {controlType:<{GDLG_CONTROL_TYPE_WIDTH}} {ConvertRect (controlProps)} {fontSpec} {partialItems} {scroll} {listItemHeight} {listFlags}{comment}")


def ConvertSingleSelList (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    ConvertSelListBase (outputBuilder, controlProps, index, controlType, targetAcVersion)


def ConvertListViewTextMode (controlProps: dict) -> str:
    return MapPropertyToGrc (controlProps.pop ('mode'), {
        'bottomText': 'bottomText',
        'rightText': 'rightText',
        'singleColumn': 'singleColumn'
    })


def ConvertListViewFlags (controlProps: dict) -> str:
    result = []
    if controlProps.pop ('scroll', None) == 'no':
        result.append ('NoScroll')

    if (controlProps.pop ('frame', 'no') == 'yes'):
        result.append ('HasFrame')

    return ' '.join (result)


def ConvertListViewBase (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    itemIndexComment = GetItemIndexComment (index)

    comment = ConvertComment (controlProps)

    fontSpec = ConvertFontSpec (controlProps)

    imageSize = controlProps.pop ('imageSize')
    cellSize = controlProps.pop ('cellSize')

    listViewImWidth = imageSize.pop ('w')
    listViewImHeight = imageSize.pop ('h')
    listViewCellWidth = cellSize.pop ('w')
    listViewCellHeight = cellSize.pop ('h')

    CheckIfAllKeysWereHandled (imageSize)
    CheckIfAllKeysWereHandled (cellSize)

    listViewTextMode = ConvertListViewTextMode (controlProps)
    listViewFlags = ConvertListViewFlags (controlProps)

    # /* [  1] */ SingleSelListView 10 10 100 20 LargePlain 100 60 16 16 bottomText NoScroll HasFrame /* comment */
    outputBuilder.AddLine (f"{itemIndexComment} {controlType:<{GDLG_CONTROL_TYPE_WIDTH}} {ConvertRect (controlProps)} {fontSpec} {listViewImWidth} {listViewImHeight} {listViewCellWidth} {listViewCellHeight} {listViewTextMode} {listViewFlags}{comment}")


def ConvertSingleSelListView (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    ConvertListViewBase (outputBuilder, controlProps, index, controlType, targetAcVersion)


def ConvertTreeViewLabelEditFlag (controlProps: dict) -> str:
    return MapPropertyToGrc (controlProps.pop ('editableLabel'), {
        'yes': 'labelEdit',
        'no': 'noLabelEdit'
    })


def ConvertTreeViewDragDropFlag (controlProps: dict) -> str:
    return MapPropertyToGrc (controlProps.pop ('dragDrop'), {
        'yes': 'dragDrop',
        'no': 'noDragDrop'
    })


def ConvertTreeViewFlags (controlProps: dict) -> str:
    flags = []

    if controlProps.pop ('rootButton', 'no') == 'no':
        flags.append ('noRootButton')

    if (controlProps.pop ('frame', 'no') == 'yes'):
        flags.append ('HasFrame')

    return ' '.join (flags)


def ConvertTreeViewBase (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    itemIndexComment = GetItemIndexComment (index)

    comment = ConvertComment (controlProps)

    fontSpec = ConvertFontSpec (controlProps)

    normalIconSize = controlProps.pop ('normalIconSize')
    smallIconSize = controlProps.pop ('stateIconSize')

    tvNormalIconWidth = normalIconSize.pop ('w')
    tvNormalIconHeight = normalIconSize.pop ('h')
    tvSmallIconWidth = smallIconSize.pop ('w')
    tvSmallIconHeight = smallIconSize.pop ('h')

    CheckIfAllKeysWereHandled (normalIconSize)
    CheckIfAllKeysWereHandled (smallIconSize)

    tvLabelEditFlag = ConvertTreeViewLabelEditFlag (controlProps)
    tvDragDropFlag = ConvertTreeViewDragDropFlag (controlProps)
    tvMaxCharCount = controlProps.pop ('maxCharCount')
    tvFlags = ConvertTreeViewFlags (controlProps)

    # /* [  1] */ SingleSelTreeView 10 10 100 20 LargePlain 16 16 16 16 labelEdit dragDrop 80 noRootButton HasFrame /* comment */
    outputBuilder.AddLine (f"{itemIndexComment} {controlType:<{GDLG_CONTROL_TYPE_WIDTH}} {ConvertRect (controlProps)} {fontSpec} {tvNormalIconWidth} {tvNormalIconHeight} {tvSmallIconWidth} {tvSmallIconHeight} {tvLabelEditFlag} {tvDragDropFlag} {tvMaxCharCount} {tvFlags}{comment}")


def ConvertSingleSelTreeView (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    ConvertTreeViewBase (outputBuilder, controlProps, index, controlType, targetAcVersion)


def ConvertSingleSpin (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    itemIndexComment = GetItemIndexComment (index)
    comment = ConvertComment (controlProps)
    spinMinIntValue = controlProps.pop ('minValue')
    spinMaxIntValue = controlProps.pop ('maxValue')

    # /* [  1] */ SingleSpin 10 10 100 20 0 100 /* comment */
    outputBuilder.AddLine (f"{itemIndexComment} {controlType:<{GDLG_CONTROL_TYPE_WIDTH}} {ConvertRect (controlProps)} {spinMinIntValue} {spinMaxIntValue}{comment}")


def ConvertSliderStyle (s: str) -> str:
    return MapPropertyToGrc (s, {
        'BottomRight': 'BottomRight',
        'TopLeft': 'TopLeft'
    })


def ConvertSlider (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    itemIndexComment = GetItemIndexComment (index)
    comment = ConvertComment (controlProps)
    sliderStepValue = controlProps.pop ('stepValue')
    sliderMinValue = controlProps.pop ('minValue')
    sliderMaxValue = controlProps.pop ('maxValue')
    sliderStyle = ConvertSliderStyle (controlProps.pop ('sliderStyle', 'BottomRight'))

    # /* [  1] */ Slider 10 10 100 20 1 0 100 BottomRight /* comment */
    outputBuilder.AddLine (f"{itemIndexComment} {controlType:<{GDLG_CONTROL_TYPE_WIDTH}} {ConvertRect (controlProps)} {sliderStepValue} {sliderMinValue} {sliderMaxValue} {sliderStyle} {comment}")


def ConvertSplitButton (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    itemIndexComment = GetItemIndexComment (index)
    comment = ConvertComment (controlProps)
    text = ConvertToEscapedString (controlProps.pop ('text'))
    fontSpec = ConvertFontSpec (controlProps)
    buttonBevelType = ConvertBevelType (controlProps, targetAcVersion)
    iconId = ConvertIconId (controlProps.pop ('iconId'))

    # /* [  1] */ SplitButton 10 10 100 20 LargePlain RoundedEdge 32005 "SplitButton Text" /* comment */
    outputBuilder.AddLine (f"{itemIndexComment} {controlType:<{GDLG_CONTROL_TYPE_WIDTH}} {ConvertRect (controlProps)} {fontSpec} {buttonBevelType} {iconId} {text}{comment}")


def ConvertSplitterType (controlProps: dict) -> str:
    return MapPropertyToGrc (controlProps.pop ('splitterType', 'normal'), {
        'normal': 'Normal',
        'transparent': 'Transparent'
    })


def ConvertSplitter (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    itemIndexComment = GetItemIndexComment (index)
    comment = ConvertComment (controlProps)
    splitterType = ConvertSplitterType (controlProps)

    # /* [  1] */ Splitter 10 10 100 20 Normal /* comment */
    outputBuilder.AddLine (f"{itemIndexComment} {controlType:<{GDLG_CONTROL_TYPE_WIDTH}} {ConvertRect (controlProps)} {splitterType}{comment}")


def ConvertTabBar (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    itemIndexComment = GetItemIndexComment (index)
    comment = ConvertComment (controlProps)
    
    # /* [  1] */ TabBar 10 10 100 20 /* comment */
    outputBuilder.AddLine (f"{itemIndexComment} {controlType:<{GDLG_CONTROL_TYPE_WIDTH}} {ConvertRect (controlProps)}{comment}")


def ConvertTextEditBase (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    itemIndexComment = GetItemIndexComment (index)
    comment = ConvertComment (controlProps)
    fontSpec = ConvertFontSpec (controlProps)
    editStyles = ConvertEditStyles (controlProps)
    maxCharCount = controlProps.pop ('maxCharCount')

    # /* [  1] */ TextEdit 10 10 100 20 LargePlain frame | update | relative | editable 80 /* comment */
    outputBuilder.AddLine (f"{itemIndexComment} {controlType:<{GDLG_CONTROL_TYPE_WIDTH}} {ConvertRect (controlProps)} {fontSpec} {editStyles} {maxCharCount}{comment}")


def ConvertTextEdit (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    ConvertTextEditBase (outputBuilder, controlProps, index, controlType, targetAcVersion)


def ConvertTimeControl (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    itemIndexComment = GetItemIndexComment (index)
    comment = ConvertComment (controlProps)
    
    # /* [  1] */ TimeControl 10 10 100 20 /* comment */
    outputBuilder.AddLine (f"{itemIndexComment} {controlType:<{GDLG_CONTROL_TYPE_WIDTH}} {ConvertRect (controlProps)}{comment}")


def ConvertResize (controlProps: dict) -> str:
    return MapPropertyToGrc (controlProps.pop ('resize', 'auto'), {
        'auto': 'autoResize',
        'noAuto': 'noAutoResize'
    })


def ConvertWrap (controlProps: dict) -> str:
    return MapPropertyToGrc (controlProps.pop ('wrap', 'eof'), {
        'word': 'wordWrap',
        'eof': 'eofWrap'
    })


def ConvertUniRichEditStyles (controlProps: dict) -> str:
    flags = []
    flags.append (ConvertResize (controlProps))
    flags.append (ConvertWrap (controlProps))
    flags.append (ConvertFrameType (controlProps))
    flags.append (ConvertReadOnly (controlProps))
    return ' | '.join (flags)


def ConvertUniRichEdit (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    itemIndexComment = GetItemIndexComment (index)
    comment = ConvertComment (controlProps)
    fontSpec = ConvertFontSpec (controlProps)
    unirichEditStyles = ConvertUniRichEditStyles (controlProps)
    scrollType = ConvertScroll (controlProps.pop ('scroll')) # Mandatory for UniRichEdit.

    # /* [  1] */ UniRichEdit 10 10 100 20 LargePlain autoResize | wordWrap NoScroll /* comment */
    outputBuilder.AddLine (f"{itemIndexComment} {controlType:<{GDLG_CONTROL_TYPE_WIDTH}} {ConvertRect (controlProps)} {fontSpec} {unirichEditStyles} {scrollType}{comment}")


def ConvertDataBytes (dataBytes: list) -> str:
    result = []
    for num in dataBytes:
        result.append (f"0x{num:04X}")
    return ' '.join (result)


def ConvertUserControl (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    itemIndexComment = GetItemIndexComment (index)
    comment = ConvertComment (controlProps)
    ucId = controlProps.pop ('ucId')
    dataBytesStr = ConvertDataBytes (controlProps.pop ('data')) if 'data' in controlProps else ''
    frameType = ConvertFrameType (controlProps)
    bevelType = ConvertBevelType (controlProps, targetAcVersion)

    # /* [  1] */ UserControl 10 10 100 20 257 0x0005 0x0600 0 RoundedEdge /* comment */
    outputBuilder.AddLine (f"{itemIndexComment} {controlType:<{GDLG_CONTROL_TYPE_WIDTH}} {ConvertRect (controlProps)} {ucId} {dataBytesStr} {frameType} {bevelType}{comment}")


def ConvertPartialUpdate (controlProps: dict) -> str:
    return MapPropertyToGrc (controlProps.pop ('partialUpdate', 'no'), {
        'yes': 'PartialUpdate',
        'no': ''
    })


def ConvertUserItem (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    itemIndexComment = GetItemIndexComment (index)
    comment = ConvertComment (controlProps)
    partialUpdate = ConvertPartialUpdate (controlProps)
    edgeType = ConvertEdgeType (controlProps)

    # /* [  1] */ UserItem 10 10 100 20 PartialItems StaticEdge /* comment */
    outputBuilder.AddLine (f"{itemIndexComment} {controlType:<{GDLG_CONTROL_TYPE_WIDTH}} {ConvertRect (controlProps)} {partialUpdate} {edgeType}{comment}")


def ConvertVolumeEdit (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    return ConvertEditBase (outputBuilder, controlProps, index, controlType, targetAcVersion)


def ConvertMMInchEdit (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    return ConvertEditBase (outputBuilder, controlProps, index, controlType, targetAcVersion)


def ConvertSAMQuantityEdit (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    return ConvertEditBase (outputBuilder, controlProps, index, controlType, targetAcVersion)


def ConvertSearchEdit (outputBuilder: GrcOutputBuilder, controlProps: dict, index: int, controlType: str, targetAcVersion: int) -> None:
    return ConvertTextEditBase (outputBuilder, controlProps, index, controlType, targetAcVersion)


def ConvertGDLGControl (outputBuilder: GrcOutputBuilder, control: dict, index: int, targetAcVersion: int) -> None:
    controlType = list (control.keys ())[0]
    controlProps = control[controlType]

    controlConverterMapping = {
        'AngleEdit': ConvertAngleEdit,
        'AreaEdit': ConvertAreaEdit,
        'Browser': ConvertBrowser,
        'Button': ConvertButton,
        'CenterText': ConvertCenterText,
        'CheckBox': ConvertCheckBox,
        'DateControl': ConvertDateControl,
        'EditSpin': ConvertEditSpin,
        'GroupBox': ConvertGroupBox,
        'Icon': ConvertIcon,
        'IconButton': ConvertIconButton,
        'IconCheckBox': ConvertIconCheckBox,
        'IconMenuCheck': ConvertIconMenuCheck,
        'IconMenuRadio': ConvertIconMenuRadio,
        'IconPushCheck': ConvertIconPushCheck,
        'IconPushRadio': ConvertIconPushRadio,
        'IconRadioButton': ConvertIconRadioButton,
        'IntEdit': ConvertIntEdit,
        'LeftText': ConvertLeftText,
        'LengthEdit': ConvertLengthEdit,
        'MMPointEdit': ConvertMMPointEdit,
        'MultiLineEdit': ConvertMultiLineEdit,
        'MultiSelList': ConvertMultiSelList,
        'MultiSelListView': ConvertMultiSelListView,
        'MultiSelTreeView': ConvertMultiSelTreeView,
        'NormalTab': ConvertNormalTab,
        'PasswordEdit': ConvertPasswordEdit,
        'Picture': ConvertPicture,
        'PolarAngleEdit': ConvertPolarAngleEdit,
        'PopupControl': ConvertPopupControl,
        'PosIntEdit': ConvertPosIntEdit,
        'ProgressBar': ConvertProgressBar,
        'PushCheck': ConvertPushCheck,
        'PushRadio': ConvertPushRadio,
        'RadioButton': ConvertRadioButton,
        'RealEdit': ConvertRealEdit,
        'RichEdit': ConvertRichEdit,
        'RightText': ConvertRightText,
        'Ruler': ConvertRuler,
        'ScrollBar': ConvertScrollBar,
        'Separator': ConvertSeparator,
        'ShortcutEdit': ConvertShortcutEdit,
        'SimpleTab': ConvertSimpleTab,
        'SingleSelList': ConvertSingleSelList,
        'SingleSelListView': ConvertSingleSelListView,
        'SingleSelTreeView': ConvertSingleSelTreeView,
        'SingleSpin': ConvertSingleSpin,
        'Slider': ConvertSlider,
        'SplitButton': ConvertSplitButton,
        'Splitter': ConvertSplitter,
        'TabBar': ConvertTabBar,
        'TextEdit': ConvertTextEdit,
        'TimeControl': ConvertTimeControl,
        'UniRichEdit': ConvertUniRichEdit,
        'UserControl': ConvertUserControl,
        'UserItem': ConvertUserItem,
        'VolumeEdit': ConvertVolumeEdit,
        'SearchEdit': ConvertSearchEdit,
        'MMInchEdit': ConvertMMInchEdit,
        'SAMQuantityEdit': ConvertSAMQuantityEdit,
    }

    if controlType not in controlConverterMapping:
        raise UnsupportedGDLGControlError (controlType)

    condition = controlProps.pop ('#condition', None)
    if condition:
        outputBuilder.AddLine (GetConditionAsIfDef (condition))

    controlConverterMapping[controlType](outputBuilder, controlProps, index, controlType, targetAcVersion)

    if condition:
        outputBuilder.AddLine (GetConditionEnd ())
