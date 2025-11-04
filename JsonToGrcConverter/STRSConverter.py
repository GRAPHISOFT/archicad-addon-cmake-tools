from .Common import (
    CheckIfAllKeysWereHandled,
    ConvertComment,
    ConvertToEscapedString,
    FormatComment,
    GetConditionAsIfDef,
    GetConditionEnd,
    GrcOutputBuilder,
)

def ConvertSTRS (outputBuilder: GrcOutputBuilder, resource: dict, targetAcVersion: int) -> None:
    resource.pop ('localized', None) # No equivalent in GRC.
    resId = resource.pop ('#id')
    comment = ConvertComment (resource)

    name = ConvertToEscapedString (resource.pop ('name'))

    resourceCondition = resource.pop ('#condition', None)
    if resourceCondition:
        outputBuilder.AddLine (GetConditionAsIfDef (resourceCondition))

    outputBuilder.AddLine (f'\'STR#\' {resId} {name} {{{comment}')

    items = resource.pop ('items')
    for item in items:
        itemId = item.pop ('#id')
        textObj = item.pop ('text')
        itemId = FormatComment (f'[{itemId:>3}]')
        text = ConvertToEscapedString (textObj)
        itemComment = ConvertComment (item)
        
        itemCondition = item.pop ('#condition', None)
        if itemCondition:
            outputBuilder.AddLine (GetConditionAsIfDef (itemCondition))

        outputBuilder.AddLine (f'{itemId} {text}{itemComment}')

        if itemCondition:
            outputBuilder.AddLine (GetConditionEnd ())

        CheckIfAllKeysWereHandled (item)

    CheckIfAllKeysWereHandled (resource)

    outputBuilder.AddLine ('}')

    if resourceCondition:
        outputBuilder.AddLine (GetConditionEnd ())
