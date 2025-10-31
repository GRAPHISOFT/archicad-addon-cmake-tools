from .Common import (
    ConvertComment,
    ConvertToEscapedString,
    GetConditionAsIfDef,
    GetConditionEnd,
    GrcOutputBuilder,
)


def ConvertFILE (outputBuilder: GrcOutputBuilder, resource: dict, targetAcVersion: int) -> None:
    resId = resource.pop ('#id')
    name = ConvertToEscapedString (resource.pop ('name'))
    fileName = ConvertToEscapedString (resource.pop ('fileName'))
    comment = ConvertComment (resource)
    
    condition = resource.pop ('#condition', None)
    if condition:
        outputBuilder.AddLine (GetConditionAsIfDef (condition))
    
    outputBuilder.AddLine (f"'FILE' {resId} {name} {{{comment}")
    outputBuilder.AddLine (f"    {fileName}")
    outputBuilder.AddLine ('}')

    if condition:
        outputBuilder.AddLine (GetConditionEnd ())
