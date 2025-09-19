from .Common import (
    CheckIfAllKeysWereHandled,
    CMND_ICONID_WIDTH,
    CMND_ID_WIDTH,
    CMND_TEXT_WIDTH,
    ConvertComment,
    ConvertIconId,
    ConvertToEscapedString,
    GetConditionAsIfDef,
    GetConditionEnd,
    GrcOutputBuilder,
)


def ConvertCMND (outputBuilder: GrcOutputBuilder, resource: dict, targetAcVersion: int) -> None:
    resId = resource.pop ('#id')
    name = ConvertToEscapedString (resource.pop ('name'))

    resourceCondition = resource.pop ('#condition', None)
    if resourceCondition:
        outputBuilder.AddLine (GetConditionAsIfDef (resourceCondition))

    outputBuilder.AddLine (f'\'CMND\' {resId} {name} {{')
    
    commands = resource.pop ('commands')
    for cmd in commands:
        cmdId = cmd.pop ('#id')
        iconId = ConvertIconId (cmd.pop ('iconId', 'noIcon'))
        if iconId == 'NoIcon':
            iconId = 'noIcon'
        items = cmd.pop ('items')
        itemCondition = cmd.pop ('#condition', None)

        if itemCondition:
            outputBuilder.AddLine (GetConditionAsIfDef (itemCondition))

        for i, item in enumerate (items):
            text = ConvertToEscapedString (item.pop ('text'))
            description = ConvertToEscapedString (item.pop ('description'))
            itemComment = ConvertComment (item)
            
            if i == 0:
                outputBuilder.AddLine (f'    {cmdId:<{CMND_ID_WIDTH}} {iconId:<{CMND_ICONID_WIDTH}} {text:<{CMND_TEXT_WIDTH}} {description}{itemComment}')
            else:
                outputBuilder.AddLine (f'    {" ":<{CMND_ID_WIDTH}} {" ":<{CMND_ICONID_WIDTH}} {text:<{CMND_TEXT_WIDTH}} {description}{itemComment}')
            CheckIfAllKeysWereHandled (item)
        
        if itemCondition:
            outputBuilder.AddLine (GetConditionEnd ())

        CheckIfAllKeysWereHandled (cmd)

    outputBuilder.AddLine ('}')

    if resourceCondition:
        outputBuilder.AddLine (GetConditionEnd ())
