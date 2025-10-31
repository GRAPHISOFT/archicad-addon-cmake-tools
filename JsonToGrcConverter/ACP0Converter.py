from .Common import (
    GrcOutputBuilder,
    ConvertToEscapedString,
    CheckIfAllKeysWereHandled,
    ConvertComment,
    GetConditionAsIfDef,
    GetConditionEnd,
)


def ConvertACP0 (outputBuilder: GrcOutputBuilder, resource: dict, targetAcVersion: int) -> None:
    resId = resource.pop ('#id')
    name = ConvertToEscapedString (resource.pop ('name'))
    comment = ConvertComment (resource)

    resource.pop ('localized', None) # Has no equivalent in GRC.

    condition = resource.pop ('#condition', None)
    if condition:
        outputBuilder.AddLine (GetConditionAsIfDef (condition))

    outputBuilder.AddLine (f"'ACP0' {resId} {name}{{{comment}")

    for item in resource.pop ('items'):
        id = item.pop ('#id')
        itemComment = ConvertComment (item)
        varName = ConvertToEscapedString (item.pop ('varName'))
        value = ConvertToEscapedString (item.pop ('value'))
        outputBuilder.AddLine (f"    /* [{id:>3}] VarName  */ {varName}{itemComment}")
        outputBuilder.AddLine (f"    /* [{id:>3}] Value    */ {value}{itemComment}")
        CheckIfAllKeysWereHandled (item)

    outputBuilder.AddLine ('}')

    if condition:
        outputBuilder.AddLine (GetConditionEnd ())
