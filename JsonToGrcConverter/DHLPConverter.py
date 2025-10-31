from .Common import (
    CheckIfAllKeysWereHandled,
    ConvertComment,
    ConvertToEscapedString,
    GDLH_TOOLTIP_WIDTH,
    GetConditionAsIfDef,
    GetConditionEnd,
    GetItemIndexComment,
    GrcOutputBuilder,
)


def ConvertDHLP (outputBuilder: GrcOutputBuilder, resource: dict, targetAcVersion: int) -> None:
    resource.pop ('localized', None) # Has no equivalent in GRC.
    resId = resource.pop ('#id')
    items = resource.pop ('items')
    comment  = ConvertComment (resource)

    condition = resource.pop ('#condition', None)
    if condition:
        outputBuilder.AddLine (GetConditionAsIfDef (condition))

    outputBuilder.AddLine (f'\'DHLP\' {resId} {{{comment}')
    for index, item in enumerate (items):
        itemIndexComment = GetItemIndexComment (index)
        strValue = ConvertToEscapedString (item.pop ('tooltipStr'))
        anchorStr = item.pop ('anchorStr')
        assert isinstance (strValue, str)
        assert isinstance (anchorStr, str)
        itemComment = ConvertComment (item)
        outputBuilder.AddLine (f"{itemIndexComment} {strValue:<{GDLH_TOOLTIP_WIDTH}} {anchorStr}{itemComment}")
        CheckIfAllKeysWereHandled (item)
    outputBuilder.AddLine ('}')

    if condition:
        outputBuilder.AddLine (GetConditionEnd ())
